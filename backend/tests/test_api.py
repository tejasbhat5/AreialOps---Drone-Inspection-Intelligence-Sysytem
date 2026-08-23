from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.main import app
from app.models.enums import JobStatus, JobType, ReportIngestionStatus
from app.models.inspection_report import InspectionReport
from app.models.processing_job import ProcessingJob
from app.models.report_chunk import ReportChunk
from app.rag.embedding_service import LocalHashEmbeddingService
from tests.conftest import APIHarness


def site_payload(name: str = "API Solar Site") -> dict[str, object]:
    return {
        "name": name,
        "site_type": "SOLAR_FARM",
        "location": "Synthetic API location",
        "latitude": 26.91,
        "longitude": 75.78,
        "status": "ACTIVE",
    }


def create_site(client: APIHarness, name: str = "API Solar Site") -> dict[str, object]:
    response = client.request("POST", "/api/sites", json=site_payload(name))
    assert response.status_code == 201
    return response.json()


def inspection_payload(site_id: str, status: str = "COMPLETED") -> dict[str, object]:
    return {
        "site_id": site_id,
        "inspected_at": datetime.now(UTC).isoformat(),
        "status": status,
        "notes": "Created through the Phase 3 API test.",
        "anomalies": [
            {
                "title": "Panel hotspot",
                "description": "Elevated temperature in array three.",
                "severity": "HIGH",
            },
            {
                "title": "Vegetation encroachment",
                "description": "Vegetation is approaching the access path.",
                "severity": "MODERATE",
            },
        ],
    }


def test_site_crud_filtering_and_error_contract(api_client: APIHarness) -> None:
    created = create_site(api_client)
    site_id = str(created["id"])

    listed = api_client.request("GET", "/api/sites", params={"query": "solar", "risk_level": "LOW"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == site_id

    detail = api_client.request("GET", f"/api/sites/{site_id}")
    assert detail.status_code == 200
    assert detail.json()["inspection_count"] == 0
    assert detail.json()["unresolved_anomaly_count"] == 0

    updated = api_client.request(
        "PATCH", f"/api/sites/{site_id}", json={"location": "Updated location"}
    )
    assert updated.status_code == 200
    assert updated.json()["location"] == "Updated location"

    duplicate = api_client.request("POST", "/api/sites", json=site_payload("api solar site"))
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "site_name_conflict"
    assert duplicate.json()["error"]["request_id"]

    malformed = api_client.request("GET", "/api/sites/not-a-uuid")
    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "validation_error"

    missing = api_client.request("GET", f"/api/sites/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "site_not_found"


def test_inspection_creation_is_atomic_and_queryable(api_client: APIHarness) -> None:
    site = create_site(api_client)
    site_id = str(site["id"])

    created = api_client.request("POST", "/api/inspections", json=inspection_payload(site_id))
    assert created.status_code == 201
    inspection = created.json()
    assert inspection["site_id"] == site_id
    assert len(inspection["anomalies"]) == 2
    assert {item["status"] for item in inspection["anomalies"]} == {"OPEN"}

    site_history = api_client.request("GET", f"/api/sites/{site_id}/inspections")
    assert site_history.status_code == 200
    assert site_history.json()["total"] == 1

    unresolved = api_client.request(
        "GET", f"/api/sites/{site_id}/anomalies", params={"unresolved_only": True}
    )
    assert unresolved.status_code == 200
    assert unresolved.json()["total"] == 2

    detail = api_client.request("GET", f"/api/sites/{site_id}")
    assert detail.json()["inspection_count"] == 1
    assert detail.json()["unresolved_anomaly_count"] == 2
    assert detail.json()["current_risk_score"] == 24
    assert detail.json()["current_risk_level"] == "LOW"

    risk = api_client.request("GET", f"/api/sites/{site_id}/risk")
    assert risk.status_code == 200
    assert risk.json()["formula_version"] == "deterministic-v1"
    assert risk.json()["factor_snapshot"]["severity_points"] == 18
    assert risk.json()["factor_snapshot"]["volume_points"] == 6


def test_inspection_creation_rolls_back_for_missing_site(api_client: APIHarness) -> None:
    response = api_client.request("POST", "/api/inspections", json=inspection_payload(str(uuid4())))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "site_not_found"

    inspections = api_client.request("GET", "/api/inspections")
    assert inspections.status_code == 200
    assert inspections.json()["total"] == 0


def test_inspection_status_transitions_are_controlled(api_client: APIHarness) -> None:
    site = create_site(api_client)
    payload = inspection_payload(str(site["id"]), status="SCHEDULED")
    payload["anomalies"] = []
    inspection = api_client.request("POST", "/api/inspections", json=payload).json()
    inspection_id = inspection["id"]

    invalid = api_client.request(
        "PATCH", f"/api/inspections/{inspection_id}", json={"status": "COMPLETED"}
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "invalid_inspection_transition"

    started = api_client.request(
        "PATCH", f"/api/inspections/{inspection_id}", json={"status": "IN_PROGRESS"}
    )
    assert started.status_code == 200
    completed = api_client.request(
        "PATCH", f"/api/inspections/{inspection_id}", json={"status": "COMPLETED"}
    )
    assert completed.status_code == 200


def test_anomaly_resolution_timestamp_and_transition(api_client: APIHarness) -> None:
    site = create_site(api_client)
    inspection = api_client.request(
        "POST", "/api/inspections", json=inspection_payload(str(site["id"]))
    ).json()
    anomaly_id = inspection["anomalies"][0]["id"]
    site_id = str(site["id"])
    assert api_client.request("GET", f"/api/sites/{site_id}").json()["current_risk_score"] == 24

    resolved = api_client.request(
        "PATCH", f"/api/anomalies/{anomaly_id}", json={"status": "RESOLVED"}
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"
    assert resolved.json()["resolved_at"] is not None
    assert api_client.request("GET", f"/api/sites/{site_id}").json()["current_risk_score"] == 9

    invalid = api_client.request(
        "PATCH", f"/api/anomalies/{anomaly_id}", json={"status": "ACKNOWLEDGED"}
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "invalid_anomaly_transition"

    reopened = api_client.request("PATCH", f"/api/anomalies/{anomaly_id}", json={"status": "OPEN"})
    assert reopened.status_code == 200
    assert reopened.json()["resolved_at"] is None
    assert api_client.request("GET", f"/api/sites/{site_id}").json()["current_risk_score"] == 24

    history = api_client.request("GET", f"/api/sites/{site_id}/risk/history")
    assert history.status_code == 200
    assert [item["score"] for item in history.json()][:3] == [24, 9, 24]


def test_assistant_compares_sites_and_persists_safe_audit(api_client: APIHarness) -> None:
    first = create_site(api_client, "Agent Solar Alpha")
    second = create_site(api_client, "Agent Solar Beta")

    for site, critical_count in ((first, 3), (second, 2)):
        payload = inspection_payload(str(site["id"]))
        payload["anomalies"] = [
            {
                "title": f"Critical finding {index + 1}",
                "description": "Requires prioritized engineering review.",
                "severity": "CRITICAL",
            }
            for index in range(critical_count)
        ]
        created = api_client.request("POST", "/api/inspections", json=payload)
        assert created.status_code == 201

    response = api_client.request(
        "POST",
        "/api/assistant/query",
        json={"message": "Compare the two highest-risk sites"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["response_type"] == "site_comparison"
    assert result["provider"] == "deterministic-local"
    assert len(result["data"]["sites"]) == 2
    assert [activity["tool_name"] for activity in result["tool_activity"]] == [
        "find_high_risk_sites",
        "compare_sites",
    ]

    conversation = api_client.request(
        "GET", f"/api/assistant/conversations/{result['conversation_id']}"
    )
    assert conversation.status_code == 200
    messages = conversation.json()["messages"]
    assert [message["role"] for message in messages] == ["USER", "ASSISTANT"]
    assert len(messages[1]["tool_audit"]) == 2
    assert "reasoning" not in messages[1]["structured_payload"]


def test_assistant_resolves_named_site_before_generic_risk_intent(
    api_client: APIHarness,
) -> None:
    site = create_site(api_client, "Named Risk Site")
    response = api_client.request(
        "POST",
        "/api/assistant/query",
        json={"message": "Why is Named Risk Site high risk?"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["response_type"] == "risk_explanation"
    assert result["data"]["site_id"] == site["id"]
    assert [item["tool_name"] for item in result["tool_activity"]] == [
        "search_sites",
        "calculate_site_risk",
    ]


def test_assistant_suggested_highest_risk_prompt_runs_directly(
    api_client: APIHarness,
) -> None:
    site = create_site(api_client, "Suggested Prompt Site")
    payload = inspection_payload(str(site["id"]))
    payload["anomalies"] = [
        {
            "title": f"Critical suggested finding {index + 1}",
            "description": "Requires immediate review.",
            "severity": "CRITICAL",
        }
        for index in range(2)
    ]
    assert api_client.request("POST", "/api/inspections", json=payload).status_code == 201

    response = api_client.request(
        "POST",
        "/api/assistant/query",
        json={"message": "Show the highest-risk sites"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["response_type"] == "high_risk_sites"
    assert result["data"]["sites"][0]["id"] == site["id"]
    assert [item["tool_name"] for item in result["tool_activity"]] == ["find_high_risk_sites"]


def test_assistant_required_critical_sites_wording(api_client: APIHarness) -> None:
    response = api_client.request(
        "POST",
        "/api/assistant/query",
        json={"message": "Which sites are critical?"},
    )
    assert response.status_code == 200
    assert response.json()["response_type"] == "high_risk_sites"
    assert response.json()["tool_activity"][0]["tool_name"] == "find_high_risk_sites"


def test_report_search_api_and_assistant_return_grounded_citations(
    api_client: APIHarness,
) -> None:
    site = create_site(api_client, "Grounded Report Site")
    inspection = api_client.request(
        "POST", "/api/inspections", json=inspection_payload(str(site["id"]))
    ).json()
    text = "Thermal survey found a recurring inverter hotspot near the western service road."
    with api_client.session() as session:
        report = InspectionReport(
            inspection_id=UUID(inspection["id"]),
            storage_key=f"reports/{uuid4()}.pdf",
            original_filename="grounded-report.pdf",
            content_type="application/pdf",
            size_bytes=256,
            ingestion_status=ReportIngestionStatus.COMPLETED,
            extracted_text=text,
        )
        session.add(report)
        session.flush()
        session.add(
            ReportChunk(
                report_id=report.id,
                chunk_index=0,
                content=text,
                token_count=len(text.split()),
                embedding=LocalHashEmbeddingService().embed(text),
            )
        )
        session.commit()

    listed = api_client.request("GET", "/api/reports")
    assert listed.status_code == 200
    assert listed.json()[0]["site_name"] == "Grounded Report Site"
    assert listed.json()[0]["chunk_count"] == 1

    searched = api_client.request(
        "POST", "/api/reports/search", json={"query": "inverter hotspot western road"}
    )
    assert searched.status_code == 200
    assert searched.json()["total"] == 1
    assert searched.json()["citations"][0]["report_filename"] == "grounded-report.pdf"

    assistant = api_client.request(
        "POST",
        "/api/assistant/query",
        json={"message": "What does the report say for Grounded Report Site?"},
    )
    assert assistant.status_code == 200
    assert assistant.json()["response_type"] == "report_summary"
    assert assistant.json()["data"]["citations"][0]["site_id"] == site["id"]


def test_job_status_and_retry_contract(api_client: APIHarness) -> None:
    site = create_site(api_client, "Retry Job Site")
    inspection = api_client.request(
        "POST", "/api/inspections", json=inspection_payload(str(site["id"]))
    ).json()
    with api_client.session() as session:
        report = InspectionReport(
            inspection_id=UUID(inspection["id"]),
            storage_key=f"reports/{uuid4()}.pdf",
            original_filename="failed.pdf",
            content_type="application/pdf",
            size_bytes=100,
            ingestion_status=ReportIngestionStatus.FAILED,
        )
        session.add(report)
        session.flush()
        job = ProcessingJob(
            job_type=JobType.REPORT_INGESTION,
            status=JobStatus.FAILED,
            report_id=report.id,
            attempts=1,
            error_code="report_extraction_failed",
            error_message="Background processing failed safely.",
        )
        session.add(job)
        session.commit()
        job_id = job.id

    status_response = api_client.request("GET", f"/api/jobs/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "FAILED"

    retry = api_client.request("POST", f"/api/jobs/{job_id}/retry")
    assert retry.status_code == 200
    assert retry.json()["status"] == "PENDING"

    missing = api_client.request("GET", f"/api/jobs/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "job_not_found"


def test_assistant_unknown_conversation_has_standard_error(api_client: APIHarness) -> None:
    response = api_client.request(
        "POST",
        "/api/assistant/query",
        json={"conversation_id": str(uuid4()), "message": "Show high-risk sites"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"


def test_assistant_capabilities_reports_safe_local_default(api_client: APIHarness) -> None:
    response = api_client.request("GET", "/api/assistant/capabilities")
    assert response.status_code == 200
    assert response.json() == {
        "active_provider": "deterministic-local",
        "model": None,
        "model_configured": False,
        "deterministic_fallback": True,
        "max_tool_calls": 4,
        "max_model_rounds": 4,
    }


def test_explicit_risk_recalculation_and_missing_site(api_client: APIHarness) -> None:
    site = create_site(api_client, "Explicit Risk Site")
    site_id = str(site["id"])

    empty = api_client.request("GET", f"/api/sites/{site_id}/risk")
    assert empty.status_code == 200
    assert empty.json() is None

    recalculated = api_client.request("POST", f"/api/sites/{site_id}/risk/recalculate")
    assert recalculated.status_code == 200
    assert recalculated.json()["score"] == 10
    assert recalculated.json()["level"] == "LOW"
    assert recalculated.json()["factor_snapshot"]["days_since_completed_inspection"] is None

    missing = api_client.request("POST", f"/api/sites/{uuid4()}/risk/recalculate")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "site_not_found"


def test_dashboard_summary_uses_database_aggregates(api_client: APIHarness) -> None:
    first = create_site(api_client, "Dashboard Site One")
    create_site(api_client, "Dashboard Site Two")
    api_client.request("POST", "/api/inspections", json=inspection_payload(str(first["id"])))

    response = api_client.request("GET", "/api/dashboard/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["metrics"]["total_sites"] == 2
    assert summary["metrics"]["active_sites"] == 2
    assert summary["metrics"]["inspections_this_month"] == 1
    assert summary["metrics"]["unresolved_anomalies"] == 2
    assert len(summary["recent_inspections"]) == 1


def test_unknown_request_fields_are_rejected(api_client: APIHarness) -> None:
    payload = site_payload()
    payload["risk_score"] = 99

    response = api_client.request("POST", "/api/sites", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_invalid_date_range_returns_bad_request(api_client: APIHarness) -> None:
    response = api_client.request(
        "GET",
        "/api/inspections",
        params={
            "date_from": "2026-08-22T00:00:00Z",
            "date_to": "2026-08-01T00:00:00Z",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_date_range"


def test_inspection_requires_timezone_aware_date(api_client: APIHarness) -> None:
    site = create_site(api_client)
    payload = inspection_payload(str(site["id"]))
    payload["inspected_at"] = "2026-08-22T10:00:00"

    response = api_client.request("POST", "/api/inspections", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_openapi_contains_phase_three_routes() -> None:
    paths = app.openapi()["paths"]
    assert {
        "/api/sites",
        "/api/sites/{site_id}",
        "/api/sites/{site_id}/inspections",
        "/api/sites/{site_id}/anomalies",
        "/api/sites/{site_id}/risk",
        "/api/sites/{site_id}/risk/history",
        "/api/sites/{site_id}/risk/recalculate",
        "/api/inspections",
        "/api/inspections/{inspection_id}",
        "/api/inspections/{inspection_id}/anomalies",
        "/api/anomalies",
        "/api/anomalies/{anomaly_id}",
        "/api/dashboard/summary",
    }.issubset(paths)


def test_inspection_uploads_validate_content_and_create_jobs(
    api_client: APIHarness, monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("AERIALOPS_UPLOAD_DIRECTORY", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    site = create_site(api_client, "Upload Test Site")
    inspection = api_client.request(
        "POST", "/api/inspections", json=inspection_payload(str(site["id"]))
    ).json()
    inspection_id = inspection["id"]

    image = api_client.request(
        "POST",
        f"/api/inspections/{inspection_id}/images",
        files=[("files", ("thermal.png", b"\x89PNG\r\n\x1a\nimage-data", "image/png"))],
    )
    assert image.status_code == 201
    assert image.json()["images"][0]["original_filename"] == "thermal.png"
    assert image.json()["processing_jobs"][0]["status"] == "PENDING"

    report = api_client.request(
        "POST",
        f"/api/inspections/{inspection_id}/report",
        files={"file": ("inspection.pdf", b"%PDF-1.7\nreport", "application/pdf")},
    )
    assert report.status_code == 201
    assert report.json()["report"]["ingestion_status"] == "PENDING"
    assert report.json()["processing_job"]["job_type"] == "REPORT_INGESTION"

    jobs = api_client.request("GET", f"/api/inspections/{inspection_id}/jobs")
    assert jobs.status_code == 200
    assert {item["job_type"] for item in jobs.json()} == {
        "IMAGE_ANALYSIS",
        "REPORT_INGESTION",
    }

    duplicate = api_client.request(
        "POST",
        f"/api/inspections/{inspection_id}/report",
        files={"file": ("second.pdf", b"%PDF-1.7\nsecond", "application/pdf")},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "inspection_report_exists"
    get_settings.cache_clear()


def test_upload_rejects_spoofed_content(api_client: APIHarness, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AERIALOPS_UPLOAD_DIRECTORY", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    site = create_site(api_client, "Spoof Test Site")
    inspection = api_client.request(
        "POST", "/api/inspections", json=inspection_payload(str(site["id"]))
    ).json()

    response = api_client.request(
        "POST",
        f"/api/inspections/{inspection['id']}/images",
        files=[("files", ("fake.png", b"not-an-image", "image/png"))],
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image_type"
    get_settings.cache_clear()

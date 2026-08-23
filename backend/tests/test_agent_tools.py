from uuid import uuid4

from sqlalchemy.orm import Session

from app.tools.operational_tools import build_operational_tool_registry


def test_operational_tool_registry_is_allowlisted_and_validated(db_session: Session) -> None:
    registry = build_operational_tool_registry(db_session)
    assert registry.names == (
        "get_site_details",
        "search_sites",
        "get_latest_inspection",
        "get_inspections",
        "get_site_anomalies",
        "find_high_risk_sites",
        "compare_sites",
        "calculate_site_risk",
        "search_reports",
        "generate_site_report",
    )

    rejected = registry.execute("delete_site", {}, request_id=uuid4())
    assert not rejected.ok
    assert rejected.error and rejected.error.code == "tool_not_allowed"

    invalid = registry.execute("get_site_details", {"site_id": "not-a-uuid"}, request_id=uuid4())
    assert not invalid.ok
    assert invalid.error and invalid.error.code == "invalid_tool_arguments"

    missing = registry.execute("get_site_details", {"site_id": str(uuid4())}, request_id=uuid4())
    assert not missing.ok
    assert missing.error and missing.error.code == "site_not_found"

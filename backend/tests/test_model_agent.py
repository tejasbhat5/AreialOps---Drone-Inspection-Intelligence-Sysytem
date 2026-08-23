import json
from uuid import uuid4

import httpx
from pydantic import BaseModel, SecretStr

from app.agents.factory import assistant_capabilities
from app.agents.model_orchestrator import ModelAgentOrchestrator
from app.agents.model_provider import (
    GeminiInteractionsProvider,
    ModelProviderError,
    ModelStep,
    ModelSynthesis,
    ModelToolCall,
    OpenAIResponsesProvider,
)
from app.core.config import Settings
from app.models.enums import RiskLevel, SiteStatus, SiteType
from app.schemas.agent_tools import SiteListInput, SiteOperationalView, SiteSearchResult
from app.schemas.assistant import AssistantContext, AssistantResponseType
from app.tools.registry import ToolDefinition, ToolRegistry


def make_provider(client: httpx.Client) -> OpenAIResponsesProvider:
    return OpenAIResponsesProvider(
        api_key="test-key",
        model="test-model",
        timeout_seconds=2,
        max_output_tokens=500,
        client=client,
    )


def make_gemini_provider(client: httpx.Client) -> GeminiInteractionsProvider:
    return GeminiInteractionsProvider(
        api_key="test-key",
        model="test-model",
        timeout_seconds=2,
        max_output_tokens=500,
        client=client,
    )


def test_gemini_provider_sends_tools_and_parses_function_calls() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "status": "requires_action",
                "steps": [
                    {
                        "type": "function_call",
                        "id": "call-1",
                        "name": "find_high_risk_sites",
                        "arguments": {"limit": 2},
                    }
                ],
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )
    step = make_gemini_provider(client).respond(
        instructions="Use tools.",
        input_items=[{"role": "user", "content": "Which sites are critical?"}],
        tool_schemas=[
            {
                "name": "find_high_risk_sites",
                "description": "Find sites",
                "input_schema": SiteListInput.model_json_schema(),
                "output_schema": SiteSearchResult.model_json_schema(),
            }
        ],
    )

    assert step.tool_calls[0].arguments == {"limit": 2}
    assert captured["store"] is False
    assert captured["system_instruction"] == "Use tools."
    tools = captured["tools"]
    assert isinstance(tools, list) and tools[0]["name"] == "find_high_risk_sites"
    assert "test-key" not in json.dumps(captured)


def test_gemini_provider_returns_tool_result_and_parses_synthesis() -> None:
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "steps": [
                        {
                            "type": "function_call",
                            "id": "call-1",
                            "name": "find_high_risk_sites",
                            "arguments": {"limit": 2},
                        }
                    ]
                },
            )
        answer = json.dumps(
            {"response_type": "high_risk_sites", "answer": "Two sites require review."}
        )
        return httpx.Response(
            200,
            json={
                "steps": [{"type": "model_output", "content": [{"type": "text", "text": answer}]}]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )
    provider = make_gemini_provider(client)
    first = provider.respond(instructions="Use tools.", input_items=[], tool_schemas=[])
    second = provider.respond(
        instructions="Use tools.",
        input_items=[
            *first.output_items,
            {"type": "function_call_output", "call_id": "call-1", "output": '{"ok":true}'},
        ],
        tool_schemas=[],
    )

    assert second.synthesis
    assert second.synthesis.response_type == AssistantResponseType.HIGH_RISK_SITES
    gemini_input = requests[1]["input"]
    assert isinstance(gemini_input, list)
    assert gemini_input[-1]["type"] == "function_result"
    assert gemini_input[-1]["name"] == "find_high_risk_sites"


def test_responses_provider_sends_controlled_tools_and_parses_calls() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call-1",
                        "name": "find_high_risk_sites",
                        "arguments": '{"limit":2}',
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.openai.com/v1"
    )
    step = make_provider(client).respond(
        instructions="Use tools.",
        input_items=[{"role": "user", "content": "Which sites are critical?"}],
        tool_schemas=[
            {
                "name": "find_high_risk_sites",
                "description": "Find sites",
                "input_schema": SiteListInput.model_json_schema(),
                "output_schema": SiteSearchResult.model_json_schema(),
            }
        ],
    )

    assert step.tool_calls[0].arguments == {"limit": 2}
    assert captured["store"] is False
    assert captured["parallel_tool_calls"] is False
    tools = captured["tools"]
    assert isinstance(tools, list) and tools[0]["name"] == "find_high_risk_sites"
    assert "test-key" not in json.dumps(captured)


def test_responses_provider_parses_structured_message_output() -> None:
    answer = {
        "response_type": "high_risk_sites",
        "answer": "Two sites require review.",
    }

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": json.dumps(answer)}],
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.openai.com/v1"
    )
    step = make_provider(client).respond(instructions="Use tools.", input_items=[], tool_schemas=[])
    assert step.synthesis
    assert step.synthesis.response_type == AssistantResponseType.HIGH_RISK_SITES


def test_responses_provider_maps_authentication_failure_to_safe_error() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(401, json={})),
        base_url="https://api.openai.com/v1",
    )
    try:
        make_provider(client).respond(instructions="", input_items=[], tool_schemas=[])
    except ModelProviderError as error:
        assert error.code == "model_authentication_failed"
        assert "local planning" in error.safe_message
    else:
        raise AssertionError("Expected a safe provider error.")


def test_responses_provider_identifies_exhausted_quota() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                429,
                json={"error": {"code": "insufficient_quota", "message": "private detail"}},
            )
        ),
        base_url="https://api.openai.com/v1",
    )
    try:
        make_provider(client).respond(instructions="", input_items=[], tool_schemas=[])
    except ModelProviderError as error:
        assert error.code == "model_quota_exceeded"
        assert "private detail" not in error.safe_message
    else:
        raise AssertionError("Expected a safe quota error.")


class FakeProvider:
    label = "fake:model"

    def __init__(self) -> None:
        self.steps = [
            ModelStep(
                output_items=[
                    {
                        "type": "function_call",
                        "call_id": "call-1",
                        "name": "find_high_risk_sites",
                        "arguments": '{"limit":2}',
                    }
                ],
                tool_calls=[
                    ModelToolCall(
                        call_id="call-1",
                        name="find_high_risk_sites",
                        arguments={"limit": 2},
                    )
                ],
            ),
            ModelStep(
                output_items=[],
                synthesis=ModelSynthesis(
                    response_type=AssistantResponseType.HIGH_RISK_SITES,
                    answer="Alpha requires review.",
                ),
            ),
        ]
        self.inputs: list[list[dict[str, object]]] = []

    def respond(self, **kwargs: object) -> ModelStep:
        inputs = kwargs["input_items"]
        assert isinstance(inputs, list)
        self.inputs.append(inputs)
        return self.steps.pop(0)


def test_model_orchestrator_executes_tool_and_returns_authoritative_data() -> None:
    site_id = uuid4()

    def high_risk(_: BaseModel) -> SiteSearchResult:
        return SiteSearchResult(
            sites=[
                SiteOperationalView(
                    id=site_id,
                    name="Alpha",
                    site_type=SiteType.SOLAR_FARM,
                    status=SiteStatus.ACTIVE,
                    location="Synthetic location",
                    latitude=26.9,
                    longitude=70.9,
                    risk_score=88,
                    risk_level=RiskLevel.CRITICAL,
                    unresolved_anomalies=3,
                    latest_inspection_at=None,
                )
            ],
            total=1,
        )

    registry = ToolRegistry(
        [
            ToolDefinition(
                "find_high_risk_sites",
                "Finding high-risk sites",
                "Find sites",
                SiteListInput,
                SiteSearchResult,
                high_risk,
            )
        ]
    )
    fake = FakeProvider()
    orchestrator = ModelAgentOrchestrator(registry, fake)  # type: ignore[arg-type]
    response = orchestrator.run(
        message="Which sites are critical?",
        context=AssistantContext(),
        request_id=uuid4(),
        conversation_id=uuid4(),
    )

    assert response.provider == "fake:model"
    assert response.response_type == AssistantResponseType.HIGH_RISK_SITES
    assert response.data
    sites = response.data["sites"]  # type: ignore[index]
    assert sites[0]["id"] == str(site_id)
    assert response.tool_activity[0].tool_name == "find_high_risk_sites"
    assert fake.inputs[1][-1]["type"] == "function_call_output"


def test_capabilities_only_enable_model_with_provider_and_secret() -> None:
    local = assistant_capabilities(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            agent_provider="deterministic",
            openai_api_key=SecretStr(""),
        )
    )
    assert not local.model_configured
    assert local.active_provider == "deterministic-local"

    blank = assistant_capabilities(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            agent_provider="openai",
            openai_api_key=SecretStr(""),
        )
    )
    assert not blank.model_configured

    configured = assistant_capabilities(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            agent_provider="openai",
            openai_api_key=SecretStr("secret"),
        )
    )
    assert configured.model_configured
    assert configured.active_provider == "openai"

    gemini = assistant_capabilities(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            agent_provider="gemini",
            gemini_api_key=SecretStr("secret"),
        )
    )
    assert gemini.model_configured
    assert gemini.active_provider == "gemini"

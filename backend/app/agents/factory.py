from sqlalchemy.orm import Session

from app.agents.model_orchestrator import ModelAgentOrchestrator
from app.agents.model_provider import GeminiInteractionsProvider, OpenAIResponsesProvider
from app.agents.orchestrator import AgentOrchestrator
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.assistant import AssistantCapabilities
from app.tools.operational_tools import build_operational_tool_registry

logger = get_logger(__name__)


def assistant_capabilities(settings: Settings | None = None) -> AssistantCapabilities:
    configured = settings or get_settings()
    provider_name = configured.agent_provider.lower()
    secret = configured.gemini_api_key if provider_name == "gemini" else configured.openai_api_key
    api_key = secret.get_secret_value().strip() if secret else ""
    use_model = provider_name in {"gemini", "openai"} and bool(api_key)
    return AssistantCapabilities(
        active_provider=provider_name if use_model else "deterministic-local",
        model=configured.agent_model if use_model else None,
        model_configured=use_model,
    )


def build_agent_orchestrator(
    session: Session, settings: Settings | None = None
) -> AgentOrchestrator | ModelAgentOrchestrator:
    configured = settings or get_settings()
    registry = build_operational_tool_registry(session)
    provider_name = configured.agent_provider.lower()
    if provider_name not in {"gemini", "openai"}:
        return AgentOrchestrator(registry)
    secret = configured.gemini_api_key if provider_name == "gemini" else configured.openai_api_key
    api_key = secret.get_secret_value().strip() if secret else ""
    if not api_key:
        logger.warning("model_provider_not_configured", extra={"provider": provider_name})
        return AgentOrchestrator(registry, provider_label="deterministic-fallback")
    provider_class = (
        GeminiInteractionsProvider if provider_name == "gemini" else OpenAIResponsesProvider
    )
    provider = provider_class(
        api_key=api_key,
        model=configured.agent_model,
        timeout_seconds=configured.agent_timeout_seconds,
        max_output_tokens=configured.agent_max_output_tokens,
    )
    return ModelAgentOrchestrator(registry, provider)

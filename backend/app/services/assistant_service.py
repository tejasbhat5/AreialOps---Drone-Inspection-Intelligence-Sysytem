from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.agents.factory import build_agent_orchestrator
from app.agents.model_orchestrator import ModelAgentOrchestrator
from app.agents.model_provider import ModelProviderError
from app.agents.orchestrator import AgentOrchestrator
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.agent_conversation import AgentConversation
from app.models.agent_message import AgentMessage
from app.models.enums import MessageRole
from app.repositories.agent_repository import AgentRepository
from app.repositories.site_repository import SiteRepository
from app.schemas.assistant import (
    AssistantQuery,
    AssistantResponse,
    ConversationCreate,
    ConversationRead,
)
from app.tools.operational_tools import build_operational_tool_registry

logger = get_logger(__name__)


class AssistantService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.agents = AgentRepository(session)
        self.sites = SiteRepository(session)

    def create_conversation(self, data: ConversationCreate) -> AgentConversation:
        if data.site_id and self.sites.get(data.site_id) is None:
            raise NotFoundError("Site was not found.", code="site_not_found")
        conversation = self.agents.add_conversation(
            AgentConversation(
                site_id=data.site_id,
                title=data.title or "New operational inquiry",
            )
        )
        self.session.commit()
        return conversation

    def get_conversation(self, conversation_id: UUID) -> ConversationRead:
        conversation = self.agents.get_conversation(conversation_id)
        if conversation is None:
            raise NotFoundError("Conversation was not found.", code="conversation_not_found")
        return ConversationRead.model_validate(conversation)

    def query(self, data: AssistantQuery) -> AssistantResponse:
        conversation = (
            self.agents.get_conversation(data.conversation_id) if data.conversation_id else None
        )
        if data.conversation_id and conversation is None:
            raise NotFoundError("Conversation was not found.", code="conversation_not_found")
        if conversation is None:
            if (
                data.context.current_site_id
                and self.sites.get(data.context.current_site_id) is None
            ):
                raise NotFoundError("Site was not found.", code="site_not_found")
            conversation = self.agents.add_conversation(
                AgentConversation(
                    site_id=data.context.current_site_id,
                    title=data.message[:177] + ("…" if len(data.message) > 177 else ""),
                )
            )

        history = [
            {
                "role": "user" if item.role == MessageRole.USER else "assistant",
                "content": item.content,
            }
            for item in conversation.messages
            if item.role in {MessageRole.USER, MessageRole.ASSISTANT}
        ]
        self.agents.add_message(
            AgentMessage(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=data.message,
            )
        )
        request_id = uuid4()
        orchestrator = build_agent_orchestrator(self.session)
        try:
            if isinstance(orchestrator, ModelAgentOrchestrator):
                response = orchestrator.run(
                    message=data.message,
                    context=data.context,
                    request_id=request_id,
                    conversation_id=conversation.id,
                    history=history,
                )
            else:
                response = orchestrator.run(
                    message=data.message,
                    context=data.context,
                    request_id=request_id,
                    conversation_id=conversation.id,
                )
        except ModelProviderError as exception:
            logger.warning(
                "model_agent_fallback",
                extra={
                    "agent_request_id": str(request_id),
                    "provider_error_code": exception.code,
                },
            )
            response = AgentOrchestrator(
                build_operational_tool_registry(self.session),
                provider_label="deterministic-fallback",
            ).run(
                message=data.message,
                context=data.context,
                request_id=request_id,
                conversation_id=conversation.id,
            )
        self.agents.add_message(
            AgentMessage(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=response.answer,
                structured_payload=response.model_dump(mode="json"),
                tool_audit=[item.model_dump(mode="json") for item in response.tool_activity],
            )
        )
        self.session.commit()
        return response

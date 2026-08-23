from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.agent_conversation import AgentConversation
from app.models.agent_message import AgentMessage


class AgentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_conversation(self, conversation: AgentConversation) -> AgentConversation:
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def get_conversation(self, conversation_id: UUID) -> AgentConversation | None:
        return self.session.scalar(
            select(AgentConversation)
            .where(AgentConversation.id == conversation_id)
            .options(selectinload(AgentConversation.messages))
        )

    def add_message(self, message: AgentMessage) -> AgentMessage:
        self.session.add(message)
        self.session.flush()
        return message

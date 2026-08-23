from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent_message import AgentMessage
    from app.models.site import Site


class AgentConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_conversations"

    site_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)

    site: Mapped["Site | None"] = relationship(back_populates="agent_conversations")
    messages: Mapped[list["AgentMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AgentMessage.created_at",
    )

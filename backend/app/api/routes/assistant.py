from uuid import UUID

from fastapi import APIRouter, status

from app.agents.factory import assistant_capabilities
from app.api.dependencies import DatabaseSession
from app.schemas.assistant import (
    AssistantCapabilities,
    AssistantQuery,
    AssistantResponse,
    ConversationCreate,
    ConversationRead,
)
from app.services.assistant_service import AssistantService

router = APIRouter(prefix="/api/assistant")


@router.get("/capabilities", response_model=AssistantCapabilities)
def get_assistant_capabilities() -> AssistantCapabilities:
    return assistant_capabilities()


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(data: ConversationCreate, session: DatabaseSession) -> ConversationRead:
    conversation = AssistantService(session).create_conversation(data)
    return ConversationRead.model_validate(conversation)


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: UUID, session: DatabaseSession) -> ConversationRead:
    return AssistantService(session).get_conversation(conversation_id)


@router.post("/query", response_model=AssistantResponse)
def query_assistant(data: AssistantQuery, session: DatabaseSession) -> AssistantResponse:
    return AssistantService(session).query(data)

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.assistant_schemas import (
    AssistantConfirmRequest,
    AssistantConfirmResponse,
    AssistantParseRequest,
    AssistantParseResponse,
)
from app.assistant_services import confirm_assistant_request, parse_assistant_request
from app.db import get_db
from app.tenant import tenant_context

router = APIRouter(prefix="/api/v1/timetable-projects", tags=["scheduling-assistant"])


@router.post("/{project_id}/assistant/parse", response_model=AssistantParseResponse)
def parse_assistant(
    project_id: uuid.UUID,
    payload: AssistantParseRequest,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return parse_assistant_request(db, tenant_id, project_id, payload)


@router.post("/{project_id}/assistant/confirm", response_model=AssistantConfirmResponse)
def confirm_assistant(
    project_id: uuid.UUID,
    payload: AssistantConfirmRequest,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return confirm_assistant_request(db, tenant_id, project_id, payload)

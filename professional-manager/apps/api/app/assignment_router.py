import uuid
from typing import Annotated, Any, TypeVar, cast

from fastapi import APIRouter, Body, Depends, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.assignment_services import (
    assignment_snapshot,
    bulk_assign,
    bulk_delete_assignments,
    bulk_replace_teachers,
    delete_assignment,
    save_assignment,
    save_offerings,
)
from app.db import get_db
from app.tenant import tenant_context

router = APIRouter(prefix="/api/v1/schools/{school_id}/assignments", tags=["assignments"])


Encoded = TypeVar("Encoded")


def encoded(value: Encoded) -> Encoded:
    return cast(Encoded, jsonable_encoder(value))


@router.get("")
def snapshot(
    school_id: uuid.UUID,
    term_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(assignment_snapshot(db, tenant_id, school_id, term_id))


@router.put("/section-offerings")
def offerings(
    school_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Any]:
    return encoded(save_offerings(db, tenant_id, school_id, payload))


@router.post("", status_code=201)
def create(
    school_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(save_assignment(db, tenant_id, school_id, payload))


@router.put("/{assignment_id}")
def update(
    school_id: uuid.UUID,
    assignment_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(save_assignment(db, tenant_id, school_id, payload, assignment_id))


@router.delete("/{assignment_id}", status_code=204)
def remove(
    school_id: uuid.UUID,
    assignment_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    delete_assignment(db, tenant_id, school_id, assignment_id)
    return Response(status_code=204)


@router.post("/bulk/apply", status_code=201)
def bulk(
    school_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    return encoded(bulk_assign(db, tenant_id, school_id, payload))


@router.post("/bulk/teachers")
def bulk_teachers(
    school_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    return encoded(bulk_replace_teachers(db, tenant_id, school_id, payload))


@router.post("/bulk/delete")
def bulk_delete(
    school_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    return {"deleted": bulk_delete_assignments(db, tenant_id, school_id, payload)}

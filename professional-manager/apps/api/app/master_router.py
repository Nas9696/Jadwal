import uuid
from typing import Annotated, Any, cast

from fastapi import APIRouter, Body, Depends, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db import get_db
from app.master_services import (
    catalog_snapshot,
    create_teacher,
    delete_catalog,
    link_teacher,
    save_catalog,
    teacher_snapshot,
    unlink_teacher,
    update_membership,
    update_teacher,
)
from app.tenant import tenant_context

router = APIRouter(prefix="/api/v1/schools/{school_id}", tags=["master data"])


def encoded(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], jsonable_encoder(value))


@router.get("/teachers")
def teachers(
    school_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(teacher_snapshot(db, tenant_id, school_id))


@router.post("/teachers", status_code=201)
def add_teacher(
    school_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(create_teacher(db, tenant_id, school_id, payload))


@router.post("/teacher-memberships", status_code=201)
def add_membership(
    school_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(link_teacher(db, tenant_id, school_id, payload))


@router.put("/teachers/{teacher_id}")
def edit_teacher(
    school_id: uuid.UUID,
    teacher_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(update_teacher(db, tenant_id, school_id, teacher_id, payload))


@router.put("/teacher-memberships/{membership_id}")
def edit_membership(
    school_id: uuid.UUID,
    membership_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(update_membership(db, tenant_id, school_id, membership_id, payload))


@router.delete("/teacher-memberships/{membership_id}", status_code=204)
def remove_membership(
    school_id: uuid.UUID,
    membership_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    unlink_teacher(db, tenant_id, school_id, membership_id)
    return Response(status_code=204)


@router.get("/catalog")
def catalog(
    school_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(catalog_snapshot(db, tenant_id, school_id))


@router.post("/catalog/{kind}", status_code=201)
def add_catalog(
    school_id: uuid.UUID,
    kind: str,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(save_catalog(db, tenant_id, school_id, kind, payload))


@router.put("/catalog/{kind}/{entity_id}")
def edit_catalog(
    school_id: uuid.UUID,
    kind: str,
    entity_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(save_catalog(db, tenant_id, school_id, kind, payload, entity_id))


@router.delete("/catalog/{kind}/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_catalog(
    school_id: uuid.UUID,
    kind: str,
    entity_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    delete_catalog(db, tenant_id, school_id, kind, entity_id)
    return Response(status_code=204)

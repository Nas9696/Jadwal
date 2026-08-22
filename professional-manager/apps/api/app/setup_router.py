import uuid
from typing import Annotated, Any, cast

from fastapi import APIRouter, Body, Depends, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db import get_db
from app.setup_services import delete_resource, save_resource, setup_snapshot
from app.tenant import tenant_context

router = APIRouter(prefix="/api/v1/schools/{school_id}/setup", tags=["school setup"])


@router.get("")
def read_setup(
    school_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return cast(dict[str, Any], jsonable_encoder(setup_snapshot(db, tenant_id, school_id)))


@router.post("/{resource}", status_code=status.HTTP_201_CREATED)
def create_setup_resource(
    school_id: uuid.UUID,
    resource: str,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return cast(dict[str, Any], jsonable_encoder(save_resource(db, tenant_id, school_id, resource, payload)))


@router.put("/{resource}/{entity_id}")
def update_setup_resource(
    school_id: uuid.UUID,
    resource: str,
    entity_id: uuid.UUID,
    payload: Annotated[dict[str, Any], Body()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return cast(dict[str, Any], jsonable_encoder(
        save_resource(db, tenant_id, school_id, resource, payload, entity_id)
    ))


@router.delete("/{resource}/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_setup_resource(
    school_id: uuid.UUID,
    resource: str,
    entity_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    delete_resource(db, tenant_id, school_id, resource, entity_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

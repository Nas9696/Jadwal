import uuid
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db import get_db
from app.import_schemas import CommitInput, ImportJobRead, MappingInput, RowExclusionInput
from app.import_services import (
    _job,
    commit_job,
    exclude_rows,
    save_mapping,
    serialize_job,
    template_csv,
    upload_job,
    validate_job,
)
from app.tenant import tenant_context

router = APIRouter(prefix="/api/v1/schools/{school_id}/imports", tags=["imports"])


def encoded(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], jsonable_encoder(value))


@router.post("/upload", response_model=ImportJobRead, status_code=201)
async def upload(
    school_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
    term_id: Annotated[uuid.UUID | None, Form()] = None,
) -> dict[str, Any]:
    content = await file.read()
    job = upload_job(db, tenant_id, school_id, term_id, file.filename, file.content_type, content)
    return encoded(serialize_job(db, job))


@router.get("/{job_id}", response_model=ImportJobRead)
def get_import(
    school_id: uuid.UUID,
    job_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(serialize_job(db, _job(db, tenant_id, school_id, job_id)))


@router.put("/{job_id}/mapping", response_model=ImportJobRead)
def map_import(
    school_id: uuid.UUID,
    job_id: uuid.UUID,
    payload: MappingInput,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    mapping = {name: config.model_dump() for name, config in payload.sheets.items()}
    job = save_mapping(db, tenant_id, school_id, job_id, mapping, payload.allow_updates)
    return encoded(serialize_job(db, job))


@router.post("/{job_id}/validate", response_model=ImportJobRead)
def validate_import(
    school_id: uuid.UUID,
    job_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return encoded(serialize_job(db, validate_job(db, tenant_id, school_id, job_id)))


@router.put("/{job_id}/exclude", response_model=ImportJobRead)
def exclude_import_rows(
    school_id: uuid.UUID,
    job_id: uuid.UUID,
    payload: RowExclusionInput,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    job = exclude_rows(db, tenant_id, school_id, job_id, payload.row_ids)
    return encoded(serialize_job(db, job))


@router.post("/{job_id}/commit", response_model=ImportJobRead)
def commit_import(
    school_id: uuid.UUID,
    job_id: uuid.UUID,
    payload: CommitInput,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    job = commit_job(db, tenant_id, school_id, job_id, payload.acknowledge_warnings)
    return encoded(serialize_job(db, job))


@router.delete("/{job_id}", status_code=204)
def cancel_import(
    school_id: uuid.UUID,
    job_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    job = _job(db, tenant_id, school_id, job_id)
    if job.status == "committed":
        from app.import_services import fail

        fail("committed_import_cannot_be_deleted", 409)
    db.delete(job)
    db.commit()
    return Response(status_code=204)


@router.get("/templates/{kind}.csv")
def template(
    school_id: uuid.UUID,
    kind: str,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    from app.master_services import school

    school(db, tenant_id, school_id)
    return Response(
        content=template_csv(kind),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{kind}-template.csv"'},
    )

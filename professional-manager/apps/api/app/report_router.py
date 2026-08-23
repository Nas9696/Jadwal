import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.report_exports import export_report
from app.report_schemas import (
    ReportDataset,
    ReportExportRequest,
    ReportOptions,
    ReportPreviewRequest,
)
from app.report_services import build_report, report_options
from app.tenant import tenant_context

router = APIRouter(prefix="/api/v1/timetable-projects", tags=["reports"])


@router.get("/{project_id}/reports/options", response_model=ReportOptions)
def options(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> ReportOptions:
    return report_options(db, tenant, project_id)


@router.post("/{project_id}/reports/preview", response_model=ReportDataset)
def preview(
    project_id: uuid.UUID,
    payload: ReportPreviewRequest,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> ReportDataset:
    return build_report(db, tenant, project_id, payload)


@router.post("/{project_id}/reports/export")
def export(
    project_id: uuid.UUID,
    payload: ReportExportRequest,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    if payload.source.kind == "working" and payload.source.expected_revision is None:
        raise HTTPException(422, detail={"code": "expected_revision_required_for_export"})
    dataset = build_report(db, tenant, project_id, payload)
    exported = export_report(dataset, payload.format)
    headers = {
        "Content-Disposition": f'attachment; filename="{exported.metadata.filename}"',
        "X-Report-Pages": str(exported.metadata.pages),
        "X-Report-Multi-Page": str(exported.metadata.multi_page).lower(),
        "X-Source-Revision": str(exported.metadata.source_revision or ""),
    }
    return Response(content=exported.content, media_type=exported.metadata.content_type, headers=headers)

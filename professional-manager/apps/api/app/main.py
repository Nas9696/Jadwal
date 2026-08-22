import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Resource, School, Section, Subject, Teacher, TimetableProject
from app.schemas import DashboardSummary, HealthResponse, SchoolRead
from app.tenant import tenant_context

app = FastAPI(title=settings.app_name, version="0.1.0", openapi_url="/api/v1/openapi.json", docs_url="/api/v1/docs")
app.add_middleware(CORSMiddleware, allow_origins=settings.api_cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="professional-manager-api", version="0.1.0")

@app.get("/api/v1/schools", response_model=list[SchoolRead], tags=["schools"])
def schools(tenant_id: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> list[School]:
    return list(db.scalars(select(School).where(School.tenant_id == tenant_id).order_by(School.name_ar)))

@app.get("/api/v1/dashboard/{school_id}", response_model=DashboardSummary, tags=["dashboard"])
def dashboard(school_id: uuid.UUID, tenant_id: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> DashboardSummary:
    school = db.scalar(select(School).where(School.id == school_id, School.tenant_id == tenant_id))
    if not school:
        raise HTTPException(status_code=404, detail="School not found in tenant")
    def count(model: type[Teacher] | type[Subject] | type[Section] | type[Resource]) -> int:
        return db.scalar(select(func.count()).select_from(model).where(model.tenant_id == tenant_id)) or 0
    project = db.scalar(select(TimetableProject).where(TimetableProject.school_id == school_id, TimetableProject.tenant_id == tenant_id).order_by(TimetableProject.created_at.desc()))
    return DashboardSummary(school=SchoolRead.model_validate(school), teachers=count(Teacher), subjects=count(Subject), sections=count(Section), resources=count(Resource), active_project_name=project.name_ar if project else None)


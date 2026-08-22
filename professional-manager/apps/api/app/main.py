import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import (
    Grade,
    Resource,
    School,
    Section,
    Stage,
    Subject,
    Teacher,
    TeacherSchoolMembership,
    TimetableProject,
    TimetableProjectSchool,
)
from app.schemas import (
    DashboardSummary,
    HealthResponse,
    SchoolRead,
    TeacherSchoolMembershipCreate,
    TeacherSchoolMembershipRead,
    TimetableProjectCreate,
    TimetableProjectRead,
)
from app.services import create_teacher_school_membership, create_timetable_project
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
    teachers = db.scalar(
        select(func.count(Teacher.id.distinct()))
        .join(TeacherSchoolMembership, TeacherSchoolMembership.teacher_id == Teacher.id)
        .where(
            Teacher.tenant_id == tenant_id,
            TeacherSchoolMembership.tenant_id == tenant_id,
            TeacherSchoolMembership.school_id == school_id,
            TeacherSchoolMembership.is_active.is_(True),
        )
    ) or 0
    subjects = db.scalar(
        select(func.count()).select_from(Subject).where(
            Subject.tenant_id == tenant_id, Subject.school_id == school_id
        )
    ) or 0
    sections = db.scalar(
        select(func.count(Section.id))
        .join(Grade, Grade.id == Section.grade_id)
        .join(Stage, Stage.id == Grade.stage_id)
        .where(
            Section.tenant_id == tenant_id,
            Grade.tenant_id == tenant_id,
            Stage.tenant_id == tenant_id,
            Stage.school_id == school_id,
        )
    ) or 0
    resources = db.scalar(
        select(func.count()).select_from(Resource).where(
            Resource.tenant_id == tenant_id, Resource.school_id == school_id
        )
    ) or 0
    project = db.scalar(
        select(TimetableProject)
        .join(
            TimetableProjectSchool,
            TimetableProjectSchool.timetable_project_id == TimetableProject.id,
        )
        .where(
            TimetableProject.tenant_id == tenant_id,
            TimetableProjectSchool.tenant_id == tenant_id,
            TimetableProjectSchool.school_id == school_id,
        )
        .order_by(TimetableProject.created_at.desc())
    )
    return DashboardSummary(
        school=SchoolRead.model_validate(school),
        teachers=teachers,
        subjects=subjects,
        sections=sections,
        resources=resources,
        active_project_name=project.name_ar if project else None,
    )


@app.post(
    "/api/v1/teacher-school-memberships",
    response_model=TeacherSchoolMembershipRead,
    status_code=201,
    tags=["teachers"],
)
def add_teacher_to_school(
    payload: TeacherSchoolMembershipCreate,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> TeacherSchoolMembership:
    return create_teacher_school_membership(db, tenant_id, payload)


@app.post(
    "/api/v1/timetable-projects",
    response_model=TimetableProjectRead,
    status_code=201,
    tags=["timetables"],
)
def add_timetable_project(
    payload: TimetableProjectCreate,
    tenant_id: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> TimetableProjectRead:
    project, school_ids = create_timetable_project(db, tenant_id, payload)
    calendars_by_school = {calendar.school_id: calendar for calendar in payload.schools}
    return TimetableProjectRead(
        id=project.id,
        tenant_id=project.tenant_id,
        name_ar=project.name_ar,
        scope_type=project.scope_type,
        schools=[calendars_by_school[school_id] for school_id in school_ids],
        complex_id=project.complex_id,
    )

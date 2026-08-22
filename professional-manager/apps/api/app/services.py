import uuid
from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AcademicYear,
    School,
    SchoolComplex,
    Teacher,
    TeacherSchoolMembership,
    Term,
    TimetableProject,
    TimetableProjectSchool,
)
from app.schemas import TeacherSchoolMembershipCreate, TimetableProjectCreate

TenantEntity = TypeVar(
    "TenantEntity", AcademicYear, School, SchoolComplex, Teacher, Term
)


def _tenant_entity(
    db: Session,
    model: type[TenantEntity],
    entity_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> TenantEntity:
    entity = db.scalar(select(model).where(model.id == entity_id, model.tenant_id == tenant_id))
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{model.__name__} reference does not belong to active tenant",
        )
    return entity


def create_teacher_school_membership(
    db: Session, tenant_id: uuid.UUID, payload: TeacherSchoolMembershipCreate
) -> TeacherSchoolMembership:
    _tenant_entity(db, Teacher, payload.teacher_id, tenant_id)
    _tenant_entity(db, School, payload.school_id, tenant_id)
    membership = TeacherSchoolMembership(tenant_id=tenant_id, **payload.model_dump())
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def create_timetable_project(
    db: Session, tenant_id: uuid.UUID, payload: TimetableProjectCreate
) -> tuple[TimetableProject, list[uuid.UUID]]:
    school_ids = list(dict.fromkeys(payload.school_ids))
    if not school_ids:
        raise HTTPException(status_code=422, detail="At least one school is required")
    if payload.scope_type not in {"school", "complex", "schools"}:
        raise HTTPException(status_code=422, detail="Invalid project scope type")
    if payload.scope_type == "school" and len(school_ids) != 1:
        raise HTTPException(status_code=422, detail="School scope requires exactly one school")
    schools = [_tenant_entity(db, School, school_id, tenant_id) for school_id in school_ids]
    complex_entity = None
    if payload.complex_id:
        complex_entity = _tenant_entity(db, SchoolComplex, payload.complex_id, tenant_id)
    if payload.scope_type == "complex":
        if complex_entity is None:
            raise HTTPException(status_code=422, detail="Complex scope requires complex_id")
        if any(school.complex_id != complex_entity.id for school in schools):
            raise HTTPException(status_code=422, detail="All schools must belong to project complex")
    if payload.term_id:
        term = _tenant_entity(db, Term, payload.term_id, tenant_id)
        academic_year = _tenant_entity(
            db, AcademicYear, term.academic_year_id, tenant_id
        )
        if academic_year.school_id not in school_ids:
            raise HTTPException(
                status_code=422,
                detail="Term school must be included in project scope",
            )
    project = TimetableProject(
        tenant_id=tenant_id,
        name_ar=payload.name_ar,
        scope_type=payload.scope_type,
        complex_id=payload.complex_id,
        term_id=payload.term_id,
    )
    db.add(project)
    db.flush()
    db.add_all(
        TimetableProjectSchool(
            tenant_id=tenant_id, timetable_project_id=project.id, school_id=school_id
        )
        for school_id in school_ids
    )
    db.commit()
    db.refresh(project)
    return project, school_ids

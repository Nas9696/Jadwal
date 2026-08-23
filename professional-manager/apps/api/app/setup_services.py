import uuid
from typing import Any, NoReturn, cast

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.models import (
    AcademicYear,
    Grade,
    PeriodTemplate,
    School,
    SchoolDay,
    SchoolShift,
    Section,
    Stage,
    Term,
    WeekPattern,
)
from app.setup_schemas import (
    BlockInput,
    GradeInput,
    SchoolDayInput,
    SectionInput,
    ShiftInput,
    StageInput,
    TermInput,
    WeekPatternInput,
    YearInput,
)

RESOURCE_MODELS: dict[str, tuple[Any, Any]] = {
    "years": (AcademicYear, YearInput),
    "terms": (Term, TermInput),
    "shifts": (SchoolShift, ShiftInput),
    "patterns": (WeekPattern, WeekPatternInput),
    "days": (SchoolDay, SchoolDayInput),
    "blocks": (PeriodTemplate, BlockInput),
    "stages": (Stage, StageInput),
    "grades": (Grade, GradeInput),
    "sections": (Section, SectionInput),
}


def fail(code: str, status_code: int = 422) -> NoReturn:
    raise HTTPException(status_code=status_code, detail={"code": code})


def school_in_tenant(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID) -> School:
    school = db.scalar(
        select(School).where(School.id == school_id, School.tenant_id == tenant_id)
    )
    if school is None:
        fail("school_not_found", 404)
    return school


def scoped(db: Session, model: Any, entity_id: uuid.UUID, tenant_id: uuid.UUID) -> Any:
    entity = db.scalar(
        select(model).where(model.id == entity_id, model.tenant_id == tenant_id)
    )
    if entity is None:
        fail("reference_not_in_tenant")
    return entity


def _school_for_entity(db: Session, entity: Any) -> uuid.UUID:
    if isinstance(entity, (AcademicYear, SchoolShift, WeekPattern, SchoolDay, PeriodTemplate, Stage)):
        return entity.school_id
    if isinstance(entity, Term):
        return cast(uuid.UUID, scoped(db, AcademicYear, entity.academic_year_id, entity.tenant_id).school_id)
    if isinstance(entity, Grade):
        return cast(uuid.UUID, scoped(db, Stage, entity.stage_id, entity.tenant_id).school_id)
    if isinstance(entity, Section):
        grade = scoped(db, Grade, entity.grade_id, entity.tenant_id)
        return cast(uuid.UUID, scoped(db, Stage, grade.stage_id, entity.tenant_id).school_id)
    fail("unsupported_resource")


def setup_snapshot(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID) -> dict[str, Any]:
    school = school_in_tenant(db, tenant_id, school_id)
    result: dict[str, Any] = {"school": school}
    for resource, (model, _) in RESOURCE_MODELS.items():
        rows: list[Any] = list(db.scalars(select(model).where(model.tenant_id == tenant_id)))
        result[resource] = [row for row in rows if _school_for_entity(db, row) == school_id]
    return result


def _validate_links(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, resource: str, data: Any, entity_id: uuid.UUID | None = None) -> dict[str, Any]:
    values = data.model_dump()
    if resource == "terms":
        year = scoped(db, AcademicYear, data.academic_year_id, tenant_id)
        if year.school_id != school_id:
            fail("year_not_in_school")
        if data.starts_on < year.starts_on or data.ends_on > year.ends_on:
            fail("term_outside_year")
    elif resource == "patterns":
        existing = list(db.scalars(select(WeekPattern).where(WeekPattern.tenant_id == tenant_id, WeekPattern.school_id == school_id)))
        if any(
            pattern.id != entity_id
            and (
                pattern.code == data.code
                or pattern.cycle_week_index == data.cycle_week_index
            )
            for pattern in existing
        ):
            fail("duplicate_or_dependent_data", 409)
        indexes = [
            pattern.cycle_week_index
            for pattern in existing
            if pattern.id != entity_id
        ] + [data.cycle_week_index]
        if sorted(indexes) != list(range(len(indexes))):
            fail("week_indexes_must_be_contiguous")
    elif resource == "days":
        shift = scoped(db, SchoolShift, data.shift_id, tenant_id)
        pattern = scoped(db, WeekPattern, data.week_pattern_id, tenant_id)
        if shift.school_id != school_id or pattern.school_id != school_id:
            fail("calendar_reference_not_in_school")
    elif resource == "blocks":
        day = scoped(db, SchoolDay, data.school_day_id, tenant_id)
        if day.school_id != school_id:
            fail("day_not_in_school")
        overlap = db.scalar(
            select(PeriodTemplate.id).where(
                PeriodTemplate.school_day_id == day.id,
                PeriodTemplate.id != entity_id if entity_id else PeriodTemplate.id.is_not(None),
                PeriodTemplate.starts_at < data.ends_at,
                PeriodTemplate.ends_at > data.starts_at,
            )
        )
        if overlap:
            fail("day_block_overlap")
        values.update(
            school_id=school_id,
            shift_id=day.shift_id,
            week_pattern_id=day.week_pattern_id,
            weekday_index=day.weekday_index,
            schedulable=data.block_type == "lesson",
        )
    elif resource == "grades":
        stage = scoped(db, Stage, data.stage_id, tenant_id)
        if stage.school_id != school_id:
            fail("stage_not_in_school")
    elif resource == "sections":
        grade = scoped(db, Grade, data.grade_id, tenant_id)
        stage = scoped(db, Stage, grade.stage_id, tenant_id)
        if stage.school_id != school_id:
            fail("grade_not_in_school")
    return cast(dict[str, Any], values)


def save_resource(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, resource: str, payload: dict[str, Any], entity_id: uuid.UUID | None = None) -> Any:
    school_in_tenant(db, tenant_id, school_id)
    try:
        model, schema = RESOURCE_MODELS[resource]
    except KeyError:
        fail("unknown_setup_resource", 404)
    try:
        data = schema.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "validation_error",
                "errors": exc.errors(include_url=False, include_context=False),
            },
        ) from exc
    values = _validate_links(db, tenant_id, school_id, resource, data, entity_id)
    if resource in {"years", "shifts", "patterns", "days", "stages"}:
        values["school_id"] = school_id
    entity = model(tenant_id=tenant_id, **values) if entity_id is None else scoped(db, model, entity_id, tenant_id)
    if entity_id is not None:
        if _school_for_entity(db, entity) != school_id:
            fail("resource_not_in_school")
        if resource == "years" and data.is_current:
            db.execute(
                update(AcademicYear)
                .where(
                    AcademicYear.tenant_id == tenant_id,
                    AcademicYear.school_id == school_id,
                    AcademicYear.id != entity_id,
                    AcademicYear.is_current.is_(True),
                )
                .values(is_current=False)
            )
        for key, value in values.items():
            setattr(entity, key, value)
        if resource == "days":
            db.execute(
                update(PeriodTemplate)
                .where(
                    PeriodTemplate.tenant_id == tenant_id,
                    PeriodTemplate.school_id == school_id,
                    PeriodTemplate.school_day_id == entity_id,
                )
                .values(
                    shift_id=data.shift_id,
                    week_pattern_id=data.week_pattern_id,
                    weekday_index=data.weekday_index,
                )
            )
    else:
        if resource == "years" and data.is_current:
            db.execute(
                update(AcademicYear)
                .where(
                    AcademicYear.tenant_id == tenant_id,
                    AcademicYear.school_id == school_id,
                    AcademicYear.is_current.is_(True),
                )
                .values(is_current=False)
            )
        db.add(entity)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "duplicate_or_dependent_data"}) from exc
    db.refresh(entity)
    return entity


def delete_resource(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, resource: str, entity_id: uuid.UUID) -> None:
    try:
        model, _ = RESOURCE_MODELS[resource]
    except KeyError:
        fail("unknown_setup_resource", 404)
    entity = scoped(db, model, entity_id, tenant_id)
    if _school_for_entity(db, entity) != school_id:
        fail("resource_not_in_school")
    dependencies = {
        "years": (Term, Term.academic_year_id),
        "shifts": (SchoolDay, SchoolDay.shift_id),
        "patterns": (SchoolDay, SchoolDay.week_pattern_id),
        "days": (PeriodTemplate, PeriodTemplate.school_day_id),
        "stages": (Grade, Grade.stage_id),
        "grades": (Section, Section.grade_id),
    }
    if resource in dependencies:
        child, column = dependencies[resource]
        if db.scalar(select(func.count()).select_from(child).where(column == entity_id)):
            fail("resource_has_dependencies", 409)
    if resource == "patterns":
        higher = db.scalar(select(func.count()).select_from(WeekPattern).where(WeekPattern.school_id == school_id, WeekPattern.cycle_week_index > entity.cycle_week_index))
        if higher:
            fail("remove_last_week_pattern_first", 409)
    db.delete(entity)
    db.commit()

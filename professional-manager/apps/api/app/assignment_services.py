import uuid
from typing import Any, NoReturn

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.assignment_schemas import (
    AssignmentInput,
    AssignmentPreview,
    AssignmentPreviewInput,
    BulkAssignmentInput,
    BulkDeleteInput,
    BulkTeacherInput,
    OfferingBulkInput,
)
from app.models import (
    AcademicYear,
    CurriculumRequirement,
    Grade,
    Resource,
    School,
    SchoolShift,
    Section,
    SectionOffering,
    Stage,
    Subject,
    Teacher,
    TeacherSchoolMembership,
    TeachingAssignment,
    TeachingAssignmentResource,
    TeachingAssignmentSection,
    TeachingAssignmentTeacher,
    Term,
)


def fail(code: str, status: int = 422) -> NoReturn:
    raise HTTPException(status_code=status, detail={"code": code})


def parse(schema: Any, payload: dict[str, Any]) -> Any:
    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "validation_error",
                "errors": exc.errors(include_url=False, include_context=False),
            },
        ) from exc


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "duplicate_relation"}) from exc


def _school(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID) -> School:
    entity = db.scalar(select(School).where(School.id == school_id, School.tenant_id == tenant_id))
    if entity is None:
        fail("school_not_found", 404)
    return entity


def _term(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, term_id: uuid.UUID) -> Term:
    entity = db.scalar(
        select(Term)
        .join(AcademicYear, AcademicYear.id == Term.academic_year_id)
        .where(
            Term.id == term_id,
            Term.tenant_id == tenant_id,
            AcademicYear.tenant_id == tenant_id,
            AcademicYear.school_id == school_id,
        )
    )
    if entity is None:
        fail("term_not_in_school")
    return entity


def _section_context(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, section_id: uuid.UUID
) -> tuple[Section, Grade, Stage]:
    row = db.execute(
        select(Section, Grade, Stage)
        .join(Grade, Grade.id == Section.grade_id)
        .join(Stage, Stage.id == Grade.stage_id)
        .where(
            Section.id == section_id,
            Section.tenant_id == tenant_id,
            Grade.tenant_id == tenant_id,
            Stage.tenant_id == tenant_id,
            Stage.school_id == school_id,
        )
    ).one_or_none()
    if row is None:
        fail("section_not_in_school")
    return row[0], row[1], row[2]


def save_offerings(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: dict[str, Any]
) -> list[SectionOffering]:
    _school(db, tenant_id, school_id)
    data = parse(OfferingBulkInput, payload)
    result = []
    for item in data.offerings:
        _term(db, tenant_id, school_id, item.term_id)
        _section_context(db, tenant_id, school_id, item.section_id)
        shift = db.scalar(
            select(SchoolShift).where(
                SchoolShift.id == item.shift_id,
                SchoolShift.tenant_id == tenant_id,
                SchoolShift.school_id == school_id,
                SchoolShift.is_active.is_(True),
            )
        )
        if shift is None:
            fail("shift_not_in_school")
        offering = db.scalar(
            select(SectionOffering).where(
                SectionOffering.tenant_id == tenant_id,
                SectionOffering.school_id == school_id,
                SectionOffering.term_id == item.term_id,
                SectionOffering.section_id == item.section_id,
            )
        )
        if offering is None:
            offering = SectionOffering(
                tenant_id=tenant_id,
                school_id=school_id,
                term_id=item.term_id,
                section_id=item.section_id,
                shift_id=item.shift_id,
                is_active=item.is_active,
            )
            db.add(offering)
        else:
            if not item.is_active and db.scalar(
                select(TeachingAssignmentSection.id).where(
                    TeachingAssignmentSection.section_offering_id == offering.id
                )
            ):
                fail("section_offering_has_assignments", 409)
            offering.shift_id = item.shift_id
            offering.is_active = item.is_active
        result.append(offering)
    commit(db)
    return result


def _validate_assignment(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    data: AssignmentInput,
    *,
    existing: TeachingAssignment | None = None,
) -> None:
    _term(db, tenant_id, school_id, data.term_id)
    subject = db.scalar(
        select(Subject).where(
            Subject.id == data.subject_id,
            Subject.tenant_id == tenant_id,
            Subject.school_id == school_id,
        )
    )
    if subject is None:
        fail("subject_not_in_school")
    if not subject.is_active and (existing is None or existing.subject_id != subject.id):
        fail("subject_inactive", 409)
    for offering_id in data.section_offering_ids:
        offering = db.scalar(
            select(SectionOffering).where(
                SectionOffering.id == offering_id,
                SectionOffering.tenant_id == tenant_id,
                SectionOffering.school_id == school_id,
                SectionOffering.term_id == data.term_id,
                SectionOffering.is_active.is_(True),
            )
        )
        if offering is None:
            fail("section_offering_not_in_term")
    for teacher_id in data.teacher_ids:
        teacher = db.scalar(
            select(Teacher).where(
                Teacher.id == teacher_id,
                Teacher.tenant_id == tenant_id,
                Teacher.is_active.is_(True),
            )
        )
        membership = db.scalar(
            select(TeacherSchoolMembership).where(
                TeacherSchoolMembership.tenant_id == tenant_id,
                TeacherSchoolMembership.school_id == school_id,
                TeacherSchoolMembership.teacher_id == teacher_id,
                TeacherSchoolMembership.is_active.is_(True),
            )
        )
        if teacher is None or membership is None:
            fail("teacher_not_active_in_school", 409)
    for resource_id in data.resource_ids:
        resource = db.scalar(
            select(Resource).where(
                Resource.id == resource_id,
                Resource.tenant_id == tenant_id,
                Resource.school_id == school_id,
            )
        )
        if resource is None:
            fail("resource_not_in_school")
        if not resource.is_active:
            fail("resource_inactive", 409)


def _replace_relations(
    db: Session, tenant_id: uuid.UUID, assignment: TeachingAssignment, data: AssignmentInput
) -> None:
    for model in (
        TeachingAssignmentTeacher,
        TeachingAssignmentSection,
        TeachingAssignmentResource,
    ):
        for relation in db.scalars(
            select(model).where(model.teaching_assignment_id == assignment.id)
        ):
            db.delete(relation)
    db.flush()
    db.add_all(
        TeachingAssignmentTeacher(
            tenant_id=tenant_id,
            teaching_assignment_id=assignment.id,
            teacher_id=teacher_id,
        )
        for teacher_id in data.teacher_ids
    )
    db.add_all(
        TeachingAssignmentSection(
            tenant_id=tenant_id,
            teaching_assignment_id=assignment.id,
            section_offering_id=offering_id,
        )
        for offering_id in data.section_offering_ids
    )
    db.add_all(
        TeachingAssignmentResource(
            tenant_id=tenant_id,
            teaching_assignment_id=assignment.id,
            resource_id=resource_id,
        )
        for resource_id in data.resource_ids
    )


def save_assignment(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    payload: dict[str, Any],
    assignment_id: uuid.UUID | None = None,
    *,
    commit_changes: bool = True,
) -> dict[str, Any]:
    _school(db, tenant_id, school_id)
    data = parse(AssignmentInput, payload)
    assignment = None
    if assignment_id:
        assignment = db.scalar(
            select(TeachingAssignment).where(
                TeachingAssignment.id == assignment_id,
                TeachingAssignment.tenant_id == tenant_id,
                TeachingAssignment.school_id == school_id,
            )
        )
        if assignment is None:
            fail("assignment_not_in_school", 404)
    _validate_assignment(db, tenant_id, school_id, data, existing=assignment)
    if assignment is None:
        assignment = TeachingAssignment(
            tenant_id=tenant_id,
            school_id=school_id,
            term_id=data.term_id,
            subject_id=data.subject_id,
            weekly_occurrences=data.weekly_occurrences,
            notes=data.notes,
            distribution={},
        )
        db.add(assignment)
        db.flush()
    else:
        assignment.term_id = data.term_id
        assignment.subject_id = data.subject_id
        assignment.weekly_occurrences = data.weekly_occurrences
        assignment.notes = data.notes
    _replace_relations(db, tenant_id, assignment, data)
    db.flush()
    warnings = _warnings(db, tenant_id, school_id, assignment, data)
    if commit_changes:
        commit(db)
    return {"assignment_id": assignment.id, "warnings": warnings}


def _warnings(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    assignment: TeachingAssignment,
    data: AssignmentInput,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for offering_id in data.section_offering_ids:
        offering = db.get(SectionOffering, offering_id)
        section = db.get(Section, offering.section_id) if offering else None
        required = (
            db.scalar(
                select(CurriculumRequirement.weekly_occurrences).where(
                    CurriculumRequirement.tenant_id == tenant_id,
                    CurriculumRequirement.school_id == school_id,
                    CurriculumRequirement.grade_id == section.grade_id,
                    CurriculumRequirement.subject_id == data.subject_id,
                )
            )
            if section
            else None
        )
        assigned = (
            db.scalar(
                select(func.coalesce(func.sum(TeachingAssignment.weekly_occurrences), 0))
                .join(
                    TeachingAssignmentSection,
                    TeachingAssignmentSection.teaching_assignment_id == TeachingAssignment.id,
                )
                .where(
                    TeachingAssignment.tenant_id == tenant_id,
                    TeachingAssignment.school_id == school_id,
                    TeachingAssignment.term_id == data.term_id,
                    TeachingAssignment.subject_id == data.subject_id,
                    TeachingAssignmentSection.section_offering_id == offering_id,
                )
            )
            or 0
        )
        if required is not None and assigned > required:
            warnings.append(
                {"code": "curriculum_over_assigned", "offering_id": offering_id, "value": assigned}
            )
    for teacher_id in data.teacher_ids:
        assigned = _teacher_workload(db, tenant_id, school_id, data.term_id, teacher_id)
        teacher = db.get(Teacher, teacher_id)
        if teacher and assigned > teacher.teaching_workload_limit:
            warnings.append(
                {"code": "teacher_workload_exceeded", "teacher_id": teacher_id, "value": assigned}
            )
    return warnings


def _teacher_workload(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    term_id: uuid.UUID,
    teacher_id: uuid.UUID,
) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(TeachingAssignment.weekly_occurrences), 0))
            .join(
                TeachingAssignmentTeacher,
                TeachingAssignmentTeacher.teaching_assignment_id == TeachingAssignment.id,
            )
            .where(
                TeachingAssignment.tenant_id == tenant_id,
                TeachingAssignment.school_id == school_id,
                TeachingAssignment.term_id == term_id,
                TeachingAssignmentTeacher.teacher_id == teacher_id,
            )
        )
        or 0
    )


def _coverage_status(required: int | None, assigned: int) -> str:
    if required is None:
        return "no_requirement"
    if assigned == 0 and required > 0:
        return "missing"
    if assigned < required:
        return "partial"
    if assigned == required:
        return "complete"
    return "over"


def _offering_required(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    offering_id: uuid.UUID,
    subject_id: uuid.UUID,
) -> int | None:
    offering = db.scalar(
        select(SectionOffering).where(
            SectionOffering.id == offering_id,
            SectionOffering.tenant_id == tenant_id,
            SectionOffering.school_id == school_id,
        )
    )
    section = db.get(Section, offering.section_id) if offering else None
    if section is None:
        fail("section_offering_not_in_term")
    return db.scalar(
        select(CurriculumRequirement.weekly_occurrences).where(
            CurriculumRequirement.tenant_id == tenant_id,
            CurriculumRequirement.school_id == school_id,
            CurriculumRequirement.grade_id == section.grade_id,
            CurriculumRequirement.subject_id == subject_id,
        )
    )


def _offering_coverage(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    term_id: uuid.UUID,
    offering_id: uuid.UUID,
    subject_id: uuid.UUID,
    *,
    exclude_assignment_id: uuid.UUID | None = None,
) -> int:
    query = (
        select(func.coalesce(func.sum(TeachingAssignment.weekly_occurrences), 0))
        .join(
            TeachingAssignmentSection,
            TeachingAssignmentSection.teaching_assignment_id == TeachingAssignment.id,
        )
        .where(
            TeachingAssignment.tenant_id == tenant_id,
            TeachingAssignment.school_id == school_id,
            TeachingAssignment.term_id == term_id,
            TeachingAssignment.subject_id == subject_id,
            TeachingAssignmentSection.section_offering_id == offering_id,
        )
    )
    if exclude_assignment_id is not None:
        query = query.where(TeachingAssignment.id != exclude_assignment_id)
    return int(db.scalar(query) or 0)


def preview_assignment(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: dict[str, Any]
) -> AssignmentPreview:
    _school(db, tenant_id, school_id)
    preview_data = parse(AssignmentPreviewInput, payload)
    data = AssignmentInput.model_validate(preview_data.model_dump(exclude={"assignment_id"}))
    existing = None
    if preview_data.assignment_id is not None:
        existing = db.scalar(
            select(TeachingAssignment).where(
                TeachingAssignment.id == preview_data.assignment_id,
                TeachingAssignment.tenant_id == tenant_id,
                TeachingAssignment.school_id == school_id,
            )
        )
        if existing is None:
            fail("assignment_not_in_school", 404)
    _validate_assignment(db, tenant_id, school_id, data, existing=existing)
    old_offering_ids = (
        set(
            db.scalars(
                select(TeachingAssignmentSection.section_offering_id).where(
                    TeachingAssignmentSection.teaching_assignment_id == existing.id
                )
            )
        )
        if existing and existing.term_id == data.term_id and existing.subject_id == data.subject_id
        else set()
    )
    coverage: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for offering_id in old_offering_ids | set(data.section_offering_ids):
        required = _offering_required(db, tenant_id, school_id, offering_id, data.subject_id)
        current = _offering_coverage(
            db, tenant_id, school_id, data.term_id, offering_id, data.subject_id
        )
        old_value = existing.weekly_occurrences if existing and offering_id in old_offering_ids else 0
        new_value = data.weekly_occurrences if offering_id in data.section_offering_ids else 0
        delta = new_value - old_value
        projected = current + delta
        status = _coverage_status(required, projected)
        coverage.append(
            {
                "offering_id": offering_id,
                "required": required,
                "current_assigned": current,
                "delta": delta,
                "projected_assigned": projected,
                "projected_status": status,
            }
        )
        if status == "over":
            warnings.append(
                {"code": "curriculum_over_assigned", "offering_id": offering_id, "value": projected}
            )
    old_teacher_ids = (
        set(
            db.scalars(
                select(TeachingAssignmentTeacher.teacher_id).where(
                    TeachingAssignmentTeacher.teaching_assignment_id == existing.id
                )
            )
        )
        if existing and existing.term_id == data.term_id
        else set()
    )
    workloads: list[dict[str, Any]] = []
    for teacher_id in old_teacher_ids | set(data.teacher_ids):
        current = _teacher_workload(db, tenant_id, school_id, data.term_id, teacher_id)
        teacher = db.get(Teacher, teacher_id)
        limit = teacher.teaching_workload_limit if teacher else 0
        old_value = existing.weekly_occurrences if existing and teacher_id in old_teacher_ids else 0
        new_value = data.weekly_occurrences if teacher_id in data.teacher_ids else 0
        delta = new_value - old_value
        projected = current + delta
        exceeds = projected > limit
        workloads.append(
            {
                "teacher_id": teacher_id,
                "current_workload": current,
                "delta": delta,
                "projected_workload": projected,
                "teaching_workload_limit": limit,
                "exceeds_limit": exceeds,
            }
        )
        if exceeds:
            warnings.append(
                {"code": "teacher_workload_exceeded", "teacher_id": teacher_id, "value": projected}
            )
    return AssignmentPreview(
        can_apply=True, coverage=coverage, teacher_workloads=workloads, warnings=warnings
    )


def preview_bulk_assignment(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: dict[str, Any]
) -> AssignmentPreview:
    _school(db, tenant_id, school_id)
    data = parse(BulkAssignmentInput, payload)
    coverage: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    total_delta = 0
    for offering_id in data.section_offering_ids:
        required = _offering_required(db, tenant_id, school_id, offering_id, data.subject_id)
        current = _offering_coverage(
            db, tenant_id, school_id, data.term_id, offering_id, data.subject_id
        )
        action = "apply"
        if data.fill_from_curriculum:
            if required is None:
                delta = 0
                action = "skip_no_requirement"
            else:
                delta = max(required - current, 0)
                if delta == 0:
                    action = "skip_complete" if current == required else "skip_over"
        else:
            delta = data.weekly_occurrences or 0
        projected = current + delta
        coverage.append(
            {
                "offering_id": offering_id,
                "required": required,
                "current_assigned": current,
                "delta": delta,
                "projected_assigned": projected,
                "projected_status": _coverage_status(required, projected),
                "action": action,
            }
        )
        total_delta += delta
        if action != "apply":
            warnings.append({"code": action, "offering_id": offering_id})
        elif _coverage_status(required, projected) == "over":
            warnings.append(
                {"code": "curriculum_over_assigned", "offering_id": offering_id, "value": projected}
            )
    validation_count = next((item["delta"] for item in coverage if item["delta"] > 0), 1)
    _validate_assignment(
        db,
        tenant_id,
        school_id,
        AssignmentInput(
            term_id=data.term_id,
            subject_id=data.subject_id,
            weekly_occurrences=validation_count,
            teacher_ids=data.teacher_ids,
            section_offering_ids=data.section_offering_ids,
            resource_ids=data.resource_ids,
        ),
    )
    workloads: list[dict[str, Any]] = []
    for teacher_id in data.teacher_ids:
        current = _teacher_workload(db, tenant_id, school_id, data.term_id, teacher_id)
        teacher = db.get(Teacher, teacher_id)
        limit = teacher.teaching_workload_limit if teacher else 0
        projected = current + total_delta
        exceeds = projected > limit
        workloads.append(
            {
                "teacher_id": teacher_id,
                "current_workload": current,
                "delta": total_delta,
                "projected_workload": projected,
                "teaching_workload_limit": limit,
                "exceeds_limit": exceeds,
            }
        )
        if exceeds:
            warnings.append(
                {"code": "teacher_workload_exceeded", "teacher_id": teacher_id, "value": projected}
            )
    return AssignmentPreview(
        can_apply=any(item["action"] == "apply" for item in coverage),
        coverage=coverage,
        teacher_workloads=workloads,
        warnings=warnings,
    )


def _overlapping_other_school_workload(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    current_term: Term,
    teacher_id: uuid.UUID,
) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(TeachingAssignment.weekly_occurrences), 0))
            .join(
                TeachingAssignmentTeacher,
                TeachingAssignmentTeacher.teaching_assignment_id == TeachingAssignment.id,
            )
            .join(Term, Term.id == TeachingAssignment.term_id)
            .where(
                TeachingAssignment.tenant_id == tenant_id,
                TeachingAssignment.school_id != school_id,
                TeachingAssignmentTeacher.teacher_id == teacher_id,
                Term.starts_on <= current_term.ends_on,
                Term.ends_on >= current_term.starts_on,
            )
        )
        or 0
    )


def delete_assignment(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    assignment_id: uuid.UUID,
) -> None:
    assignment = db.scalar(
        select(TeachingAssignment).where(
            TeachingAssignment.id == assignment_id,
            TeachingAssignment.tenant_id == tenant_id,
            TeachingAssignment.school_id == school_id,
        )
    )
    if assignment is None:
        fail("assignment_not_in_school", 404)
    db.delete(assignment)
    commit(db)


def bulk_assign(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: dict[str, Any]
) -> list[dict[str, Any]]:
    data = parse(BulkAssignmentInput, payload)
    preview = preview_bulk_assignment(db, tenant_id, school_id, payload)
    projections = {item.offering_id: item for item in preview.coverage}
    results = []
    for offering_id in data.section_offering_ids:
        projection = projections[offering_id]
        count = projection.delta
        if projection.action != "apply" or count <= 0:
            continue
        results.append(
            save_assignment(
                db,
                tenant_id,
                school_id,
                {
                    "term_id": data.term_id,
                    "subject_id": data.subject_id,
                    "weekly_occurrences": count,
                    "teacher_ids": data.teacher_ids,
                    "section_offering_ids": [offering_id],
                    "resource_ids": data.resource_ids,
                },
                commit_changes=False,
            )
        )
    commit(db)
    return results


def bulk_replace_teachers(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: dict[str, Any]
) -> list[dict[str, Any]]:
    data = parse(BulkTeacherInput, payload)
    results = []
    for assignment_id in data.assignment_ids:
        assignment = db.scalar(
            select(TeachingAssignment).where(
                TeachingAssignment.id == assignment_id,
                TeachingAssignment.tenant_id == tenant_id,
                TeachingAssignment.school_id == school_id,
                TeachingAssignment.term_id == data.term_id,
            )
        )
        if assignment is None:
            fail("assignment_not_in_term")
        results.append(
            save_assignment(
                db,
                tenant_id,
                school_id,
                {
                    "term_id": assignment.term_id,
                    "subject_id": assignment.subject_id,
                    "weekly_occurrences": assignment.weekly_occurrences,
                    "teacher_ids": data.teacher_ids,
                    "section_offering_ids": list(
                        db.scalars(
                            select(TeachingAssignmentSection.section_offering_id).where(
                                TeachingAssignmentSection.teaching_assignment_id == assignment.id
                            )
                        )
                    ),
                    "resource_ids": list(
                        db.scalars(
                            select(TeachingAssignmentResource.resource_id).where(
                                TeachingAssignmentResource.teaching_assignment_id == assignment.id
                            )
                        )
                    ),
                    "notes": assignment.notes,
                },
                assignment.id,
                commit_changes=False,
            )
        )
    commit(db)
    return results


def bulk_delete_assignments(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: dict[str, Any]
) -> int:
    data = parse(BulkDeleteInput, payload)
    assignments = list(
        db.scalars(
            select(TeachingAssignment).where(
                TeachingAssignment.id.in_(data.assignment_ids),
                TeachingAssignment.tenant_id == tenant_id,
                TeachingAssignment.school_id == school_id,
                TeachingAssignment.term_id == data.term_id,
            )
        )
    )
    if len(assignments) != len(set(data.assignment_ids)):
        fail("assignment_not_in_term")
    for assignment in assignments:
        db.delete(assignment)
    commit(db)
    return len(assignments)


def assignment_snapshot(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, term_id: uuid.UUID
) -> dict[str, Any]:
    current_school = _school(db, tenant_id, school_id)
    current_term = _term(db, tenant_id, school_id, term_id)
    years = list(
        db.scalars(
            select(AcademicYear).where(
                AcademicYear.tenant_id == tenant_id, AcademicYear.school_id == school_id
            )
        )
    )
    year_ids = [item.id for item in years]
    terms = list(
        db.scalars(
            select(Term).where(Term.tenant_id == tenant_id, Term.academic_year_id.in_(year_ids))
        )
    )
    contexts = db.execute(
        select(Section, Grade, Stage)
        .join(Grade, Grade.id == Section.grade_id)
        .join(Stage, Stage.id == Grade.stage_id)
        .where(
            Section.tenant_id == tenant_id,
            Grade.tenant_id == tenant_id,
            Stage.tenant_id == tenant_id,
            Stage.school_id == school_id,
        )
    ).all()
    section_rows: list[dict[str, Any]] = [
        {
            "id": section.id,
            "name_ar": section.name_ar,
            "grade_id": grade.id,
            "grade_name": grade.name_ar,
            "stage_id": stage.id,
            "stage_name": stage.name_ar,
        }
        for section, grade, stage in contexts
    ]
    offerings = list(
        db.scalars(
            select(SectionOffering).where(
                SectionOffering.tenant_id == tenant_id,
                SectionOffering.school_id == school_id,
                SectionOffering.term_id == term_id,
            )
        )
    )
    assignments = list(
        db.scalars(
            select(TeachingAssignment).where(
                TeachingAssignment.tenant_id == tenant_id,
                TeachingAssignment.school_id == school_id,
                TeachingAssignment.term_id == term_id,
            )
        )
    )
    assignment_rows: list[dict[str, Any]] = []
    for assignment in assignments:
        teacher_ids = list(
            db.scalars(
                select(TeachingAssignmentTeacher.teacher_id).where(
                    TeachingAssignmentTeacher.teaching_assignment_id == assignment.id
                )
            )
        )
        offering_ids = list(
            db.scalars(
                select(TeachingAssignmentSection.section_offering_id).where(
                    TeachingAssignmentSection.teaching_assignment_id == assignment.id
                )
            )
        )
        resource_ids = list(
            db.scalars(
                select(TeachingAssignmentResource.resource_id).where(
                    TeachingAssignmentResource.teaching_assignment_id == assignment.id
                )
            )
        )
        assignment_rows.append(
            {
                "id": assignment.id,
                "term_id": assignment.term_id,
                "subject_id": assignment.subject_id,
                "weekly_occurrences": assignment.weekly_occurrences,
                "teacher_ids": teacher_ids,
                "section_offering_ids": offering_ids,
                "resource_ids": resource_ids,
                "notes": assignment.notes,
            }
        )
    subjects = list(
        db.scalars(
            select(Subject).where(Subject.tenant_id == tenant_id, Subject.school_id == school_id)
        )
    )
    requirements = list(
        db.scalars(
            select(CurriculumRequirement).where(
                CurriculumRequirement.tenant_id == tenant_id,
                CurriculumRequirement.school_id == school_id,
            )
        )
    )
    requirements_map = {
        (item.grade_id, item.subject_id): item.weekly_occurrences for item in requirements
    }
    section_map = {item["id"]: item for item in section_rows}
    cells: list[dict[str, Any]] = []
    for offering in offerings:
        if not offering.is_active:
            continue
        section = section_map[offering.section_id]
        for subject in subjects:
            required = requirements_map.get((section["grade_id"], subject.id))
            assigned = sum(
                item["weekly_occurrences"]
                for item in assignment_rows
                if item["subject_id"] == subject.id and offering.id in item["section_offering_ids"]
            )
            status = (
                "no_requirement"
                if required is None
                else "missing"
                if assigned == 0
                else "partial"
                if assigned < required
                else "complete"
                if assigned == required
                else "over"
            )
            cells.append(
                {
                    "offering_id": offering.id,
                    "subject_id": subject.id,
                    "required": required,
                    "assigned": assigned,
                    "status": status,
                    "assignment_ids": [
                        item["id"]
                        for item in assignment_rows
                        if item["subject_id"] == subject.id
                        and offering.id in item["section_offering_ids"]
                    ],
                }
            )
    memberships = list(
        db.scalars(
            select(TeacherSchoolMembership).where(
                TeacherSchoolMembership.tenant_id == tenant_id,
                TeacherSchoolMembership.school_id == school_id,
                TeacherSchoolMembership.is_active.is_(True),
            )
        )
    )
    teacher_rows = []
    for membership in memberships:
        teacher = db.get(Teacher, membership.teacher_id)
        if teacher and teacher.is_active:
            teacher_rows.append(
                {
                    "id": teacher.id,
                    "name_ar": teacher.name_ar,
                    "base_workload": teacher.base_workload,
                    "teaching_workload_limit": teacher.teaching_workload_limit,
                    "assigned_workload": _teacher_workload(
                        db, tenant_id, school_id, term_id, teacher.id
                    ),
                    "other_school_overlapping_workload": _overlapping_other_school_workload(
                        db, tenant_id, school_id, current_term, teacher.id
                    ),
                }
            )
    return {
        "school": current_school,
        "selected_term": current_term,
        "years": years,
        "terms": terms,
        "shifts": list(
            db.scalars(
                select(SchoolShift).where(
                    SchoolShift.tenant_id == tenant_id,
                    SchoolShift.school_id == school_id,
                    SchoolShift.is_active.is_(True),
                )
            )
        ),
        "sections": section_rows,
        "offerings": offerings,
        "subjects": subjects,
        "resources": list(
            db.scalars(
                select(Resource).where(
                    Resource.tenant_id == tenant_id,
                    Resource.school_id == school_id,
                    Resource.is_active.is_(True),
                )
            )
        ),
        "teachers": teacher_rows,
        "assignments": assignment_rows,
        "cells": cells,
    }

import uuid
from typing import Any, NoReturn

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.master_schemas import (
    CurriculumInput,
    MembershipInput,
    MembershipUpdateInput,
    NewTeacherInput,
    ResourceInput,
    SubjectInput,
    TeacherInput,
)
from app.models import (
    CurriculumRequirement,
    Grade,
    Resource,
    School,
    Stage,
    Subject,
    Teacher,
    TeacherSchoolMembership,
    TeachingAssignment,
    TeachingAssignmentResource,
    TeachingAssignmentTeacher,
)


def fail(code: str, status_code: int = 422) -> NoReturn:
    raise HTTPException(status_code=status_code, detail={"code": code})


def school(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID) -> School:
    entity = db.scalar(select(School).where(School.id == school_id, School.tenant_id == tenant_id))
    if entity is None:
        fail("school_not_found", 404)
    return entity


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
        raise HTTPException(
            status_code=409, detail={"code": "duplicate_or_dependent_data"}
        ) from exc


def _teacher(db: Session, tenant_id: uuid.UUID, teacher_id: uuid.UUID) -> Teacher:
    entity = db.scalar(
        select(Teacher).where(Teacher.id == teacher_id, Teacher.tenant_id == tenant_id)
    )
    if entity is None:
        fail("teacher_not_in_tenant")
    return entity


def _membership(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, membership_id: uuid.UUID
) -> TeacherSchoolMembership:
    entity = db.scalar(
        select(TeacherSchoolMembership).where(
            TeacherSchoolMembership.id == membership_id,
            TeacherSchoolMembership.tenant_id == tenant_id,
            TeacherSchoolMembership.school_id == school_id,
        )
    )
    if entity is None:
        fail("membership_not_in_school", 404)
    return entity


def _clear_home(
    db: Session, tenant_id: uuid.UUID, teacher_id: uuid.UUID, except_id: uuid.UUID | None = None
) -> None:
    statement = update(TeacherSchoolMembership).where(
        TeacherSchoolMembership.tenant_id == tenant_id,
        TeacherSchoolMembership.teacher_id == teacher_id,
        TeacherSchoolMembership.is_home_school.is_(True),
    )
    if except_id is not None:
        statement = statement.where(TeacherSchoolMembership.id != except_id)
    db.execute(statement.values(is_home_school=False))


def teacher_snapshot(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID) -> dict[str, Any]:
    current_school = school(db, tenant_id, school_id)
    memberships = list(
        db.scalars(
            select(TeacherSchoolMembership).where(
                TeacherSchoolMembership.tenant_id == tenant_id,
                TeacherSchoolMembership.school_id == school_id,
            )
        )
    )
    cards = []
    for membership in memberships:
        teacher = _teacher(db, tenant_id, membership.teacher_id)
        all_memberships = list(
            db.scalars(
                select(TeacherSchoolMembership).where(
                    TeacherSchoolMembership.tenant_id == tenant_id,
                    TeacherSchoolMembership.teacher_id == teacher.id,
                )
            )
        )
        linked_schools = []
        for item in all_memberships:
            linked_school = school(db, tenant_id, item.school_id)
            linked_schools.append(
                {
                    "school_id": linked_school.id,
                    "name_ar": linked_school.name_ar,
                    "code": linked_school.code,
                    "is_home_school": item.is_home_school,
                    "is_active": item.is_active,
                    "local_employee_code": item.local_employee_code,
                    "is_current_school": item.school_id == school_id,
                }
            )
        assigned = (
            db.scalar(
                select(func.coalesce(func.sum(TeachingAssignment.weekly_occurrences), 0))
                .select_from(TeachingAssignmentTeacher)
                .join(
                    TeachingAssignment,
                    TeachingAssignment.id == TeachingAssignmentTeacher.teaching_assignment_id,
                )
                .where(
                    TeachingAssignmentTeacher.tenant_id == tenant_id,
                    TeachingAssignmentTeacher.teacher_id == teacher.id,
                    TeachingAssignment.school_id == school_id,
                )
            )
            or 0
        )
        cards.append(
            {
                "teacher": teacher,
                "membership": membership,
                "schools": linked_schools,
                "is_shared": sum(item.is_active for item in all_memberships) > 1,
                "assigned_workload": assigned,
            }
        )
    linked_ids = {membership.teacher_id for membership in memberships}
    available = list(
        db.scalars(
            select(Teacher)
            .where(
                Teacher.tenant_id == tenant_id,
                Teacher.is_active.is_(True),
                Teacher.id.not_in(linked_ids) if linked_ids else Teacher.id.is_not(None),
            )
            .order_by(Teacher.name_ar)
        )
    )
    return {"school": current_school, "teachers": cards, "available_teachers": available}


def create_teacher(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    payload: dict[str, Any],
    *,
    commit_changes: bool = True,
) -> TeacherSchoolMembership:
    school(db, tenant_id, school_id)
    data = parse(NewTeacherInput, payload)
    if not data.is_active:
        fail("archived_teacher_cannot_have_active_membership", 409)
    values = data.model_dump(exclude={"local_employee_code", "is_home_school"})
    teacher = Teacher(id=uuid.uuid4(), tenant_id=tenant_id, **values)
    db.add(teacher)
    membership = TeacherSchoolMembership(
        tenant_id=tenant_id,
        teacher_id=teacher.id,
        school_id=school_id,
        local_employee_code=data.local_employee_code,
        is_home_school=data.is_home_school,
        is_active=True,
    )
    db.add(membership)
    if commit_changes:
        commit(db)
    else:
        db.flush()
    db.refresh(membership)
    return membership


def link_teacher(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    payload: dict[str, Any],
    *,
    commit_changes: bool = True,
) -> TeacherSchoolMembership:
    school(db, tenant_id, school_id)
    data = parse(MembershipInput, payload)
    teacher = _teacher(db, tenant_id, data.teacher_id)
    if db.scalar(
        select(TeacherSchoolMembership.id).where(
            TeacherSchoolMembership.tenant_id == tenant_id,
            TeacherSchoolMembership.teacher_id == data.teacher_id,
            TeacherSchoolMembership.school_id == school_id,
        )
    ):
        fail("membership_already_exists_use_reactivation", 409)
    if data.is_active and not teacher.is_active:
        fail("archived_teacher_cannot_have_active_membership", 409)
    membership = TeacherSchoolMembership(
        tenant_id=tenant_id, school_id=school_id, **data.model_dump()
    )
    if data.is_home_school and data.is_active:
        _clear_home(db, tenant_id, data.teacher_id)
    db.add(membership)
    if commit_changes:
        commit(db)
    else:
        db.flush()
    db.refresh(membership)
    return membership


def update_teacher(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    teacher_id: uuid.UUID,
    payload: dict[str, Any],
    *,
    commit_changes: bool = True,
) -> Teacher:
    school(db, tenant_id, school_id)
    teacher = _teacher(db, tenant_id, teacher_id)
    if not db.scalar(
        select(TeacherSchoolMembership.id).where(
            TeacherSchoolMembership.tenant_id == tenant_id,
            TeacherSchoolMembership.school_id == school_id,
            TeacherSchoolMembership.teacher_id == teacher_id,
        )
    ):
        fail("teacher_not_in_school", 404)
    data = parse(TeacherInput, payload)
    if not data.is_active and db.scalar(
        select(TeacherSchoolMembership.id).where(
            TeacherSchoolMembership.tenant_id == tenant_id,
            TeacherSchoolMembership.teacher_id == teacher_id,
            TeacherSchoolMembership.is_active.is_(True),
        )
    ):
        fail("teacher_has_active_memberships", 409)
    for key, value in data.model_dump().items():
        setattr(teacher, key, value)
    if commit_changes:
        commit(db)
    else:
        db.flush()
    db.refresh(teacher)
    return teacher


def update_membership(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    membership_id: uuid.UUID,
    payload: dict[str, Any],
) -> TeacherSchoolMembership:
    membership = _membership(db, tenant_id, school_id, membership_id)
    data = parse(MembershipUpdateInput, payload)
    teacher = _teacher(db, tenant_id, membership.teacher_id)
    if (
        not data.is_active
        and membership.is_active
        and db.scalar(
            select(TeachingAssignmentTeacher.id)
            .join(
                TeachingAssignment,
                TeachingAssignment.id == TeachingAssignmentTeacher.teaching_assignment_id,
            )
            .where(
                TeachingAssignmentTeacher.tenant_id == tenant_id,
                TeachingAssignmentTeacher.teacher_id == membership.teacher_id,
                TeachingAssignment.school_id == school_id,
            )
        )
    ):
        fail("teacher_membership_has_assignments", 409)
    if data.is_active and not teacher.is_active:
        fail("archived_teacher_cannot_have_active_membership", 409)
    if data.is_home_school and data.is_active:
        _clear_home(db, tenant_id, membership.teacher_id, membership.id)
    for key, value in data.model_dump().items():
        setattr(membership, key, value)
    commit(db)
    db.refresh(membership)
    return membership


def unlink_teacher(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, membership_id: uuid.UUID
) -> None:
    membership = _membership(db, tenant_id, school_id, membership_id)
    used = db.scalar(
        select(func.count())
        .select_from(TeachingAssignmentTeacher)
        .join(
            TeachingAssignment,
            TeachingAssignment.id == TeachingAssignmentTeacher.teaching_assignment_id,
        )
        .where(
            TeachingAssignmentTeacher.tenant_id == tenant_id,
            TeachingAssignmentTeacher.teacher_id == membership.teacher_id,
            TeachingAssignment.school_id == school_id,
        )
    )
    if used:
        fail("teacher_membership_has_assignments", 409)
    db.delete(membership)
    commit(db)


def catalog_snapshot(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID) -> dict[str, Any]:
    current_school = school(db, tenant_id, school_id)
    stages = list(
        db.scalars(select(Stage).where(Stage.tenant_id == tenant_id, Stage.school_id == school_id))
    )
    stage_ids = [stage.id for stage in stages]
    grades = (
        list(
            db.scalars(
                select(Grade).where(Grade.tenant_id == tenant_id, Grade.stage_id.in_(stage_ids))
            )
        )
        if stage_ids
        else []
    )
    return {
        "school": current_school,
        "subjects": list(
            db.scalars(
                select(Subject).where(
                    Subject.tenant_id == tenant_id, Subject.school_id == school_id
                )
            )
        ),
        "resources": list(
            db.scalars(
                select(Resource).where(
                    Resource.tenant_id == tenant_id, Resource.school_id == school_id
                )
            )
        ),
        "grades": grades,
        "stages": stages,
        "requirements": list(
            db.scalars(
                select(CurriculumRequirement).where(
                    CurriculumRequirement.tenant_id == tenant_id,
                    CurriculumRequirement.school_id == school_id,
                )
            )
        ),
    }


def save_catalog(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    kind: str,
    payload: dict[str, Any],
    entity_id: uuid.UUID | None = None,
    *,
    commit_changes: bool = True,
) -> Any:
    school(db, tenant_id, school_id)
    mapping: dict[str, tuple[Any, Any]] = {
        "subjects": (Subject, SubjectInput),
        "resources": (Resource, ResourceInput),
        "requirements": (CurriculumRequirement, CurriculumInput),
    }
    if kind not in mapping:
        fail("unknown_catalog_resource", 404)
    model, schema = mapping[kind]
    data = parse(schema, payload)
    values = data.model_dump()
    if kind == "requirements":
        grade = db.scalar(
            select(Grade)
            .join(Stage, Stage.id == Grade.stage_id)
            .where(
                Grade.id == data.grade_id,
                Grade.tenant_id == tenant_id,
                Stage.school_id == school_id,
            )
        )
        subject = db.scalar(
            select(Subject).where(
                Subject.id == data.subject_id,
                Subject.tenant_id == tenant_id,
                Subject.school_id == school_id,
            )
        )
        if grade is None:
            fail("grade_not_in_school")
        if subject is None:
            fail("subject_not_in_school")
    entity = (
        model(tenant_id=tenant_id, school_id=school_id, **values)
        if entity_id is None
        else db.scalar(
            select(model).where(
                model.id == entity_id, model.tenant_id == tenant_id, model.school_id == school_id
            )
        )
    )
    if entity is None:
        fail("catalog_resource_not_in_school", 404)
    if entity_id is None:
        db.add(entity)
    else:
        if (
            kind == "resources"
            and entity.is_active
            and not data.is_active
            and db.scalar(
                select(TeachingAssignmentResource.id)
                .join(
                    TeachingAssignment,
                    TeachingAssignment.id
                    == TeachingAssignmentResource.teaching_assignment_id,
                )
                .where(
                    TeachingAssignmentResource.tenant_id == tenant_id,
                    TeachingAssignmentResource.resource_id == entity_id,
                    TeachingAssignment.school_id == school_id,
                )
            )
        ):
            fail("resource_has_assignments", 409)
        for key, value in values.items():
            setattr(entity, key, value)
    if commit_changes:
        commit(db)
    else:
        db.flush()
    db.refresh(entity)
    return entity


def delete_catalog(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, kind: str, entity_id: uuid.UUID
) -> None:
    mapping: dict[str, Any] = {
        "subjects": Subject,
        "resources": Resource,
        "requirements": CurriculumRequirement,
    }
    if kind not in mapping:
        fail("unknown_catalog_resource", 404)
    model = mapping[kind]
    entity = db.scalar(
        select(model).where(
            model.id == entity_id, model.tenant_id == tenant_id, model.school_id == school_id
        )
    )
    if entity is None:
        fail("catalog_resource_not_in_school", 404)
    if kind == "subjects":
        if db.scalar(
            select(func.count())
            .select_from(CurriculumRequirement)
            .where(CurriculumRequirement.subject_id == entity_id)
        ) or db.scalar(
            select(func.count())
            .select_from(TeachingAssignment)
            .where(TeachingAssignment.subject_id == entity_id)
        ):
            fail("subject_has_dependencies", 409)
    if kind == "resources":
        if db.scalar(
            select(TeachingAssignmentResource.id)
            .join(
                TeachingAssignment,
                TeachingAssignment.id == TeachingAssignmentResource.teaching_assignment_id,
            )
            .where(
                TeachingAssignmentResource.tenant_id == tenant_id,
                TeachingAssignmentResource.resource_id == entity_id,
                TeachingAssignment.school_id == school_id,
            )
        ):
            fail("resource_has_dependencies", 409)
    db.delete(entity)
    commit(db)

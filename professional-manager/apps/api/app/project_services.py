import uuid
from collections import Counter, defaultdict
from typing import Any
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models import (
    AcademicYear,
    Grade,
    PeriodTemplate,
    Resource,
    SchedulingRule,
    School,
    SchoolDay,
    Section,
    SectionOffering,
    Stage,
    Teacher,
    TeacherSchoolMembership,
    TeachingAssignment,
    TeachingAssignmentResource,
    TeachingAssignmentSection,
    TeachingAssignmentTeacher,
    Term,
    TimetableProject,
    TimetableProjectSchool,
    WeekPattern,
)
from app.project_schemas import ProjectInput, RuleInput
from pm_scheduler.contracts import LocalTimeSlot, TimeSlot
from pm_scheduler.cycle import expand_project_slots

MAX_CYCLE = 12
RULE_REGISTRY = {
    "teacher_unavailable": ("teacher_id", {"hard"}, "عدم توفر المعلم"),
    "section_unavailable": ("section_id", {"hard"}, "عدم توفر الشعبة"),
    "resource_unavailable": ("resource_id", {"hard"}, "عدم توفر المورد"),
    "assignment_forbidden_time": ("assignment_id", {"hard"}, "وقت ممنوع للإسناد"),
    "assignment_required_time": ("assignment_id", {"hard"}, "وقت مطلوب للإسناد"),
    "teacher_preferred_time": ("teacher_id", {"soft"}, "وقت مفضل للمعلم"),
    "teacher_avoided_time": ("teacher_id", {"soft"}, "وقت غير مفضل للمعلم"),
    "assignment_preferred_time": ("assignment_id", {"soft"}, "وقت مفضل للإسناد"),
    "assignment_avoided_time": ("assignment_id", {"soft"}, "وقت غير مفضل للإسناد"),
}


class Occurrence(BaseModel):
    id: str
    assignment_id: str
    project_cycle_week_index: int
    teacher_ids: list[str]
    section_ids: list[str]
    resource_ids: list[str]
    candidate_slot_ids: list[str]


class Problem(BaseModel):
    project_id: str
    project_cycle_length: int
    school_ids: list[str]
    slots: list[TimeSlot]
    occurrences: list[Occurrence]
    rules: list[dict[str, Any]]


def _project(db: Session, tenant: uuid.UUID, project_id: uuid.UUID) -> TimetableProject:
    value = db.scalar(
        select(TimetableProject).where(
            TimetableProject.id == project_id, TimetableProject.tenant_id == tenant
        )
    )
    if not value:
        raise HTTPException(404, detail={"code": "project_not_found"})
    return value


def _validate_scope(
    db: Session, tenant: uuid.UUID, data: ProjectInput
) -> list[tuple[School, Term, int]]:
    if not data.schools or len({x.school_id for x in data.schools}) != len(data.schools):
        raise HTTPException(422, detail={"code": "invalid_project_school_scope"})
    if data.scope_type == "school" and len(data.schools) != 1:
        raise HTTPException(422, detail={"code": "single_school_required"})
    result = []
    for item in data.schools:
        school = db.scalar(
            select(School).where(School.id == item.school_id, School.tenant_id == tenant)
        )
        term = db.scalar(
            select(Term)
            .join(AcademicYear, AcademicYear.id == Term.academic_year_id)
            .where(
                Term.id == item.term_id,
                Term.tenant_id == tenant,
                AcademicYear.school_id == item.school_id,
            )
        )
        patterns = list(
            db.scalars(
                select(WeekPattern).where(
                    WeekPattern.tenant_id == tenant, WeekPattern.school_id == item.school_id
                )
            )
        )
        length = len({p.cycle_week_index for p in patterns}) or 1
        if not school or not term:
            raise HTTPException(422, detail={"code": "term_not_in_project_school"})
        if item.cycle_phase_offset >= length:
            raise HTTPException(422, detail={"code": "invalid_cycle_phase_offset"})
        result.append((school, term, item.cycle_phase_offset))
    return result


def save_project(
    db: Session, tenant: uuid.UUID, data: ProjectInput, project_id: uuid.UUID | None = None
) -> TimetableProject:
    scope = _validate_scope(db, tenant, data)
    project = (
        _project(db, tenant, project_id)
        if project_id
        else TimetableProject(tenant_id=tenant, settings={}, status="draft")
    )
    if project.status != "draft":
        raise HTTPException(409, detail={"code": "project_not_draft"})
    project.name_ar = data.name_ar
    project.description = data.description
    project.scope_type = data.scope_type
    project.complex_id = data.complex_id
    db.add(project)
    db.flush()
    if project_id:
        db.query(TimetableProjectSchool).filter_by(
            tenant_id=tenant, timetable_project_id=project.id
        ).delete()
    for school, term, offset in scope:
        db.add(
            TimetableProjectSchool(
                tenant_id=tenant,
                timetable_project_id=project.id,
                school_id=school.id,
                term_id=term.id,
                cycle_phase_offset=offset,
            )
        )
    db.commit()
    db.refresh(project)
    return project


def serialize_project(db: Session, project: TimetableProject) -> dict[str, Any]:
    scopes = list(
        db.scalars(
            select(TimetableProjectSchool)
            .where(TimetableProjectSchool.timetable_project_id == project.id)
            .order_by(TimetableProjectSchool.school_id)
        )
    )
    return {
        "id": project.id,
        "name_ar": project.name_ar,
        "description": project.description,
        "scope_type": project.scope_type,
        "complex_id": project.complex_id,
        "status": project.status,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "schools": [
            {
                "school_id": x.school_id,
                "term_id": x.term_id,
                "cycle_phase_offset": x.cycle_phase_offset,
            }
            for x in scopes
        ],
    }


def validate_rule(
    db: Session, tenant: uuid.UUID, project: TimetableProject, data: RuleInput
) -> None:
    spec = RULE_REGISTRY.get(data.rule_type)
    if not spec or data.severity not in spec[1]:
        raise HTTPException(422, detail={"code": "invalid_rule_schema"})
    target_key = spec[0]
    raw = data.selector.get(target_key)
    try:
        target = uuid.UUID(str(raw))
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "invalid_rule_target"}) from exc
    scopes = list(
        db.scalars(
            select(TimetableProjectSchool).where(
                TimetableProjectSchool.timetable_project_id == project.id
            )
        )
    )
    school_ids = {x.school_id for x in scopes}
    model: Any = {
        "teacher_id": Teacher,
        "section_id": Section,
        "resource_id": Resource,
        "assignment_id": TeachingAssignment,
    }[target_key]
    entity: Any = db.scalar(select(model).where(model.id == target, model.tenant_id == tenant))
    if not entity:
        raise HTTPException(422, detail={"code": "cross_tenant_rule_target"})
    if target_key == "teacher_id":
        valid = db.scalar(
            select(TeacherSchoolMembership.id).where(
                TeacherSchoolMembership.teacher_id == target,
                TeacherSchoolMembership.school_id.in_(school_ids),
            )
        )
    elif target_key == "section_id":
        valid = db.scalar(
            select(Section.id)
            .join(Grade)
            .join(Stage)
            .where(Section.id == target, Stage.school_id.in_(school_ids))
        )
    else:
        valid = entity.id if getattr(entity, "school_id", None) in school_ids else None
    if not valid:
        raise HTTPException(422, detail={"code": "cross_school_rule_target"})
    allowed = {
        "project_cycle_week_index",
        "weekday_index",
        "starts_at_minute",
        "ends_at_minute",
        "slot_id",
    }
    if set(data.parameters) - allowed:
        raise HTTPException(422, detail={"code": "invalid_rule_parameters"})


def save_rule(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    data: RuleInput,
    rule_id: uuid.UUID | None = None,
) -> SchedulingRule:
    project = _project(db, tenant, project_id)
    validate_rule(db, tenant, project, data)
    rule = (
        db.scalar(
            select(SchedulingRule).where(
                SchedulingRule.id == rule_id,
                SchedulingRule.tenant_id == tenant,
                SchedulingRule.timetable_project_id == project_id,
            )
        )
        if rule_id
        else SchedulingRule(tenant_id=tenant, timetable_project_id=project_id)
    )
    if not rule:
        raise HTTPException(404, detail={"code": "rule_not_found"})
    for k, v in data.model_dump().items():
        setattr(rule, k, v)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def _matches(slot: TimeSlot, params: dict[str, Any]) -> bool:
    return all(
        params.get(k) is None or getattr(slot, k) == params[k]
        for k in ("project_cycle_week_index", "weekday_index", "starts_at_minute", "ends_at_minute")
    ) and (not params.get("slot_id") or slot.id == params["slot_id"])


def build_problem(db: Session, tenant: uuid.UUID, project_id: uuid.UUID) -> Problem:
    project = _project(db, tenant, project_id)
    scopes = list(
        db.scalars(
            select(TimetableProjectSchool)
            .where(TimetableProjectSchool.timetable_project_id == project.id)
            .order_by(TimetableProjectSchool.school_id)
        )
    )
    if not scopes:
        return Problem(
            project_id=str(project.id),
            project_cycle_length=1,
            school_ids=[],
            slots=[],
            occurrences=[],
            rules=[],
        )
    local = []
    lengths = {}
    offsets = {}
    for scope in scopes:
        patterns = list(
            db.scalars(
                select(WeekPattern)
                .where(WeekPattern.tenant_id == tenant, WeekPattern.school_id == scope.school_id)
                .order_by(WeekPattern.cycle_week_index)
            )
        )
        indexes = [p.cycle_week_index for p in patterns]
        length = len(set(indexes)) or 1
        if indexes and sorted(set(indexes)) != list(range(length)):
            raise ValueError("non_contiguous_cycle")
        lengths[str(scope.school_id)] = length
        offsets[str(scope.school_id)] = scope.cycle_phase_offset
        pattern_index = {p.id: p.cycle_week_index for p in patterns}
        blocks = list(
            db.scalars(
                select(PeriodTemplate)
                .join(SchoolDay, SchoolDay.id == PeriodTemplate.school_day_id)
                .where(
                    PeriodTemplate.tenant_id == tenant,
                    PeriodTemplate.school_id == scope.school_id,
                    PeriodTemplate.block_type == "lesson",
                    PeriodTemplate.schedulable.is_(True),
                    SchoolDay.enabled.is_(True),
                )
                .order_by(PeriodTemplate.id)
            )
        )
        for b in blocks:
            local.append(
                LocalTimeSlot(
                    id=str(b.id),
                    school_id=str(scope.school_id),
                    week_pattern_id=str(b.week_pattern_id),
                    local_cycle_week_index=pattern_index[b.week_pattern_id],
                    weekday_index=b.weekday_index,
                    starts_at_minute=b.starts_at.hour * 60 + b.starts_at.minute,
                    ends_at_minute=b.ends_at.hour * 60 + b.ends_at.minute,
                    period=b.period_number or 1,
                    attendance_mode=b.attendance_mode,
                )
            )
    cycle, slots = expand_project_slots(local, lengths, offsets, MAX_CYCLE)
    rules = list(
        db.scalars(
            select(SchedulingRule)
            .where(
                SchedulingRule.tenant_id == tenant,
                SchedulingRule.timetable_project_id == project.id,
                SchedulingRule.enabled.is_(True),
            )
            .order_by(SchedulingRule.id)
        )
    )
    occurrences = []
    for scope in scopes:
        assignments = list(
            db.scalars(
                select(TeachingAssignment)
                .where(
                    TeachingAssignment.tenant_id == tenant,
                    TeachingAssignment.school_id == scope.school_id,
                    TeachingAssignment.term_id == scope.term_id,
                )
                .order_by(TeachingAssignment.id)
            )
        )
        for a in assignments:
            teachers = sorted(
                str(x)
                for x in db.scalars(
                    select(TeachingAssignmentTeacher.teacher_id).where(
                        TeachingAssignmentTeacher.teaching_assignment_id == a.id
                    )
                )
            )
            links = list(
                db.scalars(
                    select(TeachingAssignmentSection.section_offering_id).where(
                        TeachingAssignmentSection.teaching_assignment_id == a.id
                    )
                )
            )
            offerings = (
                list(db.scalars(select(SectionOffering).where(SectionOffering.id.in_(links))))
                if links
                else []
            )
            sections = sorted(str(x.section_id) for x in offerings)
            resources = sorted(
                str(x)
                for x in db.scalars(
                    select(TeachingAssignmentResource.resource_id).where(
                        TeachingAssignmentResource.teaching_assignment_id == a.id
                    )
                )
            )
            by_shift = {o.shift_id for o in offerings}
            base = [s for s in slots if s.school_id == str(scope.school_id)]
            if by_shift:
                shift_blocks = {
                    shift: {
                        str(x.id)
                        for x in db.scalars(
                            select(PeriodTemplate).where(
                                PeriodTemplate.shift_id == shift,
                                PeriodTemplate.block_type == "lesson",
                                PeriodTemplate.schedulable.is_(True),
                            )
                        )
                    }
                    for shift in by_shift
                }

                shift_times = [
                    {
                        (
                            s.project_cycle_week_index,
                            s.weekday_index,
                            s.starts_at_minute,
                            s.ends_at_minute,
                        )
                        for s in base
                        if s.id.split("@project-week-")[0] in block_ids
                    }
                    for block_ids in shift_blocks.values()
                ]
                common_times = set.intersection(*shift_times) if shift_times else set()
                base = [
                    s
                    for s in base
                    if (
                        s.project_cycle_week_index,
                        s.weekday_index,
                        s.starts_at_minute,
                        s.ends_at_minute,
                    )
                    in common_times
                ]
            hard = [
                r
                for r in rules
                if r.severity == "hard"
                and (
                    str(r.selector.get("assignment_id")) == str(a.id)
                    or any(str(r.selector.get("teacher_id")) == t for t in teachers)
                    or any(str(r.selector.get("section_id")) == s for s in sections)
                    or any(str(r.selector.get("resource_id")) == x for x in resources)
                )
            ]
            forbidden = [
                r
                for r in hard
                if r.rule_type.endswith("unavailable") or r.rule_type == "assignment_forbidden_time"
            ]
            required = [r for r in hard if r.rule_type == "assignment_required_time"]
            candidates = [s for s in base if not any(_matches(s, r.parameters) for r in forbidden)]
            if required:
                candidates = [
                    s for s in candidates if any(_matches(s, r.parameters) for r in required)
                ]
            for week in range(cycle):
                week_slots = sorted(s.id for s in candidates if s.project_cycle_week_index == week)
                for n in range(a.weekly_occurrences):
                    occurrences.append(
                        Occurrence(
                            id=f"{a.id}@project-week-{week}#occurrence-{n}",
                            assignment_id=str(a.id),
                            project_cycle_week_index=week,
                            teacher_ids=teachers,
                            section_ids=sections,
                            resource_ids=resources,
                            candidate_slot_ids=week_slots,
                        )
                    )
    return Problem(
        project_id=str(project.id),
        project_cycle_length=cycle,
        school_ids=sorted(str(x.school_id) for x in scopes),
        slots=sorted(slots, key=lambda s: s.id),
        occurrences=occurrences,
        rules=[
            {
                "id": str(r.id),
                "rule_type": r.rule_type,
                "severity": r.severity,
                "weight": r.weight,
                "selector": r.selector,
                "parameters": r.parameters,
            }
            for r in rules
        ],
    )


def preflight(db: Session, tenant: uuid.UUID, project_id: uuid.UUID) -> dict[str, Any]:
    diagnostics: list[dict[str, Any]] = []
    try:
        problem = build_problem(db, tenant, project_id)
    except Exception as exc:
        code = "project_cycle_limit_exceeded" if "maximum" in str(exc).lower() else str(exc)
        return {
            "readiness": "غير مكتمل",
            "errors": 1,
            "warnings": 0,
            "diagnostics": [
                {
                    "severity": "error",
                    "code": code,
                    "message": "دورة المشروع غير صالحة",
                    "suggested_remediation": "راجع أنماط الأسابيع والمحاذاة.",
                }
            ],
            "problem": None,
        }
    if not problem.school_ids:
        diagnostics.append(
            {
                "severity": "error",
                "code": "project_has_no_schools",
                "message": "المشروع بلا مدارس",
                "suggested_remediation": "أضف مدرسة وفصلًا دراسيًا.",
            }
        )
    if not problem.slots:
        diagnostics.append(
            {
                "severity": "error",
                "code": "no_lesson_slots",
                "message": "لا توجد حصص قابلة للجدولة",
                "suggested_remediation": "أضف حصصًا تدريسية مفعلة.",
            }
        )
    for occurrence in problem.occurrences:
        if not occurrence.teacher_ids:
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "assignment_without_teacher",
                    "message": "إسناد بلا معلم",
                    "affected_entities": {"assignment": [occurrence.assignment_id]},
                }
            )
        if not occurrence.section_ids:
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "assignment_without_section",
                    "message": "إسناد بلا شعبة",
                    "affected_entities": {"assignment": [occurrence.assignment_id]},
                }
            )
        if not occurrence.candidate_slot_ids:
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "occurrence_without_candidate_slot",
                    "message": "لا يوجد وقت مشترك صالح للحصة",
                    "affected_entities": {"assignment": [occurrence.assignment_id]},
                    "suggested_remediation": "راجع الشفتات والقواعد الإلزامية.",
                }
            )
    demand = Counter(t for o in problem.occurrences for t in o.teacher_ids)
    capacity = defaultdict(set)
    for o in problem.occurrences:
        for t in o.teacher_ids:
            capacity[t].update(o.candidate_slot_ids)
    for teacher, required in demand.items():
        available = len(capacity[teacher])
        if required > available:
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "teacher_capacity_shortage",
                    "message": "طلب المعلم يتجاوز الأوقات المتاحة",
                    "affected_entities": {"teacher": [teacher]},
                    "required": required,
                    "available": available,
                    "shortage": required - available,
                    "suggested_remediation": "وسع توفر المعلم أو خفف الإسناد.",
                }
            )
    for entity_type, attribute, code, message in (
        ("section", "section_ids", "section_capacity_shortage", "طلب الشعبة يتجاوز الأوقات المتاحة"),
        ("resource", "resource_ids", "resource_structural_shortage", "طلب المورد يتجاوز الأوقات المتاحة"),
    ):
        entity_demand: Counter[str] = Counter(
            entity_id
            for occurrence in problem.occurrences
            for entity_id in getattr(occurrence, attribute)
        )
        entity_capacity: dict[str, set[str]] = defaultdict(set)
        for occurrence in problem.occurrences:
            for entity_id in getattr(occurrence, attribute):
                entity_capacity[entity_id].update(occurrence.candidate_slot_ids)
        for entity_id, required_count in entity_demand.items():
            available_count = len(entity_capacity[entity_id])
            if required_count > available_count:
                diagnostics.append(
                    {
                        "severity": "error",
                        "code": code,
                        "message": message,
                        "affected_entities": {entity_type: [entity_id]},
                        "required": required_count,
                        "available": available_count,
                        "shortage": required_count - available_count,
                        "suggested_remediation": "راجع الطلب والقواعد والأوقات المتاحة.",
                    }
                )
    rules = [r for r in problem.rules if r["severity"] == "hard"]
    for required_rule in [r for r in rules if r["rule_type"] == "assignment_required_time"]:
        if any(
            r["rule_type"] == "assignment_forbidden_time"
            and r["selector"] == required_rule["selector"]
            and r["parameters"] == required_rule["parameters"]
            for r in rules
        ):
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "required_forbidden_contradiction",
                    "message": "وقت مطلوب وممنوع للإسناد نفسه",
                    "affected_entities": {
                        "assignment": [str(required_rule["selector"].get("assignment_id"))]
                    },
                    "suggested_remediation": "عطّل إحدى القاعدتين.",
                }
            )
    errors = sum(x["severity"] == "error" for x in diagnostics)
    warnings = sum(x["severity"] == "warning" for x in diagnostics)
    readiness = "جاهز للتوليد" if not errors else "توجد أخطاء تمنع التوليد"
    return {
        "readiness": readiness,
        "errors": errors,
        "warnings": warnings,
        "diagnostics": diagnostics,
        "problem": problem.model_dump(mode="json"),
    }

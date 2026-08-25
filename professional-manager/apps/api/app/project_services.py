import uuid
from collections import Counter, defaultdict
from typing import Any
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
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
    Subject,
    Teacher,
    TeacherSchoolMembership,
    TeachingAssignment,
    TeachingAssignmentResource,
    TeachingAssignmentSection,
    TeachingAssignmentTeacher,
    Term,
    TimetableProject,
    TimetableProjectSchool,
    TimetableEntry,
    WeekPattern,
    WorkingTimetableEntry,
)
from app.project_schemas import ProjectInput, RuleInput
from pm_scheduler.contracts import (
    Entity,
    LessonOccurrence,
    LocalTimeSlot,
    ResourceEntity,
    SchedulingProblem,
    SchedulingRule as SolverRule,
    SolveOptions,
    TimeSlot,
)
from pm_scheduler.cycle import expand_project_slots
from pm_scheduler.rules import RULE_REGISTRY, validate_parameters

MAX_CYCLE = 12


def section_display_name(grade_name: str, section_name: str) -> str:
    """Return a readable section label without repeating an embedded grade name."""
    return (
        section_name
        if grade_name.strip() in section_name.strip()
        else f"{grade_name} — {section_name}"
    )


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
        "optimization_profile": (project.settings or {}).get("optimization_profile", "balanced"),
        "optimization_weights": (project.settings or {}).get("optimization_weights", {}),
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
    if not spec or data.severity not in spec.severities:
        raise HTTPException(422, detail={"code": "invalid_rule_schema"})
    scopes = list(
        db.scalars(
            select(TimetableProjectSchool).where(
                TimetableProjectSchool.timetable_project_id == project.id
            )
        )
    )
    school_ids = {x.school_id for x in scopes}
    term_by_school = {x.school_id: x.term_id for x in scopes}
    if set(data.selector) != set(spec.target_keys):
        raise HTTPException(422, detail={"code": "invalid_rule_selector"})
    for raw_key in spec.target_keys:
        raw_values = data.selector.get(raw_key)
        values = raw_values if raw_key == "assignment_ids" and isinstance(raw_values, list) else [raw_values]
        if raw_key == "assignment_ids" and (len(values) != 2 or len(set(map(str, values))) != 2):
            raise HTTPException(422, detail={"code": "invalid_relationship_targets"})
        key = "assignment_id" if raw_key == "assignment_ids" else raw_key
        model: Any = {"teacher_id": Teacher, "section_id": Section, "resource_id": Resource, "assignment_id": TeachingAssignment, "subject_id": Subject}[key]
        for raw in values:
            try:
                target = uuid.UUID(str(raw))
            except (ValueError, TypeError) as exc:
                raise HTTPException(422, detail={"code": "invalid_rule_target"}) from exc
            entity: Any = db.scalar(select(model).where(model.id == target, model.tenant_id == tenant))
            if not entity:
                raise HTTPException(422, detail={"code": "cross_tenant_rule_target"})
            if key == "teacher_id":
                valid = db.scalar(select(TeacherSchoolMembership.id).where(TeacherSchoolMembership.teacher_id == target, TeacherSchoolMembership.school_id.in_(school_ids), TeacherSchoolMembership.is_active.is_(True)))
            elif key == "section_id":
                valid = db.scalar(select(Section.id).join(Grade).join(Stage).where(Section.id == target, Stage.school_id.in_(school_ids)))
            elif key == "assignment_id":
                valid = entity.id if entity.school_id in school_ids and term_by_school.get(entity.school_id) == entity.term_id else None
            else:
                valid = entity.id if getattr(entity, "school_id", None) in school_ids else None
            if not valid:
                raise HTTPException(422, detail={"code": "cross_school_rule_target"})
    try:
        data.parameters = validate_parameters(data.rule_type, data.parameters)
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "invalid_rule_parameters"}) from exc


def save_rule(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    data: RuleInput,
    rule_id: uuid.UUID | None = None,
    *,
    commit: bool = True,
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
    if commit:
        db.commit()
        db.refresh(rule)
    else:
        db.flush()
    return rule


def serialize_rule(rule: SchedulingRule) -> dict[str, Any]:
    return {
        "id": rule.id,
        "project_id": rule.timetable_project_id,
        "label": rule.label,
        "description": rule.description,
        "rule_type": rule.rule_type,
        "severity": rule.severity,
        "weight": rule.weight,
        "selector": rule.selector,
        "parameters": rule.parameters,
        "enabled": rule.enabled,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }


def _matches(slot: TimeSlot, params: dict[str, Any]) -> bool:
    return all(
        params.get(k) is None or getattr(slot, k) == params[k]
        for k in ("project_cycle_week_index", "weekday_index", "starts_at_minute", "ends_at_minute")
    ) and (not params.get("slot_id") or slot.id == params["slot_id"]) and (
        not params.get("period_numbers") or slot.period in params["period_numbers"]
    )


def build_problem(db: Session, tenant: uuid.UUID, project_id: uuid.UUID) -> SchedulingProblem:
    project = _project(db, tenant, project_id)
    scopes = list(
        db.scalars(
            select(TimetableProjectSchool)
            .where(TimetableProjectSchool.timetable_project_id == project.id)
            .order_by(TimetableProjectSchool.school_id)
        )
    )
    if not scopes:
        return SchedulingProblem(
            problem_id=str(project.id),
            project_id=str(project.id),
            project_cycle_length=1,
            school_ids=[],
            slots=[],
            teachers=[],
            sections=[],
            resources=[],
            assignments=[],
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
            if not teachers:
                historical_references = bool(
                    db.scalar(
                        select(TimetableEntry.id).where(
                            TimetableEntry.tenant_id == tenant,
                            TimetableEntry.assignment_id == a.id,
                        )
                    )
                    or db.scalar(
                        select(WorkingTimetableEntry.id).where(
                            WorkingTimetableEntry.tenant_id == tenant,
                            WorkingTimetableEntry.assignment_id == a.id,
                        )
                    )
                )
                if historical_references:
                    continue
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
                        LessonOccurrence(
                            id=f"{a.id}@project-week-{week}#occurrence-{n}",
                            assignment_id=str(a.id),
                            school_id=str(a.school_id),
                            subject_id=str(a.subject_id),
                            project_cycle_week_index=week,
                            teacher_ids=teachers,
                            section_ids=sections,
                            resource_ids=resources,
                            candidate_slot_ids=week_slots,
                        )
                    )
    teacher_ids = sorted({item for occurrence in occurrences for item in occurrence.teacher_ids})
    section_ids = sorted({item for occurrence in occurrences for item in occurrence.section_ids})
    resource_ids = sorted({item for occurrence in occurrences for item in occurrence.resource_ids})
    resource_rows = (
        list(
            db.scalars(
                select(Resource).where(
                    Resource.tenant_id == tenant,
                    Resource.id.in_([uuid.UUID(item) for item in resource_ids]),
                )
            )
        )
        if resource_ids
        else []
    )
    return SchedulingProblem(
        problem_id=str(project.id),
        project_id=str(project.id),
        project_cycle_length=cycle,
        school_ids=sorted(str(x.school_id) for x in scopes),
        slots=sorted(slots, key=lambda s: s.id),
        teachers=[Entity(id=item) for item in teacher_ids],
        sections=[Entity(id=item) for item in section_ids],
        resources=[ResourceEntity(id=str(item.id), exclusive=item.exclusive, resource_type=item.resource_type) for item in resource_rows],
        assignments=[],
        occurrences=occurrences,
        rules=[
            SolverRule(
                id=str(r.id),
                rule_type=r.rule_type,
                severity=r.severity,
                weight=r.weight,
                selector=r.selector,
                parameters=r.parameters,
            )
            for r in rules
        ],
        options=SolveOptions(
            optimization_profile=(project.settings or {}).get("optimization_profile", "balanced"),
            optimization_weights=(project.settings or {}).get("optimization_weights", {}),
        ),
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
    section_labels = {
        str(section_id): section_display_name(grade_name, section_name)
        for section_id, section_name, grade_name in db.execute(
            select(Section.id, Section.name_ar, Grade.name_ar)
            .join(Grade, Grade.id == Section.grade_id)
            .where(Section.tenant_id == tenant)
        )
    }
    teacher_labels = {str(item.id): item.name_ar for item in db.scalars(select(Teacher).where(Teacher.tenant_id == tenant))}
    subject_labels = {str(item.id): item.name_ar for item in db.scalars(select(Subject).where(Subject.tenant_id == tenant))}
    resource_labels = {str(item.id): item.name_ar for item in db.scalars(select(Resource).where(Resource.tenant_id == tenant))}
    assignments_without_teacher: set[str] = set()
    assignments_without_section: set[str] = set()
    assignments_without_slot: set[str] = set()
    for occurrence in problem.occurrences:
        if not occurrence.teacher_ids and occurrence.assignment_id not in assignments_without_teacher:
            assignments_without_teacher.add(occurrence.assignment_id)
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "assignment_without_teacher",
                    "message": "إسناد بلا معلم",
                    "affected_entities": {"assignment": [occurrence.assignment_id]},
                }
            )
        if not occurrence.section_ids and occurrence.assignment_id not in assignments_without_section:
            assignments_without_section.add(occurrence.assignment_id)
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "assignment_without_section",
                    "message": "إسناد بلا شعبة",
                    "affected_entities": {"assignment": [occurrence.assignment_id]},
                }
            )
        if not occurrence.candidate_slot_ids and occurrence.assignment_id not in assignments_without_slot:
            assignments_without_slot.add(occurrence.assignment_id)
            subject_name = subject_labels.get(occurrence.subject_id, occurrence.subject_id)
            section_names = [section_labels.get(item, item) for item in occurrence.section_ids]
            teacher_names = [teacher_labels.get(item, item) for item in occurrence.teacher_ids]
            assignment_name = " — ".join(
                item
                for item in (
                    subject_name,
                    " + ".join(section_names),
                    " + ".join(teacher_names),
                )
                if item
            )
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "occurrence_without_candidate_slot",
                    "message": f"الإسناد {assignment_name}: لا يوجد وقت مشترك صالح للحصة",
                    "affected_entities": {"assignment": [occurrence.assignment_id]},
                    "affected_details": [
                        {"type": "subject", "id": occurrence.subject_id, "name": subject_name},
                        *[
                            {"type": "section", "id": item, "name": section_labels.get(item, item)}
                            for item in occurrence.section_ids
                        ],
                        *[
                            {"type": "teacher", "id": item, "name": teacher_labels.get(item, item)}
                            for item in occurrence.teacher_ids
                        ],
                    ],
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
            teacher_name = teacher_labels.get(teacher, teacher)
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "teacher_capacity_shortage",
                    "message": f"المعلم {teacher_name}: مطلوب {required} حصة، والمتاح {available} فقط (عجز {required - available}).",
                    "affected_entities": {"teacher": [teacher]},
                    "affected_details": [{"type": "teacher", "id": teacher, "name": teacher_name}],
                    "required": required,
                    "available": available,
                    "shortage": required - available,
                    "suggested_remediation": "وسع توفر المعلم أو خفف الإسناد.",
                }
            )
    for entity_type, attribute, code, _message in (
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
                labels = section_labels if entity_type == "section" else resource_labels
                entity_name = labels.get(entity_id, entity_id)
                entity_ar = "الشعبة" if entity_type == "section" else "المورد"
                diagnostics.append(
                    {
                        "severity": "error",
                        "code": code,
                        "message": f"{entity_ar} {entity_name}: مطلوب {required_count} حصة، والمتاح {available_count} فقط (عجز {required_count - available_count}).",
                        "affected_entities": {entity_type: [entity_id]},
                        "affected_details": [{"type": entity_type, "id": entity_id, "name": entity_name}],
                        "required": required_count,
                        "available": available_count,
                        "shortage": required_count - available_count,
                        "suggested_remediation": f"زد الأوقات الأسبوعية بمقدار {required_count - available_count} أو خفّض إسنادات {entity_ar} بالمقدار نفسه.",
                    }
                )
    rules = [r for r in problem.rules if r.severity == "hard"]
    for rule in rules:
        targeted = [o for o in problem.occurrences if str(rule.selector.get("assignment_id")) == o.assignment_id]
        if rule.rule_type == "assignment_min_days":
            minimum = int(rule.parameters["minimum_days"])
            available_days = len({(next(s for s in problem.slots if s.id == slot_id).project_cycle_week_index, next(s for s in problem.slots if s.id == slot_id).weekday_index) for o in targeted for slot_id in o.candidate_slot_ids})
            if targeted and available_days < minimum:
                diagnostics.append({"severity": "error", "code": "minimum_days_exceeds_available_days", "message": "عدد أيام التوزيع المطلوب يتجاوز الأيام المتاحة", "affected_entities": {"assignment": [targeted[0].assignment_id]}, "required": minimum, "available": available_days, "suggested_remediation": "خفّض الحد الأدنى للأيام أو أضف أيامًا صالحة."})
        if rule.rule_type == "assignment_max_per_day":
            maximum = int(rule.parameters["maximum"])
            for week, required_count in Counter(o.project_cycle_week_index for o in targeted).items():
                weekdays = {next(s for s in problem.slots if s.id == slot_id).weekday_index for o in targeted if o.project_cycle_week_index == week for slot_id in o.candidate_slot_ids}
                assignment_capacity = maximum * len(weekdays)
                if required_count > assignment_capacity:
                    diagnostics.append({"severity": "error", "code": "assignment_daily_max_too_strict", "message": "الحد اليومي لا يتسع لعدد حصص الإسناد", "affected_entities": {"assignment": [str(rule.selector.get("assignment_id"))]}, "required": required_count, "available": assignment_capacity, "shortage": required_count - assignment_capacity, "suggested_remediation": "ارفع الحد اليومي أو أضف يومًا متاحًا للإسناد."})
        if rule.rule_type == "assignment_require_consecutive_block":
            size = int(rule.parameters["block_size"])
            counts = Counter(o.project_cycle_week_index for o in targeted)
            if any(count % size for count in counts.values()):
                diagnostics.append({"severity": "error", "code": "consecutive_block_count_mismatch", "message": "عدد حصص الإسناد لا يقبل حجم الكتلة المطلوبة", "affected_entities": {"assignment": [str(rule.selector.get("assignment_id"))]}, "suggested_remediation": "غيّر عدد الحصص أو حجم الكتلة 2/3."})
        if rule.rule_type in {"assignments_same_time", "assignments_same_day", "assignment_before_assignment"}:
            ids = [str(x) for x in rule.selector.get("assignment_ids", [])]
            relationship_counts = [Counter(o.project_cycle_week_index for o in problem.occurrences if o.assignment_id == assignment_id) for assignment_id in ids]
            if len(relationship_counts) == 2 and relationship_counts[0] != relationship_counts[1]:
                diagnostics.append({"severity": "error", "code": "relationship_occurrence_count_mismatch", "message": "الإسنادان لا يملكان عدد الوقائع نفسه داخل أسابيع المشروع", "affected_entities": {"assignment": ids}, "suggested_remediation": "وحّد عدد الحصص أو استخدم علاقة لا تتطلب المطابقة واحدًا لواحد."})
    for required_rule in [r for r in rules if r.rule_type == "assignment_required_time"]:
        if any(
            r.rule_type == "assignment_forbidden_time"
            and r.selector == required_rule.selector
            and r.parameters == required_rule.parameters
            for r in rules
        ):
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "required_forbidden_contradiction",
                    "message": "وقت مطلوب وممنوع للإسناد نفسه",
                    "affected_entities": {
                        "assignment": [str(required_rule.selector.get("assignment_id"))]
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

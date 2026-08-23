import hashlib
import json
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    Resource,
    School,
    Section,
    Subject,
    Teacher,
    TimetableAuditEvent,
    TimetableCandidate,
    TimetableEditChange,
    TimetableEditLock,
    TimetableEntry,
    TimetableEntryResource,
    TimetableEntrySection,
    TimetableEntryTeacher,
    TimetableSnapshot,
    TimetableSolveRun,
    WorkingTimetable,
    WorkingTimetableEntry,
    WorkingTimetableEntryResource,
    WorkingTimetableEntrySection,
    WorkingTimetableEntryTeacher,
)
from app.project_services import _project, build_problem
from pm_scheduler.contracts import ExistingPlacement, Placement, SchedulingProblem, SolveOptions, TimeSlot
from pm_scheduler.evaluation import evaluate_schedule
from pm_scheduler.solver import Scheduler


def _working(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, *, lock: bool = False
) -> WorkingTimetable:
    statement = select(WorkingTimetable).where(
        WorkingTimetable.tenant_id == tenant,
        WorkingTimetable.timetable_project_id == project_id,
        WorkingTimetable.is_current.is_(True),
    )
    if lock:
        statement = statement.with_for_update()
    item = db.scalar(statement)
    if item is None:
        raise HTTPException(404, detail={"code": "working_timetable_not_found"})
    return item


def _working_problem(db: Session, item: WorkingTimetable) -> SchedulingProblem:
    candidate = db.get(TimetableCandidate, item.source_candidate_id)
    run = db.get(TimetableSolveRun, candidate.solve_run_id) if candidate else None
    if run is not None:
        return SchedulingProblem.model_validate(run.input_snapshot)
    return build_problem(db, item.tenant_id, item.timetable_project_id)


def _check_revision(item: WorkingTimetable, revision: int) -> None:
    if item.revision != revision:
        raise HTTPException(
            409,
            detail={"code": "timetable_version_conflict", "current_revision": item.revision},
        )


def create_from_candidate(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, candidate_id: uuid.UUID
) -> dict[str, Any]:
    _project(db, tenant, project_id)
    candidate = db.scalar(
        select(TimetableCandidate)
        .join(TimetableSolveRun, TimetableSolveRun.id == TimetableCandidate.solve_run_id)
        .where(
            TimetableCandidate.id == candidate_id,
            TimetableCandidate.tenant_id == tenant,
            TimetableSolveRun.tenant_id == tenant,
            TimetableSolveRun.timetable_project_id == project_id,
        )
    )
    if candidate is None:
        raise HTTPException(404, detail={"code": "candidate_not_found"})
    existing = db.scalar(
        select(WorkingTimetable).where(
            WorkingTimetable.tenant_id == tenant,
            WorkingTimetable.timetable_project_id == project_id,
            WorkingTimetable.source_candidate_id == candidate_id,
            WorkingTimetable.is_current.is_(True),
        )
    )
    if existing:
        return serialize_working(db, existing)
    current = db.scalar(
        select(WorkingTimetable).where(
            WorkingTimetable.tenant_id == tenant,
            WorkingTimetable.timetable_project_id == project_id,
            WorkingTimetable.is_current.is_(True),
        )
    )
    if current:
        current.is_current = False
        current.status = "historical"
    version = (
        int(
            db.scalar(
                select(func.coalesce(func.max(WorkingTimetable.version_number), 0)).where(
                    WorkingTimetable.tenant_id == tenant,
                    WorkingTimetable.timetable_project_id == project_id,
                )
            )
            or 0
        )
        + 1
    )
    working = WorkingTimetable(
        tenant_id=tenant,
        timetable_project_id=project_id,
        source_candidate_id=candidate_id,
        parent_timetable_id=current.id if current else None,
        version_number=version,
        name=f"نسخة العمل {version}",
        revision=1,
        history_cursor=0,
        is_current=True,
        status="working",
        change_summary="نسخة قابلة للتحرير مشتقة من بديل التوليد",
    )
    db.add(working)
    db.flush()
    candidate_entries = list(
        db.scalars(
            select(TimetableEntry).where(
                TimetableEntry.tenant_id == tenant, TimetableEntry.candidate_id == candidate_id
            )
        )
    )
    for source in candidate_entries:
        entry = WorkingTimetableEntry(
            tenant_id=tenant,
            working_timetable_id=working.id,
            source_entry_id=source.id,
            occurrence_id=source.occurrence_id,
            assignment_id=source.assignment_id,
            subject_id=source.subject_id,
            slot_id=source.slot_id,
            school_id=source.school_id,
            project_cycle_week_index=source.project_cycle_week_index,
            weekday_index=source.weekday_index,
            starts_at_minute=source.starts_at_minute,
            ends_at_minute=source.ends_at_minute,
        )
        db.add(entry)
        db.flush()
        _copy_links(db, tenant, source.id, entry.id)
    db.commit()
    db.refresh(working)
    return serialize_working(db, working)


def _copy_links(db: Session, tenant: uuid.UUID, source_id: uuid.UUID, target_id: uuid.UUID) -> None:
    for source_model, source_field, target_model, target_field in (
        (
            TimetableEntryTeacher,
            TimetableEntryTeacher.teacher_id,
            WorkingTimetableEntryTeacher,
            "teacher_id",
        ),
        (
            TimetableEntrySection,
            TimetableEntrySection.section_id,
            WorkingTimetableEntrySection,
            "section_id",
        ),
        (
            TimetableEntryResource,
            TimetableEntryResource.resource_id,
            WorkingTimetableEntryResource,
            "resource_id",
        ),
    ):
        values = db.scalars(
            select(source_field).where(
                source_model.tenant_id == tenant, source_model.timetable_entry_id == source_id
            )
        )
        db.add_all(
            target_model(
                tenant_id=tenant,
                working_timetable_entry_id=target_id,
                **{target_field: value},
            )
            for value in values
        )


def serialize_working(db: Session, item: WorkingTimetable) -> dict[str, Any]:
    entries = list(
        db.scalars(
            select(WorkingTimetableEntry)
            .where(
                WorkingTimetableEntry.tenant_id == item.tenant_id,
                WorkingTimetableEntry.working_timetable_id == item.id,
            )
            .order_by(
                WorkingTimetableEntry.project_cycle_week_index,
                WorkingTimetableEntry.weekday_index,
                WorkingTimetableEntry.starts_at_minute,
            )
        )
    )
    locks = list(
        db.scalars(
            select(TimetableEditLock).where(
                TimetableEditLock.tenant_id == item.tenant_id,
                TimetableEditLock.working_timetable_id == item.id,
            )
        )
    )
    return {
        "id": item.id,
        "project_id": item.timetable_project_id,
        "source_candidate_id": item.source_candidate_id,
        "parent_timetable_id": item.parent_timetable_id,
        "name": item.name,
        "version_number": item.version_number,
        "revision": item.revision,
        "history_cursor": item.history_cursor,
        "status": item.status,
        "change_summary": item.change_summary,
        "can_undo": item.history_cursor > 0,
        "can_redo": (db.scalar(
            select(func.count())
            .select_from(TimetableEditChange)
            .where(
                TimetableEditChange.tenant_id == item.tenant_id,
                TimetableEditChange.working_timetable_id == item.id,
                TimetableEditChange.sequence == item.history_cursor + 1,
            )
        ) or 0)
        > 0,
        "entries": [_serialize_entry(db, item.tenant_id, entry) for entry in entries],
        "locks": [_serialize_lock(lock) for lock in locks],
    }


def _ids(
    db: Session, model: Any, field: Any, tenant: uuid.UUID, entry_id: uuid.UUID
) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(field).where(
                model.tenant_id == tenant, model.working_timetable_entry_id == entry_id
            )
        )
    )


def _serialize_entry(
    db: Session, tenant: uuid.UUID, entry: WorkingTimetableEntry
) -> dict[str, Any]:
    teacher_ids = _ids(
        db, WorkingTimetableEntryTeacher, WorkingTimetableEntryTeacher.teacher_id, tenant, entry.id
    )
    section_ids = _ids(
        db, WorkingTimetableEntrySection, WorkingTimetableEntrySection.section_id, tenant, entry.id
    )
    resource_ids = _ids(
        db,
        WorkingTimetableEntryResource,
        WorkingTimetableEntryResource.resource_id,
        tenant,
        entry.id,
    )
    subject = db.get(Subject, entry.subject_id)
    school = db.get(School, entry.school_id)
    teachers = (
        list(db.scalars(select(Teacher).where(Teacher.id.in_(teacher_ids)))) if teacher_ids else []
    )
    sections = (
        list(db.scalars(select(Section).where(Section.id.in_(section_ids)))) if section_ids else []
    )
    resources = (
        list(db.scalars(select(Resource).where(Resource.id.in_(resource_ids))))
        if resource_ids
        else []
    )
    return {
        "id": entry.id,
        "occurrence_id": entry.occurrence_id,
        "assignment_id": entry.assignment_id,
        "slot_id": entry.slot_id,
        "school": {"id": entry.school_id, "name_ar": school.name_ar if school else ""},
        "subject": {"id": entry.subject_id, "name_ar": subject.name_ar if subject else ""},
        "teachers": [{"id": x.id, "name_ar": x.name_ar} for x in teachers],
        "sections": [{"id": x.id, "name_ar": x.name_ar} for x in sections],
        "resources": [{"id": x.id, "name_ar": x.name_ar} for x in resources],
        "project_cycle_week_index": entry.project_cycle_week_index,
        "weekday_index": entry.weekday_index,
        "starts_at_minute": entry.starts_at_minute,
        "ends_at_minute": entry.ends_at_minute,
    }


def _placement(entry: WorkingTimetableEntry) -> dict[str, Any]:
    return {
        "occurrence_id": entry.occurrence_id,
        "slot_id": entry.slot_id,
        "project_cycle_week_index": entry.project_cycle_week_index,
        "weekday_index": entry.weekday_index,
        "starts_at_minute": entry.starts_at_minute,
        "ends_at_minute": entry.ends_at_minute,
    }


def _entry(db: Session, item: WorkingTimetable, occurrence_id: str) -> WorkingTimetableEntry:
    entry = db.scalar(
        select(WorkingTimetableEntry).where(
            WorkingTimetableEntry.tenant_id == item.tenant_id,
            WorkingTimetableEntry.working_timetable_id == item.id,
            WorkingTimetableEntry.occurrence_id == occurrence_id,
        )
    )
    if entry is None:
        raise HTTPException(404, detail={"code": "timetable_occurrence_not_found"})
    return entry


def _slot(problem: SchedulingProblem, occurrence_id: str, slot_id: str) -> TimeSlot:
    occurrence = next((x for x in problem.occurrences if x.id == occurrence_id), None)
    slot = next((x for x in problem.slots if x.id == slot_id), None)
    if occurrence is None or slot is None or slot_id not in occurrence.candidate_slot_ids:
        raise HTTPException(409, detail={"code": "target_slot_not_available"})
    return slot


def analyze_move(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    occurrence_id: str,
    target_slot_id: str,
    revision: int,
    *,
    include_suggestions: bool = True,
) -> dict[str, Any]:
    item = _working(db, tenant, project_id)
    _check_revision(item, revision)
    problem = _working_problem(db, item)
    source = _entry(db, item, occurrence_id)
    target = _slot(problem, occurrence_id, target_slot_id)
    facts = _move_facts(db, item, source, target, problem)
    alternatives: list[dict[str, Any]] = []
    swaps: list[dict[str, Any]] = []
    if include_suggestions:
        occurrence = next(x for x in problem.occurrences if x.id == occurrence_id)
        for slot_id in occurrence.candidate_slot_ids:
            if slot_id in (source.slot_id, target_slot_id):
                continue
            candidate_slot = next(x for x in problem.slots if x.id == slot_id)
            candidate_facts = _move_facts(db, item, source, candidate_slot, problem)
            if not candidate_facts["violations"]:
                alternatives.append(_slot_data(candidate_slot))
                if len(alternatives) >= 5:
                    break
        affected_ids = {x["occurrence_id"] for x in facts["affected_entries"]}
        for affected_id in affected_ids:
            other = _entry(db, item, affected_id)
            try:
                other_target = _slot(problem, other.occurrence_id, source.slot_id)
            except HTTPException:
                continue
            left = _move_facts(db, item, source, target, problem, ignore={other.occurrence_id})
            right = _move_facts(
                db, item, other, other_target, problem, ignore={source.occurrence_id}
            )
            if not left["violations"] and not right["violations"]:
                swaps.append({"occurrence_id": other.occurrence_id, "slot_id": other.slot_id})
    return {
        "revision": item.revision,
        "occurrence_id": occurrence_id,
        "source_slot_id": source.slot_id,
        "target_slot": _slot_data(target),
        "valid": not facts["violations"],
        **facts,
        "swap_candidates": swaps,
        "alternative_slots": alternatives,
    }


def _move_facts(
    db: Session,
    item: WorkingTimetable,
    source: WorkingTimetableEntry,
    target: TimeSlot,
    problem: SchedulingProblem,
    ignore: set[str] | None = None,
) -> dict[str, Any]:
    ignore = ignore or set()
    teacher_ids = set(
        _ids(
            db,
            WorkingTimetableEntryTeacher,
            WorkingTimetableEntryTeacher.teacher_id,
            item.tenant_id,
            source.id,
        )
    )
    section_ids = set(
        _ids(
            db,
            WorkingTimetableEntrySection,
            WorkingTimetableEntrySection.section_id,
            item.tenant_id,
            source.id,
        )
    )
    resource_ids = set(
        _ids(
            db,
            WorkingTimetableEntryResource,
            WorkingTimetableEntryResource.resource_id,
            item.tenant_id,
            source.id,
        )
    )
    exclusive = (
        set(
            db.scalars(
                select(Resource.id).where(
                    Resource.id.in_(resource_ids), Resource.exclusive.is_(True)
                )
            )
        )
        if resource_ids
        else set()
    )
    conflicts: dict[str, list[dict[str, Any]]] = {"teacher": [], "section": [], "resource": []}
    others = db.scalars(
        select(WorkingTimetableEntry).where(
            WorkingTimetableEntry.tenant_id == item.tenant_id,
            WorkingTimetableEntry.working_timetable_id == item.id,
            WorkingTimetableEntry.occurrence_id != source.occurrence_id,
        )
    )
    for other in others:
        if other.occurrence_id in ignore or not _overlaps_entry_slot(other, target):
            continue
        other_teachers = set(
            _ids(
                db,
                WorkingTimetableEntryTeacher,
                WorkingTimetableEntryTeacher.teacher_id,
                item.tenant_id,
                other.id,
            )
        )
        other_sections = set(
            _ids(
                db,
                WorkingTimetableEntrySection,
                WorkingTimetableEntrySection.section_id,
                item.tenant_id,
                other.id,
            )
        )
        other_resources = set(
            _ids(
                db,
                WorkingTimetableEntryResource,
                WorkingTimetableEntryResource.resource_id,
                item.tenant_id,
                other.id,
            )
        )
        summary = {"occurrence_id": other.occurrence_id, "slot_id": other.slot_id}
        if teacher_ids & other_teachers:
            conflicts["teacher"].append(
                {**summary, "entity_ids": list(teacher_ids & other_teachers)}
            )
        if section_ids & other_sections:
            conflicts["section"].append(
                {**summary, "entity_ids": list(section_ids & other_sections)}
            )
        if exclusive & other_resources:
            conflicts["resource"].append(
                {**summary, "entity_ids": list(exclusive & other_resources)}
            )
    lock_violations = [
        _serialize_lock(lock)
        for lock in db.scalars(
            select(TimetableEditLock).where(
                TimetableEditLock.tenant_id == item.tenant_id,
                TimetableEditLock.working_timetable_id == item.id,
            )
        )
        if _lock_matches(lock, source, target, teacher_ids, section_ids)
    ]
    hard_violations = _hard_rule_violations(db, item, source, target, problem)
    violations = [
        *({"code": "teacher_conflict", **x} for x in conflicts["teacher"]),
        *({"code": "section_conflict", **x} for x in conflicts["section"]),
        *({"code": "exclusive_resource_conflict", **x} for x in conflicts["resource"]),
        *({"code": "lock_violation", "lock": x} for x in lock_violations),
        *hard_violations,
    ]
    affected = {x["occurrence_id"]: x for values in conflicts.values() for x in values}
    return {
        "violations": violations,
        "teacher_conflicts": conflicts["teacher"],
        "section_conflicts": conflicts["section"],
        "resource_conflicts": conflicts["resource"],
        "hard_rule_violations": hard_violations,
        "lock_violations": lock_violations,
        "affected_entries": list(affected.values()),
        "soft_penalty_delta": _soft_delta(db, item, source, target, problem),
    }


def _hard_rule_violations(
    db: Session,
    item: WorkingTimetable,
    entry: WorkingTimetableEntry,
    target: TimeSlot,
    problem: SchedulingProblem,
) -> list[dict[str, Any]]:
    placements = _working_placements(db, item)
    proposed = [p.model_copy(update={"slot_id": target.id}) if p.occurrence_id == entry.occurrence_id else p for p in placements]
    before = evaluate_schedule(problem, placements)["hard_violations"]
    after = evaluate_schedule(problem, proposed)["hard_violations"]
    baseline = {json.dumps(value, sort_keys=True, default=str) for value in before}
    return [{"code": "hard_rule_violation", **value} for value in after if "rule_id" in value and json.dumps(value, sort_keys=True, default=str) not in baseline]


def _soft_delta(
    db: Session,
    item: WorkingTimetable,
    entry: WorkingTimetableEntry,
    target: TimeSlot,
    problem: SchedulingProblem,
) -> int:
    placements = _working_placements(db, item)
    proposed = [p.model_copy(update={"slot_id": target.id}) if p.occurrence_id == entry.occurrence_id else p for p in placements]
    return int(evaluate_schedule(problem, proposed)["total_weighted_penalty"] - evaluate_schedule(problem, placements)["total_weighted_penalty"])


def _working_placements(db: Session, item: WorkingTimetable) -> list[Placement]:
    return [Placement(occurrence_id=row.occurrence_id, assignment_id=str(row.assignment_id), slot_id=row.slot_id) for row in db.scalars(select(WorkingTimetableEntry).where(WorkingTimetableEntry.tenant_id == item.tenant_id, WorkingTimetableEntry.working_timetable_id == item.id))]


def apply_move(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    occurrence_id: str,
    target_slot_id: str,
    revision: int,
) -> dict[str, Any]:
    item = _working(db, tenant, project_id, lock=True)
    _check_revision(item, revision)
    analysis = analyze_move(
        db, tenant, project_id, occurrence_id, target_slot_id, revision, include_suggestions=False
    )
    if not analysis["valid"]:
        raise HTTPException(409, detail={"code": "move_conflict", "analysis": analysis})
    entry = _entry(db, item, occurrence_id)
    before = [_placement(entry)]
    _set_slot(entry, analysis["target_slot"])
    after = [_placement(entry)]
    subject = db.get(Subject, entry.subject_id)
    summary = (
        f"نُقلت {subject.name_ar if subject else 'الحصة'} من "
        f"الأسبوع {before[0]['project_cycle_week_index'] + 1} اليوم {before[0]['weekday_index'] + 1} "
        f"إلى الأسبوع {after[0]['project_cycle_week_index'] + 1} اليوم {after[0]['weekday_index'] + 1}"
    )
    _record_change(db, item, "move", before, after, summary)
    db.commit()
    return serialize_working(db, item)


def apply_swap(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    first_id: str,
    second_id: str,
    revision: int,
) -> dict[str, Any]:
    item = _working(db, tenant, project_id, lock=True)
    _check_revision(item, revision)
    first = _entry(db, item, first_id)
    second = _entry(db, item, second_id)
    problem = _working_problem(db, item)
    first_target = _slot(problem, first_id, second.slot_id)
    second_target = _slot(problem, second_id, first.slot_id)
    first_facts = _move_facts(db, item, first, first_target, problem, ignore={second_id})
    second_facts = _move_facts(db, item, second, second_target, problem, ignore={first_id})
    if first_facts["violations"] or second_facts["violations"]:
        raise HTTPException(
            409, detail={"code": "swap_conflict", "first": first_facts, "second": second_facts}
        )
    before = [_placement(first), _placement(second)]
    _set_slot(first, _slot_data(first_target))
    _set_slot(second, _slot_data(second_target))
    after = [_placement(first), _placement(second)]
    _record_change(db, item, "swap", before, after, "تبديل حصتين بصورة ذرية")
    db.commit()
    return serialize_working(db, item)


def _set_slot(entry: WorkingTimetableEntry, slot: dict[str, Any]) -> None:
    entry.slot_id = str(slot["id"] if "id" in slot else slot["slot_id"])
    entry.project_cycle_week_index = int(slot["project_cycle_week_index"])
    entry.weekday_index = int(slot["weekday_index"])
    entry.starts_at_minute = int(slot["starts_at_minute"])
    entry.ends_at_minute = int(slot["ends_at_minute"])


def _record_change(
    db: Session,
    item: WorkingTimetable,
    operation: str,
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    summary: str,
) -> None:
    db.execute(
        delete(TimetableEditChange).where(
            TimetableEditChange.tenant_id == item.tenant_id,
            TimetableEditChange.working_timetable_id == item.id,
            TimetableEditChange.sequence > item.history_cursor,
        )
    )
    sequence = item.history_cursor + 1
    db.add(
        TimetableEditChange(
            tenant_id=item.tenant_id,
            working_timetable_id=item.id,
            sequence=sequence,
            operation_type=operation,
            before_data=before,
            after_data=after,
            summary=summary,
        )
    )
    item.history_cursor = sequence
    item.revision += 1
    item.change_summary = summary
    _audit(db, item, operation, before, after, summary)


def _audit(
    db: Session,
    item: WorkingTimetable,
    operation: str,
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    summary: str,
) -> None:
    db.add(
        TimetableAuditEvent(
            tenant_id=item.tenant_id,
            working_timetable_id=item.id,
            revision=item.revision,
            operation_type=operation,
            before_data=before,
            after_data=after,
            summary=summary,
        )
    )


def undo_redo(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, revision: int, *, redo: bool
) -> dict[str, Any]:
    item = _working(db, tenant, project_id, lock=True)
    _check_revision(item, revision)
    sequence = item.history_cursor + 1 if redo else item.history_cursor
    if sequence < 1:
        raise HTTPException(409, detail={"code": "nothing_to_undo"})
    change = db.scalar(
        select(TimetableEditChange).where(
            TimetableEditChange.tenant_id == tenant,
            TimetableEditChange.working_timetable_id == item.id,
            TimetableEditChange.sequence == sequence,
        )
    )
    if change is None:
        raise HTTPException(409, detail={"code": "nothing_to_redo" if redo else "nothing_to_undo"})
    placements = change.after_data if redo else change.before_data
    before = change.before_data if redo else change.after_data
    _apply_placements(db, item, placements)
    item.history_cursor = sequence if redo else sequence - 1
    item.revision += 1
    summary = ("إعادة: " if redo else "تراجع: ") + change.summary
    item.change_summary = summary
    _audit(db, item, "redo" if redo else "undo", before, placements, summary)
    db.commit()
    return serialize_working(db, item)


def _apply_placements(
    db: Session, item: WorkingTimetable, placements: list[dict[str, Any]]
) -> None:
    for placement in placements:
        _set_slot(_entry(db, item, str(placement["occurrence_id"])), placement)


def create_lock(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, payload: Any
) -> dict[str, Any]:
    item = _working(db, tenant, project_id, lock=True)
    _check_revision(item, payload.revision)
    problem = build_problem(db, tenant, project_id)
    if payload.occurrence_id and not any(
        x.id == payload.occurrence_id for x in problem.occurrences
    ):
        raise HTTPException(422, detail={"code": "invalid_lock_occurrence"})
    for model, value in (
        (Teacher, payload.teacher_id),
        (Section, payload.section_id),
        (School, payload.school_id),
    ):
        if (
            value
            and db.scalar(select(model.id).where(model.id == value, model.tenant_id == tenant))
            is None
        ):
            raise HTTPException(422, detail={"code": "invalid_lock_reference"})
    lock = TimetableEditLock(
        tenant_id=tenant, working_timetable_id=item.id, **payload.model_dump(exclude={"revision"})
    )
    db.add(lock)
    item.revision += 1
    _audit(db, item, "lock", [], [], f"إضافة قفل: {lock.label}")
    db.commit()
    db.refresh(lock)
    return {"lock": _serialize_lock(lock), "revision": item.revision}


def delete_lock(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, lock_id: uuid.UUID, revision: int
) -> dict[str, Any]:
    item = _working(db, tenant, project_id, lock=True)
    _check_revision(item, revision)
    lock = db.scalar(
        select(TimetableEditLock).where(
            TimetableEditLock.id == lock_id,
            TimetableEditLock.tenant_id == tenant,
            TimetableEditLock.working_timetable_id == item.id,
        )
    )
    if lock is None:
        raise HTTPException(404, detail={"code": "lock_not_found"})
    label = lock.label
    db.delete(lock)
    item.revision += 1
    _audit(db, item, "unlock", [], [], f"إزالة قفل: {label}")
    db.commit()
    return serialize_working(db, item)


def _serialize_lock(lock: TimetableEditLock) -> dict[str, Any]:
    return {
        key: getattr(lock, key)
        for key in (
            "id",
            "lock_type",
            "occurrence_id",
            "teacher_id",
            "section_id",
            "school_id",
            "project_cycle_week_index",
            "weekday_index",
            "starts_at_minute",
            "ends_at_minute",
            "label",
        )
    }


def _lock_matches(
    lock: TimetableEditLock,
    entry: WorkingTimetableEntry,
    target: TimeSlot,
    teachers: set[uuid.UUID],
    sections: set[uuid.UUID],
) -> bool:
    def matches_location(week: int, day: int, starts: int, ends: int) -> bool:
        interval = (
            lock.starts_at_minute is None
            or lock.ends_at_minute is None
            or max(lock.starts_at_minute, starts) < min(lock.ends_at_minute, ends)
        )
        return (
            lock.project_cycle_week_index in (None, week)
            and lock.weekday_index in (None, day)
            and interval
        )

    source_match = matches_location(
        entry.project_cycle_week_index,
        entry.weekday_index,
        entry.starts_at_minute,
        entry.ends_at_minute,
    )
    target_match = matches_location(
        target.project_cycle_week_index,
        target.weekday_index,
        target.starts_at_minute,
        target.ends_at_minute,
    )
    if lock.lock_type == "occurrence":
        return lock.occurrence_id == entry.occurrence_id
    if lock.lock_type == "teacher":
        return lock.teacher_id in teachers
    if lock.lock_type == "section":
        return lock.section_id in sections
    if lock.lock_type == "day":
        return source_match or target_match
    if lock.lock_type == "time_range":
        return source_match or target_match
    if lock.lock_type == "week":
        return lock.project_cycle_week_index in (
            entry.project_cycle_week_index,
            target.project_cycle_week_index,
        )
    return (source_match or target_match) and lock.school_id in (None, entry.school_id)


def repair_preview(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, payload: Any
) -> dict[str, Any]:
    item = _working(db, tenant, project_id)
    _check_revision(item, payload.revision)
    # Validate the requested target even when the direct move currently conflicts.
    base = _working_problem(db, item)
    _slot(base, payload.occurrence_id, payload.target_slot_id)
    entries = list(
        db.scalars(
            select(WorkingTimetableEntry).where(
                WorkingTimetableEntry.tenant_id == tenant,
                WorkingTimetableEntry.working_timetable_id == item.id,
            )
        )
    )
    locked_ids = sorted(
        {
            entry.occurrence_id
            for entry in entries
            if _entry_is_locked(db, item, entry) and entry.occurrence_id != payload.occurrence_id
        }
    )
    problem = base.model_copy(
        update={
            "existing_timetable": [
                ExistingPlacement(
                    occurrence_id=x.occurrence_id,
                    assignment_id=str(x.assignment_id),
                    slot_id=x.slot_id,
                )
                for x in entries
            ],
            "options": SolveOptions(
                seed=0,
                time_limit_seconds=payload.time_limit_seconds,
                candidate_count=1,
                optimization_profile=base.options.optimization_profile,
                optimization_weights=base.options.optimization_weights,
                repair=True,
                minimize_changes=True,
                requested_occurrence_id=payload.occurrence_id,
                requested_slot_id=payload.target_slot_id,
                locked_occurrence_ids=locked_ids,
            ),
        }
    )
    penalty_before = _current_soft_penalty(db, item, base, entries)
    result = Scheduler().solve(problem)
    if not result.feasible:
        raise HTTPException(
            409,
            detail={
                "code": "repair_infeasible",
                "diagnostics": [x.model_dump(mode="json") for x in result.diagnostics],
            },
        )
    solved = result.candidates[0]
    current = {x.occurrence_id: x for x in entries}
    slots = {x.id: x for x in problem.slots}
    changes = []
    for placement in solved.placements:
        old = current[placement.occurrence_id]
        if old.slot_id == placement.slot_id:
            continue
        new = slots[placement.slot_id]
        changes.append(
            {
                "occurrence_id": old.occurrence_id,
                "from": _placement(old),
                "to": {"slot_id": new.id, **_slot_data(new, include_id=False)},
                "reason": "حل التعارض بأقل عدد من التغييرات",
            }
        )
    fingerprint = _repair_fingerprint(
        item.revision, payload.occurrence_id, payload.target_slot_id, changes
    )
    return {
        "revision": item.revision,
        "occurrence_id": payload.occurrence_id,
        "target_slot_id": payload.target_slot_id,
        "time_limit_seconds": payload.time_limit_seconds,
        "fingerprint": fingerprint,
        "changes": changes,
        "total_moved_occurrences": len(changes),
        "penalty_before": penalty_before,
        "penalty_after": solved.total_penalty,
    }


def _current_soft_penalty(
    db: Session,
    item: WorkingTimetable,
    problem: SchedulingProblem,
    entries: list[WorkingTimetableEntry],
) -> int:
    del db, item
    placements = [Placement(occurrence_id=entry.occurrence_id, assignment_id=str(entry.assignment_id), slot_id=entry.slot_id) for entry in entries]
    return int(evaluate_schedule(problem, placements)["total_weighted_penalty"])


def apply_repair(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    occurrence_id: str,
    target_slot_id: str,
    changes: list[dict[str, Any]],
    time_limit_seconds: float,
    fingerprint: str,
    revision: int,
) -> dict[str, Any]:
    item = _working(db, tenant, project_id, lock=True)
    _check_revision(item, revision)
    expected = _repair_fingerprint(item.revision, occurrence_id, target_slot_id, changes)
    if expected != fingerprint:
        raise HTTPException(
            409, detail={"code": "timetable_version_conflict", "current_revision": item.revision}
        )
    verified = repair_preview(
        db,
        tenant,
        project_id,
        type(
            "RepairPayload",
            (),
            {
                "revision": revision,
                "occurrence_id": occurrence_id,
                "target_slot_id": target_slot_id,
                "time_limit_seconds": time_limit_seconds,
            },
        )(),
    )
    if verified["fingerprint"] != fingerprint or verified["changes"] != changes:
        raise HTTPException(409, detail={"code": "repair_preview_stale"})
    before = [_placement(_entry(db, item, str(x["occurrence_id"]))) for x in changes]
    after = [x["to"] | {"occurrence_id": x["occurrence_id"]} for x in changes]
    _apply_placements(db, item, after)
    _record_change(
        db, item, "repair", before, after, f"إصلاح تلقائي بأقل تغييرات ({len(after)} حصص)"
    )
    db.commit()
    return serialize_working(db, item)


def _entry_is_locked(db: Session, item: WorkingTimetable, entry: WorkingTimetableEntry) -> bool:
    problem = _working_problem(db, item)
    slot = next(x for x in problem.slots if x.id == entry.slot_id)
    teachers = set(
        _ids(
            db,
            WorkingTimetableEntryTeacher,
            WorkingTimetableEntryTeacher.teacher_id,
            item.tenant_id,
            entry.id,
        )
    )
    sections = set(
        _ids(
            db,
            WorkingTimetableEntrySection,
            WorkingTimetableEntrySection.section_id,
            item.tenant_id,
            entry.id,
        )
    )
    return any(
        _lock_matches(lock, entry, slot, teachers, sections)
        for lock in db.scalars(
            select(TimetableEditLock).where(
                TimetableEditLock.tenant_id == item.tenant_id,
                TimetableEditLock.working_timetable_id == item.id,
            )
        )
    )


def _repair_fingerprint(
    revision: int, occurrence_id: str, target_slot_id: str, changes: list[dict[str, Any]]
) -> str:
    raw = json.dumps(
        {
            "revision": revision,
            "occurrence_id": occurrence_id,
            "target_slot_id": target_slot_id,
            "changes": changes,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def create_snapshot(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, revision: int, name: str
) -> dict[str, Any]:
    item = _working(db, tenant, project_id, lock=True)
    _check_revision(item, revision)
    entries = list(
        db.scalars(
            select(WorkingTimetableEntry).where(
                WorkingTimetableEntry.tenant_id == tenant,
                WorkingTimetableEntry.working_timetable_id == item.id,
            )
        )
    )
    data = [_serialize_snapshot_entry(db, tenant, x) for x in entries]
    snapshot = TimetableSnapshot(
        tenant_id=tenant,
        working_timetable_id=item.id,
        name=name,
        source_revision=item.revision,
        entries_snapshot=data,
    )
    db.add(snapshot)
    item.revision += 1
    _audit(db, item, "snapshot", [], [], f"حفظ لقطة: {name}")
    db.commit()
    db.refresh(snapshot)
    return _serialize_snapshot(snapshot, 0)


def list_snapshots(db: Session, tenant: uuid.UUID, project_id: uuid.UUID) -> list[dict[str, Any]]:
    item = _working(db, tenant, project_id)
    current = {
        x.occurrence_id: x.slot_id
        for x in db.scalars(
            select(WorkingTimetableEntry).where(
                WorkingTimetableEntry.tenant_id == tenant,
                WorkingTimetableEntry.working_timetable_id == item.id,
            )
        )
    }
    result = []
    for snap in db.scalars(
        select(TimetableSnapshot)
        .where(
            TimetableSnapshot.tenant_id == tenant, TimetableSnapshot.working_timetable_id == item.id
        )
        .order_by(TimetableSnapshot.created_at.desc())
    ):
        changed = sum(
            current.get(str(x["occurrence_id"])) != str(x["slot_id"]) for x in snap.entries_snapshot
        )
        result.append(_serialize_snapshot(snap, changed))
    return result


def compare_snapshot(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, snapshot_id: uuid.UUID
) -> dict[str, Any]:
    item = _working(db, tenant, project_id)
    snapshot = db.scalar(
        select(TimetableSnapshot).where(
            TimetableSnapshot.id == snapshot_id,
            TimetableSnapshot.tenant_id == tenant,
            TimetableSnapshot.working_timetable_id == item.id,
        )
    )
    if snapshot is None:
        raise HTTPException(404, detail={"code": "snapshot_not_found"})
    current = {
        entry.occurrence_id: _placement(entry)
        for entry in db.scalars(
            select(WorkingTimetableEntry).where(
                WorkingTimetableEntry.tenant_id == tenant,
                WorkingTimetableEntry.working_timetable_id == item.id,
            )
        )
    }
    changes = []
    for previous in snapshot.entries_snapshot:
        now = current.get(str(previous["occurrence_id"]))
        if now is None or now["slot_id"] != previous["slot_id"]:
            changes.append(
                {
                    "occurrence_id": previous["occurrence_id"],
                    "snapshot": {
                        key: previous[key]
                        for key in (
                            "occurrence_id",
                            "slot_id",
                            "project_cycle_week_index",
                            "weekday_index",
                            "starts_at_minute",
                            "ends_at_minute",
                        )
                    },
                    "current": now,
                }
            )
    return {
        "snapshot_id": snapshot.id,
        "source_revision": snapshot.source_revision,
        "current_revision": item.revision,
        "changed_occurrences": len(changes),
        "changes": changes,
    }


def restore_snapshot(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    revision: int,
    summary: str | None,
) -> dict[str, Any]:
    current = _working(db, tenant, project_id, lock=True)
    _check_revision(current, revision)
    snapshot = db.scalar(
        select(TimetableSnapshot).where(
            TimetableSnapshot.id == snapshot_id,
            TimetableSnapshot.tenant_id == tenant,
            TimetableSnapshot.working_timetable_id == current.id,
        )
    )
    if snapshot is None:
        raise HTTPException(404, detail={"code": "snapshot_not_found"})
    version = (
        int(
            db.scalar(
                select(func.max(WorkingTimetable.version_number)).where(
                    WorkingTimetable.tenant_id == tenant,
                    WorkingTimetable.timetable_project_id == project_id,
                )
            )
            or 0
        )
        + 1
    )
    current.is_current = False
    current.status = "historical"
    restored = WorkingTimetable(
        tenant_id=tenant,
        timetable_project_id=project_id,
        source_candidate_id=current.source_candidate_id,
        parent_timetable_id=current.id,
        name=f"استعادة {snapshot.name}",
        version_number=version,
        revision=1,
        history_cursor=0,
        is_current=True,
        status="working",
        change_summary=summary or f"استعادة اللقطة {snapshot.name}",
    )
    db.add(restored)
    db.flush()
    for data in snapshot.entries_snapshot:
        _create_snapshot_entry(db, tenant, restored.id, data)
    _audit(db, restored, "restore", [], [], restored.change_summary or "استعادة لقطة")
    db.commit()
    return serialize_working(db, restored)


def audit_list(db: Session, tenant: uuid.UUID, project_id: uuid.UUID) -> list[dict[str, Any]]:
    item = _working(db, tenant, project_id)
    return [
        {
            "id": x.id,
            "revision": x.revision,
            "operation_type": x.operation_type,
            "summary": x.summary,
            "created_at": x.created_at,
        }
        for x in db.scalars(
            select(TimetableAuditEvent)
            .where(
                TimetableAuditEvent.tenant_id == tenant,
                TimetableAuditEvent.working_timetable_id == item.id,
            )
            .order_by(TimetableAuditEvent.created_at.desc())
        )
    ]


def _serialize_snapshot_entry(
    db: Session, tenant: uuid.UUID, entry: WorkingTimetableEntry
) -> dict[str, Any]:
    data = _placement(entry) | {
        "assignment_id": str(entry.assignment_id),
        "subject_id": str(entry.subject_id),
        "school_id": str(entry.school_id),
        "source_entry_id": str(entry.source_entry_id) if entry.source_entry_id else None,
    }
    data["teacher_ids"] = [
        str(x)
        for x in _ids(
            db,
            WorkingTimetableEntryTeacher,
            WorkingTimetableEntryTeacher.teacher_id,
            tenant,
            entry.id,
        )
    ]
    data["section_ids"] = [
        str(x)
        for x in _ids(
            db,
            WorkingTimetableEntrySection,
            WorkingTimetableEntrySection.section_id,
            tenant,
            entry.id,
        )
    ]
    data["resource_ids"] = [
        str(x)
        for x in _ids(
            db,
            WorkingTimetableEntryResource,
            WorkingTimetableEntryResource.resource_id,
            tenant,
            entry.id,
        )
    ]
    return data


def _create_snapshot_entry(
    db: Session, tenant: uuid.UUID, timetable_id: uuid.UUID, data: dict[str, Any]
) -> None:
    entry = WorkingTimetableEntry(
        tenant_id=tenant,
        working_timetable_id=timetable_id,
        source_entry_id=uuid.UUID(data["source_entry_id"]) if data.get("source_entry_id") else None,
        occurrence_id=data["occurrence_id"],
        assignment_id=uuid.UUID(data["assignment_id"]),
        subject_id=uuid.UUID(data["subject_id"]),
        school_id=uuid.UUID(data["school_id"]),
        slot_id=data["slot_id"],
        project_cycle_week_index=data["project_cycle_week_index"],
        weekday_index=data["weekday_index"],
        starts_at_minute=data["starts_at_minute"],
        ends_at_minute=data["ends_at_minute"],
    )
    db.add(entry)
    db.flush()
    for model, key, field in (
        (WorkingTimetableEntryTeacher, "teacher_ids", "teacher_id"),
        (WorkingTimetableEntrySection, "section_ids", "section_id"),
        (WorkingTimetableEntryResource, "resource_ids", "resource_id"),
    ):
        db.add_all(
            model(
                tenant_id=tenant, working_timetable_entry_id=entry.id, **{field: uuid.UUID(value)}
            )
            for value in data[key]
        )


def _serialize_snapshot(item: TimetableSnapshot, changed: int) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "source_revision": item.source_revision,
        "changed_occurrences": changed,
        "created_at": item.created_at,
    }


def _overlaps_entry_slot(entry: WorkingTimetableEntry, slot: TimeSlot) -> bool:
    return (
        entry.project_cycle_week_index == slot.project_cycle_week_index
        and entry.weekday_index == slot.weekday_index
        and max(entry.starts_at_minute, slot.starts_at_minute)
        < min(entry.ends_at_minute, slot.ends_at_minute)
    )


def _slot_data(slot: TimeSlot, *, include_id: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {
        "project_cycle_week_index": slot.project_cycle_week_index,
        "weekday_index": slot.weekday_index,
        "starts_at_minute": slot.starts_at_minute,
        "ends_at_minute": slot.ends_at_minute,
    }
    if include_id:
        result["id"] = slot.id
    return result


def _slot_matches(slot: TimeSlot, parameters: dict[str, Any]) -> bool:
    return all(
        parameters.get(field) is None or getattr(slot, field) == parameters[field]
        for field in (
            "project_cycle_week_index",
            "weekday_index",
            "starts_at_minute",
            "ends_at_minute",
        )
    ) and (parameters.get("slot_id") is None or slot.id == parameters["slot_id"])


def _rule_targets(selector: dict[str, Any], occurrence: Any) -> bool:
    values = {
        "teacher_id": occurrence.teacher_ids,
        "section_id": occurrence.section_ids,
        "resource_id": occurrence.resource_ids,
        "assignment_id": [occurrence.assignment_id],
    }
    return any(str(selector.get(key)) in ids for key, ids in values.items())

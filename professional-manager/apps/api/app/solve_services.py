import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Connection, Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Grade,
    Resource,
    School,
    Section,
    Subject,
    Teacher,
    TimetableCandidate,
    TimetableEntry,
    TimetableEntryResource,
    TimetableEntrySection,
    TimetableEntryTeacher,
    TimetableSolveRun,
)
from app.project_services import _project, build_problem, preflight, section_display_name
from app.solve_schemas import SolveRequest
from pm_scheduler.contracts import CandidateSolution, SchedulingProblem, SolveOptions
from pm_scheduler.solver import Scheduler

ACTIVE_STATUSES = ("queued", "running")


def _partial_schedule_diagnostic(db: Session, tenant_id: uuid.UUID, problem: SchedulingProblem, occurrence_ids: list[str]) -> dict[str, Any]:
    occurrence_map = {item.id: item for item in problem.occurrences}
    missing = [occurrence_map[item] for item in occurrence_ids if item in occurrence_map]
    subject_ids = {uuid.UUID(item.subject_id) for item in missing}
    section_ids = {uuid.UUID(value) for item in missing for value in item.section_ids}
    teacher_ids = {uuid.UUID(value) for item in missing for value in item.teacher_ids}
    subjects = {str(item.id): item.name_ar for item in db.scalars(select(Subject).where(Subject.tenant_id == tenant_id, Subject.id.in_(subject_ids)))} if subject_ids else {}
    sections = (
        {
            str(section_id): section_display_name(grade_name, section_name)
            for section_id, section_name, grade_name in db.execute(
                select(Section.id, Section.name_ar, Grade.name_ar)
                .join(Grade, Grade.id == Section.grade_id)
                .where(Section.tenant_id == tenant_id, Section.id.in_(section_ids))
            )
        }
        if section_ids
        else {}
    )
    teachers = {str(item.id): item.name_ar for item in db.scalars(select(Teacher).where(Teacher.tenant_id == tenant_id, Teacher.id.in_(teacher_ids)))} if teacher_ids else {}
    grouped: dict[str, dict[str, Any]] = {}
    for item in missing:
        row = grouped.setdefault(item.assignment_id, {"assignment_id": item.assignment_id, "subject": subjects.get(item.subject_id, item.subject_id), "sections": [sections.get(value, value) for value in item.section_ids], "teachers": [teachers.get(value, value) for value in item.teacher_ids], "unscheduled_count": 0})
        row["unscheduled_count"] += 1
    placed = len(problem.occurrences) - len(missing)
    return {"severity": "warning", "code": "partial_schedule", "message": f"تم توزيع {placed} حصة من أصل {len(problem.occurrences)}، وبقيت {len(missing)} حصة غير موزعة.", "affected_entities": {"occurrence": occurrence_ids}, "unscheduled_assignments": list(grouped.values()), "suggested_remediation": "زد الأوقات المتاحة أو خفّض النصاب المطلوب، ثم أعد التوليد لإكمال الجدول."}


def problem_fingerprint(problem: SchedulingProblem) -> str:
    canonical = json.dumps(
        problem.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_solve_run(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, payload: SolveRequest
) -> TimetableSolveRun:
    _project(db, tenant, project_id)
    report = preflight(db, tenant, project_id)
    partial_codes = {"section_capacity_shortage", "teacher_capacity_shortage", "resource_structural_shortage", "occurrence_without_candidate_slot"}
    blocking = [item for item in report["diagnostics"] if item.get("severity") == "error" and (not payload.allow_partial or item.get("code") not in partial_codes)]
    if blocking:
        raise HTTPException(
            409,
            detail={"code": "preflight_blocked", "diagnostics": report["diagnostics"]},
        )
    active = db.scalar(
        select(TimetableSolveRun.id).where(
            TimetableSolveRun.tenant_id == tenant,
            TimetableSolveRun.timetable_project_id == project_id,
            TimetableSolveRun.status.in_(ACTIVE_STATUSES),
        )
    )
    if active:
        raise HTTPException(409, detail={"code": "solve_run_already_active", "run_id": str(active)})
    problem = build_problem(db, tenant, project_id).model_copy(
        update={
            "options": SolveOptions(
                seed=payload.seed,
                time_limit_seconds=payload.time_limit_seconds,
                candidate_count=payload.candidate_count,
                optimization_profile=payload.optimization_profile,
                optimization_weights=payload.optimization_weights,
                allow_partial=payload.allow_partial,
            )
        }
    )
    run_diagnostics = report["diagnostics"]
    if payload.allow_partial:
        run_diagnostics = [
            {**item, "severity": "warning", "partial_mode": True}
            if item.get("code") in partial_codes
            else item
            for item in run_diagnostics
        ]
    run = TimetableSolveRun(
        tenant_id=tenant,
        timetable_project_id=project_id,
        status="queued",
        input_fingerprint=problem_fingerprint(problem),
        input_snapshot=problem.model_dump(mode="json"),
        requested_candidates=payload.candidate_count,
        time_limit_seconds=payload.time_limit_seconds,
        seed=payload.seed,
        diagnostics=run_diagnostics,
    )
    db.add(run)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, detail={"code": "solve_run_already_active"}) from exc
    db.refresh(run)
    return run


def execute_solve_run(bind: Engine | Connection, run_id: uuid.UUID) -> None:
    factory = sessionmaker(bind=bind, expire_on_commit=False)
    with factory() as db:
        run = db.get(TimetableSolveRun, run_id)
        if run is None or run.status != "queued":
            return
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        preflight_diagnostics = list(run.diagnostics or [])
        db.commit()
        try:
            problem = SchedulingProblem.model_validate(run.input_snapshot)
            result = Scheduler().solve(problem)
            run.solver_status = result.status.value
            run.solver_name = result.solver_name
            run.solver_version = result.solver_version
            result_diagnostics = [item.model_dump(mode="json") for item in result.diagnostics]
            partial = next((item for item in result.diagnostics if item.code == "partial_schedule"), None)
            if partial is not None:
                result_diagnostics = [item for item in result_diagnostics if item.get("code") != "partial_schedule"]
                result_diagnostics.append(_partial_schedule_diagnostic(db, run.tenant_id, problem, partial.affected_entity_ids))
            run.diagnostics = preflight_diagnostics + result_diagnostics
            if result.feasible:
                _persist_candidates(db, run, problem, result.candidates)
                run.status = "completed"
            elif result.status.value == "infeasible":
                run.status = "infeasible"
            else:
                run.status = "unknown"
        except Exception as exc:
            db.rollback()
            run = db.get(TimetableSolveRun, run_id)
            if run is None:
                return
            run.status = "failed"
            run.solver_status = "failed"
            run.diagnostics = [{"code": "solver_failed", "message_key": type(exc).__name__}]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()


def _persist_candidates(
    db: Session,
    run: TimetableSolveRun,
    problem: SchedulingProblem,
    candidates: list[CandidateSolution],
) -> None:
    occurrence_by_id = {item.id: item for item in problem.occurrences}
    slot_by_id = {item.id: item for item in problem.slots}
    for rank, solved in enumerate(candidates, 1):
        candidate = TimetableCandidate(
            tenant_id=run.tenant_id,
            solve_run_id=run.id,
            rank=rank,
            solver_status=solved.solver_status.value,
            total_penalty=solved.total_penalty,
            penalty_breakdown=[item.model_dump(mode="json") for item in solved.penalty_breakdown],
            solve_time_ms=round(solved.solve_time_seconds * 1000),
            diversity_count=solved.diversity_count,
        )
        db.add(candidate)
        db.flush()
        for placement in solved.placements:
            occurrence = occurrence_by_id[placement.occurrence_id]
            slot = slot_by_id[placement.slot_id]
            entry = TimetableEntry(
                tenant_id=run.tenant_id,
                candidate_id=candidate.id,
                occurrence_id=occurrence.id,
                assignment_id=uuid.UUID(occurrence.assignment_id),
                subject_id=uuid.UUID(occurrence.subject_id),
                slot_id=slot.id,
                school_id=uuid.UUID(occurrence.school_id),
                project_cycle_week_index=slot.project_cycle_week_index,
                weekday_index=slot.weekday_index,
                starts_at_minute=slot.starts_at_minute,
                ends_at_minute=slot.ends_at_minute,
            )
            db.add(entry)
            db.flush()
            db.add_all(
                TimetableEntryTeacher(
                    tenant_id=run.tenant_id,
                    timetable_entry_id=entry.id,
                    teacher_id=uuid.UUID(item),
                )
                for item in occurrence.teacher_ids
            )
            db.add_all(
                TimetableEntrySection(
                    tenant_id=run.tenant_id,
                    timetable_entry_id=entry.id,
                    section_id=uuid.UUID(item),
                )
                for item in occurrence.section_ids
            )
            db.add_all(
                TimetableEntryResource(
                    tenant_id=run.tenant_id,
                    timetable_entry_id=entry.id,
                    resource_id=uuid.UUID(item),
                )
                for item in occurrence.resource_ids
            )


def get_run(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, run_id: uuid.UUID
) -> TimetableSolveRun:
    run = db.scalar(
        select(TimetableSolveRun).where(
            TimetableSolveRun.id == run_id,
            TimetableSolveRun.tenant_id == tenant,
            TimetableSolveRun.timetable_project_id == project_id,
        )
    )
    if run is None:
        raise HTTPException(404, detail={"code": "solve_run_not_found"})
    return run


def get_latest_run(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID
) -> TimetableSolveRun | None:
    return db.scalar(
        select(TimetableSolveRun)
        .where(
            TimetableSolveRun.tenant_id == tenant,
            TimetableSolveRun.timetable_project_id == project_id,
        )
        .order_by(TimetableSolveRun.created_at.desc())
        .limit(1)
    )


def serialize_run(db: Session, run: TimetableSolveRun) -> dict[str, Any]:
    candidates = list(
        db.scalars(
            select(TimetableCandidate)
            .where(
                TimetableCandidate.solve_run_id == run.id,
                TimetableCandidate.tenant_id == run.tenant_id,
            )
            .order_by(TimetableCandidate.rank)
        )
    )
    return {
        "id": run.id,
        "project_id": run.timetable_project_id,
        "status": run.status,
        "input_fingerprint": run.input_fingerprint,
        "requested_candidates": run.requested_candidates,
        "time_limit_seconds": run.time_limit_seconds,
        "seed": run.seed,
        "solver_status": run.solver_status,
        "diagnostics": run.diagnostics,
        "candidates": [
            {
                "id": item.id,
                "rank": item.rank,
                "solver_status": item.solver_status,
                "total_penalty": item.total_penalty,
                "penalty_breakdown": item.penalty_breakdown,
                "solve_time_ms": item.solve_time_ms,
                "diversity_count": item.diversity_count,
            }
            for item in candidates
        ],
    }


def serialize_candidate(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, candidate_id: uuid.UUID
) -> dict[str, Any]:
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
    entries = list(
        db.scalars(
            select(TimetableEntry)
            .where(TimetableEntry.candidate_id == candidate.id, TimetableEntry.tenant_id == tenant)
            .order_by(
                TimetableEntry.project_cycle_week_index,
                TimetableEntry.weekday_index,
                TimetableEntry.starts_at_minute,
            )
        )
    )
    return {
        "id": candidate.id,
        "rank": candidate.rank,
        "solver_status": candidate.solver_status,
        "total_penalty": candidate.total_penalty,
        "penalty_breakdown": candidate.penalty_breakdown,
        "diversity_count": candidate.diversity_count,
        "entries": [_serialize_entry(db, tenant, item) for item in entries],
    }


def _serialize_entry(db: Session, tenant: uuid.UUID, entry: TimetableEntry) -> dict[str, Any]:
    subject = db.get(Subject, entry.subject_id)
    school = db.get(School, entry.school_id)
    teacher_ids = list(
        db.scalars(
            select(TimetableEntryTeacher.teacher_id).where(
                TimetableEntryTeacher.tenant_id == tenant,
                TimetableEntryTeacher.timetable_entry_id == entry.id,
            )
        )
    )
    section_ids = list(
        db.scalars(
            select(TimetableEntrySection.section_id).where(
                TimetableEntrySection.tenant_id == tenant,
                TimetableEntrySection.timetable_entry_id == entry.id,
            )
        )
    )
    resource_ids = list(
        db.scalars(
            select(TimetableEntryResource.resource_id).where(
                TimetableEntryResource.tenant_id == tenant,
                TimetableEntryResource.timetable_entry_id == entry.id,
            )
        )
    )
    teachers = list(db.scalars(select(Teacher).where(Teacher.tenant_id == tenant, Teacher.id.in_(teacher_ids)))) if teacher_ids else []
    sections = (
        list(
            db.execute(
                select(Section.id, Section.name_ar, Grade.name_ar)
                .join(Grade, Grade.id == Section.grade_id)
                .where(Section.tenant_id == tenant, Section.id.in_(section_ids))
            )
        )
        if section_ids
        else []
    )
    resources = list(db.scalars(select(Resource).where(Resource.tenant_id == tenant, Resource.id.in_(resource_ids)))) if resource_ids else []
    return {
        "id": entry.id,
        "occurrence_id": entry.occurrence_id,
        "assignment_id": entry.assignment_id,
        "slot_id": entry.slot_id,
        "school": {"id": entry.school_id, "name_ar": school.name_ar if school else ""},
        "subject": {"id": entry.subject_id, "name_ar": subject.name_ar if subject else ""},
        "teachers": [{"id": item.id, "name_ar": item.name_ar} for item in teachers],
        "sections": [
            {"id": section_id, "name_ar": section_display_name(grade_name, section_name)}
            for section_id, section_name, grade_name in sections
        ],
        "resources": [{"id": item.id, "name_ar": item.name_ar} for item in resources],
        "project_cycle_week_index": entry.project_cycle_week_index,
        "weekday_index": entry.weekday_index,
        "starts_at_minute": entry.starts_at_minute,
        "ends_at_minute": entry.ends_at_minute,
    }

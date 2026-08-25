import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.editor_services import _working, _working_problem, analyze_move
from app.models import (
    TimetableCandidate,
    TimetableEntry,
    TimetableSolveRun,
    WorkingTimetableEntry,
)
from pm_scheduler.contracts import Placement, SchedulingProblem
from pm_scheduler.evaluation import evaluate_schedule, placement_explanation


def _candidate_context(db: Session, tenant: uuid.UUID, project_id: uuid.UUID, candidate_id: uuid.UUID) -> tuple[SchedulingProblem, list[Placement], TimetableCandidate]:
    candidate = db.scalar(select(TimetableCandidate).join(TimetableSolveRun).where(TimetableCandidate.id == candidate_id, TimetableCandidate.tenant_id == tenant, TimetableSolveRun.timetable_project_id == project_id))
    if candidate is None:
        raise HTTPException(404, detail={"code": "candidate_not_found"})
    run = db.get(TimetableSolveRun, candidate.solve_run_id)
    if run is None:
        raise HTTPException(404, detail={"code": "solve_run_not_found"})
    problem = SchedulingProblem.model_validate(run.input_snapshot)
    entries = list(db.scalars(select(TimetableEntry).where(TimetableEntry.tenant_id == tenant, TimetableEntry.candidate_id == candidate.id)))
    placements = [Placement(occurrence_id=e.occurrence_id, assignment_id=str(e.assignment_id), slot_id=e.slot_id) for e in entries]
    return problem, placements, candidate


def candidate_quality(db: Session, tenant: uuid.UUID, project_id: uuid.UUID, candidate_id: uuid.UUID) -> dict[str, Any]:
    problem, placements, candidate = _candidate_context(db, tenant, project_id, candidate_id)
    report = evaluate_schedule(problem, placements)
    # The persisted objective is authoritative for the immutable candidate.
    report["total_weighted_penalty"] = candidate.total_penalty
    report["penalty_breakdown"] = candidate.penalty_breakdown
    report["source"] = {"type": "candidate", "id": str(candidate.id), "rank": candidate.rank}
    return report


def working_quality(db: Session, tenant: uuid.UUID, project_id: uuid.UUID) -> dict[str, Any]:
    working = _working(db, tenant, project_id)
    problem = _working_problem(db, working)
    rows = list(db.scalars(select(WorkingTimetableEntry).where(WorkingTimetableEntry.tenant_id == tenant, WorkingTimetableEntry.working_timetable_id == working.id)))
    placements = [Placement(occurrence_id=e.occurrence_id, assignment_id=str(e.assignment_id), slot_id=e.slot_id) for e in rows]
    report = evaluate_schedule(problem, placements)
    report["source"] = {"type": "working", "id": str(working.id), "revision": working.revision, "version_number": working.version_number}
    return report


def compare_quality(db: Session, tenant: uuid.UUID, project_id: uuid.UUID, candidate_id: uuid.UUID) -> dict[str, Any]:
    candidate = candidate_quality(db, tenant, project_id, candidate_id)
    working = working_quality(db, tenant, project_id)
    return {"candidate": candidate, "working": working, "weighted_penalty_delta": working["total_weighted_penalty"] - candidate["total_weighted_penalty"], "teacher_gap_delta": working["teacher_gap_total"] - candidate["teacher_gap_total"]}


def candidate_explanation(db: Session, tenant: uuid.UUID, project_id: uuid.UUID, candidate_id: uuid.UUID, occurrence_id: str) -> dict[str, Any]:
    problem, placements, _ = _candidate_context(db, tenant, project_id, candidate_id)
    try:
        return placement_explanation(problem, placements, occurrence_id)
    except StopIteration as exc:
        raise HTTPException(404, detail={"code": "timetable_occurrence_not_found"}) from exc


def working_explanation(db: Session, tenant: uuid.UUID, project_id: uuid.UUID, occurrence_id: str) -> dict[str, Any]:
    working = _working(db, tenant, project_id)
    problem = _working_problem(db, working)
    rows = list(db.scalars(select(WorkingTimetableEntry).where(WorkingTimetableEntry.tenant_id == tenant, WorkingTimetableEntry.working_timetable_id == working.id)))
    placements = [Placement(occurrence_id=e.occurrence_id, assignment_id=str(e.assignment_id), slot_id=e.slot_id) for e in rows]
    explanation = placement_explanation(problem, placements, occurrence_id)
    # Reuse PM-003C move analysis as the sole authority for move blocking facts.
    for alternative in explanation["alternatives"]:
        analysis = analyze_move(db, tenant, project_id, occurrence_id, alternative["slot"]["id"], working.revision, include_suggestions=False)
        alternative["status"] = "blocked" if not analysis["valid"] else alternative["status"]
        alternative["blocking_facts"] = analysis["violations"]
        alternative["move_analysis"] = {"teacher_conflicts": analysis["teacher_conflicts"], "section_conflicts": analysis["section_conflicts"], "resource_conflicts": analysis["resource_conflicts"], "hard_rule_violations": analysis["hard_rule_violations"], "lock_violations": analysis["lock_violations"]}
    explanation["revision"] = working.revision
    return explanation

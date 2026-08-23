from abc import ABC, abstractmethod
from collections import defaultdict
from importlib.metadata import version
from time import monotonic

from ortools.sat.python import cp_model

from pm_scheduler.contracts import (
    CandidateSolution,
    Diagnostic,
    LessonOccurrence,
    PenaltyBreakdown,
    Placement,
    SchedulingProblem,
    SchedulingRule,
    SolveResult,
    SolveStatus,
    TimeSlot,
    slots_overlap,
)

ORTOOLS_VERSION = version("ortools")


class SolverBackend(ABC):
    @abstractmethod
    def solve(self, problem: SchedulingProblem) -> SolveResult:
        """Solve or repair a validated scheduling problem."""


class CpSatBackend(SolverBackend):
    """First production CP-SAT placement backend."""

    def solve(self, problem: SchedulingProblem) -> SolveResult:
        if not problem.occurrences:
            return SolveResult(
                status=SolveStatus.INFEASIBLE,
                feasible=False,
                candidates=[],
                diagnostics=[Diagnostic(code="solver_infeasible", message_key="solver_infeasible")],
                solver_name="Google OR-Tools CP-SAT",
                solver_version=ORTOOLS_VERSION,
            )
        model = cp_model.CpModel()
        slot_by_id = {slot.id: slot for slot in problem.slots}
        decision: dict[tuple[str, str], cp_model.IntVar] = {}
        occurrence_by_id = {item.id: item for item in problem.occurrences}
        for occurrence in problem.occurrences:
            variables = []
            for slot_id in occurrence.candidate_slot_ids:
                if slot_id not in slot_by_id:
                    continue
                variable = model.new_bool_var(f"place::{occurrence.id}::{slot_id}")
                decision[(occurrence.id, slot_id)] = variable
                variables.append(variable)
            if not variables:
                return SolveResult(
                    status=SolveStatus.INFEASIBLE,
                    feasible=False,
                    candidates=[],
                    diagnostics=[
                        Diagnostic(
                            code="solver_infeasible",
                            message_key="occurrence_without_candidate_slot",
                            affected_entity_ids=[occurrence.id],
                        )
                    ],
                    solver_name="Google OR-Tools CP-SAT",
                    solver_version=ORTOOLS_VERSION,
                )
            model.add_exactly_one(variables)

        existing_by_occurrence = {
            placement.occurrence_id: placement.slot_id for placement in problem.existing_timetable
        }
        if problem.options.repair:
            requested_occurrence = problem.options.requested_occurrence_id
            requested_slot = problem.options.requested_slot_id
            if requested_occurrence and requested_slot:
                requested_variable = decision.get((requested_occurrence, requested_slot))
                if requested_variable is None:
                    return _infeasible("repair_target_not_available", [requested_occurrence])
                model.add(requested_variable == 1)
            for occurrence_id in problem.options.locked_occurrence_ids:
                current_slot = existing_by_occurrence.get(occurrence_id)
                locked_variable = decision.get((occurrence_id, current_slot or ""))
                if locked_variable is None:
                    return _infeasible("locked_occurrence_without_current_slot", [occurrence_id])
                model.add(locked_variable == 1)

        for rule in problem.rules:
            if rule.severity != "hard":
                continue
            for occurrence in problem.occurrences:
                if not _rule_targets(rule, occurrence):
                    continue
                matching = [
                    decision[(occurrence.id, slot_id)]
                    for slot_id in occurrence.candidate_slot_ids
                    if (occurrence.id, slot_id) in decision
                    and _slot_matches(slot_by_id[slot_id], rule.parameters)
                ]
                if rule.rule_type == "assignment_required_time":
                    model.add(sum(matching) == 1)
                elif (
                    rule.rule_type.endswith("unavailable")
                    or rule.rule_type == "assignment_forbidden_time"
                ):
                    for variable in matching:
                        model.add(variable == 0)

        exclusive_resources = {resource.id for resource in problem.resources if resource.exclusive}
        occupants: dict[tuple[str, str], list[str]] = defaultdict(list)
        for occurrence in problem.occurrences:
            for teacher_id in occurrence.teacher_ids:
                occupants[("teacher", teacher_id)].append(occurrence.id)
            for section_id in occurrence.section_ids:
                occupants[("section", section_id)].append(occurrence.id)
            for resource_id in occurrence.resource_ids:
                if resource_id in exclusive_resources:
                    occupants[("resource", resource_id)].append(occurrence.id)
        for occurrence_ids in occupants.values():
            for left_index, left_id in enumerate(occurrence_ids):
                left = occurrence_by_id[left_id]
                for right_id in occurrence_ids[left_index + 1 :]:
                    right = occurrence_by_id[right_id]
                    for left_slot_id in left.candidate_slot_ids:
                        left_slot = slot_by_id.get(left_slot_id)
                        if left_slot is None:
                            continue
                        for right_slot_id in right.candidate_slot_ids:
                            right_slot = slot_by_id.get(right_slot_id)
                            if right_slot is not None and slots_overlap(left_slot, right_slot):
                                model.add(
                                    decision[(left_id, left_slot_id)]
                                    + decision[(right_id, right_slot_id)]
                                    <= 1
                                )

        soft_terms: list[tuple[SchedulingRule, cp_model.IntVar]] = []
        for rule in problem.rules:
            if rule.severity != "soft" or rule.weight is None:
                continue
            matched_variables = []
            applicable_variables = []
            for occurrence in problem.occurrences:
                if not _rule_targets(rule, occurrence):
                    continue
                for slot_id in occurrence.candidate_slot_ids:
                    soft_variable = decision.get((occurrence.id, slot_id))
                    slot = slot_by_id.get(slot_id)
                    if soft_variable is None or slot is None:
                        continue
                    applicable_variables.append(soft_variable)
                    if _slot_matches(slot, rule.parameters):
                        matched_variables.append(soft_variable)
            penalty = model.new_int_var(0, len(applicable_variables), f"penalty::{rule.id}")
            if rule.rule_type.endswith("preferred_time"):
                model.add(penalty == sum(applicable_variables) - sum(matched_variables))
            else:
                model.add(penalty == sum(matched_variables))
            soft_terms.append((rule, penalty))
        soft_objective = sum((rule.weight or 0) * variable for rule, variable in soft_terms)
        if problem.options.repair and problem.options.minimize_changes:
            changed_terms = []
            displacement_terms = []
            for occurrence in problem.occurrences:
                current_slot_id = existing_by_occurrence.get(occurrence.id)
                existing_slot = slot_by_id.get(current_slot_id or "")
                current_variable = decision.get((occurrence.id, current_slot_id or ""))
                if current_variable is not None:
                    changed_terms.append(1 - current_variable)
                if existing_slot is not None:
                    for slot_id in occurrence.candidate_slot_ids:
                        displacement_variable = decision.get((occurrence.id, slot_id))
                        slot = slot_by_id.get(slot_id)
                        if displacement_variable is None or slot is None:
                            continue
                        distance = (
                            abs(
                                slot.project_cycle_week_index
                                - existing_slot.project_cycle_week_index
                            )
                            * 7
                            * 1440
                            + abs(slot.weekday_index - existing_slot.weekday_index) * 1440
                            + abs(slot.starts_at_minute - existing_slot.starts_at_minute)
                        )
                        displacement_terms.append(distance * displacement_variable)
            # Strict hierarchy: one extra move costs more than every possible
            # displacement and soft penalty in the bounded problem.
            displacement_bound = max(
                1, len(problem.occurrences) * 7 * 1440 * max(1, problem.project_cycle_length)
            )
            soft_bound = max(
                1, sum((rule.weight or 0) * len(problem.occurrences) for rule, _ in soft_terms)
            )
            displacement_weight = soft_bound + 1
            changed_weight = displacement_bound * displacement_weight + soft_bound + 1
            model.minimize(
                changed_weight * sum(changed_terms)
                + displacement_weight * sum(displacement_terms)
                + soft_objective
            )
        else:
            model.minimize(soft_objective)

        candidates: list[CandidateSolution] = []
        best_signature: set[tuple[str, str]] | None = None
        terminal_status = SolveStatus.UNKNOWN
        started = monotonic()
        for candidate_index in range(problem.options.candidate_count):
            solver = cp_model.CpSolver()
            remaining = max(0.01, problem.options.time_limit_seconds - (monotonic() - started))
            solver.parameters.max_time_in_seconds = remaining
            solver.parameters.random_seed = problem.options.seed
            solver.parameters.num_search_workers = 1
            status = solver.solve(model)
            if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                terminal_status = (
                    SolveStatus.INFEASIBLE if status == cp_model.INFEASIBLE else SolveStatus.UNKNOWN
                )
                break
            solver_status = (
                SolveStatus.OPTIMAL if status == cp_model.OPTIMAL else SolveStatus.FEASIBLE
            )
            terminal_status = solver_status
            placements = []
            signature: set[tuple[str, str]] = set()
            for occurrence in problem.occurrences:
                selected = next(
                    slot_id
                    for slot_id in occurrence.candidate_slot_ids
                    if (occurrence.id, slot_id) in decision
                    and solver.value(decision[(occurrence.id, slot_id)])
                )
                signature.add((occurrence.id, selected))
                placements.append(
                    Placement(
                        occurrence_id=occurrence.id,
                        assignment_id=occurrence.assignment_id,
                        slot_id=selected,
                        resource_ids=occurrence.resource_ids,
                    )
                )
            breakdown = [
                PenaltyBreakdown(
                    rule_id=rule.id,
                    rule_type=rule.rule_type,
                    violation_count=solver.value(variable),
                    weight=rule.weight or 0,
                    weighted_penalty=solver.value(variable) * (rule.weight or 0),
                )
                for rule, variable in soft_terms
                if solver.value(variable)
            ]
            candidates.append(
                CandidateSolution(
                    id=f"candidate-{candidate_index + 1}",
                    solver_status=solver_status,
                    placements=placements,
                    total_penalty=sum(item.weighted_penalty for item in breakdown),
                    penalty_breakdown=breakdown,
                    solve_time_seconds=monotonic() - started,
                    diversity_count=(
                        0
                        if best_signature is None
                        else len(best_signature.symmetric_difference(signature)) // 2
                    ),
                )
            )
            if best_signature is None:
                best_signature = signature
            model.add(sum(decision[item] for item in signature) <= len(signature) - 1)

        if candidates:
            return SolveResult(
                status=candidates[0].solver_status,
                feasible=True,
                candidates=candidates,
                diagnostics=[],
                solver_name="Google OR-Tools CP-SAT",
                solver_version=ORTOOLS_VERSION,
            )
        diagnostic = (
            "solver_infeasible"
            if terminal_status == SolveStatus.INFEASIBLE
            else "solver_time_limit"
        )
        return SolveResult(
            status=terminal_status,
            feasible=False,
            candidates=[],
            diagnostics=[Diagnostic(code=diagnostic, message_key=diagnostic)],
            solver_name="Google OR-Tools CP-SAT",
            solver_version=ORTOOLS_VERSION,
        )


def _slot_matches(slot: TimeSlot, parameters: dict[str, object]) -> bool:
    for field in (
        "project_cycle_week_index",
        "weekday_index",
        "starts_at_minute",
        "ends_at_minute",
    ):
        value = parameters.get(field)
        if value is not None and getattr(slot, field) != value:
            return False
    slot_id = parameters.get("slot_id")
    return slot_id is None or slot.id == slot_id


def _rule_targets(rule: SchedulingRule, occurrence: LessonOccurrence) -> bool:
    values = {
        "teacher_id": occurrence.teacher_ids,
        "section_id": occurrence.section_ids,
        "resource_id": occurrence.resource_ids,
        "assignment_id": [occurrence.assignment_id],
    }
    return any(str(rule.selector.get(key)) in ids for key, ids in values.items())


class Scheduler:
    def __init__(self, backend: SolverBackend | None = None) -> None:
        self._backend = backend or CpSatBackend()

    def solve(self, problem: SchedulingProblem) -> SolveResult:
        return self._backend.solve(problem)


def _infeasible(code: str, affected: list[str]) -> SolveResult:
    return SolveResult(
        status=SolveStatus.INFEASIBLE,
        feasible=False,
        candidates=[],
        diagnostics=[Diagnostic(code=code, message_key=code, affected_entity_ids=affected)],
        solver_name="Google OR-Tools CP-SAT",
        solver_version=ORTOOLS_VERSION,
    )

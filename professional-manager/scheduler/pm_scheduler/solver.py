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
from pm_scheduler.rules import PROFILE_POLICIES, RULE_REGISTRY, effective_rule_weight

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
        unscheduled: dict[str, cp_model.IntVar] = {}
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
                if problem.options.allow_partial:
                    missing = model.new_bool_var(f"unscheduled::{occurrence.id}")
                    model.add(missing == 1)
                    unscheduled[occurrence.id] = missing
                    continue
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
            if problem.options.allow_partial:
                missing = model.new_bool_var(f"unscheduled::{occurrence.id}")
                unscheduled[occurrence.id] = missing
                model.add(sum(variables) + missing == 1)
            else:
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

        soft_terms: list[tuple[str, str, int, cp_model.IntVar]] = []
        for rule in problem.rules:
            if (
                rule.severity != "soft"
                or rule.weight is None
                or rule.rule_type
                not in {
                    "teacher_preferred_time", "teacher_avoided_time",
                    "assignment_preferred_time", "assignment_avoided_time",
                    "subject_preferred_time", "subject_avoided_time",
                }
            ):
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
            soft_terms.append((rule.id, rule.rule_type, effective_rule_weight(problem.options.optimization_profile, rule.rule_type, rule.weight), penalty))
        soft_terms.extend(
            _compile_advanced_rules(model, problem, decision, slot_by_id, occurrence_by_id)
        )
        soft_terms.extend(
            _compile_profile_objectives(model, problem, decision, slot_by_id)
        )
        soft_objective = sum(weight * variable for _, _, weight, variable in soft_terms)
        placement_weight = 1 + sum(weight * max(1, len(problem.occurrences)) for _, _, weight, _ in soft_terms)
        partial_objective = soft_objective + placement_weight * sum(unscheduled.values())
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
                1, sum(weight * len(problem.occurrences) for _, _, weight, _ in soft_terms)
            )
            displacement_weight = soft_bound + 1
            changed_weight = displacement_bound * displacement_weight + soft_bound + 1
            model.minimize(
                changed_weight * sum(changed_terms)
                + displacement_weight * sum(displacement_terms)
                + partial_objective
            )
        else:
            model.minimize(partial_objective)

        candidates: list[CandidateSolution] = []
        best_signature: set[tuple[str, str]] | None = None
        terminal_status = SolveStatus.UNKNOWN
        started = monotonic()
        for candidate_index in range(problem.options.candidate_count):
            solver = cp_model.CpSolver()
            remaining = max(0.01, problem.options.time_limit_seconds - (monotonic() - started))
            # Reserve a fair part of the total interactive budget for every
            # requested alternative. Otherwise the first optimization may
            # consume the full budget and the UI receives only one candidate.
            remaining_candidates = problem.options.candidate_count - candidate_index
            solver.parameters.max_time_in_seconds = max(0.01, remaining / remaining_candidates)
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
                    (slot_id
                    for slot_id in occurrence.candidate_slot_ids
                    if (occurrence.id, slot_id) in decision
                    and solver.value(decision[(occurrence.id, slot_id)])),
                    None,
                )
                if selected is None:
                    continue
                signature.add((occurrence.id, selected))
                placements.append(
                    Placement(
                        occurrence_id=occurrence.id,
                        assignment_id=occurrence.assignment_id,
                        slot_id=selected,
                        resource_ids=occurrence.resource_ids,
                    )
                )
            totals: dict[tuple[str, str, int], int] = defaultdict(int)
            for rule_id, rule_type, weight, variable in soft_terms:
                totals[(rule_id, rule_type, weight)] += solver.value(variable)
            breakdown = [PenaltyBreakdown(rule_id=rule_id, rule_type=rule_type, violation_count=count, weight=weight, weighted_penalty=count * weight, category=(RULE_REGISTRY[rule_type].category if rule_type in RULE_REGISTRY else "fairness")) for (rule_id, rule_type, weight), count in totals.items() if count]
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
                    unscheduled_occurrence_ids=[occurrence.id for occurrence in problem.occurrences if occurrence.id in unscheduled and solver.value(unscheduled[occurrence.id])],
                )
            )
            if best_signature is None:
                best_signature = signature
            # A completely unscheduled candidate has an empty placement
            # signature. There is no useful diversity cut in that case.
            if signature:
                model.add(sum(decision[item] for item in signature) <= len(signature) - 1)
            else:
                break

        if candidates:
            return SolveResult(
                status=candidates[0].solver_status,
                feasible=True,
                candidates=candidates,
                diagnostics=([Diagnostic(code="partial_schedule", message_key="partial_schedule_has_unscheduled_occurrences", affected_entity_ids=candidates[0].unscheduled_occurrence_ids)] if candidates[0].unscheduled_occurrence_ids else []),
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
    period_numbers = parameters.get("period_numbers")
    if isinstance(period_numbers, list) and slot.period not in period_numbers:
        return False
    return slot_id is None or slot.id == slot_id


def _rule_targets(rule: SchedulingRule, occurrence: LessonOccurrence) -> bool:
    values = {
        "teacher_id": occurrence.teacher_ids,
        "section_id": occurrence.section_ids,
        "resource_id": occurrence.resource_ids,
        "assignment_id": [occurrence.assignment_id],
        "subject_id": [occurrence.subject_id],
    }
    if "assignment_ids" in rule.selector:
        return occurrence.assignment_id in {str(x) for x in rule.selector["assignment_ids"]}
    return any(str(rule.selector.get(key)) in ids for key, ids in values.items())


def _day_key(slot: TimeSlot) -> tuple[int, int]:
    return slot.project_cycle_week_index, slot.weekday_index


def _time_key(slot: TimeSlot) -> tuple[int, int, int, int]:
    return (*_day_key(slot), slot.starts_at_minute, slot.ends_at_minute)


def _targeted(problem: SchedulingProblem, rule: SchedulingRule) -> list[LessonOccurrence]:
    return [item for item in problem.occurrences if _rule_targets(rule, item)]


def _variables_for_day(
    occurrences: list[LessonOccurrence],
    day: tuple[int, int],
    decision: dict[tuple[str, str], cp_model.IntVar],
    slots: dict[str, TimeSlot],
) -> list[cp_model.IntVar]:
    return [
        decision[(o.id, slot_id)]
        for o in occurrences
        for slot_id in o.candidate_slot_ids
        if (o.id, slot_id) in decision and _day_key(slots[slot_id]) == day
    ]


def _add_excess(
    model: cp_model.CpModel,
    variables: list[cp_model.IntVar],
    maximum: int,
    name: str,
    hard: bool,
) -> cp_model.IntVar | None:
    if hard:
        model.add(sum(variables) <= maximum)
        return None
    excess = model.new_int_var(0, len(variables), name)
    model.add(excess >= sum(variables) - maximum)
    return excess


def _compile_advanced_rules(
    model: cp_model.CpModel,
    problem: SchedulingProblem,
    decision: dict[tuple[str, str], cp_model.IntVar],
    slots: dict[str, TimeSlot],
    occurrence_by_id: dict[str, LessonOccurrence],
) -> list[tuple[str, str, int, cp_model.IntVar]]:
    terms: list[tuple[str, str, int, cp_model.IntVar]] = []
    all_days = sorted({_day_key(slot) for slot in slots.values()})
    for rule in problem.rules:
        kind = rule.rule_type
        targets = _targeted(problem, rule)
        hard = rule.severity == "hard"
        weight = effective_rule_weight(problem.options.optimization_profile, kind, rule.weight or 0) if rule.weight else 0
        if kind in {
            "assignment_max_per_day",
            "teacher_max_lessons_per_day",
            "section_max_lessons_per_day",
        }:
            maximum = int(rule.parameters["maximum"])
            for day in all_days:
                variables = _variables_for_day(targets, day, decision, slots)
                penalty = _add_excess(model, variables, maximum, f"{rule.id}::{day}", hard)
                if penalty is not None:
                    terms.append((rule.id, kind, weight, penalty))
        elif kind == "assignment_avoid_same_day_repeat":
            for day in all_days:
                variables = _variables_for_day(targets, day, decision, slots)
                penalty = _add_excess(model, variables, 1, f"{rule.id}::{day}", hard)
                if penalty is not None:
                    terms.append((rule.id, kind, weight, penalty))
        elif kind == "assignment_min_days":
            minimum = int(rule.parameters["minimum_days"])
            for week in range(problem.project_cycle_length):
                used = []
                for day in [d for d in all_days if d[0] == week]:
                    variables = _variables_for_day(targets, day, decision, slots)
                    if not variables:
                        continue
                    flag = model.new_bool_var(f"used::{rule.id}::{day}")
                    model.add(sum(variables) >= flag)
                    model.add(sum(variables) <= len(variables) * flag)
                    used.append(flag)
                if hard:
                    model.add(sum(used) >= minimum)
                else:
                    shortage = model.new_int_var(0, minimum, f"shortage::{rule.id}::{week}")
                    model.add(shortage >= minimum - sum(used))
                    terms.append((rule.id, kind, weight, shortage))
        elif kind in {
            "teacher_max_consecutive_lessons",
            "section_max_consecutive_lessons",
        }:
            maximum = int(rule.parameters["maximum"])
            _compile_consecutive_limit(model, rule, targets, maximum, hard, weight, decision, slots, terms)
        elif kind in {"assignment_forbid_consecutive", "assignment_min_gap"}:
            minimum_gap = int(rule.parameters.get("minimum_gap_minutes", 1))
            _compile_pair_distance(model, rule, targets, minimum_gap, hard, weight, decision, slots, terms)
        elif kind == "assignment_require_consecutive_block":
            _compile_required_blocks(model, rule, targets, int(rule.parameters["block_size"]), decision, slots)
        elif kind.startswith("assignments_") or kind == "assignment_before_assignment":
            _compile_relationship(model, rule, problem, hard, weight, decision, slots, terms)
        elif kind == "assignment_required_resource_type":
            # Resource choice is fixed by PM-002C assignments. The truthful hard
            # translation is therefore a structural feasibility assertion.
            resource_types = {resource.id: resource.resource_type for resource in problem.resources}
            required_type = str(rule.parameters["resource_type"])
            if any(not any(resource_types.get(resource_id) == required_type for resource_id in occurrence.resource_ids) for occurrence in targets):
                model.add_bool_or([])
        elif kind == "assignment_preferred_resource":
            resource_id = str(rule.selector.get("resource_id"))
            missing = sum(resource_id not in occurrence.resource_ids for occurrence in targets)
            if missing:
                penalty = model.new_int_var(missing, missing, f"resource::{rule.id}")
                terms.append((rule.id, kind, weight, penalty))
    return terms


def _ordered_intervals(slots: dict[str, TimeSlot], day: tuple[int, int], school_id: str | None = None) -> list[tuple[int, int]]:
    return sorted({
        (s.starts_at_minute, s.ends_at_minute)
        for s in slots.values()
        if _day_key(s) == day and (school_id is None or s.school_id == school_id)
    })


def _compile_consecutive_limit(model: cp_model.CpModel, rule: SchedulingRule, targets: list[LessonOccurrence], maximum: int, hard: bool, weight: int, decision: dict[tuple[str, str], cp_model.IntVar], slots: dict[str, TimeSlot], terms: list[tuple[str, str, int, cp_model.IntVar]]) -> None:
    for day in sorted({_day_key(s) for s in slots.values()}):
        intervals = _ordered_intervals(slots, day)
        for start in range(max(0, len(intervals) - maximum)):
            window = intervals[start : start + maximum + 1]
            if len(window) <= maximum or any(window[i][1] != window[i + 1][0] for i in range(len(window) - 1)):
                continue
            variables = [decision[(o.id, sid)] for o in targets for sid in o.candidate_slot_ids if (o.id, sid) in decision and _day_key(slots[sid]) == day and (slots[sid].starts_at_minute, slots[sid].ends_at_minute) in window]
            penalty = _add_excess(model, variables, maximum, f"streak::{rule.id}::{day}::{start}", hard)
            if penalty is not None:
                terms.append((rule.id, rule.rule_type, weight, penalty))


def _compile_pair_distance(model: cp_model.CpModel, rule: SchedulingRule, targets: list[LessonOccurrence], minimum_gap: int, hard: bool, weight: int, decision: dict[tuple[str, str], cp_model.IntVar], slots: dict[str, TimeSlot], terms: list[tuple[str, str, int, cp_model.IntVar]]) -> None:
    for index, left in enumerate(targets):
        for right in targets[index + 1 :]:
            for left_id in left.candidate_slot_ids:
                for right_id in right.candidate_slot_ids:
                    a, b = slots[left_id], slots[right_id]
                    if _day_key(a) != _day_key(b):
                        continue
                    gap = max(b.starts_at_minute - a.ends_at_minute, a.starts_at_minute - b.ends_at_minute)
                    if gap >= minimum_gap:
                        continue
                    pair = decision[(left.id, left_id)] + decision[(right.id, right_id)]
                    if hard:
                        model.add(pair <= 1)
                    else:
                        violation = model.new_bool_var(f"gap::{rule.id}::{left.id}::{right.id}::{left_id}::{right_id}")
                        model.add(violation >= pair - 1)
                        terms.append((rule.id, rule.rule_type, weight, violation))


def _compile_required_blocks(model: cp_model.CpModel, rule: SchedulingRule, targets: list[LessonOccurrence], size: int, decision: dict[tuple[str, str], cp_model.IntVar], slots: dict[str, TimeSlot]) -> None:
    by_week: dict[int, list[LessonOccurrence]] = defaultdict(list)
    for occurrence in targets:
        by_week[occurrence.project_cycle_week_index].append(occurrence)
    for week, occurrences in by_week.items():
        if len(occurrences) % size:
            model.add_bool_or([])
            continue
        blocks = []
        school = occurrences[0].school_id
        for day in sorted({_day_key(s) for s in slots.values() if s.project_cycle_week_index == week}):
            intervals = _ordered_intervals(slots, day, school)
            for start in range(len(intervals) - size + 1):
                block = intervals[start : start + size]
                if all(block[i][1] == block[i + 1][0] for i in range(size - 1)):
                    blocks.append((day, block, model.new_bool_var(f"block::{rule.id}::{week}::{day}::{start}")))
        model.add(sum(flag for _, _, flag in blocks) == len(occurrences) // size)
        for interval_slot in [s for s in slots.values() if s.project_cycle_week_index == week and s.school_id == school]:
            occupancy = [decision[(o.id, interval_slot.id)] for o in occurrences if (o.id, interval_slot.id) in decision]
            covering = [flag for day, block, flag in blocks if day == _day_key(interval_slot) and (interval_slot.starts_at_minute, interval_slot.ends_at_minute) in block]
            model.add(sum(occupancy) == sum(covering))


def _compile_relationship(model: cp_model.CpModel, rule: SchedulingRule, problem: SchedulingProblem, hard: bool, weight: int, decision: dict[tuple[str, str], cp_model.IntVar], slots: dict[str, TimeSlot], terms: list[tuple[str, str, int, cp_model.IntVar]]) -> None:
    ids = [str(x) for x in rule.selector.get("assignment_ids", [])]
    if len(ids) != 2:
        model.add_bool_or([])
        return
    groups = [[o for o in problem.occurrences if o.assignment_id == assignment_id] for assignment_id in ids]
    for week in range(problem.project_cycle_length):
        left = sorted((o for o in groups[0] if o.project_cycle_week_index == week), key=lambda x: x.id)
        right = sorted((o for o in groups[1] if o.project_cycle_week_index == week), key=lambda x: x.id)
        if len(left) != len(right):
            model.add_bool_or([])
            continue
        for a, b in zip(left, right, strict=True):
            same_time_rule = rule.rule_type in {"assignments_same_time", "assignments_not_same_time"}
            keys: list[tuple[int, ...]] = (
                list(sorted({_time_key(slots[sid]) for sid in a.candidate_slot_ids + b.candidate_slot_ids}))
                if same_time_rule
                else list(sorted({_day_key(slots[sid]) for sid in a.candidate_slot_ids + b.candidate_slot_ids}))
            )
            for key in keys:
                av = [decision[(a.id, sid)] for sid in a.candidate_slot_ids if (_time_key(slots[sid]) if same_time_rule else _day_key(slots[sid])) == key]
                bv = [decision[(b.id, sid)] for sid in b.candidate_slot_ids if (_time_key(slots[sid]) if same_time_rule else _day_key(slots[sid])) == key]
                if rule.rule_type in {"assignments_same_time", "assignments_same_day"}:
                    if hard:
                        model.add(sum(av) == sum(bv))
                    else:
                        delta = model.new_int_var(0, 1, f"relation::{rule.id}::{a.id}::{key}")
                        model.add_abs_equality(delta, sum(av) - sum(bv))
                        terms.append((rule.id, rule.rule_type, weight, delta))
                elif rule.rule_type in {"assignments_not_same_time", "assignments_different_day"}:
                    if hard:
                        model.add(sum(av) + sum(bv) <= 1)
                    else:
                        overlap = model.new_bool_var(f"relation::{rule.id}::{a.id}::{key}")
                        model.add(overlap >= sum(av) + sum(bv) - 1)
                        terms.append((rule.id, rule.rule_type, weight, overlap))
            if rule.rule_type == "assignment_before_assignment":
                for aid in a.candidate_slot_ids:
                    for bid in b.candidate_slot_ids:
                        sa, sb = slots[aid], slots[bid]
                        invalid = _day_key(sa) != _day_key(sb) or sa.ends_at_minute > sb.starts_at_minute
                        if not invalid:
                            continue
                        pair = decision[(a.id, aid)] + decision[(b.id, bid)]
                        if hard:
                            model.add(pair <= 1)
                        else:
                            violation = model.new_bool_var(f"order::{rule.id}::{aid}::{bid}")
                            model.add(violation >= pair - 1)
                            terms.append((rule.id, rule.rule_type, weight, violation))


def _compile_profile_objectives(model: cp_model.CpModel, problem: SchedulingProblem, decision: dict[tuple[str, str], cp_model.IntVar], slots: dict[str, TimeSlot]) -> list[tuple[str, str, int, cp_model.IntVar]]:
    weights = problem.options.optimization_weights if problem.options.optimization_profile == "custom" else PROFILE_POLICIES[problem.options.optimization_profile]
    terms: list[tuple[str, str, int, cp_model.IntVar]] = []
    first_by_teacher: dict[str, list[cp_model.IntVar]] = defaultdict(list)
    last_by_teacher: dict[str, list[cp_model.IntVar]] = defaultdict(list)
    # Streak and edge-period fairness use factual occupancy variables. Gap
    # reporting remains exact in the quality evaluator; this objective counts
    # internal empty intervals bracketed by two lessons.
    for teacher in problem.teachers:
        occurrences = [o for o in problem.occurrences if teacher.id in o.teacher_ids]
        for day in sorted({_day_key(s) for s in slots.values()}):
            intervals = sorted({(slots[sid].starts_at_minute, slots[sid].ends_at_minute) for occurrence in occurrences for sid in occurrence.candidate_slot_ids if _day_key(slots[sid]) == day})
            occupied = []
            for index, interval in enumerate(intervals):
                variables = [decision[(o.id, sid)] for o in occurrences for sid in o.candidate_slot_ids if _day_key(slots[sid]) == day and (slots[sid].starts_at_minute, slots[sid].ends_at_minute) == interval]
                flag = model.new_bool_var(f"occupied::{teacher.id}::{day}::{index}")
                model.add(sum(variables) >= flag)
                model.add(sum(variables) <= max(1, len(variables)) * flag)
                occupied.append(flag)
            for index in range(1, len(occupied) - 1):
                before = model.new_bool_var(f"teacher-before::{teacher.id}::{day}::{index}")
                after = model.new_bool_var(f"teacher-after::{teacher.id}::{day}::{index}")
                model.add_max_equality(before, occupied[:index])
                model.add_max_equality(after, occupied[index + 1 :])
                gap = model.new_bool_var(f"teacher-gap::{teacher.id}::{day}::{index}")
                model.add(gap >= before + after - occupied[index] - 1)
                terms.append((f"profile:{problem.options.optimization_profile}:teacher_gaps", "teacher_gaps", weights.get("teacher_gaps", 0), gap))
            for start in range(max(0, len(occupied) - 3)):
                streak = model.new_bool_var(f"profile-streak::{teacher.id}::{day}::{start}")
                model.add(streak >= sum(occupied[start : start + 4]) - 3)
                terms.append((f"profile:{problem.options.optimization_profile}:teaching_streaks", "teaching_streaks", weights.get("teaching_streaks", 0), streak))
            if occupied:
                first_by_teacher[teacher.id].append(occupied[0])
                last_by_teacher[teacher.id].append(occupied[-1])
    day_bound = max(1, problem.project_cycle_length * 7)
    for kind, values_by_teacher in (("first_period_fairness", first_by_teacher), ("last_period_fairness", last_by_teacher)):
        counts = []
        for teacher_id, flags in values_by_teacher.items():
            count = model.new_int_var(0, day_bound, f"{kind}-count::{teacher_id}")
            model.add(count == sum(flags))
            counts.append(count)
        if len(counts) > 1:
            maximum = model.new_int_var(0, day_bound, f"{kind}-max")
            minimum = model.new_int_var(0, day_bound, f"{kind}-min")
            model.add_max_equality(maximum, counts)
            model.add_min_equality(minimum, counts)
            imbalance = model.new_int_var(0, day_bound, f"{kind}-imbalance")
            model.add(imbalance == maximum - minimum)
            terms.append((f"profile:{problem.options.optimization_profile}:{kind}", kind, weights.get(kind, 0), imbalance))
    return [term for term in terms if term[2] > 0]


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

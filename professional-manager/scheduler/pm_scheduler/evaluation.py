from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from pm_scheduler.contracts import Placement, SchedulingProblem, SchedulingRule, TimeSlot, slots_overlap
from pm_scheduler.rules import PROFILE_POLICIES, RULE_REGISTRY, effective_rule_weight


def evaluate_schedule(problem: SchedulingProblem, placements: list[Placement]) -> dict[str, Any]:
    slot_by_id = {slot.id: slot for slot in problem.slots}
    occurrence_by_id = {item.id: item for item in problem.occurrences}
    placed = [(occurrence_by_id[p.occurrence_id], slot_by_id[p.slot_id]) for p in placements]
    hard: list[dict[str, Any]] = []
    breakdown: list[dict[str, Any]] = []
    distribution: list[dict[str, Any]] = []

    occupants: dict[tuple[str, str], list[tuple[Any, TimeSlot]]] = defaultdict(list)
    exclusive = {r.id for r in problem.resources if r.exclusive}
    for occurrence, slot in placed:
        for entity in occurrence.teacher_ids:
            occupants[("teacher", entity)].append((occurrence, slot))
        for entity in occurrence.section_ids:
            occupants[("section", entity)].append((occurrence, slot))
        for entity in occurrence.resource_ids:
            if entity in exclusive:
                occupants[("resource", entity)].append((occurrence, slot))
    for (kind, entity), values in occupants.items():
        for index, (left, left_slot) in enumerate(values):
            for right, right_slot in values[index + 1 :]:
                if slots_overlap(left_slot, right_slot):
                    hard.append({"rule_type": f"{kind}_collision", "entity_id": entity, "occurrence_ids": [left.id, right.id]})

    for rule in problem.rules:
        values = [(o, s) for o, s in placed if _targets(rule, o)]
        if rule.rule_type == "assignment_required_resource_type":
            types = {resource.id: resource.resource_type for resource in problem.resources}
            expected = str(rule.parameters["resource_type"])
            count = sum(not any(types.get(resource_id) == expected for resource_id in occurrence.resource_ids) for occurrence, _ in values)
            facts: list[dict[str, Any]] = []
        else:
            count, facts = _rule_violations(rule, values)
        if count:
            fact = {"rule_id": rule.id, "rule_type": rule.rule_type, "violation_count": count, "facts": facts}
            distribution.append(fact)
            if rule.severity == "hard":
                hard.append(fact)
            else:
                effective = effective_rule_weight(problem.options.optimization_profile, rule.rule_type, rule.weight or 0)
                breakdown.append({**fact, "weight": effective, "weighted_penalty": count * effective, "category": RULE_REGISTRY[rule.rule_type].category})

    teacher_metrics = _teacher_metrics(problem, placed)
    weights = problem.options.optimization_weights if problem.options.optimization_profile == "custom" else PROFILE_POLICIES[problem.options.optimization_profile]
    profile_values = {
        "teacher_gaps": teacher_metrics["total_gaps"],
        "first_period_fairness": teacher_metrics["first_period_imbalance"],
        "last_period_fairness": teacher_metrics["last_period_imbalance"],
        "teaching_streaks": teacher_metrics["excessive_streaks"],
    }
    for kind, count in profile_values.items():
        if count and weights.get(kind, 0):
            breakdown.append({"rule_id": f"profile:{problem.options.optimization_profile}:{kind}", "rule_type": kind, "violation_count": count, "weight": weights[kind], "weighted_penalty": count * weights[kind], "category": "fairness"})
    return {
        "hard_violations": hard,
        "total_weighted_penalty": sum(item["weighted_penalty"] for item in breakdown),
        "penalty_breakdown": breakdown,
        "teacher_gaps": teacher_metrics["teacher_gaps"],
        "teacher_gap_total": teacher_metrics["total_gaps"],
        "first_period_distribution": teacher_metrics["first_distribution"],
        "last_period_distribution": teacher_metrics["last_distribution"],
        "consecutive_streaks": teacher_metrics["streaks"],
        "distribution_violations": distribution,
        "optimization_profile": problem.options.optimization_profile,
    }


def placement_explanation(problem: SchedulingProblem, placements: list[Placement], occurrence_id: str) -> dict[str, Any]:
    selected = next(p for p in placements if p.occurrence_id == occurrence_id)
    occurrence = next(o for o in problem.occurrences if o.id == occurrence_id)
    slot_by_id = {s.id: s for s in problem.slots}
    chosen = slot_by_id[selected.slot_id]
    base = evaluate_schedule(problem, placements)
    alternatives = []
    for slot_id in occurrence.candidate_slot_ids:
        if slot_id == selected.slot_id:
            continue
        proposed = [p.model_copy(update={"slot_id": slot_id}) if p.occurrence_id == occurrence_id else p for p in placements]
        report = evaluate_schedule(problem, proposed)
        new_hard = [item for item in report["hard_violations"] if item not in base["hard_violations"]]
        alternatives.append({
            "slot": slot_by_id[slot_id].model_dump(mode="json"),
            "status": "blocked" if new_hard else "valid_but_worse" if report["total_weighted_penalty"] > base["total_weighted_penalty"] else "valid",
            "blocking_facts": new_hard,
            "penalty_delta": report["total_weighted_penalty"] - base["total_weighted_penalty"],
        })
    alternatives.sort(key=lambda item: (item["status"] == "blocked", item["penalty_delta"]))
    affecting = []
    for rule in problem.rules:
        if _targets(rule, occurrence):
            matches = _slot_matches(chosen, rule.parameters)
            violated = any(item.get("rule_id") == rule.id for item in base["hard_violations"])
            effect = "penalized" if rule.severity == "soft" and ((rule.rule_type.endswith("preferred_time") and not matches) or (rule.rule_type.endswith("avoided_time") and matches)) else "favored" if rule.severity == "soft" and rule.rule_type.endswith("preferred_time") and matches else "satisfied"
            affecting.append({"rule_id": rule.id, "rule_type": rule.rule_type, "severity": rule.severity, "selected_time_matches": matches, "satisfied": not violated, "effect": effect})
    return {
        "occurrence_id": occurrence_id,
        "chosen_slot": chosen.model_dump(mode="json"),
        "mandatory_rule_facts": [x for x in affecting if x["severity"] == "hard"],
        "preference_rule_facts": [x for x in affecting if x["severity"] == "soft"],
        "entity_facts": {"teacher_ids": occurrence.teacher_ids, "section_ids": occurrence.section_ids, "resource_ids": occurrence.resource_ids},
        "alternatives": alternatives[:12],
    }


def _targets(rule: SchedulingRule, occurrence: Any) -> bool:
    if "assignment_ids" in rule.selector:
        return occurrence.assignment_id in {str(x) for x in rule.selector["assignment_ids"]}
    mapping = {"assignment_id": occurrence.assignment_id, "teacher_id": occurrence.teacher_ids, "section_id": occurrence.section_ids, "resource_id": occurrence.resource_ids, "subject_id": occurrence.subject_id}
    return any((str(value) in target if isinstance(target, list) else str(value) == target) for key, value in rule.selector.items() if (target := mapping.get(key)) is not None)


def _slot_matches(slot: TimeSlot, params: dict[str, Any]) -> bool:
    return all(params.get(key) is None or getattr(slot, key) == params[key] for key in ("project_cycle_week_index", "weekday_index", "starts_at_minute", "ends_at_minute")) and (not params.get("slot_id") or slot.id == params["slot_id"])


def _rule_violations(rule: SchedulingRule, values: list[tuple[Any, TimeSlot]]) -> tuple[int, list[dict[str, Any]]]:
    kind = rule.rule_type
    facts: list[dict[str, Any]] = []
    if kind == "assignment_required_time":
        return sum(not _slot_matches(slot, rule.parameters) for _, slot in values), facts
    if kind.endswith("unavailable") or kind == "assignment_forbidden_time":
        return sum(_slot_matches(slot, rule.parameters) for _, slot in values), facts
    if kind.endswith("preferred_time"):
        return sum(not _slot_matches(slot, rule.parameters) for _, slot in values), facts
    if kind.endswith("avoided_time"):
        return sum(_slot_matches(slot, rule.parameters) for _, slot in values), facts
    by_day: Counter[tuple[int, int]] = Counter((s.project_cycle_week_index, s.weekday_index) for _, s in values)
    if kind in {"assignment_max_per_day", "teacher_max_lessons_per_day", "section_max_lessons_per_day"}:
        maximum = int(rule.parameters["maximum"])
        count = sum(max(0, value - maximum) for value in by_day.values())
        return count, [{"day": day, "count": value, "maximum": maximum} for day, value in by_day.items() if value > maximum]
    if kind == "assignment_avoid_same_day_repeat":
        return sum(max(0, value - 1) for value in by_day.values()), facts
    if kind == "assignment_min_days":
        minimum = int(rule.parameters["minimum_days"])
        by_week: Counter[int] = Counter()
        for week, _ in by_day:
            by_week[week] += 1
        return sum(max(0, minimum - by_week[week]) for week in {s.project_cycle_week_index for _, s in values}), facts
    if kind in {"teacher_max_consecutive_lessons", "section_max_consecutive_lessons"}:
        maximum = int(rule.parameters["maximum"])
        return sum(max(0, streak - maximum) for streak in _streak_lengths(values)), facts
    if kind == "assignment_require_consecutive_block":
        size = int(rule.parameters["block_size"])
        lengths = _streak_lengths(values)
        return (0 if lengths and all(length % size == 0 for length in lengths) else max(1, len(values) % size)), facts
    if kind in {"assignment_forbid_consecutive", "assignment_min_gap"}:
        threshold = int(rule.parameters.get("minimum_gap_minutes", 1))
        return _pair_gap_violations(values, threshold), facts
    if kind in {"assignments_not_same_time", "assignments_different_day"}:
        assignment_values: dict[str, list[TimeSlot]] = defaultdict(list)
        for occurrence, slot in values:
            assignment_values[occurrence.assignment_id].append(slot)
        groups = list(assignment_values.values())
        if len(groups) != 2:
            return 1, facts
        if kind == "assignments_not_same_time":
            return sum(a.project_cycle_week_index == b.project_cycle_week_index and a.weekday_index == b.weekday_index and a.starts_at_minute == b.starts_at_minute and a.ends_at_minute == b.ends_at_minute for a in groups[0] for b in groups[1]), facts
        return sum((a.project_cycle_week_index, a.weekday_index) == (b.project_cycle_week_index, b.weekday_index) for a in groups[0] for b in groups[1]), facts
    if kind in {"assignments_same_time", "assignments_same_day", "assignment_before_assignment"}:
        paired_assignment_values: dict[str, list[TimeSlot]] = defaultdict(list)
        for occurrence, slot in values:
            paired_assignment_values[occurrence.assignment_id].append(slot)
        ids = [str(x) for x in rule.selector.get("assignment_ids", [])]
        if len(ids) != 2 or len(paired_assignment_values.get(ids[0], [])) != len(paired_assignment_values.get(ids[1], [])):
            return 1, facts
        pairs = zip(sorted(paired_assignment_values[ids[0]], key=lambda s: (s.project_cycle_week_index, s.weekday_index, s.starts_at_minute)), sorted(paired_assignment_values[ids[1]], key=lambda s: (s.project_cycle_week_index, s.weekday_index, s.starts_at_minute)), strict=True)
        if kind == "assignments_same_time":
            return sum((a.project_cycle_week_index, a.weekday_index, a.starts_at_minute, a.ends_at_minute) != (b.project_cycle_week_index, b.weekday_index, b.starts_at_minute, b.ends_at_minute) for a, b in pairs), facts
        if kind == "assignments_same_day":
            return sum((a.project_cycle_week_index, a.weekday_index) != (b.project_cycle_week_index, b.weekday_index) for a, b in pairs), facts
        return sum((a.project_cycle_week_index, a.weekday_index) != (b.project_cycle_week_index, b.weekday_index) or a.ends_at_minute > b.starts_at_minute for a, b in pairs), facts
    if kind == "assignment_preferred_resource":
        resource_id = str(rule.selector.get("resource_id"))
        return sum(resource_id not in occurrence.resource_ids for occurrence, _ in values if occurrence.assignment_id == str(rule.selector.get("assignment_id"))), facts
    if kind == "assignment_required_resource_type":
        # The compiler owns the resource type map; no dynamic choice exists.
        return 0, facts
    return 0, facts


def _pair_gap_violations(values: list[tuple[Any, TimeSlot]], threshold: int) -> int:
    count = 0
    for index, (_, left) in enumerate(values):
        for _, right in values[index + 1 :]:
            if (left.project_cycle_week_index, left.weekday_index) != (right.project_cycle_week_index, right.weekday_index):
                continue
            gap = max(right.starts_at_minute - left.ends_at_minute, left.starts_at_minute - right.ends_at_minute)
            count += gap < threshold
    return count


def _streak_lengths(values: list[tuple[Any, TimeSlot]]) -> list[int]:
    by_day: dict[tuple[int, int], list[TimeSlot]] = defaultdict(list)
    for _, slot in values:
        by_day[(slot.project_cycle_week_index, slot.weekday_index)].append(slot)
    result = []
    for rows in by_day.values():
        ordered = sorted(rows, key=lambda s: s.starts_at_minute)
        current = 1
        for left, right in zip(ordered, ordered[1:], strict=False):
            if left.ends_at_minute == right.starts_at_minute:
                current += 1
            else:
                result.append(current)
                current = 1
        result.append(current)
    return result


def _teacher_metrics(problem: SchedulingProblem, placed: list[tuple[Any, TimeSlot]]) -> dict[str, Any]:
    teacher_days: dict[str, dict[tuple[int, int], list[TimeSlot]]] = defaultdict(lambda: defaultdict(list))
    for occurrence, slot in placed:
        for teacher in occurrence.teacher_ids:
            teacher_days[teacher][(slot.project_cycle_week_index, slot.weekday_index)].append(slot)
    gaps: dict[str, int] = Counter()
    first: dict[str, int] = Counter()
    last: dict[str, int] = Counter()
    streak_rows: list[dict[str, Any]] = []
    for teacher, days in teacher_days.items():
        for day, values in days.items():
            ordered = sorted(values, key=lambda s: (s.starts_at_minute, s.ends_at_minute))
            teacher_occurrences = [occurrence for occurrence in problem.occurrences if teacher in occurrence.teacher_ids]
            slot_by_id = {slot.id: slot for slot in problem.slots}
            day_slots = sorted({(slot_by_id[slot_id].starts_at_minute, slot_by_id[slot_id].ends_at_minute) for occurrence in teacher_occurrences for slot_id in occurrence.candidate_slot_ids if (slot_by_id[slot_id].project_cycle_week_index, slot_by_id[slot_id].weekday_index) == day})
            occupied = {(s.starts_at_minute, s.ends_at_minute) for s in ordered}
            indexes = [i for i, interval in enumerate(day_slots) if interval in occupied]
            if indexes:
                gaps[teacher] += sum(1 for i in range(min(indexes) + 1, max(indexes)) if day_slots[i] not in occupied)
                first[teacher] += indexes[0] == 0
                last[teacher] += indexes[-1] == len(day_slots) - 1
            streak = current = 1 if ordered else 0
            for left_slot, right_slot in zip(ordered, ordered[1:], strict=False):
                current = current + 1 if left_slot.ends_at_minute == right_slot.starts_at_minute else 1
                streak = max(streak, current)
            streak_rows.append({"teacher_id": teacher, "project_cycle_week_index": day[0], "weekday_index": day[1], "maximum_streak": streak})
    for teacher in problem.teachers:
        first.setdefault(teacher.id, 0)
        last.setdefault(teacher.id, 0)
        gaps.setdefault(teacher.id, 0)
    first_values = list(first.values()) or [0]
    last_values = list(last.values()) or [0]
    return {"teacher_gaps": dict(gaps), "total_gaps": sum(gaps.values()), "first_distribution": dict(first), "last_distribution": dict(last), "first_period_imbalance": max(first_values) - min(first_values), "last_period_imbalance": max(last_values) - min(last_values), "streaks": streak_rows, "excessive_streaks": sum(max(0, row["maximum_streak"] - 3) for row in streak_rows)}

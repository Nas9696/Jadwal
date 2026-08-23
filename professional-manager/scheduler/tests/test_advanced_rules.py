from pm_scheduler.contracts import Entity, LessonOccurrence, SchedulingProblem, SchedulingRule, SolveOptions, TimeSlot
from pm_scheduler.evaluation import evaluate_schedule, placement_explanation
from pm_scheduler.solver import Scheduler


def slot(slot_id: str, day: int, start: int) -> TimeSlot:
    return TimeSlot(id=slot_id, school_id="school", week_pattern_id="A", local_cycle_week_index=0, project_cycle_week_index=0, weekday_index=day, starts_at_minute=start, ends_at_minute=start + 45, period=start // 45 + 1)


def occurrence(occurrence_id: str, assignment: str, teacher: str, section: str, slots: list[str], subject: str = "math") -> LessonOccurrence:
    return LessonOccurrence(id=occurrence_id, assignment_id=assignment, school_id="school", subject_id=subject, project_cycle_week_index=0, teacher_ids=[teacher], section_ids=[section], candidate_slot_ids=slots)


def problem(occurrences: list[LessonOccurrence], slots: list[TimeSlot], rules: list[SchedulingRule], profile: str = "balanced") -> SchedulingProblem:
    return SchedulingProblem(problem_id="advanced", project_cycle_length=1, slots=slots, teachers=[Entity(id=x) for x in sorted({t for o in occurrences for t in o.teacher_ids})], sections=[Entity(id=x) for x in sorted({s for o in occurrences for s in o.section_ids})], occurrences=occurrences, rules=rules, options=SolveOptions(candidate_count=1, time_limit_seconds=5, optimization_profile=profile))


def hard(rule_type: str, selector: dict[str, object], parameters: dict[str, object]) -> SchedulingRule:
    return SchedulingRule(id=rule_type, rule_type=rule_type, severity="hard", selector=selector, parameters=parameters)


def soft(rule_type: str, selector: dict[str, object], parameters: dict[str, object], weight: int = 10) -> SchedulingRule:
    return SchedulingRule(id=rule_type, rule_type=rule_type, severity="soft", weight=weight, selector=selector, parameters=parameters)


def test_daily_limit_and_minimum_days_are_cp_sat_constraints() -> None:
    slots = [slot("sun-1", 0, 480), slot("sun-2", 0, 525), slot("mon-1", 1, 480)]
    occurrences = [occurrence("a1", "a", "t", "s", [x.id for x in slots]), occurrence("a2", "a", "t", "s", [x.id for x in slots])]
    rules = [hard("assignment_max_per_day", {"assignment_id": "a"}, {"maximum": 1}), hard("assignment_min_days", {"assignment_id": "a"}, {"minimum_days": 2})]
    result = Scheduler().solve(problem(occurrences, slots, rules))
    assert result.feasible
    selected = {next(x for x in slots if x.id == p.slot_id).weekday_index for p in result.candidates[0].placements}
    assert selected == {0, 1}


def test_double_and_triple_blocks_use_real_adjacency() -> None:
    slots = [slot("p1", 0, 480), slot("p2", 0, 525), slot("p3", 0, 570), slot("late", 0, 700)]
    occurrences = [occurrence(f"a{i}", "a", "t", "s", [x.id for x in slots]) for i in range(3)]
    result = Scheduler().solve(problem(occurrences, slots, [hard("assignment_require_consecutive_block", {"assignment_id": "a"}, {"block_size": 3})]))
    assert result.feasible
    assert {p.slot_id for p in result.candidates[0].placements} == {"p1", "p2", "p3"}


def test_forbid_consecutive_and_minimum_gap() -> None:
    slots = [slot("p1", 0, 480), slot("p2", 0, 525), slot("p3", 0, 600)]
    occurrences = [occurrence("a1", "a", "t", "s", [x.id for x in slots]), occurrence("a2", "a", "t", "s", [x.id for x in slots])]
    rules = [hard("assignment_forbid_consecutive", {"assignment_id": "a"}, {}), hard("assignment_min_gap", {"assignment_id": "a"}, {"minimum_gap_minutes": 90})]
    assert not Scheduler().solve(problem(occurrences, slots, rules)).feasible


def test_same_time_and_order_relationships() -> None:
    slots = [slot("p1", 0, 480), slot("p2", 0, 525)]
    occurrences = [occurrence("a1", "a", "t1", "s1", [x.id for x in slots]), occurrence("b1", "b", "t2", "s2", [x.id for x in slots])]
    same = hard("assignments_same_time", {"assignment_ids": ["a", "b"]}, {})
    solved = Scheduler().solve(problem(occurrences, slots, [same]))
    assert solved.feasible
    assert len({p.slot_id for p in solved.candidates[0].placements}) == 1
    ordered = Scheduler().solve(problem(occurrences, slots, [hard("assignment_before_assignment", {"assignment_ids": ["a", "b"]}, {})]))
    assert ordered.feasible
    placement = {p.assignment_id: p.slot_id for p in ordered.candidates[0].placements}
    assert placement == {"a": "p1", "b": "p2"}


def test_subject_preference_quality_and_explanation_are_factual() -> None:
    slots = [slot("early", 0, 480), slot("late", 0, 525)]
    occurrence_row = occurrence("a1", "a", "t", "s", [x.id for x in slots])
    rule = soft("subject_preferred_time", {"subject_id": "math"}, {"starts_at_minute": 480}, 25)
    solved = Scheduler().solve(problem([occurrence_row], slots, [rule]))
    candidate = solved.candidates[0]
    assert candidate.placements[0].slot_id == "early"
    quality = evaluate_schedule(problem([occurrence_row], slots, [rule]), candidate.placements)
    explanation = placement_explanation(problem([occurrence_row], slots, [rule]), candidate.placements, "a1")
    assert quality["hard_violations"] == []
    assert explanation["chosen_slot"]["starts_at_minute"] == 480
    assert explanation["alternatives"][0]["penalty_delta"] == 25


def test_optimization_profile_changes_objective_fingerprint_input() -> None:
    slots = [slot("p1", 0, 480)]
    occurrence_row = occurrence("a1", "a", "t", "s", ["p1"])
    balanced = problem([occurrence_row], slots, [])
    comfort = problem([occurrence_row], slots, [], "teacher_comfort")
    assert balanced.model_dump(mode="json") != comfort.model_dump(mode="json")

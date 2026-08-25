from pm_scheduler.contracts import (
    ExistingPlacement,
    LessonOccurrence,
    ResourceEntity,
    SchedulingProblem,
    SchedulingRule,
    Severity,
    SolveOptions,
    SolveResult,
    TimeSlot,
)
from ortools.sat.python import cp_model
from pm_scheduler import solver as solver_module
from pm_scheduler.solver import Scheduler


def slot(
    slot_id: str,
    school: str,
    start: int,
    end: int,
    *,
    period: int = 1,
    attendance: str = "onsite",
) -> TimeSlot:
    return TimeSlot(
        id=slot_id,
        school_id=school,
        week_pattern_id=f"{school}-A",
        local_cycle_week_index=0,
        project_cycle_week_index=0,
        weekday_index=0,
        starts_at_minute=start,
        ends_at_minute=end,
        period=period,
        attendance_mode=attendance,
    )


def occurrence(
    occurrence_id: str,
    assignment_id: str,
    school: str,
    candidates: list[str],
    *,
    teachers: list[str] | None = None,
    sections: list[str] | None = None,
    resources: list[str] | None = None,
) -> LessonOccurrence:
    return LessonOccurrence(
        id=occurrence_id,
        assignment_id=assignment_id,
        school_id=school,
        subject_id=f"subject-{assignment_id}",
        project_cycle_week_index=0,
        teacher_ids=teachers or [],
        section_ids=sections or [],
        resource_ids=resources or [],
        candidate_slot_ids=candidates,
    )


def problem(
    slots: list[TimeSlot],
    occurrences: list[LessonOccurrence],
    *,
    resources: list[ResourceEntity] | None = None,
    rules: list[SchedulingRule] | None = None,
    count: int = 1,
    seed: int = 7,
) -> SchedulingProblem:
    return SchedulingProblem(
        problem_id="fixture",
        slots=slots,
        teachers=[],
        sections=[],
        resources=resources or [],
        occurrences=occurrences,
        rules=rules or [],
        options=SolveOptions(candidate_count=count, seed=seed, time_limit_seconds=1),
    )


def selected(result: SolveResult) -> dict[str, str]:
    candidate = result.candidates[0]
    return {item.occurrence_id: item.slot_id for item in candidate.placements}


def test_feasible_schedule_places_every_occurrence_exactly_once_and_returns_three_distinct() -> None:
    slots = [slot(f"s{i}", "school-a", 480 + i * 50, 525 + i * 50) for i in range(3)]
    occurrences = [
        occurrence("o1", "a1", "school-a", [item.id for item in slots], teachers=["t1"]),
        occurrence("o2", "a2", "school-a", [item.id for item in slots], teachers=["t1"]),
    ]
    result = Scheduler().solve(problem(slots, occurrences, count=3))
    assert result.feasible
    assert len(result.candidates) == 3
    signatures = {
        tuple(sorted((item.occurrence_id, item.slot_id) for item in candidate.placements))
        for candidate in result.candidates
    }
    assert len(signatures) == 3
    assert all(len(candidate.placements) == len(occurrences) for candidate in result.candidates)


def test_partial_schedule_maximizes_placements_and_reports_unscheduled_occurrence() -> None:
    slots = [slot("only-slot", "school-a", 480, 525)]
    occurrences = [
        occurrence("o1", "a1", "school-a", ["only-slot"], sections=["section-1"]),
        occurrence("o2", "a2", "school-a", ["only-slot"], sections=["section-1"]),
    ]
    fixture = problem(slots, occurrences)
    fixture.options = SolveOptions(candidate_count=1, seed=7, time_limit_seconds=1, allow_partial=True)
    result = Scheduler().solve(fixture)
    assert result.feasible
    assert len(result.candidates[0].placements) == 1
    assert len(result.candidates[0].unscheduled_occurrence_ids) == 1
    assert result.diagnostics[0].code == "partial_schedule"


def test_shared_teacher_cross_school_collision_uses_real_time_and_ignores_attendance() -> None:
    slots = [
        slot("a-period-2", "school-a", 480, 525, period=2),
        slot("b-period-3", "school-b", 500, 540, period=3, attendance="remote"),
        slot("b-period-4", "school-b", 550, 595, period=4),
    ]
    occurrences = [
        occurrence("oa", "aa", "school-a", ["a-period-2"], teachers=["shared"]),
        occurrence(
            "ob", "ab", "school-b", ["b-period-3", "b-period-4"], teachers=["shared"]
        ),
    ]
    result = Scheduler().solve(problem(slots, occurrences))
    assert selected(result)["ob"] == "b-period-4"


def test_combined_sections_and_co_teaching_reserve_every_link_once() -> None:
    slots = [slot("early", "school-a", 480, 525), slot("late", "school-a", 530, 575)]
    combined = occurrence(
        "combined",
        "a1",
        "school-a",
        ["early"],
        teachers=["t1", "t2"],
        sections=["s1", "s2"],
    )
    conflicting = occurrence(
        "other",
        "a2",
        "school-a",
        ["early", "late"],
        teachers=["t2"],
        sections=["s2"],
    )
    result = Scheduler().solve(problem(slots, [combined, conflicting]))
    assert len(result.candidates[0].placements) == 2
    assert selected(result)["other"] == "late"


def test_split_assignments_remain_independent() -> None:
    slots = [slot("early", "school-a", 480, 525), slot("late", "school-a", 530, 575)]
    occurrences = [
        occurrence("split-a", "assignment-a", "school-a", ["early", "late"], sections=["s1"]),
        occurrence("split-b", "assignment-b", "school-a", ["early", "late"], sections=["s2"]),
    ]
    result = Scheduler().solve(problem(slots, occurrences))
    assert result.feasible
    assert {item.assignment_id for item in result.candidates[0].placements} == {
        "assignment-a",
        "assignment-b",
    }


def test_exclusive_resource_collides_but_shareable_resource_does_not() -> None:
    slots = [slot("a", "school-a", 480, 525), slot("b", "school-a", 530, 575)]
    occurrences = [
        occurrence("o1", "a1", "school-a", ["a"], resources=["lab"]),
        occurrence("o2", "a2", "school-a", ["a", "b"], resources=["lab"]),
    ]
    exclusive = Scheduler().solve(
        problem(slots, occurrences, resources=[ResourceEntity(id="lab", exclusive=True)])
    )
    assert selected(exclusive)["o2"] == "b"
    shareable_occurrences = [
        occurrence("o1", "a1", "school-a", ["a"], resources=["lab"]),
        occurrence("o2", "a2", "school-a", ["a"], resources=["lab"]),
    ]
    shareable = Scheduler().solve(
        problem(
            slots,
            shareable_occurrences,
            resources=[ResourceEntity(id="lab", exclusive=False)],
        )
    )
    assert shareable.feasible
    assert {item.slot_id for item in shareable.candidates[0].placements} == {"a"}


def test_hard_required_forbidden_and_unavailable_rules_are_enforced() -> None:
    slots = [slot("early", "school-a", 480, 525), slot("late", "school-a", 530, 575)]
    item = occurrence("o1", "a1", "school-a", ["early", "late"], teachers=["t1"])
    rules = [
        SchedulingRule(
            id="required",
            rule_type="assignment_required_time",
            severity=Severity.HARD,
            selector={"assignment_id": "a1"},
            parameters={"slot_id": "late"},
        ),
        SchedulingRule(
            id="forbidden",
            rule_type="teacher_unavailable",
            severity=Severity.HARD,
            selector={"teacher_id": "t1"},
            parameters={"slot_id": "early"},
        ),
    ]
    assert selected(Scheduler().solve(problem(slots, [item], rules=rules)))["o1"] == "late"


def test_teacher_section_and_resource_unavailability_are_all_hard() -> None:
    slots = [slot("early", "school-a", 480, 525), slot("late", "school-a", 530, 575)]
    item = occurrence(
        "o1",
        "a1",
        "school-a",
        ["early", "late"],
        teachers=["t1"],
        sections=["s1"],
        resources=["r1"],
    )
    for rule_type, selector in (
        ("teacher_unavailable", {"teacher_id": "t1"}),
        ("section_unavailable", {"section_id": "s1"}),
        ("resource_unavailable", {"resource_id": "r1"}),
    ):
        rule = SchedulingRule(
            id=rule_type,
            rule_type=rule_type,
            severity=Severity.HARD,
            selector=selector,
            parameters={"slot_id": "early"},
        )
        assert selected(Scheduler().solve(problem(slots, [item], rules=[rule])))["o1"] == "late"


def test_soft_preferred_and_avoided_rules_drive_objective_and_breakdown() -> None:
    slots = [slot("early", "school-a", 480, 525), slot("late", "school-a", 530, 575)]
    item = occurrence("o1", "a1", "school-a", ["early", "late"], teachers=["t1"])
    rules = [
        SchedulingRule(
            id="prefer-late",
            rule_type="teacher_preferred_time",
            severity=Severity.SOFT,
            weight=20,
            selector={"teacher_id": "t1"},
            parameters={"slot_id": "late"},
        ),
        SchedulingRule(
            id="avoid-early",
            rule_type="assignment_avoided_time",
            severity=Severity.SOFT,
            weight=10,
            selector={"assignment_id": "a1"},
            parameters={"slot_id": "early"},
        ),
    ]
    result = Scheduler().solve(problem(slots, [item], rules=rules, count=2))
    assert result.candidates[0].total_penalty == 0
    assert selected(result)["o1"] == "late"
    assert result.candidates[1].total_penalty == 30
    assert {item.rule_id for item in result.candidates[1].penalty_breakdown} == {
        "prefer-late",
        "avoid-early",
    }


def test_seed_is_deterministic() -> None:
    slots = [slot(f"s{i}", "school-a", 480 + i * 50, 525 + i * 50) for i in range(3)]
    item = occurrence("o1", "a1", "school-a", [slot.id for slot in slots])
    left = Scheduler().solve(problem(slots, [item], count=3, seed=42))
    right = Scheduler().solve(problem(slots, [item], count=3, seed=42))
    left_signatures = [[(item.occurrence_id, item.slot_id) for item in x.placements] for x in left.candidates]
    right_signatures = [[(item.occurrence_id, item.slot_id) for item in x.placements] for x in right.candidates]
    assert left_signatures == right_signatures


def test_proven_infeasible_is_distinct_from_unknown_time_limit() -> None:
    only = slot("only", "school-a", 480, 525)
    impossible = problem(
        [only],
        [
            occurrence("o1", "a1", "school-a", ["only"], teachers=["t1"]),
            occurrence("o2", "a2", "school-a", ["only"], teachers=["t1"]),
        ],
    )
    assert Scheduler().solve(impossible).status == "infeasible"

    class Parameters:
        max_time_in_seconds = 0.0
        random_seed = 0
        num_search_workers = 1

    class UnknownSolver:
        parameters = Parameters()

        def solve(self, model: object) -> int:
            del model
            return cp_model.UNKNOWN

    original = solver_module.cp_model.CpSolver
    solver_module.cp_model.CpSolver = UnknownSolver  # type: ignore[misc,assignment]
    try:
        unknown = Scheduler().solve(problem([only], [occurrence("o1", "a1", "school-a", ["only"])]))
    finally:
        solver_module.cp_model.CpSolver = original
    assert unknown.status == "unknown"
    assert unknown.diagnostics[0].code == "solver_time_limit"


def test_repair_honors_requested_move_and_changes_minimum_occurrences() -> None:
    slots = [slot("s1", "school-a", 480, 525), slot("s2", "school-a", 530, 575), slot("s3", "school-a", 580, 625)]
    occurrences = [
        occurrence("o1", "a1", "school-a", ["s1", "s2", "s3"], teachers=["t1"]),
        occurrence("o2", "a2", "school-a", ["s1", "s2", "s3"], teachers=["t1"]),
        occurrence("o3", "a3", "school-a", ["s1", "s2", "s3"], teachers=["t1"]),
    ]
    fixture = problem(slots, occurrences)
    fixture.existing_timetable = [
        ExistingPlacement(occurrence_id="o1", assignment_id="a1", slot_id="s1"),
        ExistingPlacement(occurrence_id="o2", assignment_id="a2", slot_id="s2"),
        ExistingPlacement(occurrence_id="o3", assignment_id="a3", slot_id="s3"),
    ]
    fixture.options = SolveOptions(repair=True, candidate_count=1, time_limit_seconds=2, requested_occurrence_id="o1", requested_slot_id="s2")
    result = Scheduler().solve(fixture)
    assert result.feasible
    repaired = selected(result)
    assert repaired["o1"] == "s2"
    assert sum(repaired[key] != {"o1": "s1", "o2": "s2", "o3": "s3"}[key] for key in repaired) == 2


def test_repair_respects_locked_occurrence() -> None:
    slots = [slot("s1", "school-a", 480, 525), slot("s2", "school-a", 530, 575), slot("s3", "school-a", 580, 625)]
    occurrences = [
        occurrence("o1", "a1", "school-a", ["s1", "s2", "s3"], teachers=["t1"]),
        occurrence("o2", "a2", "school-a", ["s1", "s2", "s3"], teachers=["t1"]),
        occurrence("o3", "a3", "school-a", ["s1", "s2", "s3"], teachers=["t1"]),
    ]
    fixture = problem(slots, occurrences)
    fixture.existing_timetable = [ExistingPlacement(occurrence_id=f"o{i}", assignment_id=f"a{i}", slot_id=f"s{i}") for i in range(1, 4)]
    fixture.options = SolveOptions(repair=True, candidate_count=1, time_limit_seconds=2, requested_occurrence_id="o1", requested_slot_id="s2", locked_occurrence_ids=["o3"])
    repaired = selected(Scheduler().solve(fixture))
    assert repaired["o3"] == "s3"

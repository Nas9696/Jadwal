import pytest
from pydantic import ValidationError

from pm_scheduler.contracts import (
    Assignment,
    Constraint,
    SchedulingProblem,
    Severity,
    SolveOptions,
    TimeSlot,
    slots_overlap,
)
from pm_scheduler.solver import Scheduler

def test_soft_constraint_requires_weight() -> None:
    with pytest.raises(ValidationError):
        Constraint(id="c1", rule_type="prefer", severity=Severity.SOFT)

def test_solve_options_are_bounded() -> None:
    with pytest.raises(ValidationError):
        SolveOptions(candidate_count=0)

def test_cp_sat_reports_empty_problem_as_infeasible() -> None:
    problem = SchedulingProblem(problem_id="demo", slots=[], teachers=[], sections=[], assignments=[])
    result = Scheduler().solve(problem)
    assert result.status == "infeasible"
    assert not result.feasible


def test_shared_teacher_identity_is_preserved_across_school_assignments() -> None:
    assignments = [
        Assignment(id="a1", school_id="school-a", teacher_ids=["teacher-1"], section_ids=["s1"], subject_id="math", occurrence_count=1),
        Assignment(id="a2", school_id="school-b", teacher_ids=["teacher-1"], section_ids=["s2"], subject_id="science", occurrence_count=1),
    ]
    problem = SchedulingProblem(
        problem_id="shared-teacher",
        school_ids=["school-a", "school-b"],
        slots=[],
        teachers=[],
        sections=[],
        assignments=assignments,
    )
    assert problem.assignments[0].teacher_ids == problem.assignments[1].teacher_ids
    assert len(problem.school_ids) == 2


def slot(
    school: str,
    period: int,
    start: int,
    end: int,
    project_week: int = 0,
    local_week: int = 0,
    weekday: int = 0,
    day_code: str | None = "sun",
) -> TimeSlot:
    return TimeSlot(
        id=f"{school}-{period}-{project_week}",
        school_id=school,
        week_pattern_id=f"{school}-week",
        local_cycle_week_index=local_week,
        project_cycle_week_index=project_week,
        weekday_index=weekday,
        day_code=day_code,
        starts_at_minute=start,
        ends_at_minute=end,
        period=period,
    )


def test_different_period_numbers_overlap_by_real_time() -> None:
    school_a_period_2 = slot("school-a", 2, 8 * 60, 8 * 60 + 45)
    school_b_period_3 = slot("school-b", 3, 8 * 60 + 20, 9 * 60 + 5)
    assert slots_overlap(school_a_period_2, school_b_period_3)


def test_same_period_number_does_not_collide_without_time_overlap() -> None:
    school_a_period_2 = slot("school-a", 2, 8 * 60, 8 * 60 + 45)
    school_b_period_2 = slot("school-b", 2, 9 * 60, 9 * 60 + 45)
    assert not slots_overlap(school_a_period_2, school_b_period_2)


def test_different_cycle_weeks_do_not_overlap() -> None:
    week_a = slot("school-a", 2, 8 * 60, 8 * 60 + 45, project_week=0)
    week_b = slot("school-b", 3, 8 * 60 + 20, 9 * 60 + 5, project_week=1)
    assert not slots_overlap(week_a, week_b)


def test_remote_slot_still_reserves_teacher_time() -> None:
    onsite = slot("school-a", 2, 8 * 60, 8 * 60 + 45)
    remote = slot("school-b", 3, 8 * 60 + 20, 9 * 60 + 5).model_copy(
        update={"attendance_mode": "remote"}
    )
    assert slots_overlap(onsite, remote)


def test_invalid_slot_interval_is_rejected() -> None:
    with pytest.raises(ValidationError):
        slot("school-a", 1, 9 * 60, 8 * 60)


def test_local_week_index_does_not_define_collision() -> None:
    left = slot("school-a", 1, 8 * 60, 9 * 60, project_week=1, local_week=0)
    right = slot("school-b", 2, 8 * 60, 9 * 60, project_week=1, local_week=1)
    assert slots_overlap(left, right)


def test_same_local_index_in_different_project_weeks_does_not_collide() -> None:
    left = slot("school-a", 1, 8 * 60, 9 * 60, project_week=0, local_week=0)
    right = slot("school-b", 1, 8 * 60, 9 * 60, project_week=1, local_week=0)
    assert not slots_overlap(left, right)


def test_localized_day_labels_do_not_affect_normalized_weekday_overlap() -> None:
    arabic = slot("school-a", 1, 8 * 60, 9 * 60, day_code="الأحد", weekday=0)
    english = slot("school-b", 2, 8 * 60, 9 * 60, day_code="Sunday", weekday=0)
    assert slots_overlap(arabic, english)

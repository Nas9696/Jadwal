import pytest
from pydantic import ValidationError

from pm_scheduler.contracts import Assignment, Constraint, SchedulingProblem, Severity, SolveOptions
from pm_scheduler.solver import Scheduler, SolverNotImplementedError

def test_soft_constraint_requires_weight() -> None:
    with pytest.raises(ValidationError):
        Constraint(id="c1", rule_type="prefer", severity=Severity.SOFT)

def test_solve_options_are_bounded() -> None:
    with pytest.raises(ValidationError):
        SolveOptions(candidate_count=0)

def test_cp_sat_scaffold_does_not_claim_a_fake_solution() -> None:
    problem = SchedulingProblem(problem_id="demo", slots=[], teachers=[], sections=[], assignments=[])
    with pytest.raises(SolverNotImplementedError, match="not implemented in PM-001"):
        Scheduler().solve(problem)


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

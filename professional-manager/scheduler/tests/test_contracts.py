import pytest
from pydantic import ValidationError

from pm_scheduler.contracts import Constraint, SchedulingProblem, Severity, SolveOptions
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


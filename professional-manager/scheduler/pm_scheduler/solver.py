from abc import ABC, abstractmethod

from pm_scheduler.contracts import SchedulingProblem, SolveResult

class SolverNotImplementedError(RuntimeError):
    """Raised until the CP-SAT implementation arrives in PM-002/Phase 2 work."""

class SolverBackend(ABC):
    @abstractmethod
    def solve(self, problem: SchedulingProblem) -> SolveResult:
        """Solve or repair a validated scheduling problem."""

class CpSatBackend(SolverBackend):
    """OR-Tools CP-SAT boundary. Constraint translation is intentionally future work."""

    def solve(self, problem: SchedulingProblem) -> SolveResult:
        raise SolverNotImplementedError(
            f"CP-SAT model is not implemented in PM-001 (problem={problem.problem_id})"
        )

class Scheduler:
    def __init__(self, backend: SolverBackend | None = None) -> None:
        self._backend = backend or CpSatBackend()

    def solve(self, problem: SchedulingProblem) -> SolveResult:
        return self._backend.solve(problem)


from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator

class Severity(StrEnum):
    HARD = "hard"
    SOFT = "soft"

class SolveStatus(StrEnum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNKNOWN = "unknown"
    FAILED = "failed"
    NOT_RUN = "not_run"

class LocalTimeSlot(BaseModel):
    id: str
    school_id: str
    week_pattern_id: str
    local_cycle_week_index: Annotated[int, Field(ge=0)]
    weekday_index: Annotated[int, Field(ge=0, le=6)]
    starts_at_minute: Annotated[int, Field(ge=0, lt=24 * 60)]
    ends_at_minute: Annotated[int, Field(gt=0, le=24 * 60)]
    period: Annotated[int, Field(ge=1)]
    attendance_mode: str = "onsite"
    day_code: str | None = None

    @model_validator(mode="after")
    def interval_is_valid(self) -> "LocalTimeSlot":
        if self.starts_at_minute >= self.ends_at_minute:
            raise ValueError("slot start must be before slot end")
        return self


class TimeSlot(LocalTimeSlot):
    project_cycle_week_index: Annotated[int, Field(ge=0)]


def slots_overlap(left: TimeSlot, right: TimeSlot) -> bool:
    """Compare half-open intervals in the same global project week and weekday.

    Local week, labels, school, period, slot ID and attendance mode are irrelevant.
    """
    return (
        left.project_cycle_week_index == right.project_cycle_week_index
        and left.weekday_index == right.weekday_index
        and max(left.starts_at_minute, right.starts_at_minute)
        < min(left.ends_at_minute, right.ends_at_minute)
    )

class Entity(BaseModel):
    id: str
    available_slot_ids: set[str] | None = None


class ResourceEntity(Entity):
    exclusive: bool = True


class LessonOccurrence(BaseModel):
    id: str
    assignment_id: str
    school_id: str
    subject_id: str
    project_cycle_week_index: Annotated[int, Field(ge=0)]
    teacher_ids: list[str]
    section_ids: list[str]
    resource_ids: list[str] = []
    candidate_slot_ids: list[str]


class SchedulingRule(BaseModel):
    id: str
    rule_type: str
    severity: Severity
    weight: Annotated[int | None, Field(gt=0)] = None
    selector: dict[str, Any]
    parameters: dict[str, Any]

    @model_validator(mode="after")
    def soft_requires_weight(self) -> "SchedulingRule":
        if self.severity == Severity.SOFT and self.weight is None:
            raise ValueError("soft constraints require a positive weight")
        return self

class Assignment(BaseModel):
    id: str
    school_id: str
    teacher_ids: list[str]
    section_ids: list[str]
    subject_id: str
    occurrence_count: Annotated[int, Field(gt=0)]
    resource_ids: list[str] = []

class Constraint(BaseModel):
    id: str
    rule_type: str
    severity: Severity
    weight: Annotated[int | None, Field(gt=0)] = None
    selectors: dict[str, list[str]] = {}
    time_selectors: dict[str, list[str] | list[int]] = {}
    parameters: dict[str, Any] = {}

    @model_validator(mode="after")
    def soft_requires_weight(self) -> "Constraint":
        if self.severity == Severity.SOFT and self.weight is None:
            raise ValueError("soft constraints require a positive weight")
        return self

class Lock(BaseModel):
    target_type: str
    target_ids: list[str]
    slot_ids: list[str] = []

class ExistingPlacement(BaseModel):
    occurrence_id: str
    assignment_id: str
    slot_id: str
    resource_ids: list[str] = []

class SolveOptions(BaseModel):
    seed: int = 0
    time_limit_seconds: Annotated[float, Field(ge=1, le=60)] = 10
    candidate_count: Annotated[int, Field(ge=1, le=5)] = 3
    optimization_profile: str = "balanced"
    repair: bool = False
    minimize_changes: bool = True

class SchedulingProblem(BaseModel):
    problem_id: str
    project_id: str | None = None
    school_ids: list[str] = []
    project_cycle_length: Annotated[int, Field(ge=1)] = 1
    slots: list[TimeSlot]
    teachers: list[Entity]
    sections: list[Entity]
    resources: list[ResourceEntity] = []
    assignments: list[Assignment] = []
    occurrences: list[LessonOccurrence] = []
    rules: list[SchedulingRule] = []
    constraints: list[Constraint] = []
    locks: list[Lock] = []
    existing_timetable: list[ExistingPlacement] = []
    options: SolveOptions = SolveOptions()

class Violation(BaseModel):
    constraint_id: str
    message_key: str
    affected_entity_ids: list[str]
    penalty: int = 0

class Placement(BaseModel):
    occurrence_id: str
    assignment_id: str
    slot_id: str
    resource_ids: list[str] = []


class PenaltyBreakdown(BaseModel):
    rule_id: str
    rule_type: str
    violation_count: int
    weight: int
    weighted_penalty: int

class CandidateSolution(BaseModel):
    id: str
    placements: list[Placement]
    solver_status: SolveStatus
    total_penalty: int
    penalty_breakdown: list[PenaltyBreakdown] = []
    solve_time_seconds: float = 0
    diversity_count: int = 0

class Diagnostic(BaseModel):
    code: str
    message_key: str
    affected_entity_ids: list[str] = []
    suggested_relaxations: list[str] = []

class SolveResult(BaseModel):
    status: SolveStatus
    feasible: bool
    candidates: list[CandidateSolution]
    diagnostics: list[Diagnostic]
    solver_name: str
    solver_version: str

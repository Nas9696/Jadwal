from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator

class Severity(StrEnum):
    HARD = "hard"
    SOFT = "soft"

class SolveStatus(StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNKNOWN = "unknown"
    NOT_RUN = "not_run"

class TimeSlot(BaseModel):
    id: str
    week_pattern_id: str
    day_code: str
    period: Annotated[int, Field(ge=1)]

class Entity(BaseModel):
    id: str
    available_slot_ids: set[str] | None = None

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
    time_limit_seconds: Annotated[float, Field(gt=0, le=3600)] = 30
    candidate_count: Annotated[int, Field(ge=1, le=20)] = 3
    optimization_profile: str = "balanced"
    repair: bool = False
    minimize_changes: bool = True

class SchedulingProblem(BaseModel):
    problem_id: str
    school_ids: list[str] = []
    slots: list[TimeSlot]
    teachers: list[Entity]
    sections: list[Entity]
    resources: list[Entity] = []
    assignments: list[Assignment]
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

class CandidateSolution(BaseModel):
    id: str
    placements: list[Placement]
    score: float
    normalized_quality: float
    score_breakdown: dict[str, float]
    violations: list[Violation]
    unsatisfied_preferences: list[Violation]
    diversity_hints: list[str] = []

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

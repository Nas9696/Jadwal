import uuid
from typing import Literal

from pydantic import BaseModel, Field


class SolveRequest(BaseModel):
    candidate_count: int = Field(default=3, ge=1, le=5)
    time_limit_seconds: int = Field(default=10, ge=1, le=60)
    seed: int = 0
    optimization_profile: Literal["balanced", "teacher_comfort", "student_rhythm", "administration_priorities", "custom"] = "balanced"
    optimization_weights: dict[str, int] = {}
    allow_partial: bool = False


class SolveRunRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: Literal["queued", "running", "completed", "infeasible", "unknown", "failed"]
    input_fingerprint: str
    requested_candidates: int
    time_limit_seconds: int
    seed: int
    solver_status: str | None
    diagnostics: list[dict[str, object]]
    candidates: list[dict[str, object]] = []

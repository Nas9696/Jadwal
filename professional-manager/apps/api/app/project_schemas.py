import uuid
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


class ProjectSchoolInput(BaseModel):
    school_id: uuid.UUID
    term_id: uuid.UUID
    cycle_phase_offset: int = Field(default=0, ge=0)


class ProjectInput(BaseModel):
    name_ar: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    scope_type: Literal["school", "complex", "schools"] = "school"
    complex_id: uuid.UUID | None = None
    schools: list[ProjectSchoolInput]


class RuleInput(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    rule_type: str
    severity: Literal["hard", "soft"]
    weight: int | None = Field(default=None, ge=1, le=1000)
    selector: dict[str, Any]
    parameters: dict[str, Any]
    enabled: bool = True

    @model_validator(mode="after")
    def soft_weight(self) -> "RuleInput":
        if self.severity == "soft" and self.weight is None:
            raise ValueError("soft_rule_requires_weight")
        if self.severity == "hard" and self.weight is not None:
            raise ValueError("hard_rule_has_no_weight")
        return self


class DiagnosticRead(BaseModel):
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    affected_entities: dict[str, list[str]] = {}
    context: dict[str, Any] = {}
    required: int | None = None
    available: int | None = None
    shortage: int | None = None
    suggested_remediation: str | None = None

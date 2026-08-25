import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class RevisionInput(BaseModel):
    revision: int = Field(ge=1)


class MoveInput(RevisionInput):
    occurrence_id: str
    target_slot_id: str


class SwapInput(RevisionInput):
    first_occurrence_id: str
    second_occurrence_id: str


class LockInput(RevisionInput):
    lock_type: Literal["occurrence", "teacher", "section", "day", "time_range", "week", "region"]
    occurrence_id: str | None = None
    teacher_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    school_id: uuid.UUID | None = None
    project_cycle_week_index: int | None = Field(default=None, ge=0)
    weekday_index: int | None = Field(default=None, ge=0, le=6)
    starts_at_minute: int | None = Field(default=None, ge=0, lt=1440)
    ends_at_minute: int | None = Field(default=None, gt=0, le=1440)
    label: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def selector_matches_type(self) -> "LockInput":
        required = {
            "occurrence": self.occurrence_id,
            "teacher": self.teacher_id,
            "section": self.section_id,
            "day": self.weekday_index,
            "time_range": self.starts_at_minute,
            "week": self.project_cycle_week_index,
            "region": self.school_id or self.project_cycle_week_index,
        }
        if required[self.lock_type] is None:
            raise ValueError("typed lock selector is required")
        if self.starts_at_minute is not None and self.ends_at_minute is not None:
            if self.starts_at_minute >= self.ends_at_minute:
                raise ValueError("lock start must be before end")
        return self


class RepairInput(MoveInput):
    time_limit_seconds: float = Field(default=5, ge=1, le=15)


class RepairApplyInput(RevisionInput):
    occurrence_id: str
    target_slot_id: str
    changes: list[dict[str, Any]]
    time_limit_seconds: float = Field(default=5, ge=1, le=15)
    fingerprint: str = Field(min_length=64, max_length=64)


class SnapshotInput(RevisionInput):
    name: str = Field(min_length=1, max_length=200)


class SnapshotRestoreInput(RevisionInput):
    change_summary: str | None = Field(default=None, max_length=500)

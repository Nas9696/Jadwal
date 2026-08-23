import uuid
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class WaitingPolicyInput(BaseModel):
    combined_workload_limit: int | None = Field(default=None, ge=0, le=100)
    daily_waiting_limit: int | None = Field(default=None, ge=0, le=20)
    weekly_waiting_limit: int | None = Field(default=None, ge=0, le=100)
    fairness_weight: int = Field(default=5, ge=0, le=100)
    specialty_preference_enabled: bool = False
    specialty_preference_weight: int = Field(default=3, ge=0, le=100)
    same_school_preference_weight: int = Field(default=0, ge=0, le=100)
    exclude_exempt_teachers: bool = True
    enabled: bool = True


class WaitingProfileInput(BaseModel):
    exempt: bool = False
    custom_combined_limit: int | None = Field(default=None, ge=0, le=100)
    custom_daily_limit: int | None = Field(default=None, ge=0, le=20)
    custom_weekly_limit: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=500)


class AbsenceCreate(BaseModel):
    school_id: uuid.UUID
    teacher_id: uuid.UUID
    absence_date: date
    project_cycle_week_index: int = Field(ge=0)
    working_timetable_revision: int = Field(ge=1)
    full_day: bool = True
    starts_at_minute: int | None = Field(default=None, ge=0, lt=1440)
    ends_at_minute: int | None = Field(default=None, gt=0, le=1440)
    reason_code: str | None = Field(default=None, max_length=50)
    reason_text: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def valid_window(self) -> "AbsenceCreate":
        if self.full_day and (self.starts_at_minute is not None or self.ends_at_minute is not None):
            raise ValueError("full_day_has_no_time_range")
        if not self.full_day:
            if self.starts_at_minute is None or self.ends_at_minute is None:
                raise ValueError("partial_absence_requires_time_range")
            if self.starts_at_minute >= self.ends_at_minute:
                raise ValueError("invalid_absence_time_range")
        return self


class AbsenceRefresh(BaseModel):
    working_timetable_revision: int = Field(ge=1)


class SubstituteAssign(BaseModel):
    substitute_teacher_id: uuid.UUID
    need_version: int = Field(ge=1)
    working_timetable_revision: int = Field(ge=1)
    mode: Literal["recommended", "manual_override"] = "recommended"


class SubstituteUnassign(BaseModel):
    need_version: int = Field(ge=1)
    working_timetable_revision: int = Field(ge=1)


class WaitingPolicyRead(WaitingPolicyInput):
    id: str | None
    project_id: str


class WaitingProfileRead(WaitingProfileInput):
    pass


class WorkloadRead(WaitingProfileRead):
    teacher_id: str
    teacher_name: str
    base_target: int
    teaching_load: int
    assigned_today: int
    assigned_this_week: int
    combined_limit: int
    daily_limit: int | None
    weekly_limit: int | None
    remaining_capacity: int


class SubstitutionAssignmentRead(BaseModel):
    id: str
    teacher_id: str
    teacher_name: str
    score: int
    rank: int | None
    manual_override: bool
    score_breakdown: dict[str, int]
    eligibility_facts: dict[str, Any]


class SubstitutionNeedRead(BaseModel):
    id: str
    absence_id: str
    version: int
    occurrence_id: str
    school_id: str
    school_name: str
    subject_id: str
    subject_name: str
    section_names: list[str]
    project_cycle_week_index: int
    weekday_index: int
    starts_at_minute: int
    ends_at_minute: int
    status: str
    source_working_revision: int
    stale: bool
    assignment: SubstitutionAssignmentRead | None


class AbsenceRead(BaseModel):
    id: str
    project_id: str
    school_id: str
    school_name: str
    teacher_id: str
    teacher_name: str
    absence_date: date
    project_cycle_week_index: int
    weekday_index: int
    full_day: bool
    starts_at_minute: int | None
    ends_at_minute: int | None
    reason_code: str | None
    reason_text: str | None
    status: str
    working_timetable_revision: int
    stale: bool
    needs: list[SubstitutionNeedRead]


class CandidateRead(BaseModel):
    teacher_id: str
    teacher_name: str
    canonical_code: str
    eligible: bool
    blocking_reasons: list[str]
    free_at_time: bool
    teaching_load: int
    assigned_today: int
    assigned_this_week: int
    combined_after_assignment: int
    combined_limit: int
    daily_limit: int | None
    weekly_limit: int | None
    exempt: bool
    specialty_considered: bool
    specialty_match: bool | None
    same_school_membership: bool
    score_breakdown: dict[str, int]
    total_score: int
    rank: int | None = None


class CandidateListRead(BaseModel):
    need_id: str
    need_version: int
    working_timetable_revision: int
    candidates: list[CandidateRead]
    excluded: list[CandidateRead]


class DailySummaryRead(BaseModel):
    date: date
    absent_teachers: int
    needs: int
    covered: int
    uncovered: int
    teachers_carrying_substitutions: int
    absences: list[AbsenceRead]

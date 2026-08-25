import uuid
from datetime import time
from typing import Literal

from pydantic import BaseModel, Field, model_validator


StageKind = Literal["primary", "intermediate", "secondary"]
SectionNamingPattern = Literal["grade_letter", "number_slash_number", "number_dash_number", "number_slash_letter"]
AvailabilityState = Literal["available", "unavailable", "avoid"]


class BreakInput(BaseModel):
    after_period: int = Field(ge=1, le=20)
    duration_minutes: int = Field(ge=5, le=90)


class PrayerInput(BaseModel):
    after_period: int | None = Field(default=None, ge=1, le=20)
    fixed_time: time | None = None
    duration_minutes: int = Field(default=15, ge=5, le=60)

    @model_validator(mode="after")
    def has_position(self) -> "PrayerInput":
        if self.after_period is None and self.fixed_time is None:
            raise ValueError("prayer_position_required")
        return self


class DayBuilderInput(BaseModel):
    school_name: str = Field(min_length=1, max_length=200)
    stages: list[StageKind] = Field(min_length=1)
    weekdays: list[int] = Field(default=[0, 1, 2, 3, 4], min_length=1, max_length=7)
    period_count: int = Field(default=7, ge=1, le=20)
    assembly_start: time = time(6, 45)
    assembly_minutes: int = Field(default=15, ge=0, le=60)
    period_minutes: int = Field(default=45, ge=20, le=120)
    breaks: list[BreakInput] = Field(default_factory=lambda: [BreakInput(after_period=2, duration_minutes=20)], max_length=2)
    prayer: PrayerInput | None = None

    @model_validator(mode="after")
    def valid_positions(self) -> "DayBuilderInput":
        if len(set(self.weekdays)) != len(self.weekdays) or any(day < 0 or day > 6 for day in self.weekdays):
            raise ValueError("invalid_weekdays")
        positions = [item.after_period for item in self.breaks]
        if len(set(positions)) != len(positions) or any(value >= self.period_count for value in positions):
            raise ValueError("invalid_break_position")
        if self.prayer and self.prayer.after_period and self.prayer.after_period >= self.period_count:
            raise ValueError("invalid_prayer_position")
        return self


class PeriodEditInput(BaseModel):
    block_order: int = Field(ge=0)
    label_ar: str = Field(min_length=1, max_length=100)
    block_type: Literal["lesson", "break", "prayer", "assembly", "activity", "custom"]
    period_number: int | None = Field(default=None, ge=1)
    starts_at: time
    ends_at: time
    recalculate_following: bool = True

    @model_validator(mode="after")
    def valid_interval(self) -> "PeriodEditInput":
        if self.starts_at >= self.ends_at:
            raise ValueError("invalid_time_range")
        return self


class GradeCountInput(BaseModel):
    grade_name: str = Field(min_length=1, max_length=100)
    section_count: int = Field(ge=0, le=30)


class StructureInput(BaseModel):
    stage: StageKind
    grades: list[GradeCountInput] = Field(min_length=1)
    naming_pattern: SectionNamingPattern = "grade_letter"
    reset_names: bool = False


class AvailabilityCellInput(BaseModel):
    weekday_index: int = Field(ge=0, le=6)
    period_number: int = Field(ge=1, le=30)
    state: AvailabilityState


class TeacherAvailabilityInput(BaseModel):
    cells: list[AvailabilityCellInput]


class SimpleTeacherInput(BaseModel):
    name_ar: str = Field(min_length=2, max_length=200)
    workload_limit: int = Field(default=24, ge=1, le=60)
    allow_similar: bool = False


class BulkTeachersInput(BaseModel):
    names: list[str] = Field(min_length=1, max_length=1000)
    workload_limit: int = Field(default=24, ge=1, le=60)
    allow_similar: bool = False


class CurriculumCellInput(BaseModel):
    grade_id: uuid.UUID
    subject_id: uuid.UUID
    weekly_occurrences: int = Field(ge=0, le=60)


class CurriculumPlanInput(BaseModel):
    cells: list[CurriculumCellInput]


class SimpleSubjectInput(BaseModel):
    name_ar: str = Field(min_length=2, max_length=150)


class SimpleSectionInput(BaseModel):
    name_ar: str = Field(min_length=2, max_length=100)


class OrderedIdsInput(BaseModel):
    ids: list[uuid.UUID]


class TeacherMergeInput(BaseModel):
    source_teacher_id: uuid.UUID
    target_teacher_id: uuid.UUID

    @model_validator(mode="after")
    def different_teachers(self) -> "TeacherMergeInput":
        if self.source_teacher_id == self.target_teacher_id:
            raise ValueError("different_target_teacher_required")
        return self


class AvailabilityCopyInput(BaseModel):
    source_teacher_id: uuid.UUID
    target_teacher_ids: list[uuid.UUID] = Field(min_length=1)


class QuickAssignmentInput(BaseModel):
    term_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    section_ids: list[uuid.UUID] = Field(default_factory=list)
    subject_id: uuid.UUID
    teacher_id: uuid.UUID
    weekly_occurrences: int = Field(gt=0, le=60)
    allow_overload: bool = False

    @model_validator(mode="after")
    def has_sections(self) -> "QuickAssignmentInput":
        selected = ([self.section_id] if self.section_id else []) + self.section_ids
        if not selected:
            raise ValueError("section_required")
        if len(selected) != len(set(selected)):
            raise ValueError("duplicate_section")
        return self


class AssignmentTransferInput(BaseModel):
    source_teacher_id: uuid.UUID
    target_teacher_id: uuid.UUID
    assignment_ids: list[uuid.UUID] = Field(default_factory=list)
    mode: Literal["move"] = "move"
    allow_overload: bool = False

    @model_validator(mode="after")
    def different_teachers(self) -> "AssignmentTransferInput":
        if self.source_teacher_id == self.target_teacher_id:
            raise ValueError("different_target_teacher_required")
        return self


class PresetRuleInput(BaseModel):
    preset: Literal[
        "no_first_period", "no_thursday", "selected_days_only", "first_four_only", "max_daily",
        "max_consecutive", "prefer_free_day", "spread_assignment",
        "consecutive_assignment", "assignment_before",
    ]
    teacher_id: uuid.UUID | None = None
    assignment_id: uuid.UUID | None = None
    second_assignment_id: uuid.UUID | None = None
    weekdays: list[int] = Field(default_factory=list)
    value: int | None = Field(default=None, ge=1, le=20)


class GenerateInput(BaseModel):
    optimization_profile: Literal["balanced", "teacher_comfort", "student_rhythm", "custom"] = "balanced"

import uuid
from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class YearInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    starts_on: date
    ends_on: date
    is_current: bool = False

    @model_validator(mode="after")
    def valid_dates(self) -> "YearInput":
        if self.starts_on >= self.ends_on:
            raise ValueError("invalid_date_range")
        return self


class TermInput(BaseModel):
    academic_year_id: uuid.UUID
    name_ar: str = Field(min_length=1, max_length=100)
    name_en: str | None = None
    order: int = Field(ge=1)
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def valid_dates(self) -> "TermInput":
        if self.starts_on >= self.ends_on:
            raise ValueError("invalid_date_range")
        return self


class ShiftInput(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name_ar: str = Field(min_length=1, max_length=100)
    name_en: str | None = None
    is_active: bool = True
    order: int = Field(ge=0)


class WeekPatternInput(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name_ar: str = Field(min_length=1, max_length=100)
    cycle_week_index: int = Field(ge=0)


class SchoolDayInput(BaseModel):
    shift_id: uuid.UUID
    week_pattern_id: uuid.UUID
    weekday_index: int = Field(ge=0, le=6)
    enabled: bool = True
    label_ar: str | None = None


BlockType = Literal["lesson", "break", "prayer", "assembly", "activity", "custom"]
AttendanceMode = Literal["onsite", "remote", "hybrid"]


class BlockInput(BaseModel):
    school_day_id: uuid.UUID
    block_order: int = Field(ge=0)
    block_type: BlockType
    period_number: int | None = Field(default=None, ge=1)
    label_ar: str | None = None
    starts_at: time
    ends_at: time
    attendance_mode: AttendanceMode = "onsite"

    @model_validator(mode="after")
    def valid_block(self) -> "BlockInput":
        if self.starts_at >= self.ends_at:
            raise ValueError("invalid_time_range")
        if self.block_type == "lesson" and self.period_number is None:
            raise ValueError("lesson_number_required")
        return self


class StageInput(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name_ar: str = Field(min_length=1, max_length=100)
    order: int = Field(ge=0)


class GradeInput(BaseModel):
    stage_id: uuid.UUID
    name_ar: str = Field(min_length=1, max_length=100)
    order: int = Field(ge=0)


class SectionInput(BaseModel):
    grade_id: uuid.UUID
    name_ar: str = Field(min_length=1, max_length=100)
    capacity: int | None = Field(default=None, ge=1)

import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TeacherInput(BaseModel):
    canonical_code: str = Field(min_length=1, max_length=50)
    name_ar: str = Field(min_length=1, max_length=200)
    name_en: str | None = Field(default=None, max_length=200)
    specialty_reference: str | None = Field(default=None, max_length=150)
    base_workload: int = Field(default=0, ge=0, le=60)
    teaching_workload_limit: int = Field(default=24, ge=0, le=60)
    is_active: bool = True

    @model_validator(mode="after")
    def valid_workload(self) -> "TeacherInput":
        if self.base_workload > self.teaching_workload_limit:
            raise ValueError("base_workload_exceeds_limit")
        return self


class NewTeacherInput(TeacherInput):
    local_employee_code: str | None = Field(default=None, max_length=50)
    is_home_school: bool = False


class MembershipInput(BaseModel):
    teacher_id: uuid.UUID
    local_employee_code: str | None = Field(default=None, max_length=50)
    is_home_school: bool = False
    is_active: bool = True


class MembershipUpdateInput(BaseModel):
    local_employee_code: str | None = Field(default=None, max_length=50)
    is_home_school: bool = False
    is_active: bool = True


class SubjectInput(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name_ar: str = Field(min_length=1, max_length=150)
    name_en: str | None = Field(default=None, max_length=150)
    is_active: bool = True


class CurriculumInput(BaseModel):
    grade_id: uuid.UUID
    subject_id: uuid.UUID
    weekly_occurrences: int = Field(gt=0, le=60)
    notes: str | None = Field(default=None, max_length=300)


ResourceType = Literal["room", "science_lab", "computer_lab", "gym", "library", "field", "other"]


class ResourceInput(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name_ar: str = Field(min_length=1, max_length=150)
    resource_type: ResourceType = "room"
    capacity: int | None = Field(default=None, ge=1, le=10000)
    exclusive: bool = True
    is_active: bool = True

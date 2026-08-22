import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

class SchoolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    name_ar: str
    name_en: str | None
    code: str
    school_type: str
    created_at: datetime

class DashboardSummary(BaseModel):
    school: SchoolRead
    teachers: int
    subjects: int
    sections: int
    resources: int
    active_project_name: str | None


class TeacherSchoolMembershipCreate(BaseModel):
    teacher_id: uuid.UUID
    school_id: uuid.UUID
    local_employee_code: str | None = None
    is_home_school: bool = False


class TeacherSchoolMembershipRead(TeacherSchoolMembershipCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool


class ProjectSchoolCalendarCreate(BaseModel):
    school_id: uuid.UUID
    term_id: uuid.UUID


class TimetableProjectCreate(BaseModel):
    name_ar: str
    scope_type: str
    schools: list[ProjectSchoolCalendarCreate]
    complex_id: uuid.UUID | None = None


class ProjectSchoolCalendarRead(ProjectSchoolCalendarCreate):
    model_config = ConfigDict(from_attributes=True)


class TimetableProjectRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name_ar: str
    scope_type: str
    schools: list[ProjectSchoolCalendarRead]
    complex_id: uuid.UUID | None

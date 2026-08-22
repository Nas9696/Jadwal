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


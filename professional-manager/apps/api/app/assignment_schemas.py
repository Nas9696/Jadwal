import uuid

from pydantic import BaseModel, Field, model_validator


class OfferingInput(BaseModel):
    term_id: uuid.UUID
    section_id: uuid.UUID
    shift_id: uuid.UUID
    is_active: bool = True


class OfferingBulkInput(BaseModel):
    offerings: list[OfferingInput] = Field(min_length=1)


class AssignmentInput(BaseModel):
    term_id: uuid.UUID
    subject_id: uuid.UUID
    weekly_occurrences: int = Field(gt=0, le=60)
    teacher_ids: list[uuid.UUID] = Field(min_length=1)
    section_offering_ids: list[uuid.UUID] = Field(min_length=1)
    resource_ids: list[uuid.UUID] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def unique_relations(self) -> "AssignmentInput":
        for values in (self.teacher_ids, self.section_offering_ids, self.resource_ids):
            if len(values) != len(set(values)):
                raise ValueError("duplicate_relation")
        return self


class AssignmentPreviewInput(AssignmentInput):
    assignment_id: uuid.UUID | None = None


class BulkAssignmentInput(BaseModel):
    term_id: uuid.UUID
    subject_id: uuid.UUID
    section_offering_ids: list[uuid.UUID] = Field(min_length=1)
    teacher_ids: list[uuid.UUID] = Field(min_length=1)
    resource_ids: list[uuid.UUID] = Field(default_factory=list)
    fill_from_curriculum: bool = True
    weekly_occurrences: int | None = Field(default=None, gt=0, le=60)

    @model_validator(mode="after")
    def has_count(self) -> "BulkAssignmentInput":
        if not self.fill_from_curriculum and self.weekly_occurrences is None:
            raise ValueError("weekly_occurrences_required")
        for values in (self.section_offering_ids, self.teacher_ids, self.resource_ids):
            if len(values) != len(set(values)):
                raise ValueError("duplicate_relation")
        return self


class BulkTeacherInput(BaseModel):
    term_id: uuid.UUID
    assignment_ids: list[uuid.UUID] = Field(min_length=1)
    teacher_ids: list[uuid.UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_relations(self) -> "BulkTeacherInput":
        if len(self.assignment_ids) != len(set(self.assignment_ids)):
            raise ValueError("duplicate_assignment_id")
        if len(self.teacher_ids) != len(set(self.teacher_ids)):
            raise ValueError("duplicate_teacher_id")
        return self


class BulkDeleteInput(BaseModel):
    term_id: uuid.UUID
    assignment_ids: list[uuid.UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_assignments(self) -> "BulkDeleteInput":
        if len(self.assignment_ids) != len(set(self.assignment_ids)):
            raise ValueError("duplicate_assignment_id")
        return self


class CoverageProjection(BaseModel):
    offering_id: uuid.UUID
    required: int | None
    current_assigned: int
    delta: int
    projected_assigned: int
    projected_status: str
    action: str = "apply"


class WorkloadProjection(BaseModel):
    teacher_id: uuid.UUID
    current_workload: int
    delta: int
    projected_workload: int
    teaching_workload_limit: int
    exceeds_limit: bool


class AssignmentPreview(BaseModel):
    can_apply: bool
    coverage: list[CoverageProjection]
    teacher_workloads: list[WorkloadProjection]
    warnings: list[dict[str, object]]

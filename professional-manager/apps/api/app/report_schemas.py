import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ReportType = Literal[
    "general_timetable",
    "section_timetable",
    "teacher_timetable",
    "subject_timetable",
    "resource_timetable",
    "daily_substitutions",
    "waiting_workload",
]


class ReportSource(BaseModel):
    kind: Literal["working", "candidate"] = "working"
    candidate_id: uuid.UUID | None = None
    expected_revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def candidate_is_explicit(self) -> "ReportSource":
        if self.kind == "candidate" and self.candidate_id is None:
            raise ValueError("candidate_id_required")
        if self.kind == "working" and self.candidate_id is not None:
            raise ValueError("candidate_id_only_for_candidate_source")
        return self


class ReportFilters(BaseModel):
    school_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None
    resource_id: uuid.UUID | None = None
    project_cycle_week_index: int | None = Field(default=None, ge=0)
    weekday_index: int | None = Field(default=None, ge=0, le=6)
    on_date: date | None = None


class PrintOptions(BaseModel):
    paper: Literal["A4", "A3"] = "A4"
    orientation: Literal["portrait", "landscape"] = "landscape"
    density: Literal["compact", "comfortable"] = "compact"
    theme: Literal["color", "monochrome"] = "color"
    show_heading: bool = True
    show_period_time: bool = True
    show_resource: bool = True


class ReportBranding(BaseModel):
    title_override: str | None = Field(default=None, max_length=160)
    subtitle: str | None = Field(default=None, max_length=240)
    logo_data_url: str | None = Field(default=None, max_length=1_500_000)
    qr_payload: str | None = Field(default=None, max_length=1000)
    footer_text: str | None = Field(default=None, max_length=300)
    signature_labels: list[str] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def safe_labels(self) -> "ReportBranding":
        self.signature_labels = [label.strip() for label in self.signature_labels if label.strip()]
        if any(len(label) > 80 for label in self.signature_labels):
            raise ValueError("signature_label_too_long")
        return self


class ReportPreviewRequest(BaseModel):
    report_type: ReportType
    source: ReportSource = Field(default_factory=ReportSource)
    filters: ReportFilters = Field(default_factory=ReportFilters)
    print_options: PrintOptions = Field(default_factory=PrintOptions)
    branding: ReportBranding = Field(default_factory=ReportBranding)


class ReportExportRequest(ReportPreviewRequest):
    format: Literal["pdf", "xlsx", "png"]


class ReportSourceMetadata(BaseModel):
    kind: Literal["working", "candidate"]
    timetable_id: uuid.UUID | None
    candidate_id: uuid.UUID | None
    version_number: int | None
    revision: int | None
    generated_at: datetime
    project_id: uuid.UUID
    project_name: str
    school_labels: list[str]
    term_labels: list[str]


class ReportRow(BaseModel):
    row_id: str
    project_cycle_week_index: int | None = None
    local_cycle_week_label: str | None = None
    weekday_index: int | None = None
    weekday_label: str | None = None
    starts_at_minute: int | None = None
    ends_at_minute: int | None = None
    period_label: str | None = None
    school_id: uuid.UUID | None = None
    school_name: str | None = None
    subject_id: uuid.UUID | None = None
    subject_name: str | None = None
    teacher_ids: list[uuid.UUID] = Field(default_factory=list)
    teacher_names: list[str] = Field(default_factory=list)
    section_ids: list[uuid.UUID] = Field(default_factory=list)
    section_names: list[str] = Field(default_factory=list)
    resource_ids: list[uuid.UUID] = Field(default_factory=list)
    resource_names: list[str] = Field(default_factory=list)
    attendance_mode: str | None = None
    attendance_label: str | None = None
    absent_teacher_name: str | None = None
    substitute_teacher_name: str | None = None
    coverage_status: str | None = None
    recommendation_rank: int | None = None
    base_workload: int | None = None
    teaching_workload: int | None = None
    substitution_count: int | None = None
    effective_limit: int | None = None
    remaining_capacity: int | None = None
    exempt: bool | None = None
    stale: bool = False


class ReportDataset(BaseModel):
    report_type: ReportType
    title: str
    subtitle: str | None
    source: ReportSourceMetadata
    filters: ReportFilters
    print_options: PrintOptions
    branding: ReportBranding
    columns: list[str]
    rows: list[ReportRow]
    row_count: int
    stale: bool = False
    warnings: list[str] = Field(default_factory=list)


class ReportExportMetadata(BaseModel):
    filename: str
    content_type: str
    pages: int
    source_revision: int | None
    multi_page: bool


class ReportOption(BaseModel):
    id: uuid.UUID
    label: str
    school_id: uuid.UUID | None = None
    school_ids: list[uuid.UUID] = Field(default_factory=list)


class ReportOptions(BaseModel):
    schools: list[ReportOption]
    teachers: list[ReportOption]
    sections: list[ReportOption]
    subjects: list[ReportOption]
    resources: list[ReportOption]

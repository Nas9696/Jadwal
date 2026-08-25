import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator


EntityType = Literal[
    "teachers", "subjects", "structure", "curriculum", "resources", "offerings", "assignments"
]


class SheetMapping(BaseModel):
    entity_type: EntityType | Literal["skip"]
    columns: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def exclusive_targets(self) -> "SheetMapping":
        targets = [value for value in self.columns.values() if value]
        if len(targets) != len(set(targets)):
            raise ValueError("duplicate_target_mapping")
        return self


class MappingInput(BaseModel):
    sheets: dict[str, SheetMapping]
    allow_updates: bool = False


class RowExclusionInput(BaseModel):
    row_ids: list[uuid.UUID]

    @model_validator(mode="after")
    def unique_rows(self) -> "RowExclusionInput":
        if len(self.row_ids) != len(set(self.row_ids)):
            raise ValueError("duplicate_row_id")
        return self


class CommitInput(BaseModel):
    acknowledge_warnings: bool = False


class DiagnosticRead(BaseModel):
    sheet: str
    row: int
    field: str | None = None
    severity: Literal["error", "warning", "info"]
    code: str
    message_ar: str
    resolution_ar: str | None = None


class ImportRowRead(BaseModel):
    id: uuid.UUID
    sheet_name: str
    source_row_number: int
    entity_type: str
    source_values: dict[str, object]
    normalized_values: dict[str, object]
    proposed_action: str
    diagnostics: list[dict[str, object]]
    before_values: dict[str, object]
    after_values: dict[str, object]
    excluded: bool
    group_key: str | None


class ImportJobRead(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    term_id: uuid.UUID | None
    source_filename: str
    file_size: int
    file_sha256: str
    status: str
    detected_sheets: list[dict[str, object]]
    mapping: dict[str, object]
    validation_summary: dict[str, object]
    result_summary: dict[str, object]
    duplicate_file_warning: bool
    rows: list[ImportRowRead] = Field(default_factory=list)

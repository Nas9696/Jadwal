import uuid
from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)


class TenantScoped:
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Tenant(IdMixin, Timestamped, Base):
    __tablename__ = "tenants"
    name_ar: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)


class User(IdMixin, Timestamped, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name_ar: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TenantMembership(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "tenant_memberships"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(40))
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    __table_args__ = (UniqueConstraint("tenant_id", "user_id"),)


class SchoolComplex(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "school_complexes"
    name_ar: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(50))
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)


class School(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "schools"
    name_ar: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200))
    complex_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("school_complexes.id", ondelete="SET NULL"), index=True
    )
    code: Mapped[str] = mapped_column(String(50))
    school_type: Mapped[str] = mapped_column(String(40), default="school")
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)


class AcademicYear(IdMixin, TenantScoped, Base):
    __tablename__ = "academic_years"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint("tenant_id", "school_id", "name"),
        CheckConstraint("starts_on < ends_on"),
    )


class Term(IdMixin, TenantScoped, Base):
    __tablename__ = "terms"
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE")
    )
    name_ar: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str | None] = mapped_column(String(100))
    order: Mapped[int] = mapped_column(Integer)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    __table_args__ = (
        UniqueConstraint("tenant_id", "academic_year_id", "order"),
        CheckConstraint("starts_on < ends_on"),
    )


class SchoolShift(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "school_shifts"
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(30))
    name_ar: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (
        UniqueConstraint("tenant_id", "school_id", "code"),
        UniqueConstraint("tenant_id", "school_id", "order"),
    )


class Teacher(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "teachers"
    canonical_code: Mapped[str] = mapped_column(String(50))
    name_ar: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200))
    specialty_reference: Mapped[str | None] = mapped_column(String(150))
    base_workload: Mapped[int] = mapped_column(Integer, default=0)
    teaching_workload_limit: Mapped[int] = mapped_column(Integer, default=24)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("tenant_id", "canonical_code"),)


class TeacherSchoolMembership(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "teacher_school_memberships"
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    local_employee_code: Mapped[str | None] = mapped_column(String(50))
    is_home_school: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        UniqueConstraint("tenant_id", "teacher_id", "school_id"),
        UniqueConstraint("tenant_id", "school_id", "local_employee_code"),
        Index(
            "uq_teacher_active_home_school",
            "tenant_id",
            "teacher_id",
            unique=True,
            postgresql_where=text("is_home_school = true AND is_active = true"),
            sqlite_where=text("is_home_school = 1 AND is_active = 1"),
        ),
    )


class Subject(IdMixin, TenantScoped, Base):
    __tablename__ = "subjects"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(50))
    name_ar: Mapped[str] = mapped_column(String(150))
    name_en: Mapped[str | None] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        UniqueConstraint("tenant_id", "school_id", "code"),
        UniqueConstraint("tenant_id", "school_id", "name_ar"),
    )


class Stage(IdMixin, TenantScoped, Base):
    __tablename__ = "stages"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(50))
    name_ar: Mapped[str] = mapped_column(String(100))
    order: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (
        UniqueConstraint("tenant_id", "school_id", "code"),
        UniqueConstraint("tenant_id", "school_id", "order"),
    )


class Grade(IdMixin, TenantScoped, Base):
    __tablename__ = "grades"
    stage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stages.id", ondelete="CASCADE"))
    name_ar: Mapped[str] = mapped_column(String(100))
    order: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("tenant_id", "stage_id", "order"),)


class Section(IdMixin, TenantScoped, Base):
    __tablename__ = "sections"
    grade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grades.id", ondelete="CASCADE"))
    name_ar: Mapped[str] = mapped_column(String(100))
    capacity: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("tenant_id", "grade_id", "name_ar"),)


class SectionOffering(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "section_offerings"
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sections.id", ondelete="RESTRICT"), index=True
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school_shifts.id", ondelete="RESTRICT"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("tenant_id", "school_id", "term_id", "section_id"),)


class Resource(IdMixin, TenantScoped, Base):
    __tablename__ = "resources"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(50))
    name_ar: Mapped[str] = mapped_column(String(150))
    resource_type: Mapped[str] = mapped_column(String(40), default="room")
    capacity: Mapped[int | None] = mapped_column(Integer)
    exclusive: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("tenant_id", "school_id", "code"),)


class CurriculumRequirement(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "curriculum_requirements"
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    grade_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grades.id", ondelete="RESTRICT"), index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), index=True
    )
    weekly_occurrences: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(300))
    __table_args__ = (
        UniqueConstraint("tenant_id", "school_id", "grade_id", "subject_id"),
        CheckConstraint("weekly_occurrences > 0"),
    )


class WeekPattern(IdMixin, TenantScoped, Base):
    __tablename__ = "week_patterns"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(20))
    name_ar: Mapped[str] = mapped_column(String(100))
    cycle_week_index: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("id", "school_id", "tenant_id"),
        UniqueConstraint("tenant_id", "school_id", "code"),
        UniqueConstraint("tenant_id", "school_id", "cycle_week_index"),
        CheckConstraint("cycle_week_index >= 0"),
    )


class SchoolDay(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "school_days"
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school_shifts.id", ondelete="CASCADE"), index=True
    )
    week_pattern_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("week_patterns.id", ondelete="CASCADE"), index=True
    )
    weekday_index: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    label_ar: Mapped[str | None] = mapped_column(String(80))
    __table_args__ = (
        UniqueConstraint("tenant_id", "school_id", "shift_id", "week_pattern_id", "weekday_index"),
        CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
    )


class PeriodTemplate(IdMixin, TenantScoped, Base):
    __tablename__ = "period_templates"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    week_pattern_id: Mapped[uuid.UUID] = mapped_column(index=True)
    shift_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school_shifts.id", ondelete="CASCADE"), index=True
    )
    school_day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school_days.id", ondelete="CASCADE"), index=True
    )
    weekday_index: Mapped[int] = mapped_column(Integer)
    block_order: Mapped[int] = mapped_column(Integer)
    period_number: Mapped[int | None] = mapped_column(Integer)
    label_ar: Mapped[str | None] = mapped_column(String(100))
    starts_at: Mapped[time] = mapped_column(Time)
    ends_at: Mapped[time] = mapped_column(Time)
    block_type: Mapped[str] = mapped_column(String(30), default="lesson")
    attendance_mode: Mapped[str] = mapped_column(String(20), default="onsite")
    schedulable: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["week_pattern_id", "school_id", "tenant_id"],
            ["week_patterns.id", "week_patterns.school_id", "week_patterns.tenant_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("tenant_id", "school_day_id", "block_order"),
        CheckConstraint("starts_at < ends_at"),
        CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
        CheckConstraint(
            "block_type != 'lesson' OR (period_number IS NOT NULL AND schedulable = TRUE)"
        ),
    )


class TeachingAssignment(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "teaching_assignments"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subjects.id"))
    weekly_occurrences: Mapped[int] = mapped_column(Integer)
    distribution: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(String(300))
    __table_args__ = (CheckConstraint("weekly_occurrences > 0"),)


class TeachingAssignmentTeacher(IdMixin, TenantScoped, Base):
    __tablename__ = "teaching_assignment_teachers"
    teaching_assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teaching_assignments.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    __table_args__ = (UniqueConstraint("tenant_id", "teaching_assignment_id", "teacher_id"),)


class TeachingAssignmentSection(IdMixin, TenantScoped, Base):
    __tablename__ = "teaching_assignment_sections"
    teaching_assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teaching_assignments.id", ondelete="CASCADE"), index=True
    )
    section_offering_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("section_offerings.id", ondelete="RESTRICT"), index=True
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "teaching_assignment_id", "section_offering_id"),
    )


class TeachingAssignmentResource(IdMixin, TenantScoped, Base):
    __tablename__ = "teaching_assignment_resources"
    teaching_assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teaching_assignments.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resources.id", ondelete="RESTRICT"), index=True
    )
    __table_args__ = (UniqueConstraint("tenant_id", "teaching_assignment_id", "resource_id"),)


class ImportJob(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "import_jobs"
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    term_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("terms.id", ondelete="RESTRICT"), index=True
    )
    source_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    file_size: Mapped[int] = mapped_column(Integer)
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30), default="uploaded", index=True)
    detected_sheets: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validation_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    duplicate_file_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    actor_reference: Mapped[str | None] = mapped_column(String(200))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("file_size >= 0"),)


class ImportRow(IdMixin, TenantScoped, Base):
    __tablename__ = "import_rows"
    import_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="CASCADE"), index=True
    )
    sheet_name: Mapped[str] = mapped_column(String(150))
    source_row_number: Mapped[int] = mapped_column(Integer)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    source_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    normalized_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    proposed_action: Mapped[str] = mapped_column(String(30), default="warning")
    diagnostics: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    before_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    after_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    group_key: Mapped[str | None] = mapped_column(String(120))
    __table_args__ = (
        UniqueConstraint("tenant_id", "import_job_id", "sheet_name", "source_row_number"),
        CheckConstraint("source_row_number > 0"),
    )


class Rule(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "rules"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    name_ar: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[str] = mapped_column(String(10))
    weight: Mapped[int | None] = mapped_column(Integer)
    rule_type: Mapped[str] = mapped_column(String(80))
    target_selectors: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    time_selectors: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(20), default="manual")


class TimetableProject(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "timetable_projects"
    scope_type: Mapped[str] = mapped_column(String(20))
    complex_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("school_complexes.id", ondelete="RESTRICT"), index=True
    )
    name_ar: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class TimetableProjectSchool(IdMixin, TenantScoped, Base):
    __tablename__ = "timetable_project_schools"
    timetable_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_projects.id", ondelete="CASCADE"), index=True
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="RESTRICT"), index=True
    )
    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="RESTRICT"), index=True
    )
    cycle_phase_offset: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("tenant_id", "timetable_project_id", "school_id"),)


class SchedulingRule(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "scheduling_rules"
    timetable_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_projects.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500))
    rule_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(10))
    weight: Mapped[int | None] = mapped_column(Integer)
    selector: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        CheckConstraint("severity IN ('hard','soft')"),
        CheckConstraint("weight IS NULL OR weight > 0"),
    )


class AssistantRuleDraft(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "assistant_rule_drafts"
    timetable_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_projects.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_text: Mapped[str] = mapped_column(String(2000))
    parser_type: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), index=True)
    proposals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    clarifications: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_rule_ids: Mapped[list[str]] = mapped_column(JSON, default=list)



class TimetableSolveRun(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "timetable_solve_runs"
    timetable_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_projects.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    input_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    requested_candidates: Mapped[int] = mapped_column(Integer, default=3)
    time_limit_seconds: Mapped[int] = mapped_column(Integer, default=10)
    seed: Mapped[int] = mapped_column(Integer, default=0)
    solver_status: Mapped[str | None] = mapped_column(String(30))
    solver_name: Mapped[str | None] = mapped_column(String(100))
    solver_version: Mapped[str | None] = mapped_column(String(50))
    diagnostics: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("requested_candidates >= 1 AND requested_candidates <= 5"),
        CheckConstraint("time_limit_seconds >= 1 AND time_limit_seconds <= 60"),
        Index(
            "uq_active_solve_run_per_project",
            "tenant_id",
            "timetable_project_id",
            unique=True,
            postgresql_where=text("status IN ('queued','running')"),
            sqlite_where=text("status IN ('queued','running')"),
        ),
    )


class TimetableCandidate(IdMixin, TenantScoped, Base):
    __tablename__ = "timetable_candidates"
    solve_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_solve_runs.id", ondelete="CASCADE"), index=True
    )
    rank: Mapped[int] = mapped_column(Integer)
    solver_status: Mapped[str] = mapped_column(String(30))
    total_penalty: Mapped[int] = mapped_column(Integer, default=0)
    penalty_breakdown: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    solve_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    diversity_count: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("tenant_id", "solve_run_id", "rank"),)


class TimetableEntry(IdMixin, TenantScoped, Base):
    __tablename__ = "timetable_entries"
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_candidates.id", ondelete="CASCADE"), index=True
    )
    occurrence_id: Mapped[str] = mapped_column(String(220))
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teaching_assignments.id", ondelete="RESTRICT"), index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), index=True
    )
    slot_id: Mapped[str] = mapped_column(String(220))
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="RESTRICT"), index=True
    )
    project_cycle_week_index: Mapped[int] = mapped_column(Integer)
    weekday_index: Mapped[int] = mapped_column(Integer)
    starts_at_minute: Mapped[int] = mapped_column(Integer)
    ends_at_minute: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("tenant_id", "candidate_id", "occurrence_id"),
        CheckConstraint("project_cycle_week_index >= 0"),
        CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
        CheckConstraint("starts_at_minute < ends_at_minute"),
    )


class TimetableEntryTeacher(IdMixin, TenantScoped, Base):
    __tablename__ = "timetable_entry_teachers"
    timetable_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_entries.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teachers.id", ondelete="RESTRICT"), index=True
    )
    __table_args__ = (UniqueConstraint("tenant_id", "timetable_entry_id", "teacher_id"),)


class TimetableEntrySection(IdMixin, TenantScoped, Base):
    __tablename__ = "timetable_entry_sections"
    timetable_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_entries.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sections.id", ondelete="RESTRICT"), index=True
    )
    __table_args__ = (UniqueConstraint("tenant_id", "timetable_entry_id", "section_id"),)


class TimetableEntryResource(IdMixin, TenantScoped, Base):
    __tablename__ = "timetable_entry_resources"
    timetable_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_entries.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resources.id", ondelete="RESTRICT"), index=True
    )
    __table_args__ = (UniqueConstraint("tenant_id", "timetable_entry_id", "resource_id"),)


class WorkingTimetable(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "working_timetables"
    timetable_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_projects.id", ondelete="CASCADE"), index=True
    )
    source_candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_candidates.id", ondelete="RESTRICT"), index=True
    )
    parent_timetable_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("working_timetables.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), default="نسخة العمل")
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    history_cursor: Mapped[int] = mapped_column(Integer, default=0)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="working")
    created_by: Mapped[str | None] = mapped_column(String(200))
    change_summary: Mapped[str | None] = mapped_column(String(500))
    __table_args__ = (
        UniqueConstraint("tenant_id", "timetable_project_id", "version_number"),
        Index(
            "uq_current_working_timetable_per_project",
            "tenant_id",
            "timetable_project_id",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
        CheckConstraint("revision > 0"),
        CheckConstraint("history_cursor >= 0"),
    )


class WorkingTimetableEntry(IdMixin, TenantScoped, Base):
    __tablename__ = "working_timetable_entries"
    working_timetable_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetables.id", ondelete="CASCADE"), index=True
    )
    source_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("timetable_entries.id", ondelete="SET NULL"), index=True
    )
    occurrence_id: Mapped[str] = mapped_column(String(220))
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teaching_assignments.id", ondelete="RESTRICT"), index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), index=True
    )
    slot_id: Mapped[str] = mapped_column(String(220))
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="RESTRICT"), index=True
    )
    project_cycle_week_index: Mapped[int] = mapped_column(Integer)
    weekday_index: Mapped[int] = mapped_column(Integer)
    starts_at_minute: Mapped[int] = mapped_column(Integer)
    ends_at_minute: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("tenant_id", "working_timetable_id", "occurrence_id"),
        CheckConstraint("project_cycle_week_index >= 0"),
        CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
        CheckConstraint("starts_at_minute < ends_at_minute"),
    )


class WorkingTimetableEntryTeacher(IdMixin, TenantScoped, Base):
    __tablename__ = "working_timetable_entry_teachers"
    working_timetable_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetable_entries.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teachers.id", ondelete="RESTRICT"), index=True
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "working_timetable_entry_id", "teacher_id"),
    )


class WorkingTimetableEntrySection(IdMixin, TenantScoped, Base):
    __tablename__ = "working_timetable_entry_sections"
    working_timetable_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetable_entries.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sections.id", ondelete="RESTRICT"), index=True
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "working_timetable_entry_id", "section_id"),
    )


class WorkingTimetableEntryResource(IdMixin, TenantScoped, Base):
    __tablename__ = "working_timetable_entry_resources"
    working_timetable_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetable_entries.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resources.id", ondelete="RESTRICT"), index=True
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "working_timetable_entry_id", "resource_id"),
    )


class WaitingPolicy(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "waiting_policies"
    timetable_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_projects.id", ondelete="CASCADE"), index=True
    )
    combined_workload_limit: Mapped[int | None] = mapped_column(Integer)
    daily_waiting_limit: Mapped[int | None] = mapped_column(Integer)
    weekly_waiting_limit: Mapped[int | None] = mapped_column(Integer)
    fairness_weight: Mapped[int] = mapped_column(Integer, default=5)
    specialty_preference_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    specialty_preference_weight: Mapped[int] = mapped_column(Integer, default=3)
    same_school_preference_weight: Mapped[int] = mapped_column(Integer, default=0)
    exclude_exempt_teachers: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        UniqueConstraint("tenant_id", "timetable_project_id"),
        CheckConstraint("combined_workload_limit IS NULL OR combined_workload_limit >= 0"),
        CheckConstraint("daily_waiting_limit IS NULL OR daily_waiting_limit >= 0"),
        CheckConstraint("weekly_waiting_limit IS NULL OR weekly_waiting_limit >= 0"),
        CheckConstraint("fairness_weight >= 0"),
        CheckConstraint("specialty_preference_weight >= 0"),
        CheckConstraint("same_school_preference_weight >= 0"),
    )


class TeacherWaitingProfile(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "teacher_waiting_profiles"
    timetable_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_projects.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    exempt: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_combined_limit: Mapped[int | None] = mapped_column(Integer)
    custom_daily_limit: Mapped[int | None] = mapped_column(Integer)
    custom_weekly_limit: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(500))
    __table_args__ = (
        UniqueConstraint("tenant_id", "timetable_project_id", "teacher_id"),
        CheckConstraint("custom_combined_limit IS NULL OR custom_combined_limit >= 0"),
        CheckConstraint("custom_daily_limit IS NULL OR custom_daily_limit >= 0"),
        CheckConstraint("custom_weekly_limit IS NULL OR custom_weekly_limit >= 0"),
    )


class TeacherAbsence(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "teacher_absences"
    timetable_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetable_projects.id", ondelete="CASCADE"), index=True
    )
    working_timetable_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetables.id", ondelete="RESTRICT"), index=True
    )
    working_timetable_revision: Mapped[int] = mapped_column(Integer)
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="RESTRICT"), index=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teachers.id", ondelete="RESTRICT"), index=True
    )
    absence_date: Mapped[date] = mapped_column(Date, index=True)
    project_cycle_week_index: Mapped[int] = mapped_column(Integer)
    weekday_index: Mapped[int] = mapped_column(Integer)
    full_day: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at_minute: Mapped[int | None] = mapped_column(Integer)
    ends_at_minute: Mapped[int | None] = mapped_column(Integer)
    reason_code: Mapped[str | None] = mapped_column(String(50))
    reason_text: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    __table_args__ = (
        CheckConstraint("working_timetable_revision > 0"),
        CheckConstraint("project_cycle_week_index >= 0"),
        CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
        CheckConstraint(
            "(full_day = TRUE AND starts_at_minute IS NULL AND ends_at_minute IS NULL) OR "
            "(full_day = FALSE AND starts_at_minute IS NOT NULL AND ends_at_minute IS NOT NULL AND starts_at_minute < ends_at_minute)"
        ),
        CheckConstraint("status IN ('open','covered','partially_covered','cancelled')"),
    )


class SubstitutionNeed(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "substitution_needs"
    absence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teacher_absences.id", ondelete="CASCADE"), index=True
    )
    working_timetable_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetable_entries.id", ondelete="RESTRICT"), index=True
    )
    occurrence_id: Mapped[str] = mapped_column(String(220), index=True)
    absent_teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teachers.id", ondelete="RESTRICT"), index=True
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id", ondelete="RESTRICT"), index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), index=True
    )
    project_cycle_week_index: Mapped[int] = mapped_column(Integer)
    weekday_index: Mapped[int] = mapped_column(Integer)
    starts_at_minute: Mapped[int] = mapped_column(Integer)
    ends_at_minute: Mapped[int] = mapped_column(Integer)
    source_working_revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="unassigned", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint("project_cycle_week_index >= 0"),
        CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
        CheckConstraint("starts_at_minute < ends_at_minute"),
        CheckConstraint("source_working_revision > 0"),
        CheckConstraint("version > 0"),
        CheckConstraint("status IN ('unassigned','assigned','uncovered','cancelled')"),
    )


class SubstitutionAssignment(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "substitution_assignments"
    need_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("substitution_needs.id", ondelete="RESTRICT"), index=True
    )
    substitute_teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teachers.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    recommendation_rank: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    eligibility_facts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_by: Mapped[str | None] = mapped_column(String(200))
    __table_args__ = (
        CheckConstraint("status IN ('active','cancelled')"),
        CheckConstraint("score >= 0"),
        Index(
            "uq_active_substitution_per_need",
            "tenant_id",
            "need_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )


class TimetableEditLock(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "timetable_edit_locks"
    working_timetable_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetables.id", ondelete="CASCADE"), index=True
    )
    lock_type: Mapped[str] = mapped_column(String(30), index=True)
    occurrence_id: Mapped[str | None] = mapped_column(String(220))
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"))
    section_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sections.id", ondelete="RESTRICT"))
    school_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("schools.id", ondelete="RESTRICT"))
    project_cycle_week_index: Mapped[int | None] = mapped_column(Integer)
    weekday_index: Mapped[int | None] = mapped_column(Integer)
    starts_at_minute: Mapped[int | None] = mapped_column(Integer)
    ends_at_minute: Mapped[int | None] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(200))
    created_by: Mapped[str | None] = mapped_column(String(200))
    __table_args__ = (
        CheckConstraint(
            "lock_type IN ('occurrence','teacher','section','day','time_range','week','region')"
        ),
        CheckConstraint("weekday_index IS NULL OR (weekday_index >= 0 AND weekday_index <= 6)"),
        CheckConstraint("project_cycle_week_index IS NULL OR project_cycle_week_index >= 0"),
        CheckConstraint(
            "starts_at_minute IS NULL OR ends_at_minute IS NULL OR starts_at_minute < ends_at_minute"
        ),
    )


class TimetableEditChange(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "timetable_edit_changes"
    working_timetable_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetables.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    operation_type: Mapped[str] = mapped_column(String(30))
    before_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    after_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(String(500))
    __table_args__ = (UniqueConstraint("tenant_id", "working_timetable_id", "sequence"),)


class TimetableAuditEvent(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "timetable_audit_events"
    working_timetable_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetables.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    operation_type: Mapped[str] = mapped_column(String(30))
    before_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    after_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(String(500))
    actor_reference: Mapped[str | None] = mapped_column(String(200))


class TimetableSnapshot(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "timetable_snapshots"
    working_timetable_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetables.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    source_revision: Mapped[int] = mapped_column(Integer)
    entries_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    created_by: Mapped[str | None] = mapped_column(String(200))


class TimetableRepairPreview(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "timetable_repair_previews"
    working_timetable_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("working_timetables.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    occurrence_id: Mapped[str] = mapped_column(String(220))
    target_slot_id: Mapped[str] = mapped_column(String(220))
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    fingerprint: Mapped[str] = mapped_column(String(64))
    total_moved_occurrences: Mapped[int] = mapped_column(Integer)
    penalty_before: Mapped[int] = mapped_column(Integer, default=0)
    penalty_after: Mapped[int] = mapped_column(Integer, default=0)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

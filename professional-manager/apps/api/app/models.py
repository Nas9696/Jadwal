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

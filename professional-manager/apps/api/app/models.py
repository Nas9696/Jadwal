import uuid
from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

def new_uuid() -> uuid.UUID:
    return uuid.uuid4()

class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)

class TenantScoped:
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)

class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

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
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_years.id", ondelete="CASCADE"))
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
    specialty_reference: Mapped[str | None] = mapped_column(String(150))
    base_workload: Mapped[int] = mapped_column(Integer, default=0)
    teaching_workload_limit: Mapped[int] = mapped_column(Integer, default=24)
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
    )

class Subject(IdMixin, TenantScoped, Base):
    __tablename__ = "subjects"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(50))
    name_ar: Mapped[str] = mapped_column(String(150))
    name_en: Mapped[str | None] = mapped_column(String(150))

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

class Resource(IdMixin, TenantScoped, Base):
    __tablename__ = "resources"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    name_ar: Mapped[str] = mapped_column(String(150))
    resource_type: Mapped[str] = mapped_column(String(40), default="room")
    capacity: Mapped[int | None] = mapped_column(Integer)
    exclusive: Mapped[bool] = mapped_column(Boolean, default=True)

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
        UniqueConstraint(
            "tenant_id", "school_id", "shift_id", "week_pattern_id", "weekday_index"
        ),
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
        UniqueConstraint(
            "tenant_id", "school_day_id", "block_order"
        ),
        CheckConstraint("starts_at < ends_at"),
        CheckConstraint("weekday_index >= 0 AND weekday_index <= 6"),
        CheckConstraint(
            "block_type != 'lesson' OR (period_number IS NOT NULL AND schedulable = TRUE)"
        ),
    )

class TeachingAssignment(IdMixin, TenantScoped, Timestamped, Base):
    __tablename__ = "teaching_assignments"
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subjects.id"))
    section_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    resource_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    weekly_occurrences: Mapped[int] = mapped_column(Integer)
    distribution: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class TeachingAssignmentTeacher(IdMixin, TenantScoped, Base):
    __tablename__ = "teaching_assignment_teachers"
    teaching_assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teaching_assignments.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "teaching_assignment_id", "teacher_id"),
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
    __table_args__ = (
        UniqueConstraint("tenant_id", "timetable_project_id", "school_id"),
    )

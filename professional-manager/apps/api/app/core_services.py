from __future__ import annotations

import uuid
import re
import unicodedata
from datetime import date, time
from typing import Any, NoReturn

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.assignment_services import save_assignment
from app.core_schemas import (
    AssignmentTransferInput,
    AvailabilityCopyInput,
    BulkTeachersInput,
    CurriculumPlanInput,
    DayBuilderInput,
    GenerateInput,
    PeriodEditInput,
    PresetRuleInput,
    QuickAssignmentInput,
    OrderedIdsInput,
    SimpleSectionInput,
    SimpleSubjectInput,
    SimpleTeacherInput,
    StructureInput,
    TeacherMergeInput,
    TeacherAvailabilityInput,
)
from app.models import (
    AcademicYear,
    CurriculumRequirement,
    Grade,
    PeriodTemplate,
    SchedulingRule,
    School,
    SchoolDay,
    SchoolShift,
    Section,
    SectionOffering,
    Stage,
    Subject,
    Teacher,
    TeacherSchoolMembership,
    TeachingAssignment,
    TeachingAssignmentResource,
    TeachingAssignmentSection,
    TeachingAssignmentTeacher,
    Term,
    TimetableEntry,
    TimetableProject,
    TimetableProjectSchool,
    WeekPattern,
    WorkingTimetableEntry,
)
from app.project_services import preflight
from app.solve_schemas import SolveRequest
from app.solve_services import create_solve_run


WEEKDAYS = ("الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت")
STAGES: dict[str, tuple[str, tuple[str, ...]]] = {
    "primary": ("المرحلة الابتدائية", ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")),
    "intermediate": ("المرحلة المتوسطة", ("الأول المتوسط", "الثاني المتوسط", "الثالث المتوسط")),
    "secondary": ("المرحلة الثانوية", ("الأول الثانوي", "الثاني الثانوي", "الثالث الثانوي")),
}
SECTION_LETTERS = tuple("أبجدهوزحطيكلمنسعفصقرشتثخذضظغ")
CORE_PROJECT_PREFIX = "جدول المدرسة"
CORE_RULE_PREFIX = "المسار المبسط:"
MINISTRY_SUBJECT_ORDER = (
    ("قران", "اسلام"), ("اسلام",), ("لغتي", "لغهعربي", "عربي"), ("رياضيات",),
    ("علوم",), ("انجليزي", "لغهانجليزي"), ("اجتماع",), ("رقمي",),
    ("فني",), ("بدني",), ("حياتي", "اسري"), ("نشاط",),
)


def fail(code: str, status: int = 422) -> NoReturn:
    raise HTTPException(status_code=status, detail={"code": code})


def _school(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID) -> School:
    row = db.scalar(select(School).where(School.id == school_id, School.tenant_id == tenant_id))
    if row is None:
        fail("school_not_found", 404)
    return row


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _clock(value: int) -> time:
    if value < 0 or value >= 24 * 60:
        fail("school_day_exceeds_midnight")
    return time(value // 60, value % 60)


def build_day_blocks(payload: DayBuilderInput) -> list[dict[str, Any]]:
    cursor = _minutes(payload.assembly_start)
    blocks: list[dict[str, Any]] = []
    order = 0
    if payload.assembly_minutes:
        blocks.append({"block_order": order, "label_ar": "الطابور", "block_type": "assembly", "period_number": None, "starts_at": _clock(cursor), "ends_at": _clock(cursor + payload.assembly_minutes)})
        cursor += payload.assembly_minutes
        order += 1
    breaks = {item.after_period: item.duration_minutes for item in payload.breaks}
    prayer_added = False
    for period_number in range(1, payload.period_count + 1):
        blocks.append({"block_order": order, "label_ar": f"الحصة {period_number}", "block_type": "lesson", "period_number": period_number, "starts_at": _clock(cursor), "ends_at": _clock(cursor + payload.period_minutes)})
        cursor += payload.period_minutes
        order += 1
        if period_number in breaks:
            duration = breaks[period_number]
            blocks.append({"block_order": order, "label_ar": "الفسحة", "block_type": "break", "period_number": None, "starts_at": _clock(cursor), "ends_at": _clock(cursor + duration)})
            cursor += duration
            order += 1
        if payload.prayer and payload.prayer.after_period == period_number:
            duration = payload.prayer.duration_minutes
            blocks.append({"block_order": order, "label_ar": "الصلاة", "block_type": "prayer", "period_number": None, "starts_at": _clock(cursor), "ends_at": _clock(cursor + duration)})
            cursor += duration
            order += 1
            prayer_added = True
        if payload.prayer and payload.prayer.fixed_time and not prayer_added:
            fixed = _minutes(payload.prayer.fixed_time)
            if cursor == fixed:
                duration = payload.prayer.duration_minutes
                blocks.append({"block_order": order, "label_ar": "الصلاة", "block_type": "prayer", "period_number": None, "starts_at": _clock(cursor), "ends_at": _clock(cursor + duration)})
                cursor += duration
                order += 1
                prayer_added = True
            elif cursor > fixed:
                fail("fixed_prayer_time_breaks_sequence")
    if payload.prayer and payload.prayer.fixed_time and not prayer_added:
        fail("fixed_prayer_time_not_on_period_boundary")
    return blocks


def _foundation(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID) -> tuple[AcademicYear, Term, SchoolShift, WeekPattern]:
    _school(db, tenant_id, school_id)
    year = db.scalar(select(AcademicYear).where(AcademicYear.tenant_id == tenant_id, AcademicYear.school_id == school_id, AcademicYear.is_current.is_(True)))
    if year is None:
        year = db.scalar(select(AcademicYear).where(AcademicYear.tenant_id == tenant_id, AcademicYear.school_id == school_id).order_by(AcademicYear.starts_on.desc()))
        if year is None:
            today = date.today()
            year = AcademicYear(tenant_id=tenant_id, school_id=school_id, name=f"العام الدراسي {today.year}", starts_on=date(today.year, 8, 1), ends_on=date(today.year + 1, 7, 31), is_current=True)
            db.add(year)
            db.flush()
        else:
            year.is_current = True
    term = db.scalar(select(Term).where(Term.tenant_id == tenant_id, Term.academic_year_id == year.id).order_by(Term.order))
    if term is None:
        term = Term(tenant_id=tenant_id, academic_year_id=year.id, name_ar="الفصل الدراسي الحالي", order=1, starts_on=year.starts_on, ends_on=year.ends_on)
        db.add(term)
        db.flush()
    shift = db.scalar(select(SchoolShift).where(SchoolShift.tenant_id == tenant_id, SchoolShift.school_id == school_id).order_by(SchoolShift.order))
    if shift is None:
        shift = SchoolShift(tenant_id=tenant_id, school_id=school_id, code="DEFAULT-AM", name_ar="الدوام الصباحي", is_active=True, order=0)
        db.add(shift)
        db.flush()
    pattern = db.scalar(select(WeekPattern).where(WeekPattern.tenant_id == tenant_id, WeekPattern.school_id == school_id).order_by(WeekPattern.cycle_week_index))
    if pattern is None:
        pattern = WeekPattern(tenant_id=tenant_id, school_id=school_id, code="DEFAULT", name_ar="الأسبوع الدراسي", cycle_week_index=0)
        db.add(pattern)
        db.flush()
    db.flush()
    return year, term, shift, pattern


def _project(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID) -> TimetableProject:
    _, term, _, _ = _foundation(db, tenant_id, school_id)
    project = db.scalar(select(TimetableProject).join(TimetableProjectSchool, TimetableProjectSchool.timetable_project_id == TimetableProject.id).where(TimetableProject.tenant_id == tenant_id, TimetableProjectSchool.tenant_id == tenant_id, TimetableProjectSchool.school_id == school_id).order_by(TimetableProject.created_at.desc()))
    if project is None:
        school = _school(db, tenant_id, school_id)
        project = TimetableProject(tenant_id=tenant_id, scope_type="school", name_ar=f"{CORE_PROJECT_PREFIX} - {school.name_ar}", description="مشروع أنشئه المسار الأساسي", status="ready", settings={"optimization_profile": "balanced", "project_cycle_limit": 12})
        db.add(project)
        db.flush()
        db.add(TimetableProjectSchool(tenant_id=tenant_id, timetable_project_id=project.id, school_id=school_id, term_id=term.id, cycle_phase_offset=0))
        db.flush()
    return project


def save_day_builder(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: DayBuilderInput) -> dict[str, Any]:
    school = _school(db, tenant_id, school_id)
    school.name_ar = payload.school_name
    _, _, shift, pattern = _foundation(db, tenant_id, school_id)
    project = _project(db, tenant_id, school_id)
    project.settings = {**project.settings, "core_stages": payload.stages}
    blocks = build_day_blocks(payload)
    days = list(db.scalars(select(SchoolDay).where(SchoolDay.tenant_id == tenant_id, SchoolDay.school_id == school_id, SchoolDay.shift_id == shift.id, SchoolDay.week_pattern_id == pattern.id)))
    by_weekday = {day.weekday_index: day for day in days}
    for day in days:
        day.enabled = day.weekday_index in payload.weekdays
    for weekday in payload.weekdays:
        selected_day = by_weekday.get(weekday)
        if selected_day is None:
            selected_day = SchoolDay(tenant_id=tenant_id, school_id=school_id, shift_id=shift.id, week_pattern_id=pattern.id, weekday_index=weekday, enabled=True, label_ar=WEEKDAYS[weekday])
            db.add(selected_day)
            db.flush()
        db.execute(delete(PeriodTemplate).where(PeriodTemplate.tenant_id == tenant_id, PeriodTemplate.school_day_id == selected_day.id))
        for block in blocks:
            db.add(PeriodTemplate(tenant_id=tenant_id, school_id=school_id, shift_id=shift.id, school_day_id=selected_day.id, week_pattern_id=pattern.id, weekday_index=weekday, attendance_mode="onsite", schedulable=block["block_type"] == "lesson", **block))
    db.commit()
    return {"school_name": school.name_ar, "weekdays": payload.weekdays, "blocks": blocks}


def edit_period(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, block_id: uuid.UUID, payload: PeriodEditInput) -> dict[str, Any]:
    block = db.scalar(select(PeriodTemplate).where(PeriodTemplate.id == block_id, PeriodTemplate.tenant_id == tenant_id, PeriodTemplate.school_id == school_id))
    if block is None:
        fail("period_not_found", 404)
    old_end = _minutes(block.ends_at)
    new_end = _minutes(payload.ends_at)
    delta = new_end - old_end
    block.block_order = payload.block_order
    block.label_ar = payload.label_ar
    block.block_type = payload.block_type
    block.period_number = payload.period_number
    block.starts_at = payload.starts_at
    block.ends_at = payload.ends_at
    block.schedulable = payload.block_type == "lesson"
    if payload.recalculate_following and delta:
        following = list(db.scalars(select(PeriodTemplate).where(PeriodTemplate.tenant_id == tenant_id, PeriodTemplate.school_day_id == block.school_day_id, PeriodTemplate.block_order > block.block_order).order_by(PeriodTemplate.block_order)))
        cursor = new_end
        for item in following:
            duration = _minutes(item.ends_at) - _minutes(item.starts_at)
            item.starts_at = _clock(cursor)
            item.ends_at = _clock(cursor + duration)
            cursor += duration
    db.commit()
    return {"id": block.id, "starts_at": block.starts_at, "ends_at": block.ends_at}


def _section_suffix(grade_name: str, section_name: str) -> str:
    normalized = " ".join(section_name.split())
    return normalized.removeprefix(grade_name).strip() or normalized


def _section_usage(db: Session, tenant_id: uuid.UUID, section_id: uuid.UUID) -> int:
    return int(db.scalar(select(func.count()).select_from(TeachingAssignmentSection).join(SectionOffering, SectionOffering.id == TeachingAssignmentSection.section_offering_id).where(TeachingAssignmentSection.tenant_id == tenant_id, SectionOffering.section_id == section_id)) or 0)


def _generated_section_name(grade_name: str, grade_number: int, section_number: int, pattern: str) -> str:
    letter = SECTION_LETTERS[section_number - 1] if section_number <= len(SECTION_LETTERS) else str(section_number)
    if pattern == "number_slash_number":
        return f"{grade_number} / {section_number}"
    if pattern == "number_dash_number":
        return f"{grade_number} ـ {section_number}"
    if pattern == "number_slash_letter":
        return f"{grade_number} / {letter}"
    return f"{grade_name} {letter}"


def _detach_section_assignments(db: Session, tenant_id: uuid.UUID, offerings: list[SectionOffering]) -> int:
    if not offerings:
        return 0
    links = list(db.scalars(select(TeachingAssignmentSection).where(TeachingAssignmentSection.tenant_id == tenant_id, TeachingAssignmentSection.section_offering_id.in_([item.id for item in offerings]))))
    assignment_ids = {link.teaching_assignment_id for link in links}
    for link in links:
        db.delete(link)
    db.flush()
    for assignment_id in assignment_ids:
        remaining = db.scalar(select(TeachingAssignmentSection.id).where(TeachingAssignmentSection.tenant_id == tenant_id, TeachingAssignmentSection.teaching_assignment_id == assignment_id).limit(1))
        if remaining is not None:
            continue
        db.execute(delete(TeachingAssignmentTeacher).where(TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teaching_assignment_id == assignment_id))
        db.execute(delete(TeachingAssignmentResource).where(TeachingAssignmentResource.tenant_id == tenant_id, TeachingAssignmentResource.teaching_assignment_id == assignment_id))
        assignment = db.get(TeachingAssignment, assignment_id)
        if assignment is not None:
            historical = db.scalar(select(TimetableEntry.id).where(TimetableEntry.tenant_id == tenant_id, TimetableEntry.assignment_id == assignment_id).limit(1)) or db.scalar(select(WorkingTimetableEntry.id).where(WorkingTimetableEntry.tenant_id == tenant_id, WorkingTimetableEntry.assignment_id == assignment_id).limit(1))
            if historical is None:
                db.delete(assignment)
    return len(links)


def save_structure(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: StructureInput) -> dict[str, Any]:
    _, term, shift, _ = _foundation(db, tenant_id, school_id)
    stage_name, standard = STAGES[payload.stage]
    stage = db.scalar(select(Stage).where(Stage.tenant_id == tenant_id, Stage.school_id == school_id, Stage.name_ar == stage_name))
    if stage is None:
        stage = Stage(tenant_id=tenant_id, school_id=school_id, code=f"AUTO-{payload.stage.upper()}", name_ar=stage_name, order=len(db.scalars(select(Stage).where(Stage.tenant_id == tenant_id, Stage.school_id == school_id)).all()))
        db.add(stage)
        db.flush()
    requested = {item.grade_name: item.section_count for item in payload.grades}
    created: list[dict[str, Any]] = []
    for order, grade_name in enumerate(standard):
        if grade_name not in requested:
            continue
        grade = db.scalar(select(Grade).where(Grade.tenant_id == tenant_id, Grade.stage_id == stage.id, Grade.order == order))
        if grade is None:
            grade = Grade(tenant_id=tenant_id, stage_id=stage.id, name_ar=grade_name, order=order)
            db.add(grade)
            db.flush()
        else:
            grade.name_ar = grade_name
        all_existing = list(db.scalars(select(Section).where(Section.tenant_id == tenant_id, Section.grade_id == grade.id).order_by(Section.name_ar)))
        grouped: dict[str, list[Section]] = {}
        for section in all_existing:
            grouped.setdefault(_section_suffix(grade_name, section.name_ar), []).append(section)
        existing: list[Section] = []
        for group in grouped.values():
            ranked = sorted(group, key=lambda item: (-_section_usage(db, tenant_id, item.id), len(item.name_ar), item.name_ar))
            canonical = ranked[0]
            existing.append(canonical)
            for duplicate in ranked[1:]:
                if _section_usage(db, tenant_id, duplicate.id):
                    continue
                duplicate_offerings = list(db.scalars(select(SectionOffering).where(SectionOffering.tenant_id == tenant_id, SectionOffering.school_id == school_id, SectionOffering.section_id == duplicate.id)))
                for duplicate_offering in duplicate_offerings:
                    duplicate_offering.is_active = False
        existing.sort(key=lambda item: (SECTION_LETTERS.index(_section_suffix(grade_name, item.name_ar)) if _section_suffix(grade_name, item.name_ar) in SECTION_LETTERS else len(SECTION_LETTERS), item.name_ar))
        for index in range(len(existing), requested[grade_name]):
            section = Section(tenant_id=tenant_id, grade_id=grade.id, name_ar=_generated_section_name(grade_name, order + 1, index + 1, payload.naming_pattern), capacity=None)
            db.add(section)
            db.flush()
            existing.append(section)
        if payload.reset_names:
            for index, section in enumerate(existing[: requested[grade_name]]):
                section.name_ar = _generated_section_name(grade_name, order + 1, index + 1, payload.naming_pattern)
        for section in existing[: requested[grade_name]]:
            offering = db.scalar(select(SectionOffering).where(SectionOffering.tenant_id == tenant_id, SectionOffering.school_id == school_id, SectionOffering.term_id == term.id, SectionOffering.section_id == section.id))
            if offering is None:
                db.add(SectionOffering(tenant_id=tenant_id, school_id=school_id, term_id=term.id, section_id=section.id, shift_id=shift.id, is_active=True))
            else:
                offering.is_active = True
        for section in existing[requested[grade_name] :]:
            offering = db.scalar(select(SectionOffering).where(SectionOffering.tenant_id == tenant_id, SectionOffering.school_id == school_id, SectionOffering.term_id == term.id, SectionOffering.section_id == section.id))
            if offering is not None:
                _detach_section_assignments(db, tenant_id, [offering])
                offering.is_active = False
        created.append({"grade_name": grade_name, "sections": [section.name_ar for section in existing[: requested[grade_name]]]})
    db.commit()
    return {"stage": stage_name, "grades": created}


def _teacher_in_school(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, teacher_id: uuid.UUID) -> Teacher:
    teacher = db.scalar(select(Teacher).join(TeacherSchoolMembership, TeacherSchoolMembership.teacher_id == Teacher.id).where(Teacher.id == teacher_id, Teacher.tenant_id == tenant_id, TeacherSchoolMembership.tenant_id == tenant_id, TeacherSchoolMembership.school_id == school_id, TeacherSchoolMembership.is_active.is_(True)))
    if teacher is None:
        fail("teacher_not_in_school", 404)
    return teacher


def _name_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.strip().casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    substitutions: dict[int, str] = {ord("أ"): "ا", ord("إ"): "ا", ord("آ"): "ا", ord("ٱ"): "ا", ord("ى"): "ي", ord("ة"): "ه", ord("ؤ"): "و", ord("ئ"): "ي"}
    text = text.translate(substitutions)
    return re.sub(r"[^\u0600-\u06ffA-Za-z]+", "", text.replace("ـ", ""))


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for index, left_char in enumerate(left, 1):
        current = [index]
        for other_index, right_char in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[other_index] + 1, previous[other_index - 1] + (left_char != right_char)))
        previous = current
    return previous[-1]


def _ordered(rows: list[Any], configured: list[str], fallback: Any) -> list[Any]:
    positions = {value: index for index, value in enumerate(configured)}
    return sorted(rows, key=lambda row: (positions.get(str(row.id), len(positions)), fallback(row)))


def _ministry_subject_rank(subject: Subject) -> tuple[int, str]:
    key = _name_key(subject.name_ar)
    rank = next((index for index, aliases in enumerate(MINISTRY_SUBJECT_ORDER) if any(alias in key for alias in aliases)), len(MINISTRY_SUBJECT_ORDER))
    return rank, key


def _similar_teachers(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, name: str, exclude_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
    key = _name_key(name)
    rows = db.execute(
        select(Teacher, TeacherSchoolMembership)
        .join(TeacherSchoolMembership, TeacherSchoolMembership.teacher_id == Teacher.id)
        .where(
            Teacher.tenant_id == tenant_id,
            TeacherSchoolMembership.tenant_id == tenant_id,
            TeacherSchoolMembership.school_id == school_id,
            TeacherSchoolMembership.is_active.is_(True),
        )
    ).all()
    matches = []
    for teacher, _ in rows:
        if teacher.id == exclude_id:
            continue
        other = _name_key(teacher.name_ar)
        threshold = 1 if max(len(key), len(other)) < 8 else 2
        distance = _edit_distance(key, other)
        if key == other or distance <= threshold:
            matches.append({"id": str(teacher.id), "name_ar": teacher.name_ar, "distance": distance})
    return matches


def _ensure_teacher_name(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, name: str, allow_similar: bool, exclude_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
    matches = _similar_teachers(db, tenant_id, school_id, name, exclude_id)
    if matches and not allow_similar:
        raise HTTPException(status_code=409, detail={"code": "similar_teacher_confirmation_required", "entered_name": name, "matches": matches})
    return matches


def create_simple_teacher(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: SimpleTeacherInput) -> dict[str, Any]:
    _school(db, tenant_id, school_id)
    name = " ".join(payload.name_ar.split())
    _ensure_teacher_name(db, tenant_id, school_id, name, payload.allow_similar)
    teacher = Teacher(tenant_id=tenant_id, canonical_code=f"AUTO-{uuid.uuid4().hex[:12].upper()}", name_ar=name, base_workload=payload.workload_limit, teaching_workload_limit=payload.workload_limit, is_active=True)
    db.add(teacher)
    db.flush()
    db.add(TeacherSchoolMembership(tenant_id=tenant_id, teacher_id=teacher.id, school_id=school_id, local_employee_code=None, is_home_school=True, is_active=True))
    db.commit()
    return {"id": teacher.id, "name_ar": teacher.name_ar, "workload_limit": teacher.teaching_workload_limit}


def update_simple_teacher(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, teacher_id: uuid.UUID, payload: SimpleTeacherInput) -> dict[str, Any]:
    teacher = _teacher_in_school(db, tenant_id, school_id, teacher_id)
    name = " ".join(payload.name_ar.split())
    _ensure_teacher_name(db, tenant_id, school_id, name, payload.allow_similar, teacher_id)
    teacher.name_ar = name
    teacher.base_workload = payload.workload_limit
    teacher.teaching_workload_limit = payload.workload_limit
    db.commit()
    return {"id": teacher.id, "name_ar": teacher.name_ar, "workload_limit": teacher.teaching_workload_limit}


def delete_simple_teacher(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, teacher_id: uuid.UUID, cascade: bool = False) -> None:
    _teacher_in_school(db, tenant_id, school_id, teacher_id)
    membership = db.scalar(select(TeacherSchoolMembership).where(TeacherSchoolMembership.tenant_id == tenant_id, TeacherSchoolMembership.school_id == school_id, TeacherSchoolMembership.teacher_id == teacher_id))
    links = list(db.scalars(select(TeachingAssignmentTeacher).join(TeachingAssignment, TeachingAssignment.id == TeachingAssignmentTeacher.teaching_assignment_id).where(TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teacher_id == teacher_id, TeachingAssignment.school_id == school_id)))
    if links and not cascade:
        fail("teacher_has_assignments_move_or_delete_first", 409)
    for link in links:
        teacher_count = int(db.scalar(select(func.count()).select_from(TeachingAssignmentTeacher).where(TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teaching_assignment_id == link.teaching_assignment_id)) or 0)
        assignment = db.scalar(select(TeachingAssignment).where(TeachingAssignment.id == link.teaching_assignment_id))
        if teacher_count <= 1 and assignment is not None:
            _remove_assignment_from_current(db, tenant_id, school_id, assignment)
        else:
            db.delete(link)
    project = _project(db, tenant_id, school_id)
    db.execute(delete(SchedulingRule).where(SchedulingRule.tenant_id == tenant_id, SchedulingRule.timetable_project_id == project.id, SchedulingRule.selector["teacher_id"].as_string() == str(teacher_id)))
    if membership is not None:
        db.delete(membership)
    db.commit()


def _assignment_section_key(db: Session, tenant_id: uuid.UUID, assignment_id: uuid.UUID) -> tuple[str, ...]:
    rows = db.scalars(
        select(SectionOffering.section_id)
        .join(
            TeachingAssignmentSection,
            TeachingAssignmentSection.section_offering_id == SectionOffering.id,
        )
        .where(
            TeachingAssignmentSection.tenant_id == tenant_id,
            TeachingAssignmentSection.teaching_assignment_id == assignment_id,
        )
    )
    return tuple(sorted(str(section_id) for section_id in rows))


def _remove_assignment_from_current(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    assignment: TeachingAssignment,
) -> None:
    historical_references = int(
        db.scalar(
            select(func.count())
            .select_from(TimetableEntry)
            .where(
                TimetableEntry.tenant_id == tenant_id,
                TimetableEntry.assignment_id == assignment.id,
            )
        )
        or 0
    ) + int(
        db.scalar(
            select(func.count())
            .select_from(WorkingTimetableEntry)
            .where(
                WorkingTimetableEntry.tenant_id == tenant_id,
                WorkingTimetableEntry.assignment_id == assignment.id,
            )
        )
        or 0
    )
    if historical_references:
        db.execute(
            delete(TeachingAssignmentTeacher).where(
                TeachingAssignmentTeacher.tenant_id == tenant_id,
                TeachingAssignmentTeacher.teaching_assignment_id == assignment.id,
            )
        )
        return
    db.delete(assignment)


def _teacher_workload(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    term_id: uuid.UUID,
    teacher_id: uuid.UUID,
) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(TeachingAssignment.weekly_occurrences), 0))
            .join(
                TeachingAssignmentTeacher,
                TeachingAssignmentTeacher.teaching_assignment_id == TeachingAssignment.id,
            )
            .where(
                TeachingAssignment.tenant_id == tenant_id,
                TeachingAssignment.school_id == school_id,
                TeachingAssignment.term_id == term_id,
                TeachingAssignmentTeacher.tenant_id == tenant_id,
                TeachingAssignmentTeacher.teacher_id == teacher_id,
            )
        )
        or 0
    )


def _section_key(db: Session, tenant_id: uuid.UUID, section_id: uuid.UUID) -> tuple[str, ...]:
    row = db.execute(
        select(Grade.name_ar, Section.name_ar)
        .join(Grade, Grade.id == Section.grade_id)
        .where(Section.id == section_id, Section.tenant_id == tenant_id)
    ).one_or_none()
    if row is None:
        fail("section_not_in_school", 404)
    grade_name, section_name = row
    return (f"{_name_key(grade_name)}:{_name_key(_section_suffix(grade_name, section_name))}",)


def _assignment_conflict(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    term_id: uuid.UUID,
    subject_id: uuid.UUID,
    section_id: uuid.UUID,
    *,
    exclude_assignment_ids: set[uuid.UUID] | None = None,
) -> TeachingAssignment | None:
    subject_name = db.scalar(
        select(Subject.name_ar).where(
            Subject.id == subject_id,
            Subject.tenant_id == tenant_id,
            Subject.school_id == school_id,
        )
    )
    if subject_name is None:
        fail("subject_not_in_school", 404)
    target = (str(subject_id), (str(section_id),))
    excluded = exclude_assignment_ids or set()
    candidates = db.scalars(
        select(TeachingAssignment)
        .join(
            TeachingAssignmentTeacher,
            TeachingAssignmentTeacher.teaching_assignment_id == TeachingAssignment.id,
        )
        .where(
            TeachingAssignment.tenant_id == tenant_id,
            TeachingAssignment.school_id == school_id,
            TeachingAssignment.term_id == term_id,
            TeachingAssignmentTeacher.tenant_id == tenant_id,
        )
    ).unique()
    return next(
        (
            assignment
            for assignment in candidates
            if assignment.id not in excluded
            and (
                _assignment_subject_key(db, tenant_id, assignment),
                _assignment_section_key(db, tenant_id, assignment.id),
            )
            == target
        ),
        None,
    )


def _require_workload_capacity(
    teacher: Teacher,
    projected: int,
    allow_overload: bool,
) -> None:
    if projected > teacher.teaching_workload_limit and not allow_overload:
        fail("teacher_workload_limit_exceeded", 409)


def _assignment_has_active_section(
    db: Session, tenant_id: uuid.UUID, assignment_id: uuid.UUID
) -> bool:
    return bool(
        db.scalar(
            select(func.count())
            .select_from(TeachingAssignmentSection)
            .join(
                SectionOffering,
                SectionOffering.id == TeachingAssignmentSection.section_offering_id,
            )
            .where(
                TeachingAssignmentSection.tenant_id == tenant_id,
                TeachingAssignmentSection.teaching_assignment_id == assignment_id,
                SectionOffering.is_active.is_(True),
            )
        )
    )


def _assignment_subject_key(
    db: Session, tenant_id: uuid.UUID, assignment: TeachingAssignment
) -> str:
    belongs_to_tenant = db.scalar(select(Subject.id).where(Subject.id == assignment.subject_id, Subject.tenant_id == tenant_id))
    return str(belongs_to_tenant or assignment.subject_id)


def _assignment_has_active_subject(
    db: Session, tenant_id: uuid.UUID, assignment: TeachingAssignment
) -> bool:
    return bool(
        db.scalar(
            select(func.count())
            .select_from(Subject)
            .where(
                Subject.id == assignment.subject_id,
                Subject.tenant_id == tenant_id,
                Subject.is_active.is_(True),
            )
        )
    )


def deduplicate_teacher_assignments(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, teacher_id: uuid.UUID) -> dict[str, Any]:
    _teacher_in_school(db, tenant_id, school_id, teacher_id)
    assignments = list(db.scalars(select(TeachingAssignment).join(TeachingAssignmentTeacher, TeachingAssignmentTeacher.teaching_assignment_id == TeachingAssignment.id).where(TeachingAssignment.tenant_id == tenant_id, TeachingAssignment.school_id == school_id, TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teacher_id == teacher_id).order_by(TeachingAssignment.created_at)))
    assignments.sort(
        key=lambda assignment: (
            not _assignment_has_active_subject(db, tenant_id, assignment),
            not _assignment_has_active_section(db, tenant_id, assignment.id),
            assignment.created_at,
        )
    )
    seen: dict[tuple[str, tuple[str, ...]], TeachingAssignment] = {}
    removed = 0
    for assignment in assignments:
        key = (
            _assignment_subject_key(db, tenant_id, assignment),
            _assignment_section_key(db, tenant_id, assignment.id),
        )
        canonical = seen.get(key)
        if canonical is None:
            seen[key] = assignment
            continue
        canonical.weekly_occurrences = max(canonical.weekly_occurrences, assignment.weekly_occurrences)
        teacher_links = list(db.scalars(select(TeachingAssignmentTeacher).where(TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teaching_assignment_id == assignment.id)))
        if len(teacher_links) <= 1:
            _remove_assignment_from_current(db, tenant_id, school_id, assignment)
        else:
            duplicate_link = next((link for link in teacher_links if link.teacher_id == teacher_id), None)
            if duplicate_link is not None:
                db.delete(duplicate_link)
        removed += 1
    db.commit()
    return {"removed": removed}


def merge_simple_teachers(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: TeacherMergeInput) -> dict[str, Any]:
    source = _teacher_in_school(db, tenant_id, school_id, payload.source_teacher_id)
    target = _teacher_in_school(db, tenant_id, school_id, payload.target_teacher_id)
    links = list(db.scalars(select(TeachingAssignmentTeacher).join(TeachingAssignment, TeachingAssignment.id == TeachingAssignmentTeacher.teaching_assignment_id).where(TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teacher_id == source.id, TeachingAssignment.school_id == school_id)))
    moved = 0
    for link in links:
        duplicate = db.scalar(select(TeachingAssignmentTeacher).where(TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teaching_assignment_id == link.teaching_assignment_id, TeachingAssignmentTeacher.teacher_id == target.id))
        if duplicate is not None:
            db.delete(link)
        else:
            link.teacher_id = target.id
            moved += 1
    project = _project(db, tenant_id, school_id)
    source_rules = list(db.scalars(select(SchedulingRule).where(SchedulingRule.tenant_id == tenant_id, SchedulingRule.timetable_project_id == project.id, SchedulingRule.selector["teacher_id"].as_string() == str(source.id))))
    for rule in source_rules:
        rule.selector = {**rule.selector, "teacher_id": str(target.id)}
    membership = db.scalar(select(TeacherSchoolMembership).where(TeacherSchoolMembership.tenant_id == tenant_id, TeacherSchoolMembership.school_id == school_id, TeacherSchoolMembership.teacher_id == source.id))
    if membership is not None:
        db.delete(membership)
    db.commit()
    repaired = deduplicate_teacher_assignments(db, tenant_id, school_id, target.id)
    return {"source_name": source.name_ar, "target_name": target.name_ar, "moved_assignments": moved, "removed_duplicates": repaired["removed"]}


def _save_order(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, key: str, payload: OrderedIdsInput) -> dict[str, Any]:
    project = _project(db, tenant_id, school_id)
    project.settings = {**(project.settings or {}), key: [str(item) for item in payload.ids]}
    db.commit()
    return {"saved": len(payload.ids)}


def save_teacher_order(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: OrderedIdsInput) -> dict[str, Any]:
    valid = set(db.scalars(select(TeacherSchoolMembership.teacher_id).where(TeacherSchoolMembership.tenant_id == tenant_id, TeacherSchoolMembership.school_id == school_id, TeacherSchoolMembership.is_active.is_(True))))
    if not set(payload.ids).issubset(valid):
        fail("teacher_not_in_school")
    return _save_order(db, tenant_id, school_id, "core_teacher_order", payload)


def create_simple_teachers(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: BulkTeachersInput) -> dict[str, Any]:
    _school(db, tenant_id, school_id)
    existing = {
        _name_key(name)
        for name in db.scalars(
            select(Teacher.name_ar)
            .join(TeacherSchoolMembership, TeacherSchoolMembership.teacher_id == Teacher.id)
            .where(
                Teacher.tenant_id == tenant_id,
                TeacherSchoolMembership.tenant_id == tenant_id,
                TeacherSchoolMembership.school_id == school_id,
                TeacherSchoolMembership.is_active.is_(True),
            )
        )
    }
    created: list[str] = []
    skipped: list[str] = []
    seen: set[str] = set()
    for raw_name in payload.names:
        name = " ".join(raw_name.split())[:200]
        normalized = _name_key(name)
        similar = _similar_teachers(db, tenant_id, school_id, name)
        if len(name) < 2 or ((normalized in existing or normalized in seen or similar) and not payload.allow_similar):
            if name:
                skipped.append(name)
            continue
        teacher = Teacher(tenant_id=tenant_id, canonical_code=f"AUTO-{uuid.uuid4().hex[:12].upper()}", name_ar=name, base_workload=payload.workload_limit, teaching_workload_limit=payload.workload_limit, is_active=True)
        db.add(teacher)
        db.flush()
        db.add(TeacherSchoolMembership(tenant_id=tenant_id, teacher_id=teacher.id, school_id=school_id, local_employee_code=None, is_home_school=True, is_active=True))
        created.append(name)
        seen.add(normalized)
    db.commit()
    return {"created": len(created), "skipped": len(skipped), "names": created, "skipped_names": skipped}


def save_curriculum_plan(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: CurriculumPlanInput) -> dict[str, Any]:
    _school(db, tenant_id, school_id)
    saved = 0
    for cell in payload.cells:
        grade = db.scalar(select(Grade).join(Stage, Stage.id == Grade.stage_id).where(Grade.id == cell.grade_id, Grade.tenant_id == tenant_id, Stage.school_id == school_id))
        subject = db.scalar(select(Subject).where(Subject.id == cell.subject_id, Subject.tenant_id == tenant_id, Subject.school_id == school_id))
        if grade is None or subject is None:
            fail("curriculum_cell_not_in_school")
        row = db.scalar(select(CurriculumRequirement).where(CurriculumRequirement.tenant_id == tenant_id, CurriculumRequirement.school_id == school_id, CurriculumRequirement.grade_id == cell.grade_id, CurriculumRequirement.subject_id == cell.subject_id))
        if cell.weekly_occurrences == 0:
            if row is not None:
                db.delete(row)
            continue
        if row is None:
            row = CurriculumRequirement(tenant_id=tenant_id, school_id=school_id, grade_id=cell.grade_id, subject_id=cell.subject_id, weekly_occurrences=cell.weekly_occurrences, notes=None)
            db.add(row)
        else:
            row.weekly_occurrences = cell.weekly_occurrences
        saved += 1
    db.commit()
    return {"saved": saved}


def create_simple_subject(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: SimpleSubjectInput) -> dict[str, Any]:
    _school(db, tenant_id, school_id)
    existing = db.scalar(select(Subject).where(Subject.tenant_id == tenant_id, Subject.school_id == school_id, Subject.name_ar == payload.name_ar))
    if existing is not None:
        existing.is_active = True
        db.commit()
        return {"id": existing.id, "name_ar": existing.name_ar}
    subject = Subject(tenant_id=tenant_id, school_id=school_id, code=f"AUTO-{uuid.uuid4().hex[:10].upper()}", name_ar=payload.name_ar, is_active=True)
    db.add(subject)
    db.commit()
    return {"id": subject.id, "name_ar": subject.name_ar}


def update_simple_subject(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, subject_id: uuid.UUID, payload: SimpleSubjectInput) -> dict[str, Any]:
    subject = db.scalar(select(Subject).where(Subject.id == subject_id, Subject.tenant_id == tenant_id, Subject.school_id == school_id, Subject.is_active.is_(True)))
    if subject is None:
        fail("subject_not_in_school", 404)
    name = " ".join(payload.name_ar.split())
    duplicate = db.scalar(select(Subject).where(Subject.tenant_id == tenant_id, Subject.school_id == school_id, Subject.id != subject_id, Subject.name_ar == name, Subject.is_active.is_(True)))
    if duplicate is not None:
        fail("subject_name_exists", 409)
    subject.name_ar = name
    db.commit()
    return {"id": subject.id, "name_ar": subject.name_ar}


def delete_simple_subject(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, subject_id: uuid.UUID) -> None:
    subject = db.scalar(select(Subject).where(Subject.id == subject_id, Subject.tenant_id == tenant_id, Subject.school_id == school_id, Subject.is_active.is_(True)))
    if subject is None:
        fail("subject_not_in_school", 404)
    assignments = list(db.scalars(select(TeachingAssignment).where(TeachingAssignment.tenant_id == tenant_id, TeachingAssignment.school_id == school_id, TeachingAssignment.subject_id == subject_id)))
    if assignments:
        fail("subject_has_assignments", 409)
    subject.is_active = False
    db.commit()


def save_subject_order(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: OrderedIdsInput) -> dict[str, Any]:
    valid = set(db.scalars(select(Subject.id).where(Subject.tenant_id == tenant_id, Subject.school_id == school_id, Subject.is_active.is_(True))))
    if not set(payload.ids).issubset(valid):
        fail("subject_not_in_school")
    return _save_order(db, tenant_id, school_id, "core_subject_order", payload)


def update_simple_section(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, section_id: uuid.UUID, payload: SimpleSectionInput) -> dict[str, Any]:
    section = db.scalar(select(Section).join(Grade, Grade.id == Section.grade_id).join(Stage, Stage.id == Grade.stage_id).where(Section.id == section_id, Section.tenant_id == tenant_id, Stage.school_id == school_id))
    if section is None:
        fail("section_not_in_school", 404)
    name = " ".join(payload.name_ar.split())
    duplicate = db.scalar(select(Section).where(Section.tenant_id == tenant_id, Section.grade_id == section.grade_id, Section.id != section_id, Section.name_ar == name))
    if duplicate is not None:
        fail("section_name_exists", 409)
    section.name_ar = name
    db.commit()
    return {"id": section.id, "name_ar": section.name_ar}


def delete_simple_section(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, section_id: uuid.UUID) -> None:
    section = db.scalar(select(Section).join(Grade, Grade.id == Section.grade_id).join(Stage, Stage.id == Grade.stage_id).where(Section.id == section_id, Section.tenant_id == tenant_id, Stage.school_id == school_id))
    if section is None:
        fail("section_not_in_school", 404)
    offerings = list(db.scalars(select(SectionOffering).where(SectionOffering.tenant_id == tenant_id, SectionOffering.school_id == school_id, SectionOffering.section_id == section_id)))
    _detach_section_assignments(db, tenant_id, offerings)
    for offering in offerings:
        offering.is_active = False
    db.commit()


def save_section_order(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: OrderedIdsInput) -> dict[str, Any]:
    valid = set(db.scalars(select(Section.id).join(Grade, Grade.id == Section.grade_id).join(Stage, Stage.id == Grade.stage_id).where(Section.tenant_id == tenant_id, Stage.school_id == school_id)))
    if not set(payload.ids).issubset(valid):
        fail("section_not_in_school")
    return _save_order(db, tenant_id, school_id, "core_section_order", payload)


def save_availability(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, teacher_id: uuid.UUID, payload: TeacherAvailabilityInput) -> dict[str, Any]:
    teacher = _teacher_in_school(db, tenant_id, school_id, teacher_id)
    project = _project(db, tenant_id, school_id)
    db.execute(delete(SchedulingRule).where(SchedulingRule.tenant_id == tenant_id, SchedulingRule.timetable_project_id == project.id, SchedulingRule.selector["teacher_id"].as_string() == str(teacher_id), SchedulingRule.label.like(f"{CORE_RULE_PREFIX} توفر%")))
    for cell in payload.cells:
        if cell.state == "available":
            continue
        hard = cell.state == "unavailable"
        db.add(SchedulingRule(tenant_id=tenant_id, timetable_project_id=project.id, label=f"{CORE_RULE_PREFIX} توفر {teacher.name_ar}", description="حفظ من شبكة توفر المعلم", rule_type="teacher_unavailable" if hard else "teacher_avoided_time", severity="hard" if hard else "soft", weight=None if hard else 40, selector={"teacher_id": str(teacher_id)}, parameters={"weekday_index": cell.weekday_index, "period_numbers": [cell.period_number]}, enabled=True))
    db.commit()
    return {"teacher_name": teacher.name_ar, "cells": [cell.model_dump() for cell in payload.cells]}


def copy_availability(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: AvailabilityCopyInput) -> dict[str, Any]:
    _teacher_in_school(db, tenant_id, school_id, payload.source_teacher_id)
    project = _project(db, tenant_id, school_id)
    source_rules = list(db.scalars(select(SchedulingRule).where(SchedulingRule.tenant_id == tenant_id, SchedulingRule.timetable_project_id == project.id, SchedulingRule.selector["teacher_id"].as_string() == str(payload.source_teacher_id), SchedulingRule.label.like(f"{CORE_RULE_PREFIX}%"))))
    for target_id in payload.target_teacher_ids:
        teacher = _teacher_in_school(db, tenant_id, school_id, target_id)
        db.execute(delete(SchedulingRule).where(SchedulingRule.tenant_id == tenant_id, SchedulingRule.timetable_project_id == project.id, SchedulingRule.selector["teacher_id"].as_string() == str(target_id), SchedulingRule.label.like(f"{CORE_RULE_PREFIX}%")))
        for source in source_rules:
            db.add(SchedulingRule(tenant_id=tenant_id, timetable_project_id=project.id, label=f"{CORE_RULE_PREFIX} منسوخ إلى {teacher.name_ar}", description=source.description, rule_type=source.rule_type, severity=source.severity, weight=source.weight, selector={**source.selector, "teacher_id": str(target_id)}, parameters=source.parameters, enabled=source.enabled))
    db.commit()
    return {"copied_to": len(payload.target_teacher_ids)}


def quick_assignment(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: QuickAssignmentInput) -> dict[str, Any]:
    _, default_term, shift, _ = _foundation(db, tenant_id, school_id)
    term_id = payload.term_id or default_term.id
    teacher = _teacher_in_school(db, tenant_id, school_id, payload.teacher_id)
    selected_sections = ([payload.section_id] if payload.section_id else []) + payload.section_ids
    for section_id in selected_sections:
        if _assignment_conflict(
            db, tenant_id, school_id, term_id, payload.subject_id, section_id
        ) is not None:
            fail("section_subject_already_assigned", 409)
    projected = _teacher_workload(db, tenant_id, school_id, term_id, payload.teacher_id) + (
        len(selected_sections) * payload.weekly_occurrences
    )
    _require_workload_capacity(teacher, projected, payload.allow_overload)
    results = []
    for section_id in selected_sections:
        offering = db.scalar(select(SectionOffering).where(SectionOffering.tenant_id == tenant_id, SectionOffering.school_id == school_id, SectionOffering.term_id == term_id, SectionOffering.section_id == section_id))
        if offering is None:
            offering = SectionOffering(tenant_id=tenant_id, school_id=school_id, term_id=term_id, section_id=section_id, shift_id=shift.id, is_active=True)
            db.add(offering)
            db.flush()
        results.append(save_assignment(db, tenant_id, school_id, {"term_id": term_id, "subject_id": payload.subject_id, "weekly_occurrences": payload.weekly_occurrences, "teacher_ids": [payload.teacher_id], "section_offering_ids": [offering.id], "resource_ids": [], "notes": "إسناد من المسار الأساسي"}, commit_changes=False))
    db.commit()
    workload = int(db.scalar(select(func.coalesce(func.sum(TeachingAssignment.weekly_occurrences), 0)).join(TeachingAssignmentTeacher, TeachingAssignmentTeacher.teaching_assignment_id == TeachingAssignment.id).where(TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teacher_id == payload.teacher_id, TeachingAssignment.school_id == school_id, TeachingAssignment.term_id == term_id)) or 0)
    return {"assignment_ids": [result["assignment_id"] for result in results], "teacher_name": teacher.name_ar if teacher else "", "assigned": workload, "limit": teacher.teaching_workload_limit if teacher else 0}


def _quick_assignment_record(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    assignment_id: uuid.UUID,
) -> TeachingAssignment:
    assignment = db.scalar(
        select(TeachingAssignment).where(
            TeachingAssignment.id == assignment_id,
            TeachingAssignment.tenant_id == tenant_id,
            TeachingAssignment.school_id == school_id,
        )
    )
    if assignment is None:
        fail("assignment_not_in_school", 404)
    return assignment


def update_quick_assignment(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    assignment_id: uuid.UUID,
    payload: QuickAssignmentInput,
) -> dict[str, Any]:
    assignment = _quick_assignment_record(db, tenant_id, school_id, assignment_id)
    _, default_term, shift, _ = _foundation(db, tenant_id, school_id)
    term_id = payload.term_id or default_term.id
    teacher = _teacher_in_school(db, tenant_id, school_id, payload.teacher_id)
    selected_sections = ([payload.section_id] if payload.section_id else []) + payload.section_ids
    if len(selected_sections) != 1:
        fail("single_section_required_for_edit")
    section_id = selected_sections[0]
    if _assignment_conflict(
        db,
        tenant_id,
        school_id,
        term_id,
        payload.subject_id,
        section_id,
        exclude_assignment_ids={assignment.id},
    ) is not None:
        fail("section_subject_already_assigned", 409)
    linked_teacher_ids = set(
        db.scalars(
            select(TeachingAssignmentTeacher.teacher_id).where(
                TeachingAssignmentTeacher.tenant_id == tenant_id,
                TeachingAssignmentTeacher.teaching_assignment_id == assignment.id,
            )
        )
    )
    projected = _teacher_workload(db, tenant_id, school_id, term_id, payload.teacher_id)
    if payload.teacher_id in linked_teacher_ids:
        projected -= assignment.weekly_occurrences
    projected += payload.weekly_occurrences
    _require_workload_capacity(teacher, projected, payload.allow_overload)
    offering = db.scalar(
        select(SectionOffering).where(
            SectionOffering.tenant_id == tenant_id,
            SectionOffering.school_id == school_id,
            SectionOffering.term_id == term_id,
            SectionOffering.section_id == section_id,
        )
    )
    if offering is None:
        offering = SectionOffering(
            tenant_id=tenant_id,
            school_id=school_id,
            term_id=term_id,
            section_id=section_id,
            shift_id=shift.id,
            is_active=True,
        )
        db.add(offering)
        db.flush()
    return save_assignment(
        db,
        tenant_id,
        school_id,
        {
            "term_id": term_id,
            "subject_id": payload.subject_id,
            "weekly_occurrences": payload.weekly_occurrences,
            "teacher_ids": [payload.teacher_id],
            "section_offering_ids": [offering.id],
            "resource_ids": [],
            "notes": assignment.notes or "إسناد من المسار الأساسي",
        },
        assignment_id=assignment.id,
    )


def remove_quick_assignment(
    db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, assignment_id: uuid.UUID
) -> None:
    assignment = _quick_assignment_record(db, tenant_id, school_id, assignment_id)
    _remove_assignment_from_current(db, tenant_id, school_id, assignment)
    db.commit()


def transfer_assignments(
    db: Session,
    tenant_id: uuid.UUID,
    school_id: uuid.UUID,
    payload: AssignmentTransferInput,
) -> dict[str, Any]:
    _teacher_in_school(db, tenant_id, school_id, payload.source_teacher_id)
    target_teacher = _teacher_in_school(db, tenant_id, school_id, payload.target_teacher_id)
    query = (
        select(TeachingAssignment)
        .join(
            TeachingAssignmentTeacher,
            TeachingAssignmentTeacher.teaching_assignment_id == TeachingAssignment.id,
        )
        .where(
            TeachingAssignment.tenant_id == tenant_id,
            TeachingAssignment.school_id == school_id,
            TeachingAssignmentTeacher.teacher_id == payload.source_teacher_id,
        )
    )
    if payload.assignment_ids:
        query = query.where(TeachingAssignment.id.in_(payload.assignment_ids))
    assignments = list(db.scalars(query).unique())
    if not assignments:
        fail("assignments_required")
    assignment_keys = [
        (
            _assignment_subject_key(db, tenant_id, assignment),
            _assignment_section_key(db, tenant_id, assignment.id),
        )
        for assignment in assignments
    ]
    if len(assignment_keys) != len(set(assignment_keys)):
        fail("duplicate_assignments_repair_first", 409)
    moving_ids = {assignment.id for assignment in assignments}
    for assignment in assignments:
        section_ids = list(
            db.scalars(
                select(SectionOffering.section_id)
                .join(
                    TeachingAssignmentSection,
                    TeachingAssignmentSection.section_offering_id == SectionOffering.id,
                )
                .where(
                    TeachingAssignmentSection.tenant_id == tenant_id,
                    TeachingAssignmentSection.teaching_assignment_id == assignment.id,
                )
            )
        )
        for section_id in section_ids:
            if _assignment_conflict(
                db,
                tenant_id,
                school_id,
                assignment.term_id,
                assignment.subject_id,
                section_id,
                exclude_assignment_ids=moving_ids,
            ) is not None:
                fail("section_subject_already_assigned", 409)
    projected = _teacher_workload(
        db, tenant_id, school_id, assignments[0].term_id, payload.target_teacher_id
    ) + sum(
        assignment.weekly_occurrences
        for assignment in assignments
        if payload.target_teacher_id
        not in set(
            db.scalars(
                select(TeachingAssignmentTeacher.teacher_id).where(
                    TeachingAssignmentTeacher.tenant_id == tenant_id,
                    TeachingAssignmentTeacher.teaching_assignment_id == assignment.id,
                )
            )
        )
    )
    _require_workload_capacity(target_teacher, projected, payload.allow_overload)
    changed = 0
    for assignment in assignments:
        teacher_ids = list(
            db.scalars(
                select(TeachingAssignmentTeacher.teacher_id).where(
                    TeachingAssignmentTeacher.tenant_id == tenant_id,
                    TeachingAssignmentTeacher.teaching_assignment_id == assignment.id,
                )
            )
        )
        offering_ids = list(
            db.scalars(
                select(TeachingAssignmentSection.section_offering_id).where(
                    TeachingAssignmentSection.tenant_id == tenant_id,
                    TeachingAssignmentSection.teaching_assignment_id == assignment.id,
                )
            )
        )
        resource_ids = list(
            db.scalars(
                select(TeachingAssignmentResource.resource_id).where(
                    TeachingAssignmentResource.tenant_id == tenant_id,
                    TeachingAssignmentResource.teaching_assignment_id == assignment.id,
                )
            )
        )
        next_teachers = list(
            dict.fromkeys(
                payload.target_teacher_id if item == payload.source_teacher_id else item
                for item in teacher_ids
            )
        )
        save_assignment(
            db,
            tenant_id,
            school_id,
            {
                "term_id": assignment.term_id,
                "subject_id": assignment.subject_id,
                "weekly_occurrences": assignment.weekly_occurrences,
                "teacher_ids": next_teachers,
                "section_offering_ids": offering_ids,
                "resource_ids": resource_ids,
                "notes": assignment.notes,
            },
            assignment_id=assignment.id,
            commit_changes=False,
        )
        changed += 1
    db.commit()
    return {"changed": changed, "mode": payload.mode}


def save_preset_rule(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: PresetRuleInput) -> dict[str, Any]:
    project = _project(db, tenant_id, school_id)
    preset = payload.preset
    selector: dict[str, Any]
    parameters: dict[str, Any]
    severity = "hard"
    weight: int | None = None
    if preset in {"no_first_period", "no_thursday", "selected_days_only", "first_four_only", "max_daily", "max_consecutive", "prefer_free_day"}:
        if payload.teacher_id is None:
            fail("teacher_required")
        teacher = _teacher_in_school(db, tenant_id, school_id, payload.teacher_id)
        selector = {"teacher_id": str(teacher.id)}
    else:
        if payload.assignment_id is None:
            fail("assignment_required")
        selector = {"assignment_id": str(payload.assignment_id)}
    labels = {
        "no_first_period": "لا تعطه الحصة الأولى", "no_thursday": "لا يعمل يوم الخميس",
        "selected_days_only": "يعمل في الأيام المحددة فقط", "first_four_only": "يعمل أول أربع حصص فقط", "max_daily": "حد الحصص اليومي",
        "max_consecutive": "حد الحصص المتتالية", "prefer_free_day": "يفضل يومًا فارغًا",
        "spread_assignment": "وزع المادة على عدة أيام", "consecutive_assignment": "اجعل الحصتين متتاليتين",
        "assignment_before": "مادة قبل مادة",
    }
    rule_type = "teacher_unavailable"
    parameters = {}
    rules: list[tuple[str, dict[str, Any]]] = []
    if preset == "no_first_period":
        parameters = {"period_numbers": [1]}
    elif preset == "no_thursday":
        parameters = {"weekday_index": 4}
    elif preset == "selected_days_only":
        for day in sorted(set(range(5)) - set(payload.weekdays)):
            rules.append(("teacher_unavailable", {"weekday_index": day}))
    elif preset == "first_four_only":
        parameters = {"period_numbers": list(range(5, 21))}
    elif preset == "max_daily":
        rule_type, parameters = "teacher_max_lessons_per_day", {"maximum": payload.value or 4}
    elif preset == "max_consecutive":
        rule_type, parameters = "teacher_max_consecutive_lessons", {"maximum": payload.value or 3}
    elif preset == "prefer_free_day":
        rule_type, parameters, severity, weight = "teacher_avoided_time", {"weekday_index": payload.weekdays[0] if payload.weekdays else 4}, "soft", 35
    elif preset == "spread_assignment":
        rule_type, parameters = "assignment_min_days", {"minimum_days": payload.value or 4}
    elif preset == "consecutive_assignment":
        rule_type, parameters = "assignment_require_consecutive_block", {"block_size": payload.value or 2}
    elif preset == "assignment_before":
        if payload.second_assignment_id is None:
            fail("second_assignment_required")
        rule_type, selector = "assignment_before_assignment", {"assignment_ids": [str(payload.assignment_id), str(payload.second_assignment_id)]}
    rules = rules or [(rule_type, parameters)]
    for kind, params in rules:
        db.add(SchedulingRule(tenant_id=tenant_id, timetable_project_id=project.id, label=f"{CORE_RULE_PREFIX} {labels[preset]}", description="قاعدة جاهزة من المسار الأساسي", rule_type=kind, severity=severity, weight=weight, selector=selector, parameters=params, enabled=True))
    db.commit()
    return {"label": labels[preset], "created": len(rules)}


def workflow_snapshot(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID) -> dict[str, Any]:
    school = _school(db, tenant_id, school_id)
    _, term, shift, pattern = _foundation(db, tenant_id, school_id)
    project = _project(db, tenant_id, school_id)
    # The simplified route initializes hidden foundation records for a new school once.
    db.commit()
    days = list(db.scalars(select(SchoolDay).where(SchoolDay.tenant_id == tenant_id, SchoolDay.school_id == school_id, SchoolDay.shift_id == shift.id, SchoolDay.week_pattern_id == pattern.id, SchoolDay.enabled.is_(True)).order_by(SchoolDay.weekday_index)))
    first_day = days[0] if days else None
    blocks = list(db.scalars(select(PeriodTemplate).where(PeriodTemplate.tenant_id == tenant_id, PeriodTemplate.school_day_id == first_day.id).order_by(PeriodTemplate.block_order))) if first_day else []
    stages = list(db.scalars(select(Stage).where(Stage.tenant_id == tenant_id, Stage.school_id == school_id).order_by(Stage.order)))
    grades = list(db.scalars(select(Grade).where(Grade.tenant_id == tenant_id, Grade.stage_id.in_([x.id for x in stages])).order_by(Grade.order))) if stages else []
    settings = project.settings or {}
    sections = list(db.scalars(select(Section).join(SectionOffering, SectionOffering.section_id == Section.id).where(Section.tenant_id == tenant_id, Section.grade_id.in_([x.id for x in grades]), SectionOffering.tenant_id == tenant_id, SectionOffering.school_id == school_id, SectionOffering.term_id == term.id, SectionOffering.is_active.is_(True)).order_by(Section.name_ar))) if grades else []
    sections = _ordered(sections, settings.get("core_section_order", []), lambda row: row.name_ar)
    teachers = list(db.execute(select(Teacher, TeacherSchoolMembership).join(TeacherSchoolMembership, TeacherSchoolMembership.teacher_id == Teacher.id).where(Teacher.tenant_id == tenant_id, TeacherSchoolMembership.tenant_id == tenant_id, TeacherSchoolMembership.school_id == school_id, TeacherSchoolMembership.is_active.is_(True)).order_by(Teacher.name_ar)).all())
    teacher_positions = {value: index for index, value in enumerate(settings.get("core_teacher_order", []))}
    teachers.sort(key=lambda row: (teacher_positions.get(str(row[0].id), len(teacher_positions)), _name_key(row[0].name_ar)))
    teacher_rows = []
    for teacher, membership in teachers:
        assigned = int(db.scalar(select(func.coalesce(func.sum(TeachingAssignment.weekly_occurrences), 0)).join(TeachingAssignmentTeacher, TeachingAssignmentTeacher.teaching_assignment_id == TeachingAssignment.id).where(TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teacher_id == teacher.id, TeachingAssignment.school_id == school_id, TeachingAssignment.term_id == term.id)) or 0)
        teacher_rows.append({"id": teacher.id, "name_ar": teacher.name_ar, "workload_limit": teacher.teaching_workload_limit, "assigned": assigned, "remaining": teacher.teaching_workload_limit - assigned, "shared": not membership.is_home_school})
    subjects = list(db.scalars(select(Subject).where(Subject.tenant_id == tenant_id, Subject.school_id == school_id, Subject.is_active.is_(True))))
    subjects = _ordered(subjects, settings.get("core_subject_order", []), _ministry_subject_rank)
    requirements = list(db.scalars(select(CurriculumRequirement).where(CurriculumRequirement.tenant_id == tenant_id, CurriculumRequirement.school_id == school_id)))
    assignments = list(db.scalars(select(TeachingAssignment).where(TeachingAssignment.tenant_id == tenant_id, TeachingAssignment.school_id == school_id, TeachingAssignment.term_id == term.id)))
    rules = list(db.scalars(select(SchedulingRule).where(SchedulingRule.tenant_id == tenant_id, SchedulingRule.timetable_project_id == project.id, SchedulingRule.enabled.is_(True))))
    for teacher_row in teacher_rows:
        cells = []
        for rule in rules:
            if str(rule.selector.get("teacher_id", "")) != str(teacher_row["id"]) or rule.rule_type not in {"teacher_unavailable", "teacher_avoided_time"}:
                continue
            for period_number in rule.parameters.get("period_numbers", []):
                if "weekday_index" in rule.parameters:
                    cells.append({"weekday_index": rule.parameters["weekday_index"], "period_number": period_number, "state": "unavailable" if rule.rule_type == "teacher_unavailable" else "avoid"})
        teacher_row["availability"] = cells
    assignment_rows = []
    for assignment in assignments:
        subject = next((item for item in subjects if item.id == assignment.subject_id), None)
        teacher_ids = list(db.scalars(select(TeachingAssignmentTeacher.teacher_id).where(TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teaching_assignment_id == assignment.id)))
        offering_ids = list(db.scalars(select(TeachingAssignmentSection.section_offering_id).where(TeachingAssignmentSection.tenant_id == tenant_id, TeachingAssignmentSection.teaching_assignment_id == assignment.id)))
        offerings = list(db.scalars(select(SectionOffering).where(SectionOffering.id.in_(offering_ids)))) if offering_ids else []
        assignment_sections = list(db.scalars(select(Section).where(Section.id.in_([item.section_id for item in offerings])))) if offerings else []
        assignment_grades = {
            grade.id: grade
            for grade in db.scalars(
                select(Grade).where(Grade.id.in_([section.grade_id for section in assignment_sections]))
            )
        }
        if not teacher_ids:
            continue
        assignment_rows.append(
            {
                "id": assignment.id,
                "subject_id": assignment.subject_id,
                "subject_name": subject.name_ar if subject else "",
                "teacher_ids": teacher_ids,
                "teacher_names": [
                    teacher.name_ar for teacher, _ in teachers if teacher.id in teacher_ids
                ],
                "section_ids": [section.id for section in assignment_sections],
                "section_names": [
                    section.name_ar
                    if not (grade := assignment_grades.get(section.grade_id))
                    or grade.name_ar in section.name_ar
                    else f"{grade.name_ar} {section.name_ar}"
                    for section in assignment_sections
                ],
                "weekly_occurrences": assignment.weekly_occurrences,
            }
        )
    preflight_report = preflight(db, tenant_id, project.id)
    readiness = {"basic_data": bool(days and blocks and sections and teachers and subjects), "assignments": bool(assignment_rows), "constraints": True, "preflight": not preflight_report["errors"]}
    selected_stages = project.settings.get("core_stages") or []
    if not selected_stages:
        stage_text = " ".join(item.name_ar for item in stages)
        grade_text = " ".join(item.name_ar for item in grades)
        if "ابتدائ" in stage_text:
            selected_stages.append("primary")
        if "متوسط" in stage_text or "المتوسط" in grade_text:
            selected_stages.append("intermediate")
        if "ثانو" in stage_text or "الثانوي" in grade_text:
            selected_stages.append("secondary")
    if not selected_stages:
        selected_stages = ["primary"]
    return {"school": {"name_ar": school.name_ar}, "selected_stages": selected_stages, "term_id": term.id, "project_id": project.id, "weekdays": [day.weekday_index for day in days], "blocks": blocks, "stages": stages, "grades": grades, "sections": sections, "teachers": teacher_rows, "subjects": subjects, "curriculum": [{"id": row.id, "grade_id": row.grade_id, "subject_id": row.subject_id, "weekly_occurrences": row.weekly_occurrences} for row in requirements], "assignments": assignment_rows, "assignments_count": len(assignment_rows), "rules_count": len(rules), "readiness": readiness}


def generate(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: GenerateInput) -> dict[str, Any]:
    project = _project(db, tenant_id, school_id)
    report = preflight(db, tenant_id, project.id)
    partial_codes = {"section_capacity_shortage", "teacher_capacity_shortage", "resource_structural_shortage", "occurrence_without_candidate_slot"}
    blocking = [item for item in report["diagnostics"] if item.get("severity") == "error" and item.get("code") not in partial_codes]
    if blocking:
        return {"started": False, "project_id": project.id, "preflight": report}
    custom_weights = project.settings.get("optimization_weights") or {"teacher_gaps": 8, "first_period_fairness": 5, "last_period_fairness": 5, "teaching_streaks": 7}
    run = create_solve_run(db, tenant_id, project.id, SolveRequest(candidate_count=3, time_limit_seconds=10, seed=0, optimization_profile=payload.optimization_profile, optimization_weights=custom_weights if payload.optimization_profile == "custom" else {}, allow_partial=True))
    return {"started": True, "partial": bool(report["errors"]), "project_id": project.id, "run_id": run.id, "preflight": report}

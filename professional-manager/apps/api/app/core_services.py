from __future__ import annotations

import uuid
from datetime import date, time
from typing import Any, NoReturn

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.assignment_services import save_assignment
from app.core_schemas import (
    AvailabilityCopyInput,
    BulkTeachersInput,
    DayBuilderInput,
    GenerateInput,
    PeriodEditInput,
    PresetRuleInput,
    QuickAssignmentInput,
    SimpleSubjectInput,
    SimpleTeacherInput,
    StructureInput,
    TeacherAvailabilityInput,
)
from app.models import (
    AcademicYear,
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
    TeachingAssignmentSection,
    TeachingAssignmentTeacher,
    Term,
    TimetableProject,
    TimetableProjectSchool,
    WeekPattern,
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
        existing = list(db.scalars(select(Section).where(Section.tenant_id == tenant_id, Section.grade_id == grade.id).order_by(Section.name_ar)))
        for index in range(len(existing), requested[grade_name]):
            suffix = SECTION_LETTERS[index] if index < len(SECTION_LETTERS) else str(index + 1)
            section = Section(tenant_id=tenant_id, grade_id=grade.id, name_ar=f"{grade_name} {suffix}", capacity=None)
            db.add(section)
            db.flush()
            existing.append(section)
        for section in existing[: requested[grade_name]]:
            offering = db.scalar(select(SectionOffering).where(SectionOffering.tenant_id == tenant_id, SectionOffering.school_id == school_id, SectionOffering.term_id == term.id, SectionOffering.section_id == section.id))
            if offering is None:
                db.add(SectionOffering(tenant_id=tenant_id, school_id=school_id, term_id=term.id, section_id=section.id, shift_id=shift.id, is_active=True))
            else:
                offering.is_active = True
        for section in existing[requested[grade_name] :]:
            offering = db.scalar(select(SectionOffering).where(SectionOffering.tenant_id == tenant_id, SectionOffering.school_id == school_id, SectionOffering.term_id == term.id, SectionOffering.section_id == section.id))
            if offering is not None:
                offering.is_active = False
        created.append({"grade_name": grade_name, "sections": [section.name_ar for section in existing[: requested[grade_name]]]})
    db.commit()
    return {"stage": stage_name, "grades": created}


def _teacher_in_school(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, teacher_id: uuid.UUID) -> Teacher:
    teacher = db.scalar(select(Teacher).join(TeacherSchoolMembership, TeacherSchoolMembership.teacher_id == Teacher.id).where(Teacher.id == teacher_id, Teacher.tenant_id == tenant_id, TeacherSchoolMembership.tenant_id == tenant_id, TeacherSchoolMembership.school_id == school_id, TeacherSchoolMembership.is_active.is_(True)))
    if teacher is None:
        fail("teacher_not_in_school", 404)
    return teacher


def create_simple_teacher(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: SimpleTeacherInput) -> dict[str, Any]:
    _school(db, tenant_id, school_id)
    teacher = Teacher(tenant_id=tenant_id, canonical_code=f"AUTO-{uuid.uuid4().hex[:12].upper()}", name_ar=payload.name_ar, base_workload=payload.workload_limit, teaching_workload_limit=payload.workload_limit, is_active=True)
    db.add(teacher)
    db.flush()
    db.add(TeacherSchoolMembership(tenant_id=tenant_id, teacher_id=teacher.id, school_id=school_id, local_employee_code=None, is_home_school=True, is_active=True))
    db.commit()
    return {"id": teacher.id, "name_ar": teacher.name_ar, "workload_limit": teacher.teaching_workload_limit}


def create_simple_teachers(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: BulkTeachersInput) -> dict[str, Any]:
    _school(db, tenant_id, school_id)
    existing = {
        name.strip().casefold()
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
        normalized = name.casefold()
        if len(name) < 2 or normalized in existing or normalized in seen:
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
    return {"created": len(created), "skipped": len(skipped), "names": created}


def create_simple_subject(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: SimpleSubjectInput) -> dict[str, Any]:
    _school(db, tenant_id, school_id)
    existing = db.scalar(select(Subject).where(Subject.tenant_id == tenant_id, Subject.school_id == school_id, Subject.name_ar == payload.name_ar))
    if existing is not None:
        return {"id": existing.id, "name_ar": existing.name_ar}
    subject = Subject(tenant_id=tenant_id, school_id=school_id, code=f"AUTO-{uuid.uuid4().hex[:10].upper()}", name_ar=payload.name_ar, is_active=True)
    db.add(subject)
    db.commit()
    return {"id": subject.id, "name_ar": subject.name_ar}


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
    _teacher_in_school(db, tenant_id, school_id, payload.teacher_id)
    selected_sections = ([payload.section_id] if payload.section_id else []) + payload.section_ids
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
    teacher = db.get(Teacher, payload.teacher_id)
    return {"assignment_ids": [result["assignment_id"] for result in results], "teacher_name": teacher.name_ar if teacher else "", "assigned": workload, "limit": teacher.teaching_workload_limit if teacher else 0}


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
    sections = list(db.scalars(select(Section).join(SectionOffering, SectionOffering.section_id == Section.id).where(Section.tenant_id == tenant_id, Section.grade_id.in_([x.id for x in grades]), SectionOffering.tenant_id == tenant_id, SectionOffering.school_id == school_id, SectionOffering.term_id == term.id, SectionOffering.is_active.is_(True)).order_by(Section.name_ar))) if grades else []
    teachers = list(db.execute(select(Teacher, TeacherSchoolMembership).join(TeacherSchoolMembership, TeacherSchoolMembership.teacher_id == Teacher.id).where(Teacher.tenant_id == tenant_id, TeacherSchoolMembership.tenant_id == tenant_id, TeacherSchoolMembership.school_id == school_id, TeacherSchoolMembership.is_active.is_(True)).order_by(Teacher.name_ar)).all())
    teacher_rows = []
    for teacher, membership in teachers:
        assigned = int(db.scalar(select(func.coalesce(func.sum(TeachingAssignment.weekly_occurrences), 0)).join(TeachingAssignmentTeacher, TeachingAssignmentTeacher.teaching_assignment_id == TeachingAssignment.id).where(TeachingAssignmentTeacher.tenant_id == tenant_id, TeachingAssignmentTeacher.teacher_id == teacher.id, TeachingAssignment.school_id == school_id, TeachingAssignment.term_id == term.id)) or 0)
        teacher_rows.append({"id": teacher.id, "name_ar": teacher.name_ar, "workload_limit": teacher.teaching_workload_limit, "assigned": assigned, "remaining": teacher.teaching_workload_limit - assigned, "shared": not membership.is_home_school})
    subjects = list(db.scalars(select(Subject).where(Subject.tenant_id == tenant_id, Subject.school_id == school_id, Subject.is_active.is_(True)).order_by(Subject.name_ar)))
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
        assignment_rows.append({"id": assignment.id, "subject_name": subject.name_ar if subject else "", "teacher_names": [teacher.name_ar for teacher, _ in teachers if teacher.id in teacher_ids], "section_names": [section.name_ar for section in assignment_sections], "weekly_occurrences": assignment.weekly_occurrences})
    preflight_report = preflight(db, tenant_id, project.id)
    readiness = {"basic_data": bool(days and blocks and sections and teachers and subjects), "assignments": bool(assignments), "constraints": True, "preflight": not preflight_report["errors"]}
    selected_stages = project.settings.get("core_stages") or ["primary"]
    return {"school": {"name_ar": school.name_ar}, "selected_stages": selected_stages, "term_id": term.id, "project_id": project.id, "weekdays": [day.weekday_index for day in days], "blocks": blocks, "stages": stages, "grades": grades, "sections": sections, "teachers": teacher_rows, "subjects": subjects, "assignments": assignment_rows, "assignments_count": len(assignments), "rules_count": len(rules), "readiness": readiness}


def generate(db: Session, tenant_id: uuid.UUID, school_id: uuid.UUID, payload: GenerateInput) -> dict[str, Any]:
    project = _project(db, tenant_id, school_id)
    report = preflight(db, tenant_id, project.id)
    if report["errors"]:
        return {"started": False, "project_id": project.id, "preflight": report}
    custom_weights = project.settings.get("optimization_weights") or {"teacher_gaps": 8, "first_period_fairness": 5, "last_period_fairness": 5, "teaching_streaks": 7}
    run = create_solve_run(db, tenant_id, project.id, SolveRequest(candidate_count=3, time_limit_seconds=10, seed=0, optimization_profile=payload.optimization_profile, optimization_weights=custom_weights if payload.optimization_profile == "custom" else {}))
    return {"started": True, "project_id": project.id, "run_id": run.id, "preflight": report}

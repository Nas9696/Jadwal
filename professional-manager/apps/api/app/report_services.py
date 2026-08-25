from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.editor_services import _working
from app.models import (
    Grade,
    PeriodTemplate,
    Resource,
    School,
    Section,
    Stage,
    Subject,
    SubstitutionAssignment,
    SubstitutionNeed,
    Teacher,
    TeacherAbsence,
    TeacherSchoolMembership,
    Term,
    TimetableCandidate,
    TimetableEntry,
    TimetableEntryResource,
    TimetableEntrySection,
    TimetableEntryTeacher,
    TimetableProjectSchool,
    TimetableSolveRun,
    WeekPattern,
    WorkingTimetable,
    WorkingTimetableEntry,
    WorkingTimetableEntryResource,
    WorkingTimetableEntrySection,
    WorkingTimetableEntryTeacher,
)
from app.project_services import _project
from app.report_schemas import (
    ReportDataset,
    ReportFilters,
    ReportOption,
    ReportOptions,
    ReportPreviewRequest,
    ReportRow,
    ReportSourceMetadata,
)
from app.substitution_services import workload_summary

WEEKDAYS = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
ATTENDANCE = {"onsite": "حضوري", "remote": "عن بُعد", "hybrid": "مدمج"}
TITLES = {
    "general_timetable": "الجدول العام",
    "section_timetable": "جدول الشعبة",
    "teacher_timetable": "جدول المعلم",
    "subject_timetable": "جدول المادة",
    "resource_timetable": "جدول المورد / المعمل",
    "daily_substitutions": "تقرير البدلاء اليومي",
    "waiting_workload": "تقرير الانتظار والحمولة",
}
NORMAL_COLUMNS = ["الأسبوع", "اليوم", "الوقت", "المدرسة", "المادة", "المعلمون", "الشعب", "المورد", "النمط"]
MAX_REPORT_ROWS = 5000


def report_options(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID
) -> ReportOptions:
    scopes = _scopes(db, tenant, project_id)
    school_ids = [scope.school_id for scope in scopes]
    schools = list(
        db.scalars(
            select(School)
            .where(School.tenant_id == tenant, School.id.in_(school_ids))
            .order_by(School.name_ar)
        )
    )
    memberships = list(
        db.execute(
            select(Teacher, TeacherSchoolMembership.school_id)
            .join(TeacherSchoolMembership, TeacherSchoolMembership.teacher_id == Teacher.id)
            .where(
                Teacher.tenant_id == tenant,
                Teacher.is_active.is_(True),
                TeacherSchoolMembership.tenant_id == tenant,
                TeacherSchoolMembership.school_id.in_(school_ids),
                TeacherSchoolMembership.is_active.is_(True),
            )
            .order_by(Teacher.name_ar)
        )
    )
    teacher_options: dict[uuid.UUID, ReportOption] = {}
    for teacher, school_id in memberships:
        option = teacher_options.setdefault(
            teacher.id, ReportOption(id=teacher.id, label=teacher.name_ar)
        )
        option.school_ids.append(school_id)
    sections = list(
        db.execute(
            select(Section, Stage.school_id)
            .join(Grade, Grade.id == Section.grade_id)
            .join(Stage, Stage.id == Grade.stage_id)
            .where(
                Section.tenant_id == tenant,
                Grade.tenant_id == tenant,
                Stage.tenant_id == tenant,
                Stage.school_id.in_(school_ids),
            )
            .order_by(Section.name_ar)
        )
    )
    subjects = list(
        db.scalars(
            select(Subject)
            .where(Subject.tenant_id == tenant, Subject.school_id.in_(school_ids))
            .order_by(Subject.name_ar)
        )
    )
    resources = list(
        db.scalars(
            select(Resource)
            .where(Resource.tenant_id == tenant, Resource.school_id.in_(school_ids))
            .order_by(Resource.name_ar)
        )
    )
    return ReportOptions(
        schools=[ReportOption(id=row.id, label=row.name_ar, school_id=row.id, school_ids=[row.id]) for row in schools],
        teachers=list(teacher_options.values()),
        sections=[ReportOption(id=row.id, label=row.name_ar, school_id=school_id, school_ids=[school_id]) for row, school_id in sections],
        subjects=[ReportOption(id=row.id, label=row.name_ar, school_id=row.school_id, school_ids=[row.school_id]) for row in subjects],
        resources=[ReportOption(id=row.id, label=row.name_ar, school_id=row.school_id, school_ids=[row.school_id]) for row in resources],
    )


def _scopes(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID
) -> list[TimetableProjectSchool]:
    _project(db, tenant, project_id)
    rows = list(
        db.scalars(
            select(TimetableProjectSchool).where(
                TimetableProjectSchool.tenant_id == tenant,
                TimetableProjectSchool.timetable_project_id == project_id,
            )
        )
    )
    if not rows:
        raise HTTPException(422, detail={"code": "project_has_no_school_scope"})
    return rows


def _source(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    request: ReportPreviewRequest,
) -> tuple[WorkingTimetable | TimetableCandidate, list[Any]]:
    if request.report_type in {"daily_substitutions", "waiting_workload"} and request.source.kind != "working":
        raise HTTPException(422, detail={"code": "operational_report_requires_working_source"})
    if request.source.kind == "working":
        working = _working(db, tenant, project_id)
        if (
            request.source.expected_revision is not None
            and request.source.expected_revision != working.revision
        ):
            raise HTTPException(
                409,
                detail={
                    "code": "report_source_revision_conflict",
                    "current_revision": working.revision,
                },
            )
        entries = list(
            db.scalars(
                select(WorkingTimetableEntry)
                .where(
                    WorkingTimetableEntry.tenant_id == tenant,
                    WorkingTimetableEntry.working_timetable_id == working.id,
                )
                .order_by(
                    WorkingTimetableEntry.project_cycle_week_index,
                    WorkingTimetableEntry.weekday_index,
                    WorkingTimetableEntry.starts_at_minute,
                    WorkingTimetableEntry.id,
                )
            )
        )
        return working, entries
    candidate = db.scalar(
        select(TimetableCandidate)
        .join(TimetableSolveRun, TimetableSolveRun.id == TimetableCandidate.solve_run_id)
        .where(
            TimetableCandidate.id == request.source.candidate_id,
            TimetableCandidate.tenant_id == tenant,
            TimetableSolveRun.tenant_id == tenant,
            TimetableSolveRun.timetable_project_id == project_id,
        )
    )
    if not candidate:
        raise HTTPException(404, detail={"code": "candidate_not_found_in_project"})
    entries = list(
        db.scalars(
            select(TimetableEntry)
            .where(TimetableEntry.tenant_id == tenant, TimetableEntry.candidate_id == candidate.id)
            .order_by(
                TimetableEntry.project_cycle_week_index,
                TimetableEntry.weekday_index,
                TimetableEntry.starts_at_minute,
                TimetableEntry.id,
            )
        )
    )
    return candidate, entries


def _link_map(
    db: Session, entry_field: Any, value_field: Any, entry_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[uuid.UUID]]:
    result: dict[uuid.UUID, list[uuid.UUID]] = {entry_id: [] for entry_id in entry_ids}
    if not entry_ids:
        return result
    for entry_id, value in db.execute(
        select(entry_field, value_field).where(entry_field.in_(entry_ids))
    ):
        result.setdefault(entry_id, []).append(value)
    return result


def _maps(db: Session, tenant: uuid.UUID, source: Any, entries: list[Any]) -> dict[str, Any]:
    entry_ids = [entry.id for entry in entries]
    if isinstance(source, WorkingTimetable):
        teacher_links = _link_map(
            db,
            WorkingTimetableEntryTeacher.working_timetable_entry_id,
            WorkingTimetableEntryTeacher.teacher_id,
            entry_ids,
        )
        section_links = _link_map(
            db,
            WorkingTimetableEntrySection.working_timetable_entry_id,
            WorkingTimetableEntrySection.section_id,
            entry_ids,
        )
        resource_links = _link_map(
            db,
            WorkingTimetableEntryResource.working_timetable_entry_id,
            WorkingTimetableEntryResource.resource_id,
            entry_ids,
        )
    else:
        teacher_links = _link_map(
            db,
            TimetableEntryTeacher.timetable_entry_id,
            TimetableEntryTeacher.teacher_id,
            entry_ids,
        )
        section_links = _link_map(
            db,
            TimetableEntrySection.timetable_entry_id,
            TimetableEntrySection.section_id,
            entry_ids,
        )
        resource_links = _link_map(
            db,
            TimetableEntryResource.timetable_entry_id,
            TimetableEntryResource.resource_id,
            entry_ids,
        )
    teacher_ids = {item for values in teacher_links.values() for item in values}
    section_ids = {item for values in section_links.values() for item in values}
    resource_ids = {item for values in resource_links.values() for item in values}
    subject_ids = {entry.subject_id for entry in entries}
    school_ids = {entry.school_id for entry in entries}
    teachers = {
        row.id: row.name_ar
        for row in db.scalars(
            select(Teacher).where(Teacher.tenant_id == tenant, Teacher.id.in_(teacher_ids))
        )
    }
    sections = {
        row.id: row.name_ar
        for row in db.scalars(
            select(Section).where(Section.tenant_id == tenant, Section.id.in_(section_ids))
        )
    }
    resources = {
        row.id: row.name_ar
        for row in db.scalars(
            select(Resource).where(Resource.tenant_id == tenant, Resource.id.in_(resource_ids))
        )
    }
    subjects = {
        row.id: row.name_ar
        for row in db.scalars(
            select(Subject).where(Subject.tenant_id == tenant, Subject.id.in_(subject_ids))
        )
    }
    schools = {
        row.id: row.name_ar
        for row in db.scalars(
            select(School).where(School.tenant_id == tenant, School.id.in_(school_ids))
        )
    }
    period_ids: set[uuid.UUID] = set()
    for entry in entries:
        try:
            period_ids.add(uuid.UUID(entry.slot_id.split("@project-week-")[0]))
        except ValueError:
            continue
    periods = {
        row.id: row
        for row in db.scalars(
            select(PeriodTemplate).where(
                PeriodTemplate.tenant_id == tenant, PeriodTemplate.id.in_(period_ids)
            )
        )
    }
    pattern_ids = {row.week_pattern_id for row in periods.values()}
    patterns = {
        row.id: row.name_ar
        for row in db.scalars(
            select(WeekPattern).where(
                WeekPattern.tenant_id == tenant, WeekPattern.id.in_(pattern_ids)
            )
        )
    }
    return {
        "teacher_links": teacher_links,
        "section_links": section_links,
        "resource_links": resource_links,
        "teachers": teachers,
        "sections": sections,
        "resources": resources,
        "subjects": subjects,
        "schools": schools,
        "periods": periods,
        "patterns": patterns,
    }


def _metadata(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    source: WorkingTimetable | TimetableCandidate,
    scopes: list[TimetableProjectSchool],
) -> ReportSourceMetadata:
    project = _project(db, tenant, project_id)
    school_ids = [scope.school_id for scope in scopes]
    term_ids = [scope.term_id for scope in scopes]
    schools = list(
        db.scalars(
            select(School)
            .where(School.tenant_id == tenant, School.id.in_(school_ids))
            .order_by(School.name_ar)
        )
    )
    terms = list(
        db.scalars(
            select(Term)
            .where(Term.tenant_id == tenant, Term.id.in_(term_ids))
            .order_by(Term.name_ar)
        )
    )
    return ReportSourceMetadata(
        kind="working" if isinstance(source, WorkingTimetable) else "candidate",
        timetable_id=source.id if isinstance(source, WorkingTimetable) else None,
        candidate_id=(source.source_candidate_id if isinstance(source, WorkingTimetable) else source.id),
        version_number=source.version_number if isinstance(source, WorkingTimetable) else None,
        revision=source.revision if isinstance(source, WorkingTimetable) else None,
        generated_at=datetime.now(UTC),
        project_id=project.id,
        project_name=project.name_ar,
        school_labels=[row.name_ar for row in schools],
        term_labels=[row.name_ar for row in terms],
    )


def _ensure_filters(
    db: Session,
    tenant: uuid.UUID,
    scopes: list[TimetableProjectSchool],
    report_type: str,
    filters: ReportFilters,
) -> None:
    required = {
        "section_timetable": filters.section_id,
        "teacher_timetable": filters.teacher_id,
        "subject_timetable": filters.subject_id,
        "resource_timetable": filters.resource_id,
    }
    if report_type in required and required[report_type] is None:
        raise HTTPException(422, detail={"code": f"{report_type}_filter_required"})
    school_ids = {scope.school_id for scope in scopes}
    if filters.school_id and filters.school_id not in school_ids:
        raise HTTPException(422, detail={"code": "report_school_outside_project"})
    if filters.teacher_id:
        valid = db.scalar(
            select(TeacherSchoolMembership.id).where(
                TeacherSchoolMembership.tenant_id == tenant,
                TeacherSchoolMembership.teacher_id == filters.teacher_id,
                TeacherSchoolMembership.school_id.in_(school_ids),
            )
        )
        if not valid:
            raise HTTPException(422, detail={"code": "report_teacher_outside_project"})
    if filters.section_id:
        valid = db.scalar(
            select(Section.id)
            .join(Grade, Grade.id == Section.grade_id)
            .join(Stage, Stage.id == Grade.stage_id)
            .where(
                Section.id == filters.section_id,
                Section.tenant_id == tenant,
                Grade.tenant_id == tenant,
                Stage.tenant_id == tenant,
                Stage.school_id.in_(school_ids),
            )
        )
        if not valid:
            raise HTTPException(422, detail={"code": "report_section_outside_project"})
    for value, model, code in (
        (filters.subject_id, Subject, "report_subject_outside_project"),
        (filters.resource_id, Resource, "report_resource_outside_project"),
    ):
        if value and not db.scalar(
            select(model.id).where(
                model.id == value, model.tenant_id == tenant, model.school_id.in_(school_ids)
            )
        ):
            raise HTTPException(422, detail={"code": code})


def _normal_rows(entries: list[Any], maps: dict[str, Any], filters: ReportFilters) -> list[ReportRow]:
    rows: list[ReportRow] = []
    for entry in entries:
        teachers = maps["teacher_links"].get(entry.id, [])
        sections = maps["section_links"].get(entry.id, [])
        resources = maps["resource_links"].get(entry.id, [])
        if filters.school_id and entry.school_id != filters.school_id:
            continue
        if filters.teacher_id and filters.teacher_id not in teachers:
            continue
        if filters.section_id and filters.section_id not in sections:
            continue
        if filters.subject_id and entry.subject_id != filters.subject_id:
            continue
        if filters.resource_id and filters.resource_id not in resources:
            continue
        if (
            filters.project_cycle_week_index is not None
            and entry.project_cycle_week_index != filters.project_cycle_week_index
        ):
            continue
        if filters.weekday_index is not None and entry.weekday_index != filters.weekday_index:
            continue
        try:
            period_id = uuid.UUID(entry.slot_id.split("@project-week-")[0])
        except ValueError:
            period_id = None
        period = maps["periods"].get(period_id)
        attendance_mode = period.attendance_mode if period else "onsite"
        rows.append(
            ReportRow(
                row_id=str(entry.id),
                project_cycle_week_index=entry.project_cycle_week_index,
                local_cycle_week_label=(maps["patterns"].get(period.week_pattern_id) if period else None),
                weekday_index=entry.weekday_index,
                weekday_label=WEEKDAYS[entry.weekday_index],
                starts_at_minute=entry.starts_at_minute,
                ends_at_minute=entry.ends_at_minute,
                period_label=period.label_ar if period else None,
                school_id=entry.school_id,
                school_name=maps["schools"].get(entry.school_id, ""),
                subject_id=entry.subject_id,
                subject_name=maps["subjects"].get(entry.subject_id, ""),
                teacher_ids=teachers,
                teacher_names=[maps["teachers"].get(item, "") for item in teachers],
                section_ids=sections,
                section_names=[maps["sections"].get(item, "") for item in sections],
                resource_ids=resources,
                resource_names=[maps["resources"].get(item, "") for item in resources],
                attendance_mode=attendance_mode,
                attendance_label=ATTENDANCE.get(attendance_mode, attendance_mode),
            )
        )
    return rows


def _substitution_rows(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    current: WorkingTimetable,
    filters: ReportFilters,
) -> tuple[list[ReportRow], bool]:
    if filters.on_date is None:
        raise HTTPException(422, detail={"code": "substitution_report_date_required"})
    absences = list(
        db.scalars(
            select(TeacherAbsence).where(
                TeacherAbsence.tenant_id == tenant,
                TeacherAbsence.timetable_project_id == project_id,
                TeacherAbsence.absence_date == filters.on_date,
                TeacherAbsence.status != "cancelled",
            )
        )
    )
    if filters.school_id:
        absences = [row for row in absences if row.school_id == filters.school_id]
    absence_ids = [row.id for row in absences]
    absence_map = {row.id: row for row in absences}
    needs = (
        list(
            db.scalars(
                select(SubstitutionNeed)
                .where(
                    SubstitutionNeed.tenant_id == tenant,
                    SubstitutionNeed.absence_id.in_(absence_ids),
                    SubstitutionNeed.status != "cancelled",
                )
                .order_by(SubstitutionNeed.starts_at_minute, SubstitutionNeed.id)
            )
        )
        if absence_ids
        else []
    )
    need_ids = [row.id for row in needs]
    assignments = (
        list(
            db.scalars(
                select(SubstitutionAssignment).where(
                    SubstitutionAssignment.tenant_id == tenant,
                    SubstitutionAssignment.need_id.in_(need_ids),
                    SubstitutionAssignment.status == "active",
                )
            )
        )
        if need_ids
        else []
    )
    assignment_map = {row.need_id: row for row in assignments}
    teacher_ids = {row.teacher_id for row in absences} | {
        row.substitute_teacher_id for row in assignments
    }
    teachers = {
        row.id: row.name_ar
        for row in db.scalars(
            select(Teacher).where(Teacher.tenant_id == tenant, Teacher.id.in_(teacher_ids))
        )
    }
    subject_ids = {row.subject_id for row in needs}
    subjects = {
        row.id: row.name_ar
        for row in db.scalars(
            select(Subject).where(Subject.tenant_id == tenant, Subject.id.in_(subject_ids))
        )
    }
    school_ids = {row.school_id for row in needs}
    schools = {
        row.id: row.name_ar
        for row in db.scalars(
            select(School).where(School.tenant_id == tenant, School.id.in_(school_ids))
        )
    }
    entry_ids = [row.working_timetable_entry_id for row in needs]
    section_links = _link_map(
        db,
        WorkingTimetableEntrySection.working_timetable_entry_id,
        WorkingTimetableEntrySection.section_id,
        entry_ids,
    )
    section_ids = {item for values in section_links.values() for item in values}
    sections = {
        row.id: row.name_ar
        for row in db.scalars(
            select(Section).where(Section.tenant_id == tenant, Section.id.in_(section_ids))
        )
    }
    rows = []
    stale = False
    for need in needs:
        absence = absence_map[need.absence_id]
        assignment = assignment_map.get(need.id)
        row_stale = (
            absence.working_timetable_id != current.id
            or absence.working_timetable_revision != current.revision
            or need.source_working_revision != current.revision
        )
        stale = stale or row_stale
        rows.append(
            ReportRow(
                row_id=str(need.id),
                project_cycle_week_index=need.project_cycle_week_index,
                weekday_index=need.weekday_index,
                weekday_label=WEEKDAYS[need.weekday_index],
                starts_at_minute=need.starts_at_minute,
                ends_at_minute=need.ends_at_minute,
                school_id=need.school_id,
                school_name=schools.get(need.school_id, ""),
                subject_id=need.subject_id,
                subject_name=subjects.get(need.subject_id, ""),
                section_ids=section_links.get(need.working_timetable_entry_id, []),
                section_names=[
                    sections.get(item, "")
                    for item in section_links.get(need.working_timetable_entry_id, [])
                ],
                absent_teacher_name=teachers.get(absence.teacher_id, ""),
                substitute_teacher_name=(
                    teachers.get(assignment.substitute_teacher_id, "") if assignment else None
                ),
                coverage_status="مغطاة" if assignment else "غير مغطاة",
                recommendation_rank=assignment.recommendation_rank if assignment else None,
                stale=row_stale,
            )
        )
    return rows, stale


def _waiting_rows(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, filters: ReportFilters
) -> list[ReportRow]:
    on_date = filters.on_date or date.today()
    school_teacher_ids: set[str] | None = None
    if filters.school_id:
        school_teacher_ids = {
            str(value)
            for value in db.scalars(
                select(TeacherSchoolMembership.teacher_id).where(
                    TeacherSchoolMembership.tenant_id == tenant,
                    TeacherSchoolMembership.school_id == filters.school_id,
                    TeacherSchoolMembership.is_active.is_(True),
                )
            )
        }
    rows = []
    for item in workload_summary(db, tenant, project_id, on_date):
        if school_teacher_ids is not None and item["teacher_id"] not in school_teacher_ids:
            continue
        if filters.teacher_id and str(filters.teacher_id) != item["teacher_id"]:
            continue
        rows.append(
            ReportRow(
                row_id=item["teacher_id"],
                teacher_ids=[uuid.UUID(item["teacher_id"])],
                teacher_names=[item["teacher_name"]],
                base_workload=item["base_target"],
                teaching_workload=item["teaching_load"],
                substitution_count=item["assigned_this_week"],
                effective_limit=item["combined_limit"],
                remaining_capacity=item["remaining_capacity"],
                exempt=item["exempt"],
            )
        )
    return rows


def build_report(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, request: ReportPreviewRequest
) -> ReportDataset:
    scopes = _scopes(db, tenant, project_id)
    _ensure_filters(db, tenant, scopes, request.report_type, request.filters)
    source, entries = _source(db, tenant, project_id, request)
    metadata = _metadata(db, tenant, project_id, source, scopes)
    stale = False
    warnings: list[str] = []
    if request.report_type == "daily_substitutions":
        assert isinstance(source, WorkingTimetable)
        rows, stale = _substitution_rows(
            db, tenant, project_id, source, request.filters
        )
        columns = ["اليوم", "المدرسة", "المعلم الغائب", "المادة", "الشعبة", "البديل", "الحالة"]
        if request.print_options.show_period_time:
            columns.insert(1, "الوقت")
        if stale:
            warnings.append("توجد احتياجات بدلاء مبنية على نسخة جدول أقدم؛ حدّث الغياب قبل التصدير.")
    elif request.report_type == "waiting_workload":
        rows = _waiting_rows(db, tenant, project_id, request.filters)
        columns = ["المعلم", "النصاب الأساسي", "التدريس", "الانتظار", "الحد الفعلي", "المتبقي", "الاستثناء"]
    else:
        rows = _normal_rows(entries, _maps(db, tenant, source, entries), request.filters)
        columns = list(NORMAL_COLUMNS)
        if not request.print_options.show_period_time:
            columns.remove("الوقت")
        if not request.print_options.show_resource:
            columns.remove("المورد")
    if len(rows) > MAX_REPORT_ROWS:
        raise HTTPException(413, detail={"code": "report_row_limit_exceeded", "limit": MAX_REPORT_ROWS})
    title = request.branding.title_override or TITLES[request.report_type]
    subtitle = request.branding.subtitle or metadata.project_name
    return ReportDataset(
        report_type=request.report_type,
        title=title,
        subtitle=subtitle,
        source=metadata,
        filters=request.filters,
        print_options=request.print_options,
        branding=request.branding,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        stale=stale,
        warnings=warnings,
    )

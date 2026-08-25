from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.editor_services import _working
from app.models import (
    SchedulingRule,
    School,
    Section,
    Subject,
    SubstitutionAssignment,
    SubstitutionNeed,
    Teacher,
    TeacherAbsence,
    TeacherSchoolMembership,
    TeacherWaitingProfile,
    TeachingAssignment,
    TeachingAssignmentTeacher,
    TimetableProjectSchool,
    WaitingPolicy,
    WorkingTimetable,
    WorkingTimetableEntry,
    WorkingTimetableEntrySection,
    WorkingTimetableEntryTeacher,
)
from app.project_services import _matches, _project, build_problem
from app.substitution_schemas import (
    AbsenceCreate,
    SubstituteAssign,
    SubstituteUnassign,
    WaitingPolicyInput,
    WaitingProfileInput,
)


def _scopes(db: Session, tenant: uuid.UUID, project_id: uuid.UUID) -> list[TimetableProjectSchool]:
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


def _policy(db: Session, tenant: uuid.UUID, project_id: uuid.UUID) -> WaitingPolicy:
    row = db.scalar(
        select(WaitingPolicy).where(
            WaitingPolicy.tenant_id == tenant,
            WaitingPolicy.timetable_project_id == project_id,
        )
    )
    return row or WaitingPolicy(
        tenant_id=tenant,
        timetable_project_id=project_id,
        combined_workload_limit=None,
        daily_waiting_limit=None,
        weekly_waiting_limit=None,
        fairness_weight=5,
        specialty_preference_enabled=False,
        specialty_preference_weight=3,
        same_school_preference_weight=0,
        exclude_exempt_teachers=True,
        enabled=True,
    )


def serialize_policy(row: WaitingPolicy) -> dict[str, Any]:
    return {
        "id": str(row.id) if row.id else None,
        "project_id": str(row.timetable_project_id),
        "combined_workload_limit": row.combined_workload_limit,
        "daily_waiting_limit": row.daily_waiting_limit,
        "weekly_waiting_limit": row.weekly_waiting_limit,
        "fairness_weight": row.fairness_weight,
        "specialty_preference_enabled": row.specialty_preference_enabled,
        "specialty_preference_weight": row.specialty_preference_weight,
        "same_school_preference_weight": row.same_school_preference_weight,
        "exclude_exempt_teachers": row.exclude_exempt_teachers,
        "enabled": row.enabled,
    }


def get_policy(db: Session, tenant: uuid.UUID, project_id: uuid.UUID) -> dict[str, Any]:
    _scopes(db, tenant, project_id)
    return serialize_policy(_policy(db, tenant, project_id))


def save_policy(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, payload: WaitingPolicyInput
) -> dict[str, Any]:
    _scopes(db, tenant, project_id)
    row = db.scalar(
        select(WaitingPolicy).where(
            WaitingPolicy.tenant_id == tenant,
            WaitingPolicy.timetable_project_id == project_id,
        )
    ) or WaitingPolicy(tenant_id=tenant, timetable_project_id=project_id)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_policy(row)


def save_profile(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    teacher_id: uuid.UUID,
    payload: WaitingProfileInput,
) -> dict[str, Any]:
    scopes = _scopes(db, tenant, project_id)
    teacher = db.scalar(
        select(Teacher).where(Teacher.id == teacher_id, Teacher.tenant_id == tenant)
    )
    membership = db.scalar(
        select(TeacherSchoolMembership.id).where(
            TeacherSchoolMembership.tenant_id == tenant,
            TeacherSchoolMembership.teacher_id == teacher_id,
            TeacherSchoolMembership.school_id.in_([row.school_id for row in scopes]),
        )
    )
    if not teacher or not membership:
        raise HTTPException(422, detail={"code": "teacher_outside_project_scope"})
    row = db.scalar(
        select(TeacherWaitingProfile).where(
            TeacherWaitingProfile.tenant_id == tenant,
            TeacherWaitingProfile.timetable_project_id == project_id,
            TeacherWaitingProfile.teacher_id == teacher_id,
        )
    ) or TeacherWaitingProfile(
        tenant_id=tenant, timetable_project_id=project_id, teacher_id=teacher_id
    )
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _profile_dict(row)


def _profile(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, teacher_id: uuid.UUID
) -> TeacherWaitingProfile | None:
    return db.scalar(
        select(TeacherWaitingProfile).where(
            TeacherWaitingProfile.tenant_id == tenant,
            TeacherWaitingProfile.timetable_project_id == project_id,
            TeacherWaitingProfile.teacher_id == teacher_id,
        )
    )


def _profile_dict(row: TeacherWaitingProfile | None) -> dict[str, Any]:
    return {
        "exempt": row.exempt if row else False,
        "custom_combined_limit": row.custom_combined_limit if row else None,
        "custom_daily_limit": row.custom_daily_limit if row else None,
        "custom_weekly_limit": row.custom_weekly_limit if row else None,
        "notes": row.notes if row else None,
    }


def _teaching_load(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, teacher_id: uuid.UUID
) -> int:
    scopes = _scopes(db, tenant, project_id)
    conditions = [
        (TeachingAssignment.school_id == scope.school_id)
        & (TeachingAssignment.term_id == scope.term_id)
        for scope in scopes
    ]
    if not conditions:
        return 0
    from sqlalchemy import or_

    value = db.scalar(
        select(func.coalesce(func.sum(TeachingAssignment.weekly_occurrences), 0))
        .join(
            TeachingAssignmentTeacher,
            TeachingAssignmentTeacher.teaching_assignment_id == TeachingAssignment.id,
        )
        .where(
            TeachingAssignment.tenant_id == tenant,
            TeachingAssignmentTeacher.tenant_id == tenant,
            TeachingAssignmentTeacher.teacher_id == teacher_id,
            or_(*conditions),
        )
    )
    return int(value or 0)


def _week_bounds(day: date) -> tuple[date, date]:
    first = day - timedelta(days=day.weekday())
    return first, first + timedelta(days=7)


def _assigned_counts(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, teacher_id: uuid.UUID, day: date
) -> tuple[int, int]:
    first, after = _week_bounds(day)
    base = (
        select(func.count(SubstitutionAssignment.id))
        .join(SubstitutionNeed, SubstitutionNeed.id == SubstitutionAssignment.need_id)
        .join(TeacherAbsence, TeacherAbsence.id == SubstitutionNeed.absence_id)
        .where(
            SubstitutionAssignment.tenant_id == tenant,
            SubstitutionAssignment.substitute_teacher_id == teacher_id,
            SubstitutionAssignment.status == "active",
            TeacherAbsence.timetable_project_id == project_id,
        )
    )
    daily = int(db.scalar(base.where(TeacherAbsence.absence_date == day)) or 0)
    weekly = int(
        db.scalar(
            base.where(TeacherAbsence.absence_date >= first, TeacherAbsence.absence_date < after)
        )
        or 0
    )
    return daily, weekly


def _effective_limits(
    teacher: Teacher, policy: WaitingPolicy, profile: TeacherWaitingProfile | None
) -> tuple[int, int | None, int | None]:
    combined = (
        profile.custom_combined_limit
        if profile and profile.custom_combined_limit is not None
        else policy.combined_workload_limit
    )
    if combined is None:
        combined = teacher.base_workload
    daily = (
        profile.custom_daily_limit
        if profile and profile.custom_daily_limit is not None
        else policy.daily_waiting_limit
    )
    weekly = (
        profile.custom_weekly_limit
        if profile and profile.custom_weekly_limit is not None
        else policy.weekly_waiting_limit
    )
    return combined, daily, weekly


def workload_summary(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, day: date
) -> list[dict[str, Any]]:
    scopes = _scopes(db, tenant, project_id)
    policy = _policy(db, tenant, project_id)
    memberships = list(
        db.scalars(
            select(TeacherSchoolMembership).where(
                TeacherSchoolMembership.tenant_id == tenant,
                TeacherSchoolMembership.school_id.in_([row.school_id for row in scopes]),
                TeacherSchoolMembership.is_active.is_(True),
            )
        )
    )
    teacher_ids = sorted({row.teacher_id for row in memberships}, key=str)
    result = []
    for teacher in db.scalars(
        select(Teacher)
        .where(Teacher.tenant_id == tenant, Teacher.id.in_(teacher_ids))
        .order_by(Teacher.name_ar, Teacher.id)
    ):
        profile = _profile(db, tenant, project_id, teacher.id)
        teaching = _teaching_load(db, tenant, project_id, teacher.id)
        daily, weekly = _assigned_counts(db, tenant, project_id, teacher.id, day)
        combined_limit, daily_limit, weekly_limit = _effective_limits(teacher, policy, profile)
        remaining = max(0, combined_limit - teaching - weekly)
        if weekly_limit is not None:
            remaining = min(remaining, max(0, weekly_limit - weekly))
        result.append(
            {
                "teacher_id": str(teacher.id),
                "teacher_name": teacher.name_ar,
                "base_target": teacher.base_workload,
                "teaching_load": teaching,
                "assigned_today": daily,
                "assigned_this_week": weekly,
                "combined_limit": combined_limit,
                "daily_limit": daily_limit,
                "weekly_limit": weekly_limit,
                "remaining_capacity": remaining,
                **_profile_dict(profile),
            }
        )
    return result


def _weekday(day: date) -> int:
    return (day.weekday() + 1) % 7


def _teacher_in_school(
    db: Session,
    tenant: uuid.UUID,
    teacher_id: uuid.UUID,
    school_id: uuid.UUID,
    *,
    active: bool = True,
) -> bool:
    conditions: list[Any] = [
        TeacherSchoolMembership.tenant_id == tenant,
        TeacherSchoolMembership.teacher_id == teacher_id,
        TeacherSchoolMembership.school_id == school_id,
    ]
    if active:
        conditions.append(TeacherSchoolMembership.is_active.is_(True))
    return db.scalar(select(TeacherSchoolMembership.id).where(*conditions)) is not None


def create_absence(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, payload: AbsenceCreate
) -> dict[str, Any]:
    scopes = _scopes(db, tenant, project_id)
    if payload.school_id not in {row.school_id for row in scopes}:
        raise HTTPException(422, detail={"code": "school_outside_project_scope"})
    teacher = db.scalar(
        select(Teacher).where(
            Teacher.id == payload.teacher_id,
            Teacher.tenant_id == tenant,
            Teacher.is_active.is_(True),
        )
    )
    if not teacher or not _teacher_in_school(db, tenant, payload.teacher_id, payload.school_id):
        raise HTTPException(422, detail={"code": "inactive_or_out_of_scope_absent_teacher"})
    working = _working(db, tenant, project_id, lock=True)
    if working.revision != payload.working_timetable_revision:
        raise HTTPException(
            409, detail={"code": "timetable_version_conflict", "current_revision": working.revision}
        )
    if (
        payload.project_cycle_week_index
        >= build_problem(db, tenant, project_id).project_cycle_length
    ):
        raise HTTPException(422, detail={"code": "invalid_project_cycle_week"})
    absence = TeacherAbsence(
        tenant_id=tenant,
        timetable_project_id=project_id,
        working_timetable_id=working.id,
        working_timetable_revision=working.revision,
        school_id=payload.school_id,
        teacher_id=payload.teacher_id,
        absence_date=payload.absence_date,
        project_cycle_week_index=payload.project_cycle_week_index,
        weekday_index=_weekday(payload.absence_date),
        full_day=payload.full_day,
        starts_at_minute=payload.starts_at_minute,
        ends_at_minute=payload.ends_at_minute,
        reason_code=payload.reason_code,
        reason_text=payload.reason_text,
        status="open",
    )
    db.add(absence)
    db.flush()
    _expand_absence(db, absence, working)
    _update_coverage(db, absence)
    db.commit()
    db.refresh(absence)
    return serialize_absence(db, absence, working)


def _entry_matches_absence(entry: WorkingTimetableEntry, absence: TeacherAbsence) -> bool:
    if (
        entry.school_id != absence.school_id
        or entry.project_cycle_week_index != absence.project_cycle_week_index
        or entry.weekday_index != absence.weekday_index
    ):
        return False
    if absence.full_day:
        return True
    assert absence.starts_at_minute is not None and absence.ends_at_minute is not None
    return (
        entry.starts_at_minute < absence.ends_at_minute
        and absence.starts_at_minute < entry.ends_at_minute
    )


def _affected_entries(
    db: Session, absence: TeacherAbsence, working: WorkingTimetable
) -> list[WorkingTimetableEntry]:
    return [
        entry
        for entry in db.scalars(
            select(WorkingTimetableEntry)
            .join(
                WorkingTimetableEntryTeacher,
                WorkingTimetableEntryTeacher.working_timetable_entry_id == WorkingTimetableEntry.id,
            )
            .where(
                WorkingTimetableEntry.tenant_id == absence.tenant_id,
                WorkingTimetableEntry.working_timetable_id == working.id,
                WorkingTimetableEntryTeacher.tenant_id == absence.tenant_id,
                WorkingTimetableEntryTeacher.teacher_id == absence.teacher_id,
            )
        )
        if _entry_matches_absence(entry, absence)
    ]


def _expand_absence(db: Session, absence: TeacherAbsence, working: WorkingTimetable) -> None:
    existing = list(
        db.scalars(
            select(SubstitutionNeed).where(
                SubstitutionNeed.tenant_id == absence.tenant_id,
                SubstitutionNeed.absence_id == absence.id,
                SubstitutionNeed.status.in_(["unassigned", "uncovered"]),
            )
        )
    )
    by_entry = {row.working_timetable_entry_id: row for row in existing}
    affected = _affected_entries(db, absence, working)
    affected_ids = {row.id for row in affected}
    for old in existing:
        if old.working_timetable_entry_id not in affected_ids:
            old.status = "cancelled"
            old.version += 1
    for entry in affected:
        need = by_entry.get(entry.id)
        if need:
            need.occurrence_id = entry.occurrence_id
            need.school_id = entry.school_id
            need.subject_id = entry.subject_id
            need.project_cycle_week_index = entry.project_cycle_week_index
            need.weekday_index = entry.weekday_index
            need.starts_at_minute = entry.starts_at_minute
            need.ends_at_minute = entry.ends_at_minute
            need.source_working_revision = working.revision
            need.status = "unassigned"
            need.version += 1
        else:
            db.add(
                SubstitutionNeed(
                    tenant_id=absence.tenant_id,
                    absence_id=absence.id,
                    working_timetable_entry_id=entry.id,
                    occurrence_id=entry.occurrence_id,
                    absent_teacher_id=absence.teacher_id,
                    school_id=entry.school_id,
                    subject_id=entry.subject_id,
                    project_cycle_week_index=entry.project_cycle_week_index,
                    weekday_index=entry.weekday_index,
                    starts_at_minute=entry.starts_at_minute,
                    ends_at_minute=entry.ends_at_minute,
                    source_working_revision=working.revision,
                    status="unassigned",
                    version=1,
                )
            )
    db.flush()


def refresh_absence(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, absence_id: uuid.UUID, revision: int
) -> dict[str, Any]:
    absence = _absence(db, tenant, project_id, absence_id, lock=True)
    if absence.status == "cancelled":
        raise HTTPException(409, detail={"code": "absence_cancelled"})
    working = _working(db, tenant, project_id, lock=True)
    if working.revision != revision:
        raise HTTPException(
            409, detail={"code": "timetable_version_conflict", "current_revision": working.revision}
        )
    absence.working_timetable_id = working.id
    absence.working_timetable_revision = working.revision
    _expand_absence(db, absence, working)
    _update_coverage(db, absence)
    db.commit()
    db.refresh(absence)
    return serialize_absence(db, absence, working)


def _absence(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    absence_id: uuid.UUID,
    *,
    lock: bool = False,
) -> TeacherAbsence:
    query = select(TeacherAbsence).where(
        TeacherAbsence.id == absence_id,
        TeacherAbsence.tenant_id == tenant,
        TeacherAbsence.timetable_project_id == project_id,
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if not row:
        raise HTTPException(404, detail={"code": "absence_not_found"})
    return row


def list_absences(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    day: date | None = None,
    school_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    _scopes(db, tenant, project_id)
    working = _working(db, tenant, project_id)
    query = select(TeacherAbsence).where(
        TeacherAbsence.tenant_id == tenant, TeacherAbsence.timetable_project_id == project_id
    )
    if day is not None:
        query = query.where(TeacherAbsence.absence_date == day)
    if school_id is not None:
        query = query.where(TeacherAbsence.school_id == school_id)
    return [
        serialize_absence(db, row, working)
        for row in db.scalars(
            query.order_by(TeacherAbsence.absence_date.desc(), TeacherAbsence.created_at.desc())
        )
    ]


def serialize_absence(
    db: Session, absence: TeacherAbsence, working: WorkingTimetable
) -> dict[str, Any]:
    teacher = db.get(Teacher, absence.teacher_id)
    school = db.get(School, absence.school_id)
    needs = list(
        db.scalars(
            select(SubstitutionNeed)
            .where(
                SubstitutionNeed.tenant_id == absence.tenant_id,
                SubstitutionNeed.absence_id == absence.id,
            )
            .order_by(SubstitutionNeed.starts_at_minute)
        )
    )
    return {
        "id": str(absence.id),
        "project_id": str(absence.timetable_project_id),
        "school_id": str(absence.school_id),
        "school_name": school.name_ar if school else "",
        "teacher_id": str(absence.teacher_id),
        "teacher_name": teacher.name_ar if teacher else "",
        "absence_date": absence.absence_date.isoformat(),
        "project_cycle_week_index": absence.project_cycle_week_index,
        "weekday_index": absence.weekday_index,
        "full_day": absence.full_day,
        "starts_at_minute": absence.starts_at_minute,
        "ends_at_minute": absence.ends_at_minute,
        "reason_code": absence.reason_code,
        "reason_text": absence.reason_text,
        "status": absence.status,
        "working_timetable_revision": absence.working_timetable_revision,
        "stale": absence.working_timetable_id != working.id
        or absence.working_timetable_revision != working.revision,
        "needs": [serialize_need(db, row, working) for row in needs],
    }


def serialize_need(
    db: Session, need: SubstitutionNeed, working: WorkingTimetable
) -> dict[str, Any]:
    subject = db.get(Subject, need.subject_id)
    school = db.get(School, need.school_id)
    section_ids = list(
        db.scalars(
            select(WorkingTimetableEntrySection.section_id).where(
                WorkingTimetableEntrySection.working_timetable_entry_id
                == need.working_timetable_entry_id
            )
        )
    )
    sections = (
        list(db.scalars(select(Section).where(Section.id.in_(section_ids)))) if section_ids else []
    )
    assignment = db.scalar(
        select(SubstitutionAssignment).where(
            SubstitutionAssignment.tenant_id == need.tenant_id,
            SubstitutionAssignment.need_id == need.id,
            SubstitutionAssignment.status == "active",
        )
    )
    substitute = db.get(Teacher, assignment.substitute_teacher_id) if assignment else None
    return {
        "id": str(need.id),
        "absence_id": str(need.absence_id),
        "version": need.version,
        "occurrence_id": need.occurrence_id,
        "school_id": str(need.school_id),
        "school_name": school.name_ar if school else "",
        "subject_id": str(need.subject_id),
        "subject_name": subject.name_ar if subject else "",
        "section_names": [row.name_ar for row in sections],
        "project_cycle_week_index": need.project_cycle_week_index,
        "weekday_index": need.weekday_index,
        "starts_at_minute": need.starts_at_minute,
        "ends_at_minute": need.ends_at_minute,
        "status": need.status,
        "source_working_revision": need.source_working_revision,
        "stale": need.source_working_revision != working.revision
        or need.working_timetable_entry_id
        not in {
            entry.id
            for entry in db.scalars(
                select(WorkingTimetableEntry).where(
                    WorkingTimetableEntry.working_timetable_id == working.id
                )
            )
        },
        "assignment": None
        if not assignment
        else {
            "id": str(assignment.id),
            "teacher_id": str(assignment.substitute_teacher_id),
            "teacher_name": substitute.name_ar if substitute else "",
            "score": assignment.score,
            "rank": assignment.recommendation_rank,
            "manual_override": assignment.manual_override,
            "score_breakdown": assignment.score_breakdown,
            "eligibility_facts": assignment.eligibility_facts,
        },
    }


def _need(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, need_id: uuid.UUID, *, lock: bool = False
) -> tuple[SubstitutionNeed, TeacherAbsence]:
    query = (
        select(SubstitutionNeed)
        .join(TeacherAbsence, TeacherAbsence.id == SubstitutionNeed.absence_id)
        .where(
            SubstitutionNeed.id == need_id,
            SubstitutionNeed.tenant_id == tenant,
            TeacherAbsence.tenant_id == tenant,
            TeacherAbsence.timetable_project_id == project_id,
        )
    )
    need = db.scalar(query.with_for_update() if lock else query)
    if not need:
        raise HTTPException(404, detail={"code": "substitution_need_not_found"})
    return need, _absence(db, tenant, project_id, need.absence_id, lock=lock)


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def _eligibility(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    need: SubstitutionNeed,
    absence: TeacherAbsence,
    teacher: Teacher,
) -> dict[str, Any]:
    scopes = _scopes(db, tenant, project_id)
    school_ids = [row.school_id for row in scopes]
    policy = _policy(db, tenant, project_id)
    profile = _profile(db, tenant, project_id, teacher.id)
    reasons: list[str] = []
    memberships = list(
        db.scalars(
            select(TeacherSchoolMembership).where(
                TeacherSchoolMembership.tenant_id == tenant,
                TeacherSchoolMembership.teacher_id == teacher.id,
                TeacherSchoolMembership.school_id.in_(school_ids),
                TeacherSchoolMembership.is_active.is_(True),
            )
        )
    )
    if not teacher.is_active:
        reasons.append("teacher_inactive")
    if not memberships:
        reasons.append("no_active_project_membership")
    if teacher.id == need.absent_teacher_id:
        reasons.append("same_as_absent_teacher")
    if policy.enabled and policy.exclude_exempt_teachers and profile and profile.exempt:
        reasons.append("waiting_exempt")
    other_absences = list(
        db.scalars(
            select(TeacherAbsence).where(
                TeacherAbsence.tenant_id == tenant,
                TeacherAbsence.timetable_project_id == project_id,
                TeacherAbsence.teacher_id == teacher.id,
                TeacherAbsence.status != "cancelled",
                TeacherAbsence.project_cycle_week_index == need.project_cycle_week_index,
                TeacherAbsence.weekday_index == need.weekday_index,
            )
        )
    )
    if any(
        row.full_day
        or (
            row.starts_at_minute is not None
            and row.ends_at_minute is not None
            and _overlap(
                need.starts_at_minute, need.ends_at_minute, row.starts_at_minute, row.ends_at_minute
            )
        )
        for row in other_absences
    ):
        reasons.append("teacher_absent")
    working = _working(db, tenant, project_id)
    teaching_collision = db.scalar(
        select(WorkingTimetableEntry.id)
        .join(
            WorkingTimetableEntryTeacher,
            WorkingTimetableEntryTeacher.working_timetable_entry_id == WorkingTimetableEntry.id,
        )
        .where(
            WorkingTimetableEntry.tenant_id == tenant,
            WorkingTimetableEntry.working_timetable_id == working.id,
            WorkingTimetableEntryTeacher.teacher_id == teacher.id,
            WorkingTimetableEntry.project_cycle_week_index == need.project_cycle_week_index,
            WorkingTimetableEntry.weekday_index == need.weekday_index,
            WorkingTimetableEntry.starts_at_minute < need.ends_at_minute,
            WorkingTimetableEntry.ends_at_minute > need.starts_at_minute,
        )
    )
    if teaching_collision:
        reasons.append("teaching_time_collision")
    substitution_collision = db.scalar(
        select(SubstitutionAssignment.id)
        .join(SubstitutionNeed, SubstitutionNeed.id == SubstitutionAssignment.need_id)
        .join(TeacherAbsence, TeacherAbsence.id == SubstitutionNeed.absence_id)
        .where(
            SubstitutionAssignment.tenant_id == tenant,
            SubstitutionAssignment.substitute_teacher_id == teacher.id,
            SubstitutionAssignment.status == "active",
            TeacherAbsence.timetable_project_id == project_id,
            SubstitutionNeed.project_cycle_week_index == need.project_cycle_week_index,
            SubstitutionNeed.weekday_index == need.weekday_index,
            SubstitutionNeed.starts_at_minute < need.ends_at_minute,
            SubstitutionNeed.ends_at_minute > need.starts_at_minute,
        )
    )
    if substitution_collision:
        reasons.append("substitution_time_collision")
    problem = build_problem(db, tenant, project_id)
    source_entry = db.get(WorkingTimetableEntry, need.working_timetable_entry_id)
    slot = (
        next((row for row in problem.slots if row.id == source_entry.slot_id), None)
        if source_entry
        else None
    )
    if slot:
        hard_unavailable_rules = db.scalars(
            select(SchedulingRule).where(
                SchedulingRule.tenant_id == tenant,
                SchedulingRule.timetable_project_id == project_id,
                SchedulingRule.rule_type == "teacher_unavailable",
                SchedulingRule.severity == "hard",
                SchedulingRule.enabled.is_(True),
            )
        )
        for rule in hard_unavailable_rules:
            if str(rule.selector.get("teacher_id")) == str(teacher.id) and _matches(
                slot, rule.parameters
            ):
                reasons.append("hard_unavailable_rule")
    teaching = _teaching_load(db, tenant, project_id, teacher.id)
    daily, weekly = _assigned_counts(db, tenant, project_id, teacher.id, absence.absence_date)
    combined_limit, daily_limit, weekly_limit = _effective_limits(teacher, policy, profile)
    if teaching + weekly + 1 > combined_limit:
        reasons.append("combined_workload_cap")
    if daily_limit is not None and daily + 1 > daily_limit:
        reasons.append("daily_waiting_cap")
    if weekly_limit is not None and weekly + 1 > weekly_limit:
        reasons.append("weekly_waiting_cap")
    subject = db.get(Subject, need.subject_id)
    specialty_match = bool(
        policy.specialty_preference_enabled
        and teacher.specialty_reference
        and subject
        and normalize(teacher.specialty_reference)
        in {normalize(subject.name_ar), normalize(subject.code)}
    )
    remaining_after = max(0, combined_limit - teaching - weekly - 1)
    components = {
        "remaining_capacity": remaining_after * policy.fairness_weight,
        "daily_fairness": max(0, (daily_limit if daily_limit is not None else 10) - daily - 1)
        * policy.fairness_weight,
        "weekly_fairness": max(0, (weekly_limit if weekly_limit is not None else 20) - weekly - 1)
        * policy.fairness_weight,
        "specialty_preference": policy.specialty_preference_weight if specialty_match else 0,
        "same_school_preference": policy.same_school_preference_weight
        if any(row.school_id == need.school_id for row in memberships)
        else 0,
    }
    return {
        "eligible": not reasons,
        "blocking_reasons": reasons,
        "free_at_time": not teaching_collision and not substitution_collision,
        "teaching_load": teaching,
        "assigned_today": daily,
        "assigned_this_week": weekly,
        "combined_after_assignment": teaching + weekly + 1,
        "combined_limit": combined_limit,
        "daily_limit": daily_limit,
        "weekly_limit": weekly_limit,
        "exempt": profile.exempt if profile else False,
        "specialty_considered": policy.specialty_preference_enabled,
        "specialty_match": specialty_match if policy.specialty_preference_enabled else None,
        "same_school_membership": any(row.school_id == need.school_id for row in memberships),
        "score_breakdown": components,
        "total_score": sum(components.values()),
    }


def normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def rank_candidates(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, need_id: uuid.UUID
) -> dict[str, Any]:
    need, absence = _need(db, tenant, project_id, need_id)
    working = _working(db, tenant, project_id)
    if need.source_working_revision != working.revision:
        raise HTTPException(
            409, detail={"code": "stale_substitution_need", "current_revision": working.revision}
        )
    scopes = _scopes(db, tenant, project_id)
    teacher_ids = set(
        db.scalars(
            select(TeacherSchoolMembership.teacher_id).where(
                TeacherSchoolMembership.tenant_id == tenant,
                TeacherSchoolMembership.school_id.in_([row.school_id for row in scopes]),
            )
        )
    )
    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for teacher in db.scalars(
        select(Teacher)
        .where(Teacher.tenant_id == tenant, Teacher.id.in_(teacher_ids))
        .order_by(Teacher.canonical_code, Teacher.id)
    ):
        facts = _eligibility(db, tenant, project_id, need, absence, teacher)
        item = {
            "teacher_id": str(teacher.id),
            "teacher_name": teacher.name_ar,
            "canonical_code": teacher.canonical_code,
            **facts,
        }
        (eligible if facts["eligible"] else excluded).append(item)
    eligible.sort(
        key=lambda item: (
            -int(item["total_score"]),
            str(item["canonical_code"]),
            str(item["teacher_id"]),
        )
    )
    for rank, item in enumerate(eligible, 1):
        item["rank"] = rank
    return {
        "need_id": str(need.id),
        "need_version": need.version,
        "working_timetable_revision": working.revision,
        "candidates": eligible,
        "excluded": excluded,
    }


def assign_substitute(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    need_id: uuid.UUID,
    payload: SubstituteAssign,
) -> dict[str, Any]:
    need, absence = _need(db, tenant, project_id, need_id, lock=True)
    working = _working(db, tenant, project_id, lock=True)
    if (
        working.revision != payload.working_timetable_revision
        or need.source_working_revision != working.revision
    ):
        raise HTTPException(
            409, detail={"code": "stale_substitution_need", "current_revision": working.revision}
        )
    if need.version != payload.need_version:
        raise HTTPException(
            409,
            detail={"code": "substitution_need_version_conflict", "current_version": need.version},
        )
    if need.status != "unassigned":
        raise HTTPException(409, detail={"code": "substitution_need_already_assigned"})
    teacher = db.scalar(
        select(Teacher)
        .where(Teacher.id == payload.substitute_teacher_id, Teacher.tenant_id == tenant)
        .with_for_update()
    )
    if not teacher:
        raise HTTPException(422, detail={"code": "substitute_outside_tenant"})
    ranked = rank_candidates(db, tenant, project_id, need_id)
    candidate = next(
        (row for row in ranked["candidates"] if row["teacher_id"] == str(teacher.id)), None
    )
    if not candidate:
        excluded = next(
            (row for row in ranked["excluded"] if row["teacher_id"] == str(teacher.id)), None
        )
        raise HTTPException(422, detail={"code": "hard_ineligible_substitute", "facts": excluded})
    assignment = SubstitutionAssignment(
        tenant_id=tenant,
        need_id=need.id,
        substitute_teacher_id=teacher.id,
        status="active",
        recommendation_rank=candidate["rank"],
        score=candidate["total_score"],
        score_breakdown=candidate["score_breakdown"],
        eligibility_facts={
            key: value
            for key, value in candidate.items()
            if key not in {"score_breakdown", "canonical_code"}
        },
        manual_override=payload.mode == "manual_override",
        assigned_at=datetime.now(UTC),
        assigned_by="مدير المدرسة",
    )
    db.add(assignment)
    need.status = "assigned"
    need.version += 1
    _update_coverage(db, absence)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(need)
    return serialize_need(db, need, working)


def unassign_substitute(
    db: Session,
    tenant: uuid.UUID,
    project_id: uuid.UUID,
    need_id: uuid.UUID,
    payload: SubstituteUnassign,
) -> dict[str, Any]:
    need, absence = _need(db, tenant, project_id, need_id, lock=True)
    working = _working(db, tenant, project_id, lock=True)
    if working.revision != payload.working_timetable_revision:
        raise HTTPException(
            409, detail={"code": "timetable_version_conflict", "current_revision": working.revision}
        )
    if need.version != payload.need_version:
        raise HTTPException(
            409,
            detail={"code": "substitution_need_version_conflict", "current_version": need.version},
        )
    assignment = db.scalar(
        select(SubstitutionAssignment)
        .where(
            SubstitutionAssignment.tenant_id == tenant,
            SubstitutionAssignment.need_id == need.id,
            SubstitutionAssignment.status == "active",
        )
        .with_for_update()
    )
    if not assignment:
        raise HTTPException(409, detail={"code": "active_substitution_not_found"})
    assignment.status = "cancelled"
    assignment.cancelled_at = datetime.now(UTC)
    need.status = "unassigned"
    need.version += 1
    _update_coverage(db, absence)
    db.commit()
    db.refresh(need)
    return serialize_need(db, need, working)


def cancel_absence(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, absence_id: uuid.UUID
) -> dict[str, Any]:
    absence = _absence(db, tenant, project_id, absence_id, lock=True)
    working = _working(db, tenant, project_id, lock=True)
    needs = list(
        db.scalars(
            select(SubstitutionNeed)
            .where(SubstitutionNeed.absence_id == absence.id)
            .with_for_update()
        )
    )
    for need in needs:
        assignment = db.scalar(
            select(SubstitutionAssignment)
            .where(
                SubstitutionAssignment.need_id == need.id, SubstitutionAssignment.status == "active"
            )
            .with_for_update()
        )
        if assignment:
            assignment.status = "cancelled"
            assignment.cancelled_at = datetime.now(UTC)
        need.status = "cancelled"
        need.version += 1
    absence.status = "cancelled"
    db.commit()
    db.refresh(absence)
    return serialize_absence(db, absence, working)


def _update_coverage(db: Session, absence: TeacherAbsence) -> None:
    db.flush()
    needs = list(
        db.scalars(
            select(SubstitutionNeed).where(
                SubstitutionNeed.absence_id == absence.id, SubstitutionNeed.status != "cancelled"
            )
        )
    )
    assigned = sum(row.status == "assigned" for row in needs)
    absence.status = (
        "covered"
        if needs and assigned == len(needs)
        else "partially_covered"
        if assigned
        else "open"
    )


def daily_summary(
    db: Session, tenant: uuid.UUID, project_id: uuid.UUID, day: date
) -> dict[str, Any]:
    all_absences = list_absences(db, tenant, project_id, day=day)
    absences = [row for row in all_absences if row["status"] != "cancelled"]
    needs = [
        need for absence in absences for need in absence["needs"] if need["status"] != "cancelled"
    ]
    carrying = {need["assignment"]["teacher_id"] for need in needs if need["assignment"]}
    return {
        "date": day.isoformat(),
        "absent_teachers": len({row["teacher_id"] for row in absences}),
        "needs": len(needs),
        "covered": sum(row["status"] == "assigned" for row in needs),
        "uncovered": sum(row["status"] != "assigned" for row in needs),
        "teachers_carrying_substitutions": len(carrying),
        "absences": absences,
    }

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    SubstitutionAssignment,
    PeriodTemplate,
    Subject,
    Teacher,
    TeacherSchoolMembership,
    TeachingAssignment,
    TeachingAssignmentTeacher,
    TimetableProjectSchool,
    WorkingTimetable,
    WorkingTimetableEntry,
    WorkingTimetableEntryTeacher,
)
from conftest import (
    FIRST_SCHOOL,
    OTHER_TENANT,
    SECOND_SCHOOL,
    SECOND_TERM,
    SHARED_TEACHER,
    TEST_TENANT,
)
from test_solve_api import HEADERS
from test_timetable_editor_api import derive

SUNDAY = date(2026, 8, 23)


def _candidate(
    session: Session,
    *,
    code: str = "WAIT-1",
    name: str = "معلم بديل",
    base_workload: int = 24,
    specialty: str | None = None,
) -> Teacher:
    teacher = Teacher(
        tenant_id=uuid.UUID(TEST_TENANT),
        canonical_code=code,
        name_ar=name,
        base_workload=base_workload,
        teaching_workload_limit=base_workload,
        specialty_reference=specialty,
        is_active=True,
    )
    session.add(teacher)
    session.flush()
    session.add(
        TeacherSchoolMembership(
            tenant_id=uuid.UUID(TEST_TENANT),
            teacher_id=teacher.id,
            school_id=uuid.UUID(FIRST_SCHOOL),
            is_home_school=False,
            is_active=True,
        )
    )
    session.commit()
    return teacher


def _absence(client: TestClient, project_id: str, working: dict[str, object]) -> dict[str, object]:
    response = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/absences",
        headers=HEADERS,
        json={
            "school_id": FIRST_SCHOOL,
            "teacher_id": SHARED_TEACHER,
            "absence_date": SUNDAY.isoformat(),
            "project_cycle_week_index": 0,
            "working_timetable_revision": working["revision"],
            "full_day": True,
            "reason_code": "sick",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_workload_capacity_uses_teaching_plus_waiting_and_preserves_zero(
    client: TestClient, session: Session
) -> None:
    project_id, _working = derive(client, session)
    teacher = session.get(Teacher, uuid.UUID(SHARED_TEACHER))
    assignment = session.scalar(select(TeachingAssignment))
    assert teacher is not None and assignment is not None
    teacher.base_workload = 24
    assignment.weekly_occurrences = 14
    session.commit()

    rows = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/workloads",
        headers=HEADERS,
        params={"date": SUNDAY.isoformat()},
    ).json()
    shared = next(row for row in rows if row["teacher_id"] == SHARED_TEACHER)
    assert shared["teaching_load"] == 14
    assert shared["combined_limit"] == 24
    assert shared["remaining_capacity"] == 10

    saved = client.put(
        f"/api/v1/timetable-projects/{project_id}/substitutions/profiles/{SHARED_TEACHER}",
        headers=HEADERS,
        json={"custom_combined_limit": 0, "custom_daily_limit": 0, "custom_weekly_limit": 0},
    )
    assert saved.status_code == 200
    rows = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/workloads",
        headers=HEADERS,
        params={"date": SUNDAY.isoformat()},
    ).json()
    shared = next(row for row in rows if row["teacher_id"] == SHARED_TEACHER)
    assert shared["combined_limit"] == 0
    assert shared["daily_limit"] == 0
    assert shared["weekly_limit"] == 0


def test_absence_expands_current_timetable_and_assignment_is_atomic(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    candidate = _candidate(session)
    absence = _absence(client, project_id, working)
    assert len(absence["needs"]) == 1
    need = absence["needs"][0]

    ranked = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/candidates",
        headers=HEADERS,
    )
    assert ranked.status_code == 200, ranked.text
    candidate_row = next(
        row for row in ranked.json()["candidates"] if row["teacher_id"] == str(candidate.id)
    )
    assert candidate_row["eligible"] is True
    assert sum(candidate_row["score_breakdown"].values()) == candidate_row["total_score"]

    payload = {
        "substitute_teacher_id": str(candidate.id),
        "need_version": need["version"],
        "working_timetable_revision": working["revision"],
        "mode": "manual_override",
    }
    assigned = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/assign",
        headers=HEADERS,
        json=payload,
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assignment"]["manual_override"] is True
    duplicate = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/assign",
        headers=HEADERS,
        json=payload,
    )
    assert duplicate.status_code == 409
    assert session.scalar(select(SubstitutionAssignment).where(SubstitutionAssignment.status == "active"))
    cancelled = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/absences/{absence['id']}/cancel",
        headers=HEADERS,
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    session.expire_all()
    archived = session.scalar(select(SubstitutionAssignment))
    assert archived is not None and archived.status == "cancelled"


def test_partial_absence_co_teaching_and_specialty_is_soft(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    candidate = _candidate(session, specialty="علوم")
    entry = session.scalar(select(WorkingTimetableEntry))
    assert entry is not None
    session.add(
        WorkingTimetableEntryTeacher(
            tenant_id=uuid.UUID(TEST_TENANT),
            working_timetable_entry_id=entry.id,
            teacher_id=candidate.id,
        )
    )
    session.commit()

    outside = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/absences",
        headers=HEADERS,
        json={
            "school_id": FIRST_SCHOOL,
            "teacher_id": SHARED_TEACHER,
            "absence_date": SUNDAY.isoformat(),
            "project_cycle_week_index": 0,
            "working_timetable_revision": working["revision"],
            "full_day": False,
            "starts_at_minute": entry.ends_at_minute,
            "ends_at_minute": entry.ends_at_minute + 30,
        },
    )
    assert outside.status_code == 201 and outside.json()["needs"] == []
    inside_response = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/absences",
        headers=HEADERS,
        json={
            "school_id": FIRST_SCHOOL,
            "teacher_id": SHARED_TEACHER,
            "absence_date": SUNDAY.isoformat(),
            "project_cycle_week_index": 0,
            "working_timetable_revision": working["revision"],
            "full_day": False,
            "starts_at_minute": entry.starts_at_minute + 5,
            "ends_at_minute": entry.ends_at_minute - 5,
        },
    )
    assert inside_response.status_code == 201
    inside = inside_response.json()
    assert len(inside["needs"]) == 1  # one absent teacher position, not the whole co-taught lesson

    need = inside["needs"][0]
    ranked = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/candidates",
        headers=HEADERS,
    ).json()
    row = next(item for item in ranked["excluded"] if item["teacher_id"] == str(candidate.id))
    assert "teaching_time_collision" in row["blocking_reasons"]
    assert "specialty_mismatch" not in row["blocking_reasons"]


def test_shared_teacher_remote_cross_school_real_time_collision(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    candidate = _candidate(session, code="SHARED-WAIT")
    project_uuid = uuid.UUID(project_id)
    session.add_all(
        [
            TeacherSchoolMembership(
                tenant_id=uuid.UUID(TEST_TENANT),
                teacher_id=candidate.id,
                school_id=uuid.UUID(SECOND_SCHOOL),
                is_home_school=False,
                is_active=True,
            ),
            TimetableProjectSchool(
                tenant_id=uuid.UUID(TEST_TENANT),
                timetable_project_id=project_uuid,
                school_id=uuid.UUID(SECOND_SCHOOL),
                term_id=uuid.UUID(SECOND_TERM),
                cycle_phase_offset=0,
            ),
        ]
    )
    source = session.scalar(select(WorkingTimetableEntry))
    current = session.scalar(select(WorkingTimetable))
    second_subject = session.scalar(
        select(Subject).where(Subject.school_id == uuid.UUID(SECOND_SCHOOL))
    )
    assert source is not None and current is not None and second_subject is not None
    base_slot_id = source.slot_id.split("@project-week-")[0]
    period = session.get(PeriodTemplate, uuid.UUID(base_slot_id))
    assert period is not None
    period.attendance_mode = "remote"
    collision = WorkingTimetableEntry(
        tenant_id=uuid.UUID(TEST_TENANT),
        working_timetable_id=current.id,
        source_entry_id=None,
        occurrence_id="cross-school-overlap",
        assignment_id=source.assignment_id,
        subject_id=second_subject.id,
        slot_id="second-school-remote-slot",
        school_id=uuid.UUID(SECOND_SCHOOL),
        project_cycle_week_index=source.project_cycle_week_index,
        weekday_index=source.weekday_index,
        starts_at_minute=source.starts_at_minute + 10,
        ends_at_minute=source.ends_at_minute + 10,
    )
    session.add(collision)
    session.flush()
    session.add(
        WorkingTimetableEntryTeacher(
            tenant_id=uuid.UUID(TEST_TENANT),
            working_timetable_entry_id=collision.id,
            teacher_id=candidate.id,
        )
    )
    session.commit()

    absence = _absence(client, project_id, working)
    need = absence["needs"][0]
    ranked = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/candidates",
        headers=HEADERS,
    ).json()
    excluded = next(row for row in ranked["excluded"] if row["teacher_id"] == str(candidate.id))
    assert "teaching_time_collision" in excluded["blocking_reasons"]
    assert period.attendance_mode == "remote"  # remote never bypasses the half-open overlap


def test_caps_fair_ranking_and_overlapping_substitution_are_enforced(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    lower_load = _candidate(session, code="FAIR-A", name="الأقل حمولة", base_workload=24)
    higher_load = _candidate(session, code="FAIR-B", name="الأعلى حمولة", base_workload=24)
    assignment = session.scalar(select(TeachingAssignment))
    assert assignment is not None
    session.add(
        TeachingAssignmentTeacher(
            tenant_id=uuid.UUID(TEST_TENANT),
            teaching_assignment_id=assignment.id,
            teacher_id=higher_load.id,
        )
    )
    session.commit()
    client.put(
        f"/api/v1/timetable-projects/{project_id}/substitutions/policy",
        headers=HEADERS,
        json={
            "combined_workload_limit": 24,
            "daily_waiting_limit": 2,
            "weekly_waiting_limit": 5,
            "fairness_weight": 5,
            "specialty_preference_enabled": False,
            "specialty_preference_weight": 99,
            "same_school_preference_weight": 0,
            "exclude_exempt_teachers": True,
            "enabled": True,
        },
    )
    first_absence = _absence(client, project_id, working)
    first_need = first_absence["needs"][0]
    ranked = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{first_need['id']}/candidates",
        headers=HEADERS,
    ).json()
    eligible_ids = [row["teacher_id"] for row in ranked["candidates"]]
    assert eligible_ids.index(str(lower_load.id)) < eligible_ids.index(str(higher_load.id))
    lower = next(row for row in ranked["candidates"] if row["teacher_id"] == str(lower_load.id))
    assert lower["specialty_considered"] is False

    assigned = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{first_need['id']}/assign",
        headers=HEADERS,
        json={
            "substitute_teacher_id": str(lower_load.id),
            "need_version": first_need["version"],
            "working_timetable_revision": working["revision"],
            "mode": "recommended",
        },
    )
    assert assigned.status_code == 200
    second_absence = _absence(client, project_id, working)
    second_need = second_absence["needs"][0]
    second_ranked = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{second_need['id']}/candidates",
        headers=HEADERS,
    ).json()
    blocked = next(
        row for row in second_ranked["excluded"] if row["teacher_id"] == str(lower_load.id)
    )
    assert "substitution_time_collision" in blocked["blocking_reasons"]

    unassigned = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{first_need['id']}/unassign",
        headers=HEADERS,
        json={
            "need_version": assigned.json()["version"],
            "working_timetable_revision": working["revision"],
        },
    )
    assert unassigned.status_code == 200
    session.expire_all()
    history = list(session.scalars(select(SubstitutionAssignment)))
    assert len(history) == 1 and history[0].status == "cancelled"
    refreshed_absence = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/absences",
        headers=HEADERS,
        params={"date": SUNDAY.isoformat()},
    ).json()
    assert next(row for row in refreshed_absence if row["id"] == first_absence["id"])["status"] == "open"


def test_daily_weekly_and_combined_zero_caps_each_block_candidate(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    candidate = _candidate(session, code="CAP-0", base_workload=24)
    absence = _absence(client, project_id, working)
    need = absence["needs"][0]
    client.put(
        f"/api/v1/timetable-projects/{project_id}/substitutions/profiles/{candidate.id}",
        headers=HEADERS,
        json={
            "custom_combined_limit": 0,
            "custom_daily_limit": 0,
            "custom_weekly_limit": 0,
        },
    )
    ranked = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/candidates",
        headers=HEADERS,
    ).json()
    row = next(item for item in ranked["excluded"] if item["teacher_id"] == str(candidate.id))
    assert {"combined_workload_cap", "daily_waiting_cap", "weekly_waiting_cap"}.issubset(
        row["blocking_reasons"]
    )


def test_exemption_hard_ineligible_and_stale_revision_require_refresh(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    candidate = _candidate(session)
    absence = _absence(client, project_id, working)
    need = absence["needs"][0]
    profile = client.put(
        f"/api/v1/timetable-projects/{project_id}/substitutions/profiles/{candidate.id}",
        headers=HEADERS,
        json={"exempt": True},
    )
    assert profile.status_code == 200
    ranked = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/candidates",
        headers=HEADERS,
    ).json()
    excluded = next(row for row in ranked["excluded"] if row["teacher_id"] == str(candidate.id))
    assert "waiting_exempt" in excluded["blocking_reasons"]
    rejected = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/assign",
        headers=HEADERS,
        json={
            "substitute_teacher_id": str(candidate.id),
            "need_version": need["version"],
            "working_timetable_revision": working["revision"],
            "mode": "manual_override",
        },
    )
    assert rejected.status_code == 422

    current = session.scalar(select(WorkingTimetable))
    assert current is not None
    current.revision += 1
    session.commit()
    stale = client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/candidates",
        headers=HEADERS,
    )
    assert stale.status_code == 409
    refreshed = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/absences/{absence['id']}/refresh",
        headers=HEADERS,
        json={"working_timetable_revision": current.revision},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["stale"] is False


def test_substitution_endpoints_are_tenant_scoped(client: TestClient, session: Session) -> None:
    project_id, working = derive(client, session)
    absence = _absence(client, project_id, working)
    assert client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/absences",
        headers={"X-Tenant-ID": OTHER_TENANT},
    ).status_code == 404
    need = absence["needs"][0]
    assert client.get(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/candidates",
        headers={"X-Tenant-ID": OTHER_TENANT},
    ).status_code == 404

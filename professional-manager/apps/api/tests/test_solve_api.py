import uuid
from datetime import time

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    PeriodTemplate,
    SchoolDay,
    SchoolShift,
    Section,
    SectionOffering,
    Subject,
    TeacherSchoolMembership,
    TeachingAssignment,
    TeachingAssignmentSection,
    TeachingAssignmentTeacher,
    TimetableEntry,
    TimetableProject,
    WeekPattern,
)
from app.project_services import build_problem
from app.solve_schemas import SolveRequest
from app.solve_services import create_solve_run, problem_fingerprint
from conftest import FIRST_SCHOOL, FIRST_TERM, OTHER_TENANT, SHARED_TEACHER, TEST_TENANT

HEADERS = {"X-Tenant-ID": TEST_TENANT}


def ready_project(session: Session) -> TimetableProject:
    tenant = uuid.UUID(TEST_TENANT)
    school = uuid.UUID(FIRST_SCHOOL)
    shift = SchoolShift(
        tenant_id=tenant, school_id=school, code="SOLVE", name_ar="صباحي", order=8
    )
    pattern = WeekPattern(
        tenant_id=tenant,
        school_id=school,
        code="SOLVE-A",
        name_ar="أسبوع واحد",
        cycle_week_index=0,
    )
    session.add_all([shift, pattern])
    session.flush()
    day = SchoolDay(
        tenant_id=tenant,
        school_id=school,
        shift_id=shift.id,
        week_pattern_id=pattern.id,
        weekday_index=0,
        label_ar="الأحد",
    )
    session.add(day)
    session.flush()
    for order, hour in enumerate((8, 9, 10), 1):
        session.add(
            PeriodTemplate(
                tenant_id=tenant,
                school_id=school,
                week_pattern_id=pattern.id,
                shift_id=shift.id,
                school_day_id=day.id,
                weekday_index=0,
                block_order=order,
                period_number=order,
                label_ar=f"الحصة {order}",
                starts_at=time(hour, 0),
                ends_at=time(hour, 45),
                block_type="lesson",
                schedulable=True,
            )
        )
    section = session.scalar(select(Section).where(Section.tenant_id == tenant))
    subject = session.scalar(
        select(Subject).where(Subject.tenant_id == tenant, Subject.school_id == school)
    )
    assert section is not None and subject is not None
    offering = SectionOffering(
        tenant_id=tenant,
        school_id=school,
        term_id=uuid.UUID(FIRST_TERM),
        section_id=section.id,
        shift_id=shift.id,
        is_active=True,
    )
    session.add(offering)
    session.flush()
    assignment = TeachingAssignment(
        tenant_id=tenant,
        school_id=school,
        term_id=uuid.UUID(FIRST_TERM),
        subject_id=subject.id,
        weekly_occurrences=1,
        distribution={},
    )
    session.add(assignment)
    session.flush()
    session.add_all(
        [
            TeacherSchoolMembership(
                tenant_id=tenant,
                teacher_id=uuid.UUID(SHARED_TEACHER),
                school_id=school,
                is_home_school=True,
                is_active=True,
            ),
            TeachingAssignmentTeacher(
                tenant_id=tenant,
                teaching_assignment_id=assignment.id,
                teacher_id=uuid.UUID(SHARED_TEACHER),
            ),
            TeachingAssignmentSection(
                tenant_id=tenant,
                teaching_assignment_id=assignment.id,
                section_offering_id=offering.id,
            ),
        ]
    )
    project = TimetableProject(
        tenant_id=tenant,
        scope_type="school",
        name_ar="مشروع CP-SAT",
        status="draft",
        settings={},
    )
    session.add(project)
    session.flush()
    from app.models import TimetableProjectSchool

    session.add(
        TimetableProjectSchool(
            tenant_id=tenant,
            timetable_project_id=project.id,
            school_id=school,
            term_id=uuid.UUID(FIRST_TERM),
            cycle_phase_offset=0,
        )
    )
    session.commit()
    return project


def test_background_solve_persists_and_reloads_candidates_with_labels(
    client: TestClient, session: Session
) -> None:
    project = ready_project(session)
    response = client.post(
        f"/api/v1/timetable-projects/{project.id}/solve",
        headers=HEADERS,
        json={"candidate_count": 3, "time_limit_seconds": 1, "seed": 11},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["id"]
    run = client.get(
        f"/api/v1/timetable-projects/{project.id}/solve-runs/{run_id}", headers=HEADERS
    )
    assert run.status_code == 200
    body = run.json()
    assert body["status"] == "completed", body
    assert len(body["candidates"]) == 3
    detail = client.get(
        f"/api/v1/timetable-projects/{project.id}/candidates/{body['candidates'][0]['id']}",
        headers=HEADERS,
    )
    assert detail.status_code == 200
    entry = detail.json()["entries"][0]
    assert entry["subject"]["name_ar"] == "رياضيات"
    assert entry["teachers"][0]["name_ar"] == "معلم مشترك"
    assert entry["sections"][0]["name_ar"] == "أ"
    assert session.scalar(select(TimetableEntry)) is not None
    assert (
        client.get(
            f"/api/v1/timetable-projects/{project.id}/solve-runs/{run_id}",
            headers={"X-Tenant-ID": OTHER_TENANT},
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/timetable-projects/{project.id}/candidates/{body['candidates'][0]['id']}",
            headers={"X-Tenant-ID": OTHER_TENANT},
        ).status_code
        == 404
    )


def test_fingerprint_is_stable_and_changes_with_relevant_slot_time(session: Session) -> None:
    project = ready_project(session)
    first = build_problem(session, uuid.UUID(TEST_TENANT), project.id)
    assert problem_fingerprint(first) == problem_fingerprint(first.model_copy(deep=True))
    changed = first.model_copy(
        update={"slots": [first.slots[0].model_copy(update={"starts_at_minute": 481}), *first.slots[1:]]}
    )
    assert problem_fingerprint(first) != problem_fingerprint(changed)
    profiled = first.model_copy(
        update={"options": first.options.model_copy(update={"optimization_profile": "teacher_comfort"})}
    )
    assert problem_fingerprint(first) != problem_fingerprint(profiled)


def test_only_one_active_run_is_allowed(session: Session) -> None:
    project = ready_project(session)
    payload = SolveRequest(candidate_count=1, time_limit_seconds=1, seed=1)
    create_solve_run(session, uuid.UUID(TEST_TENANT), project.id, payload)
    try:
        create_solve_run(session, uuid.UUID(TEST_TENANT), project.id, payload)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
    else:
        raise AssertionError("a second active solve run was accepted")


def test_preflight_blocks_solve(client: TestClient) -> None:
    project = client.post(
        "/api/v1/timetable-projects",
        headers=HEADERS,
        json={
            "name_ar": "غير جاهز",
            "scope_type": "school",
            "schools": [
                {"school_id": FIRST_SCHOOL, "term_id": FIRST_TERM, "cycle_phase_offset": 0}
            ],
        },
    ).json()
    response = client.post(
        f"/api/v1/timetable-projects/{project['id']}/solve", headers=HEADERS, json={}
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "preflight_blocked"


def test_solve_request_limits_are_bounded(client: TestClient) -> None:
    project = client.post(
        "/api/v1/timetable-projects",
        headers=HEADERS,
        json={
            "name_ar": "حدود الطلب",
            "scope_type": "school",
            "schools": [
                {"school_id": FIRST_SCHOOL, "term_id": FIRST_TERM, "cycle_phase_offset": 0}
            ],
        },
    ).json()
    for payload in (
        {"candidate_count": 0, "time_limit_seconds": 10},
        {"candidate_count": 6, "time_limit_seconds": 10},
        {"candidate_count": 3, "time_limit_seconds": 0},
        {"candidate_count": 3, "time_limit_seconds": 61},
    ):
        assert (
            client.post(
                f"/api/v1/timetable-projects/{project['id']}/solve",
                headers=HEADERS,
                json=payload,
            ).status_code
            == 422
        )


def test_advanced_rule_contract_is_typed_and_project_scoped(
    client: TestClient, session: Session
) -> None:
    project = ready_project(session)
    built = build_problem(session, uuid.UUID(TEST_TENANT), project.id)
    assignment_id = built.occurrences[0].assignment_id
    valid = client.post(
        f"/api/v1/timetable-projects/{project.id}/rules",
        headers=HEADERS,
        json={
            "label": "حد يومي",
            "rule_type": "assignment_max_per_day",
            "severity": "hard",
            "selector": {"assignment_id": assignment_id},
            "parameters": {"maximum": 2},
        },
    )
    assert valid.status_code == 201, valid.text
    invalid = client.post(
        f"/api/v1/timetable-projects/{project.id}/rules",
        headers=HEADERS,
        json={
            "label": "حد غير صالح",
            "rule_type": "assignment_max_per_day",
            "severity": "hard",
            "selector": {"assignment_id": assignment_id},
            "parameters": {"maximum": 0},
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "invalid_rule_parameters"

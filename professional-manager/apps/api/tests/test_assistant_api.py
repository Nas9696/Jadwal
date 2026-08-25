import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assistant_parser import ProjectEntityResolver
from app.models import AssistantRuleDraft, SchedulingRule, Teacher, TeacherSchoolMembership
from app.project_services import build_problem
from conftest import FIRST_SCHOOL, OTHER_TENANT, SHARED_TEACHER, TEST_TENANT
from test_solve_api import HEADERS, ready_project


def _parse(client: TestClient, project_id: uuid.UUID, text: str, **extra: object):
    return client.post(
        f"/api/v1/timetable-projects/{project_id}/assistant/parse",
        headers=HEADERS,
        json={"text": text, **extra},
    )


def test_parse_is_zero_rule_write_then_confirm_is_single_use_and_solver_visible(
    client: TestClient, session: Session
) -> None:
    project = ready_project(session)
    before = session.scalar(select(func.count()).select_from(SchedulingRule))
    preview = _parse(
        client,
        project.id,
        "لا تضع للمعلم معلم مشترك الحصة الأولى يوم الأحد",
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["status"] == "ready"
    assert body["parser_type"] == "deterministic_ar_v1"
    assert body["proposals"][0]["rule_type"] == "teacher_unavailable"
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(SchedulingRule)) == before

    confirmed = client.post(
        f"/api/v1/timetable-projects/{project.id}/assistant/confirm",
        headers=HEADERS,
        json={
            "preview_token": body["preview_token"],
            "proposal_ids": [body["proposals"][0]["id"]],
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["created_rules"][0]["parameters"]["period_numbers"] == [1]
    problem = build_problem(session, uuid.UUID(TEST_TENANT), project.id)
    slots = {slot.id: slot for slot in problem.slots}
    assert all(
        slots[slot_id].period != 1
        for occurrence in problem.occurrences
        for slot_id in occurrence.candidate_slot_ids
    )
    repeated = client.post(
        f"/api/v1/timetable-projects/{project.id}/assistant/confirm",
        headers=HEADERS,
        json={
            "preview_token": body["preview_token"],
            "proposal_ids": [body["proposals"][0]["id"]],
        },
    )
    assert repeated.status_code == 409
    assert repeated.json()["detail"]["code"] == "assistant_preview_already_consumed"


def test_tampered_selection_and_duplicate_ids_are_rejected(
    client: TestClient, session: Session
) -> None:
    project = ready_project(session)
    body = _parse(
        client, project.id, "يفضل أن تكون الرياضيات في أول ثلاث حصص"
    ).json()
    tampered = client.post(
        f"/api/v1/timetable-projects/{project.id}/assistant/confirm",
        headers=HEADERS,
        json={"preview_token": body["preview_token"], "proposal_ids": [str(uuid.uuid4())]},
    )
    assert tampered.status_code == 409
    duplicate = client.post(
        f"/api/v1/timetable-projects/{project.id}/assistant/confirm",
        headers=HEADERS,
        json={
            "preview_token": body["preview_token"],
            "proposal_ids": [body["proposals"][0]["id"]] * 2,
        },
    )
    assert duplicate.status_code == 422


def test_expired_preview_is_rejected(client: TestClient, session: Session) -> None:
    project = ready_project(session)
    body = _parse(client, project.id, "يفضل أن تكون الرياضيات في أول ثلاث حصص").json()
    draft = session.scalar(select(AssistantRuleDraft))
    assert draft is not None
    draft.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    response = client.post(
        f"/api/v1/timetable-projects/{project.id}/assistant/confirm",
        headers=HEADERS,
        json={
            "preview_token": body["preview_token"],
            "proposal_ids": [body["proposals"][0]["id"]],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "assistant_preview_expired"


def test_ambiguous_teacher_requires_explicit_clarification(
    client: TestClient, session: Session
) -> None:
    project = ready_project(session)
    teacher = Teacher(
        tenant_id=uuid.UUID(TEST_TENANT),
        canonical_code="T-AMBIGUOUS",
        name_ar="معلم مشترك",
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
    first = _parse(client, project.id, "لا تجعل للمعلم معلم مشترك أكثر من ٤ حصص في اليوم")
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "needs_clarification"
    assert body["proposals"] == []
    clarification = body["clarifications"][0]
    second = _parse(
        client,
        project.id,
        "لا تجعل للمعلم معلم مشترك أكثر من ٤ حصص في اليوم",
        resolutions={clarification["key"]: clarification["choices"][0]["id"]},
    )
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "ready"
    assert second.json()["proposals"][0]["parameters"] == {"maximum": 4}


def test_unsupported_and_unresolved_requests_never_create_rules(
    client: TestClient, session: Session
) -> None:
    project = ready_project(session)
    unsupported = _parse(client, project.id, "اجعل الجدول جميلا جدا")
    unresolved = _parse(client, project.id, "لا تضع للمعلم غير موجود الحصة الأولى يوم الأحد")
    assert unsupported.json()["status"] == "unsupported"
    assert unresolved.json()["status"] == "invalid"
    assert session.scalar(select(func.count()).select_from(SchedulingRule)) == 0


def test_multiple_proposals_allow_selective_confirmation(
    client: TestClient, session: Session
) -> None:
    project = ready_project(session)
    body = _parse(
        client,
        project.id,
        "لا تضع معلم مشترك الأحد الأولى ولا الثلاثاء الأخيرة",
    ).json()
    assert body["status"] == "ready"
    assert len(body["proposals"]) == 2
    chosen = body["proposals"][1]
    response = client.post(
        f"/api/v1/timetable-projects/{project.id}/assistant/confirm",
        headers=HEADERS,
        json={"preview_token": body["preview_token"], "proposal_ids": [chosen["id"]]},
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["created_rules"]) == 1
    assert response.json()["created_rules"][0]["parameters"] == chosen["parameters"]


def test_entity_resolution_is_project_scoped_for_sections_resources_and_subjects(
    session: Session,
) -> None:
    project = ready_project(session)
    resolver = ProjectEntityResolver(session, uuid.UUID(TEST_TENANT), project, {})
    assert resolver.section("أ").status == "resolved"
    assert resolver.resource("LAB-1").status == "resolved"
    assert resolver.subject("علوم").status == "unresolved"


def test_cross_tenant_project_and_stale_reference_are_rejected(
    client: TestClient, session: Session
) -> None:
    project = ready_project(session)
    foreign = client.post(
        f"/api/v1/timetable-projects/{project.id}/assistant/parse",
        headers={"X-Tenant-ID": OTHER_TENANT},
        json={"text": "لا تضع للمعلم معلم مشترك الحصة الأولى يوم الأحد"},
    )
    assert foreign.status_code == 404
    body = _parse(
        client, project.id, "لا تضع للمعلم معلم مشترك الحصة الأولى يوم الأحد"
    ).json()
    membership = session.scalar(
        select(TeacherSchoolMembership).where(
            TeacherSchoolMembership.teacher_id == uuid.UUID(SHARED_TEACHER),
            TeacherSchoolMembership.school_id == uuid.UUID(FIRST_SCHOOL),
        )
    )
    assert membership is not None
    membership.is_active = False
    session.commit()
    stale = client.post(
        f"/api/v1/timetable-projects/{project.id}/assistant/confirm",
        headers=HEADERS,
        json={
            "preview_token": body["preview_token"],
            "proposal_ids": [body["proposals"][0]["id"]],
        },
    )
    assert stale.status_code == 422
    assert session.scalar(select(func.count()).select_from(SchedulingRule)) == 0

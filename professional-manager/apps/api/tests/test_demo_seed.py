from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.demo_seed import DEMO_PROJECT_NAME, DEMO_TENANT_ID, seed_demo
from app.models import (
    PeriodTemplate,
    Resource,
    SchedulingRule,
    Teacher,
    TeacherSchoolMembership,
    TeachingAssignment,
    TimetableProject,
)
from app.project_services import preflight


def test_realistic_demo_seed_is_idempotent_and_ready(session: Session) -> None:
    created = seed_demo(session)
    assert created["status"] == "created"
    project = session.scalar(
        select(TimetableProject).where(
            TimetableProject.tenant_id == DEMO_TENANT_ID,
            TimetableProject.name_ar == DEMO_PROJECT_NAME,
        )
    )
    assert project is not None
    assert session.scalar(
        select(func.count()).select_from(Teacher).where(Teacher.tenant_id == DEMO_TENANT_ID)
    ) == 13

    reset = seed_demo(session, reset=True)
    assert reset["status"] == "reset"
    assert session.scalar(
        select(func.count()).select_from(Teacher).where(Teacher.tenant_id == DEMO_TENANT_ID)
    ) == 13
    reset_project = session.scalar(
        select(TimetableProject).where(
            TimetableProject.tenant_id == DEMO_TENANT_ID,
            TimetableProject.name_ar == DEMO_PROJECT_NAME,
        )
    )
    assert reset_project is not None
    assert preflight(session, DEMO_TENANT_ID, reset_project.id)["errors"] == 0
    assert session.scalar(
        select(func.count())
        .select_from(TeachingAssignment)
        .where(TeachingAssignment.tenant_id == DEMO_TENANT_ID)
    ) == 19
    assert session.scalar(
        select(func.count())
        .select_from(SchedulingRule)
        .where(SchedulingRule.tenant_id == DEMO_TENANT_ID)
    ) == 7
    assert session.scalar(
        select(func.count())
        .select_from(PeriodTemplate)
        .where(PeriodTemplate.tenant_id == DEMO_TENANT_ID)
    ) == 90
    assert session.scalar(
        select(func.count())
        .select_from(Resource)
        .where(Resource.tenant_id == DEMO_TENANT_ID, Resource.exclusive.is_(True))
    ) == 3
    shared = session.scalar(
        select(Teacher.id)
        .join(TeacherSchoolMembership, TeacherSchoolMembership.teacher_id == Teacher.id)
        .where(Teacher.tenant_id == DEMO_TENANT_ID)
        .group_by(Teacher.id)
        .having(func.count(TeacherSchoolMembership.id) > 1)
    )
    assert shared is not None
    assert preflight(session, DEMO_TENANT_ID, reset_project.id)["errors"] == 0

    unchanged = seed_demo(session)
    assert unchanged["status"] == "already_ready"
    assert session.scalar(
        select(func.count()).select_from(Teacher).where(Teacher.tenant_id == DEMO_TENANT_ID)
    ) == 13

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import seed as seed_module
from app.models import School, Section, Subject, Teacher
from app.seed import DEMO_SCHOOL_ID, DEMO_TENANT_ID


def test_default_seed_creates_an_empty_editable_workspace(session: Session, monkeypatch) -> None:
    factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    monkeypatch.setattr(seed_module, "SessionLocal", factory)

    result = seed_module.seed()

    assert result["status"] == "created"
    school = session.scalar(select(School).where(School.id == DEMO_SCHOOL_ID))
    assert school is not None
    assert school.name_ar == "مدرستي"
    assert session.scalar(select(func.count()).select_from(Teacher).where(Teacher.tenant_id == DEMO_TENANT_ID)) == 0
    assert session.scalar(select(func.count()).select_from(Subject).where(Subject.tenant_id == DEMO_TENANT_ID)) == 0
    assert session.scalar(select(func.count()).select_from(Section).where(Section.tenant_id == DEMO_TENANT_ID)) == 0

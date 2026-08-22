import os
import uuid

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Grade, Resource, School, Section, Stage, Subject, Teacher, Tenant

TEST_TENANT = "10000000-0000-4000-8000-000000000001"
OTHER_TENANT = "20000000-0000-4000-8000-000000000001"
FIRST_SCHOOL = "10000000-0000-4000-8000-000000000101"
SECOND_SCHOOL = "10000000-0000-4000-8000-000000000102"
OTHER_SCHOOL = "20000000-0000-4000-8000-000000000101"
SHARED_TEACHER = "10000000-0000-4000-8000-000000000201"
OTHER_TEACHER = "20000000-0000-4000-8000-000000000201"

@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        for tenant_id, slug, tenant_name in [
            (TEST_TENANT, "first", "مجموعة النور"),
            (OTHER_TENANT, "other", "مجموعة أخرى"),
        ]:
            tenant = Tenant(id=uuid.UUID(tenant_id), name_ar=tenant_name, slug=slug)
            db.add(tenant)
        db.flush()
        schools = [
            School(id=uuid.UUID(FIRST_SCHOOL), tenant_id=uuid.UUID(TEST_TENANT), name_ar="مدرسة النور", code="S1"),
            School(id=uuid.UUID(SECOND_SCHOOL), tenant_id=uuid.UUID(TEST_TENANT), name_ar="مدرسة الفجر", code="S2"),
            School(id=uuid.UUID(OTHER_SCHOOL), tenant_id=uuid.UUID(OTHER_TENANT), name_ar="مدرسة أخرى", code="S1"),
        ]
        db.add_all(schools)
        db.add_all([
            Teacher(id=uuid.UUID(SHARED_TEACHER), tenant_id=uuid.UUID(TEST_TENANT), canonical_code="T1", name_ar="معلم مشترك"),
            Teacher(id=uuid.UUID(OTHER_TEACHER), tenant_id=uuid.UUID(OTHER_TENANT), canonical_code="T1", name_ar="معلم آخر"),
            Subject(tenant_id=uuid.UUID(TEST_TENANT), school_id=uuid.UUID(FIRST_SCHOOL), code="M1", name_ar="رياضيات"),
            Subject(tenant_id=uuid.UUID(TEST_TENANT), school_id=uuid.UUID(SECOND_SCHOOL), code="M2", name_ar="علوم"),
            Resource(tenant_id=uuid.UUID(TEST_TENANT), school_id=uuid.UUID(FIRST_SCHOOL), name_ar="معمل أول"),
            Resource(tenant_id=uuid.UUID(TEST_TENANT), school_id=uuid.UUID(SECOND_SCHOOL), name_ar="معمل ثان"),
        ])
        stage = Stage(tenant_id=uuid.UUID(TEST_TENANT), school_id=uuid.UUID(FIRST_SCHOOL), code="P", name_ar="ابتدائي")
        db.add(stage)
        db.flush()
        grade = Grade(tenant_id=uuid.UUID(TEST_TENANT), stage_id=stage.id, name_ar="الأول", order=1)
        db.add(grade)
        db.flush()
        db.add(Section(tenant_id=uuid.UUID(TEST_TENANT), grade_id=grade.id, name_ar="أ"))
        db.commit()
        yield db

@pytest.fixture
def client(session: Session) -> TestClient:
    def override_db():
        yield session
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

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
from app.models import School, Tenant

TEST_TENANT = "10000000-0000-4000-8000-000000000001"
OTHER_TENANT = "20000000-0000-4000-8000-000000000001"

@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        for tenant_id, slug, school_name in [(TEST_TENANT, "first", "مدرسة النور"), (OTHER_TENANT, "other", "مدرسة أخرى")]:
            tenant = Tenant(id=uuid.UUID(tenant_id), name_ar=school_name, slug=slug)
            db.add(tenant)
            db.flush()
            db.add(School(tenant_id=tenant.id, name_ar=school_name, code="S1"))
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

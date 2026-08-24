import uuid
from io import BytesIO
from datetime import time

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core_schemas import DayBuilderInput
from app.core_services import build_day_blocks
from app.models import Grade, PeriodTemplate, SchedulingRule, Section, SectionOffering, Stage, TeacherSchoolMembership
from app.config import Settings
from conftest import FIRST_SCHOOL, SHARED_TEACHER, TEST_TENANT


HEADERS = {"X-Tenant-ID": TEST_TENANT}
BASE = f"/api/v1/schools/{FIRST_SCHOOL}/core-workflow"


def test_cors_environment_accepts_demo_value_without_json(monkeypatch) -> None:
    monkeypatch.setenv("API_CORS_ORIGINS", "http://localhost:3000")
    assert Settings(_env_file=None).api_cors_origins == ["http://localhost:3000"]


def school_day_payload() -> dict[str, object]:
    return {
        "school_name": "مدرسة النور المطورة",
        "stages": ["primary"],
        "weekdays": [0, 1, 2, 3, 4],
        "period_count": 6,
        "assembly_start": "06:45:00",
        "assembly_minutes": 15,
        "period_minutes": 45,
        "breaks": [{"after_period": 2, "duration_minutes": 20}],
        "prayer": {"after_period": 4, "duration_minutes": 15},
    }


def test_day_builder_produces_contiguous_realistic_times() -> None:
    blocks = build_day_blocks(DayBuilderInput.model_validate(school_day_payload()))
    assert blocks[0]["starts_at"] == time(6, 45)
    assert blocks[0]["ends_at"] == time(7, 0)
    assert blocks[1]["starts_at"] == time(7, 0)
    assert blocks[2]["ends_at"] == time(8, 30)
    assert blocks[3]["starts_at"] == time(8, 30)
    assert blocks[3]["ends_at"] == time(8, 50)
    assert all(left["ends_at"] == right["starts_at"] for left, right in zip(blocks, blocks[1:], strict=False))


def test_simple_school_setup_creates_hidden_defaults_and_days(client: TestClient) -> None:
    response = client.put(f"{BASE}/school-day", headers=HEADERS, json=school_day_payload())
    assert response.status_code == 200, response.text
    snapshot = client.get(BASE, headers=HEADERS)
    assert snapshot.status_code == 200
    data = snapshot.json()
    assert data["school"]["name_ar"] == "مدرسة النور المطورة"
    assert data["selected_stages"] == ["primary"]
    assert data["weekdays"] == [0, 1, 2, 3, 4]
    assert [block["starts_at"][:5] for block in data["blocks"][:4]] == ["06:45", "07:00", "07:45", "08:30"]


def test_entered_teacher_name_is_persisted_and_returned(client: TestClient) -> None:
    response = client.post(f"{BASE}/teachers", headers=HEADERS, json={"name_ar": "ناصر آل مستنير", "workload_limit": 24})
    assert response.status_code == 201, response.text
    snapshot = client.get(BASE, headers=HEADERS)
    assert snapshot.status_code == 200
    assert "ناصر آل مستنير" in [teacher["name_ar"] for teacher in snapshot.json()["teachers"]]


def test_bulk_teacher_paste_ignores_duplicate_names(client: TestClient) -> None:
    response = client.post(f"{BASE}/teachers/bulk", headers=HEADERS, json={"names": ["أحمد علي", "سارة محمد", "أحمد علي", "  "], "workload_limit": 22})
    assert response.status_code == 201, response.text
    assert response.json()["created"] == 2
    snapshot = client.get(BASE, headers=HEADERS).json()
    added = {teacher["name_ar"]: teacher["workload_limit"] for teacher in snapshot["teachers"]}
    assert added == {"أحمد علي": 22, "سارة محمد": 22}


def test_bulk_teacher_excel_uses_the_name_column(client: TestClient) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["اسم المعلم", "ملاحظات"])
    sheet.append(["خالد حسن", "منتدب"])
    sheet.append(["نورة سعيد", ""])
    content = BytesIO()
    workbook.save(content)
    response = client.post(
        f"{BASE}/teachers/bulk-file",
        headers=HEADERS,
        files={"file": ("teachers.xlsx", content.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"workload_limit": "24"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["created"] == 2
    assert response.json()["names"] == ["خالد حسن", "نورة سعيد"]


def test_period_edit_recalculates_following_blocks(client: TestClient, session: Session) -> None:
    client.put(f"{BASE}/school-day", headers=HEADERS, json=school_day_payload())
    blocks = list(session.scalars(select(PeriodTemplate).where(PeriodTemplate.weekday_index == 0).order_by(PeriodTemplate.block_order)))
    first_lesson = next(block for block in blocks if block.period_number == 1)
    second_lesson = next(block for block in blocks if block.period_number == 2)
    response = client.put(
        f"{BASE}/periods/{first_lesson.id}",
        headers=HEADERS,
        json={
            "block_order": first_lesson.block_order,
            "label_ar": first_lesson.label_ar,
            "block_type": "lesson",
            "period_number": 1,
            "starts_at": "07:00:00",
            "ends_at": "07:50:00",
            "recalculate_following": True,
        },
    )
    assert response.status_code == 200
    session.refresh(second_lesson)
    assert second_lesson.starts_at == time(7, 50)
    assert second_lesson.ends_at == time(8, 35)


def test_primary_stage_creates_human_grade_and_section_names(client: TestClient, session: Session) -> None:
    response = client.put(
        f"{BASE}/structure",
        headers=HEADERS,
        json={
            "stage": "primary",
            "grades": [
                {"grade_name": "الأول", "section_count": 3},
                {"grade_name": "الثاني", "section_count": 2},
                {"grade_name": "الثالث", "section_count": 1},
                {"grade_name": "الرابع", "section_count": 0},
                {"grade_name": "الخامس", "section_count": 0},
                {"grade_name": "السادس", "section_count": 0},
            ],
        },
    )
    assert response.status_code == 200, response.text
    stage = session.scalar(select(Stage).where(Stage.school_id == uuid.UUID(FIRST_SCHOOL), Stage.name_ar == "المرحلة الابتدائية"))
    assert stage is not None
    grade = session.scalar(select(Grade).where(Grade.stage_id == stage.id, Grade.name_ar == "الأول"))
    assert grade is not None
    names = list(session.scalars(select(Section.name_ar).where(Section.grade_id == grade.id).order_by(Section.name_ar)))
    assert names == ["الأول أ", "الأول ب", "الأول ج"]


def test_reducing_section_count_preserves_data_but_hides_excess_sections(client: TestClient, session: Session) -> None:
    payload = {"stage": "primary", "grades": [{"grade_name": name, "section_count": 3 if name == "الأول" else 0} for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")]}
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=payload).status_code == 200
    payload["grades"][0]["section_count"] = 1
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=payload).status_code == 200
    snapshot = client.get(BASE, headers=HEADERS).json()
    assert [item["name_ar"] for item in snapshot["sections"] if item["name_ar"].startswith("الأول ")] == ["الأول أ"]
    assert session.scalar(select(SectionOffering).where(SectionOffering.section_id == select(Section.id).where(Section.name_ar == "الأول ب").scalar_subquery())).is_active is False


def test_teacher_availability_grid_persists_unavailable_and_avoid(client: TestClient, session: Session) -> None:
    session.add(TeacherSchoolMembership(tenant_id=uuid.UUID(TEST_TENANT), teacher_id=uuid.UUID(SHARED_TEACHER), school_id=uuid.UUID(FIRST_SCHOOL), is_home_school=True, is_active=True))
    session.commit()
    client.put(f"{BASE}/school-day", headers=HEADERS, json=school_day_payload())
    response = client.put(
        f"{BASE}/teachers/{SHARED_TEACHER}/availability",
        headers=HEADERS,
        json={"cells": [
            {"weekday_index": 0, "period_number": 1, "state": "unavailable"},
            {"weekday_index": 1, "period_number": 2, "state": "avoid"},
            {"weekday_index": 2, "period_number": 3, "state": "available"},
        ]},
    )
    assert response.status_code == 200, response.text
    rules = list(session.scalars(select(SchedulingRule).where(SchedulingRule.selector["teacher_id"].as_string() == SHARED_TEACHER)))
    assert {rule.rule_type for rule in rules} == {"teacher_unavailable", "teacher_avoided_time"}

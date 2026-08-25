import uuid
from io import BytesIO
from datetime import time

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core_schemas import DayBuilderInput
from app.core_services import build_day_blocks
from app.assignment_services import save_assignment
from app.models import (
    CurriculumRequirement,
    Grade,
    PeriodTemplate,
    SchedulingRule,
    Section,
    SectionOffering,
    Stage,
    TeacherSchoolMembership,
    TeachingAssignment,
    TeachingAssignmentTeacher,
    TimetableCandidate,
    TimetableEntry,
    TimetableSolveRun,
)
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


def test_teacher_duplicate_detection_understands_arabic_variants(client: TestClient) -> None:
    first = client.post(f"{BASE}/teachers", headers=HEADERS, json={"name_ar": "أحمد العلي", "workload_limit": 24})
    assert first.status_code == 201, first.text
    blocked = client.post(f"{BASE}/teachers", headers=HEADERS, json={"name_ar": " احمد  العلى ", "workload_limit": 22})
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "similar_teacher_confirmation_required"
    approved = client.post(f"{BASE}/teachers", headers=HEADERS, json={"name_ar": "احمد العلى", "workload_limit": 22, "allow_similar": True})
    assert approved.status_code == 201, approved.text


def test_teacher_can_be_edited_and_deleted_when_unassigned(client: TestClient) -> None:
    created = client.post(f"{BASE}/teachers", headers=HEADERS, json={"name_ar": "معلم مؤقت", "workload_limit": 24}).json()
    updated = client.put(f"{BASE}/teachers/{created['id']}", headers=HEADERS, json={"name_ar": "معلم العلوم", "workload_limit": 18})
    assert updated.status_code == 200, updated.text
    assert updated.json()["workload_limit"] == 18
    removed = client.delete(f"{BASE}/teachers/{created['id']}", headers=HEADERS)
    assert removed.status_code == 204, removed.text
    assert created["id"] not in [item["id"] for item in client.get(BASE, headers=HEADERS).json()["teachers"]]


def test_teacher_cascade_delete_removes_assignments_but_keeps_school_plan(client: TestClient) -> None:
    teacher = client.post(f"{BASE}/teachers", headers=HEADERS, json={"name_ar": "معلم سيغادر", "workload_limit": 24}).json()
    structure = {"stage": "primary", "grades": [{"grade_name": name, "section_count": 1 if name == "الأول" else 0} for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")]}
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=structure).status_code == 200
    snapshot = client.get(BASE, headers=HEADERS).json()
    subject_id = snapshot["subjects"][0]["id"]
    section_id = snapshot["sections"][0]["id"]
    created = client.post(f"{BASE}/assignments", headers=HEADERS, json={"term_id": snapshot["term_id"], "section_ids": [section_id], "subject_id": subject_id, "teacher_id": teacher["id"], "weekly_occurrences": 5})
    assert created.status_code == 201, created.text
    removed = client.delete(f"{BASE}/teachers/{teacher['id']}?cascade=true", headers=HEADERS)
    assert removed.status_code == 204, removed.text
    refreshed = client.get(BASE, headers=HEADERS).json()
    assert teacher["id"] not in [item["id"] for item in refreshed["teachers"]]
    assert all(teacher["id"] not in item["teacher_ids"] for item in refreshed["assignments"])
    assert subject_id in [item["id"] for item in refreshed["subjects"]]
    assert section_id in [item["id"] for item in refreshed["sections"]]


def test_similar_teacher_merge_preserves_assignments(client: TestClient) -> None:
    source = client.post(f"{BASE}/teachers", headers=HEADERS, json={"name_ar": "أحمد العلي", "workload_limit": 24}).json()
    target = client.post(f"{BASE}/teachers", headers=HEADERS, json={"name_ar": "احمد العلى", "workload_limit": 24, "allow_similar": True}).json()
    structure = {"stage": "primary", "grades": [{"grade_name": name, "section_count": 1 if name == "الأول" else 0} for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")]}
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=structure).status_code == 200
    snapshot = client.get(BASE, headers=HEADERS).json()
    assignment = {"term_id": snapshot["term_id"], "section_ids": [snapshot["sections"][0]["id"]], "subject_id": snapshot["subjects"][0]["id"], "weekly_occurrences": 5}
    created = client.post(f"{BASE}/assignments", headers=HEADERS, json={**assignment, "teacher_id": source["id"]})
    assert created.status_code == 201, created.text
    duplicate = client.post(f"{BASE}/assignments", headers=HEADERS, json={**assignment, "teacher_id": target["id"]})
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "section_subject_already_assigned"
    merged = client.post(f"{BASE}/teachers/merge", headers=HEADERS, json={"source_teacher_id": source["id"], "target_teacher_id": target["id"]})
    assert merged.status_code == 200, merged.text
    refreshed = client.get(BASE, headers=HEADERS).json()
    assert source["id"] not in [item["id"] for item in refreshed["teachers"]]
    target_assignments = [item for item in refreshed["assignments"] if target["id"] in item["teacher_ids"]]
    assert len(target_assignments) == 1
    assert target_assignments[0]["weekly_occurrences"] == 5
    refreshed_target = next(item for item in refreshed["teachers"] if item["id"] == target["id"])
    assert refreshed_target["assigned"] == 5


def test_subject_crud_and_custom_order(client: TestClient) -> None:
    created = client.post(f"{BASE}/subjects", headers=HEADERS, json={"name_ar": "مادة تجريبية"}).json()
    updated = client.put(f"{BASE}/subjects/{created['id']}", headers=HEADERS, json={"name_ar": "مادة اختيارية"})
    assert updated.status_code == 200, updated.text
    ids = [item["id"] for item in client.get(BASE, headers=HEADERS).json()["subjects"]]
    ordered = [created["id"], *[item for item in ids if item != created["id"]]]
    assert client.put(f"{BASE}/ordering/subjects", headers=HEADERS, json={"ids": ordered}).status_code == 200
    assert client.get(BASE, headers=HEADERS).json()["subjects"][0]["id"] == created["id"]
    assert client.delete(f"{BASE}/subjects/{created['id']}", headers=HEADERS).status_code == 204
    assert created["id"] not in [item["id"] for item in client.get(BASE, headers=HEADERS).json()["subjects"]]


def test_section_can_be_renamed_deleted_and_ordered(client: TestClient) -> None:
    structure = {"stage": "primary", "grades": [{"grade_name": name, "section_count": 2 if name == "الأول" else 0} for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")]}
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=structure).status_code == 200
    sections = client.get(BASE, headers=HEADERS).json()["sections"]
    assert client.put(f"{BASE}/sections/{sections[0]['id']}", headers=HEADERS, json={"name_ar": "الأول المتميز"}).status_code == 200
    reversed_ids = [item["id"] for item in reversed(sections)]
    assert client.put(f"{BASE}/ordering/sections", headers=HEADERS, json={"ids": reversed_ids}).status_code == 200
    assert client.get(BASE, headers=HEADERS).json()["sections"][0]["id"] == reversed_ids[0]
    assert client.delete(f"{BASE}/sections/{sections[0]['id']}", headers=HEADERS).status_code == 204
    assert sections[0]["id"] not in [item["id"] for item in client.get(BASE, headers=HEADERS).json()["sections"]]


def test_deleting_section_removes_its_assignments_but_keeps_teacher_and_subject(client: TestClient) -> None:
    teacher = client.post(f"{BASE}/teachers", headers=HEADERS, json={"name_ar": "معلم يبقى بلا إسناد", "workload_limit": 24}).json()
    structure = {"stage": "primary", "grades": [{"grade_name": name, "section_count": 1 if name == "الأول" else 0} for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")]}
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=structure).status_code == 200
    snapshot = client.get(BASE, headers=HEADERS).json()
    section_id = snapshot["sections"][0]["id"]
    subject_id = snapshot["subjects"][0]["id"]
    created = client.post(f"{BASE}/assignments", headers=HEADERS, json={"term_id": snapshot["term_id"], "section_ids": [section_id], "subject_id": subject_id, "teacher_id": teacher["id"], "weekly_occurrences": 5})
    assert created.status_code == 201, created.text
    assignment_id = next(item["id"] for item in client.get(BASE, headers=HEADERS).json()["assignments"] if teacher["id"] in item["teacher_ids"])

    removed = client.delete(f"{BASE}/sections/{section_id}", headers=HEADERS)
    assert removed.status_code == 204, removed.text
    refreshed = client.get(BASE, headers=HEADERS).json()
    assert section_id not in [item["id"] for item in refreshed["sections"]]
    assert assignment_id not in [item["id"] for item in refreshed["assignments"]]
    kept_teacher = next(item for item in refreshed["teachers"] if item["id"] == teacher["id"])
    assert kept_teacher["assigned"] == 0
    assert subject_id in [item["id"] for item in refreshed["subjects"]]


def test_structure_builder_applies_selected_naming_pattern(client: TestClient) -> None:
    structure = {"stage": "primary", "naming_pattern": "number_slash_letter", "reset_names": True, "grades": [{"grade_name": name, "section_count": 2 if name == "الأول" else 0} for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")]}
    response = client.put(f"{BASE}/structure", headers=HEADERS, json=structure)
    assert response.status_code == 200, response.text
    names = [item["name_ar"] for item in client.get(BASE, headers=HEADERS).json()["sections"]]
    assert "1 / أ" in names
    assert "1 / ب" in names


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


def test_curriculum_plan_is_saved_and_returned_in_core_snapshot(client: TestClient, session: Session) -> None:
    payload = {"stage": "primary", "grades": [{"grade_name": name, "section_count": 2 if name == "الأول" else 0} for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")]}
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=payload).status_code == 200
    snapshot = client.get(BASE, headers=HEADERS).json()
    grade_id = next(item["id"] for item in snapshot["grades"] if item["name_ar"] == "الأول")
    subject_id = snapshot["subjects"][0]["id"]
    saved = client.put(f"{BASE}/curriculum", headers=HEADERS, json={"cells": [{"grade_id": grade_id, "subject_id": subject_id, "weekly_occurrences": 5}]})
    assert saved.status_code == 200, saved.text
    assert saved.json()["saved"] == 1
    session.expire_all()
    requirement = session.scalar(select(CurriculumRequirement).where(CurriculumRequirement.grade_id == uuid.UUID(grade_id), CurriculumRequirement.subject_id == uuid.UUID(subject_id)))
    assert requirement is not None and requirement.weekly_occurrences == 5
    assert client.get(BASE, headers=HEADERS).json()["curriculum"][0]["weekly_occurrences"] == 5


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


def test_teacher_first_assignment_can_edit_move_and_delete(
    client: TestClient, session: Session
) -> None:
    session.add(
        TeacherSchoolMembership(
            tenant_id=uuid.UUID(TEST_TENANT),
            teacher_id=uuid.UUID(SHARED_TEACHER),
            school_id=uuid.UUID(FIRST_SCHOOL),
            is_home_school=True,
            is_active=True,
        )
    )
    session.commit()
    target = client.post(
        f"{BASE}/teachers",
        headers=HEADERS,
        json={"name_ar": "معلم النقل", "workload_limit": 24},
    ).json()
    structure = {
        "stage": "primary",
        "grades": [
            {"grade_name": name, "section_count": 1 if name == "الأول" else 0}
            for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")
        ],
    }
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=structure).status_code == 200
    snapshot = client.get(BASE, headers=HEADERS).json()
    subject_id = snapshot["subjects"][0]["id"]
    section_id = snapshot["sections"][0]["id"]
    payload = {
        "term_id": snapshot["term_id"],
        "section_ids": [section_id],
        "subject_id": subject_id,
        "teacher_id": SHARED_TEACHER,
        "weekly_occurrences": 5,
    }
    created = client.post(f"{BASE}/assignments", headers=HEADERS, json=payload)
    assert created.status_code == 201, created.text
    assignment_id = str(created.json()["assignment_ids"][0])
    row = next(
        item
        for item in client.get(BASE, headers=HEADERS).json()["assignments"]
        if item["id"] == assignment_id
    )
    assert row["teacher_ids"] == [SHARED_TEACHER]
    assert row["subject_id"] == subject_id
    assert row["section_ids"] == [section_id]

    updated = client.put(
        f"{BASE}/assignments/{assignment_id}",
        headers=HEADERS,
        json={**payload, "weekly_occurrences": 6},
    )
    assert updated.status_code == 200, updated.text

    copied = client.post(
        f"{BASE}/assignments/transfer",
        headers=HEADERS,
        json={
            "source_teacher_id": SHARED_TEACHER,
            "target_teacher_id": target["id"],
            "assignment_ids": [assignment_id],
            "mode": "copy",
        },
    )
    assert copied.status_code == 422

    moved = client.post(
        f"{BASE}/assignments/transfer",
        headers=HEADERS,
        json={
            "source_teacher_id": SHARED_TEACHER,
            "target_teacher_id": target["id"],
            "assignment_ids": [assignment_id],
            "mode": "move",
        },
    )
    assert moved.status_code == 200, moved.text
    source = next(
        item
        for item in client.get(BASE, headers=HEADERS).json()["teachers"]
        if item["id"] == SHARED_TEACHER
    )
    assert source["assigned"] == 0
    moved_target = next(
        item for item in client.get(BASE, headers=HEADERS).json()["teachers"]
        if item["id"] == target["id"]
    )
    assert moved_target["assigned"] == 6
    assert client.delete(f"{BASE}/assignments/{assignment_id}", headers=HEADERS).status_code == 204
    refreshed = client.get(BASE, headers=HEADERS).json()
    assert assignment_id not in [item["id"] for item in refreshed["assignments"]]
    refreshed_target = next(item for item in refreshed["teachers"] if item["id"] == target["id"])
    assert refreshed_target["assigned"] == 0


def test_assignment_overload_requires_explicit_approval(client: TestClient) -> None:
    teacher = client.post(
        f"{BASE}/teachers",
        headers=HEADERS,
        json={"name_ar": "معلم النصاب المحدود", "workload_limit": 4},
    ).json()
    structure = {
        "stage": "primary",
        "grades": [
            {"grade_name": name, "section_count": 1 if name == "الأول" else 0}
            for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")
        ],
    }
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=structure).status_code == 200
    snapshot = client.get(BASE, headers=HEADERS).json()
    payload = {
        "term_id": snapshot["term_id"],
        "section_ids": [snapshot["sections"][0]["id"]],
        "subject_id": snapshot["subjects"][0]["id"],
        "teacher_id": teacher["id"],
        "weekly_occurrences": 5,
    }
    blocked = client.post(f"{BASE}/assignments", headers=HEADERS, json=payload)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "teacher_workload_limit_exceeded"
    approved = client.post(
        f"{BASE}/assignments", headers=HEADERS, json={**payload, "allow_overload": True}
    )
    assert approved.status_code == 201, approved.text


def test_delete_assignment_preserves_generated_history(
    client: TestClient, session: Session
) -> None:
    session.add(
        TeacherSchoolMembership(
            tenant_id=uuid.UUID(TEST_TENANT),
            teacher_id=uuid.UUID(SHARED_TEACHER),
            school_id=uuid.UUID(FIRST_SCHOOL),
            is_home_school=True,
            is_active=True,
        )
    )
    session.commit()
    structure = {
        "stage": "primary",
        "grades": [
            {"grade_name": name, "section_count": 1 if name == "الأول" else 0}
            for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")
        ],
    }
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=structure).status_code == 200
    snapshot = client.get(BASE, headers=HEADERS).json()
    created = client.post(
        f"{BASE}/assignments",
        headers=HEADERS,
        json={
            "term_id": snapshot["term_id"],
            "section_ids": [snapshot["sections"][0]["id"]],
            "subject_id": snapshot["subjects"][0]["id"],
            "teacher_id": SHARED_TEACHER,
            "weekly_occurrences": 5,
        },
    )
    assignment_id = uuid.UUID(created.json()["assignment_ids"][0])
    solve = TimetableSolveRun(
        tenant_id=uuid.UUID(TEST_TENANT),
        timetable_project_id=uuid.UUID(snapshot["project_id"]),
        status="completed",
        input_fingerprint="history-test",
        input_snapshot={},
        requested_candidates=1,
        time_limit_seconds=1,
    )
    session.add(solve)
    session.flush()
    candidate = TimetableCandidate(
        tenant_id=uuid.UUID(TEST_TENANT),
        solve_run_id=solve.id,
        rank=1,
        solver_status="feasible",
    )
    session.add(candidate)
    session.flush()
    session.add(
        TimetableEntry(
            tenant_id=uuid.UUID(TEST_TENANT),
            candidate_id=candidate.id,
            occurrence_id="history-1",
            assignment_id=assignment_id,
            subject_id=uuid.UUID(snapshot["subjects"][0]["id"]),
            slot_id="0:1",
            school_id=uuid.UUID(FIRST_SCHOOL),
            project_cycle_week_index=0,
            weekday_index=0,
            starts_at_minute=420,
            ends_at_minute=465,
        )
    )
    session.commit()

    deleted = client.delete(f"{BASE}/assignments/{assignment_id}", headers=HEADERS)
    assert deleted.status_code == 204, deleted.text
    session.expire_all()
    assert session.get(TeachingAssignment, assignment_id) is not None
    assert session.scalar(
        select(TeachingAssignmentTeacher).where(
            TeachingAssignmentTeacher.teaching_assignment_id == assignment_id
        )
    ) is None
    assert str(assignment_id) not in {
        item["id"] for item in client.get(BASE, headers=HEADERS).json()["assignments"]
    }
    report = client.post(
        f"/api/v1/timetable-projects/{snapshot['project_id']}/preflight", headers=HEADERS
    )
    assert report.status_code == 200, report.text
    assert "assignment_without_teacher" not in {
        item["code"] for item in report.json()["diagnostics"]
    }


def test_deduplicate_assignments_repairs_imported_duplicates_with_history(
    client: TestClient, session: Session
) -> None:
    session.add(
        TeacherSchoolMembership(
            tenant_id=uuid.UUID(TEST_TENANT),
            teacher_id=uuid.UUID(SHARED_TEACHER),
            school_id=uuid.UUID(FIRST_SCHOOL),
            is_home_school=True,
            is_active=True,
        )
    )
    session.commit()
    structure = {
        "stage": "primary",
        "grades": [
            {"grade_name": name, "section_count": 1 if name == "الأول" else 0}
            for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")
        ],
    }
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=structure).status_code == 200
    snapshot = client.get(BASE, headers=HEADERS).json()
    offering = session.scalar(
        select(SectionOffering).where(
            SectionOffering.section_id == uuid.UUID(snapshot["sections"][0]["id"]),
            SectionOffering.term_id == uuid.UUID(snapshot["term_id"]),
        )
    )
    assert offering is not None
    assignment_payload = {
        "term_id": uuid.UUID(snapshot["term_id"]),
        "subject_id": uuid.UUID(snapshot["subjects"][0]["id"]),
        "weekly_occurrences": 5,
        "teacher_ids": [uuid.UUID(SHARED_TEACHER)],
        "section_offering_ids": [offering.id],
        "resource_ids": [],
        "notes": "بيانات مستوردة مكررة",
    }
    first = save_assignment(
        session, uuid.UUID(TEST_TENANT), uuid.UUID(FIRST_SCHOOL), assignment_payload
    )
    duplicate = save_assignment(
        session, uuid.UUID(TEST_TENANT), uuid.UUID(FIRST_SCHOOL), assignment_payload
    )
    solve = TimetableSolveRun(
        tenant_id=uuid.UUID(TEST_TENANT),
        timetable_project_id=uuid.UUID(snapshot["project_id"]),
        status="completed",
        input_fingerprint="deduplicate-history-test",
        input_snapshot={},
        requested_candidates=1,
        time_limit_seconds=1,
    )
    session.add(solve)
    session.flush()
    candidate = TimetableCandidate(
        tenant_id=uuid.UUID(TEST_TENANT),
        solve_run_id=solve.id,
        rank=1,
        solver_status="feasible",
    )
    session.add(candidate)
    session.flush()
    session.add(
        TimetableEntry(
            tenant_id=uuid.UUID(TEST_TENANT),
            candidate_id=candidate.id,
            occurrence_id="duplicate-history-1",
            assignment_id=duplicate["assignment_id"],
            subject_id=uuid.UUID(snapshot["subjects"][0]["id"]),
            slot_id="0:1",
            school_id=uuid.UUID(FIRST_SCHOOL),
            project_cycle_week_index=0,
            weekday_index=0,
            starts_at_minute=420,
            ends_at_minute=465,
        )
    )
    session.commit()

    repaired = client.post(
        f"{BASE}/teachers/{SHARED_TEACHER}/deduplicate-assignments", headers=HEADERS
    )
    assert repaired.status_code == 200, repaired.text
    assert repaired.json()["removed"] == 1
    refreshed = client.get(BASE, headers=HEADERS).json()
    teacher_assignments = [
        item for item in refreshed["assignments"] if SHARED_TEACHER in item["teacher_ids"]
    ]
    assert len(teacher_assignments) == 1
    assert teacher_assignments[0]["id"] == str(first["assignment_id"])
    teacher = next(item for item in refreshed["teachers"] if item["id"] == SHARED_TEACHER)
    assert teacher["assigned"] == 5
    assert session.get(TeachingAssignment, duplicate["assignment_id"]) is not None


def test_same_subject_in_different_numeric_sections_is_not_duplicate(client: TestClient) -> None:
    teacher = client.post(f"{BASE}/teachers", headers=HEADERS, json={"name_ar": "معلم لغتي للفصول", "workload_limit": 24}).json()
    structure = {"stage": "primary", "naming_pattern": "number_slash_number", "reset_names": True, "grades": [{"grade_name": name, "section_count": 2 if name == "الأول" else 0} for name in ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس")]}
    assert client.put(f"{BASE}/structure", headers=HEADERS, json=structure).status_code == 200
    snapshot = client.get(BASE, headers=HEADERS).json()
    subject_id = snapshot["subjects"][0]["id"]
    for section in snapshot["sections"][:2]:
        response = client.post(f"{BASE}/assignments", headers=HEADERS, json={"term_id": snapshot["term_id"], "section_ids": [section["id"]], "subject_id": subject_id, "teacher_id": teacher["id"], "weekly_occurrences": 2})
        assert response.status_code == 201, response.text
    repaired = client.post(f"{BASE}/teachers/{teacher['id']}/deduplicate-assignments", headers=HEADERS)
    assert repaired.status_code == 200, repaired.text
    assert repaired.json()["removed"] == 0
    assignments = [item for item in client.get(BASE, headers=HEADERS).json()["assignments"] if teacher["id"] in item["teacher_ids"]]
    assert len(assignments) == 2
    assert {tuple(item["section_ids"]) for item in assignments} == {(snapshot["sections"][0]["id"],), (snapshot["sections"][1]["id"],)}

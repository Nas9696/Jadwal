from fastapi.testclient import TestClient

from conftest import (
    FIRST_SCHOOL,
    FIRST_TERM,
    OTHER_SCHOOL,
    OTHER_TEACHER,
    OTHER_TERM,
    OTHER_TENANT,
    SECOND_SCHOOL,
    SECOND_TERM,
    SHARED_TEACHER,
    TEST_TENANT,
    TEST_COMPLEX,
)

def test_tenant_header_is_required(client: TestClient) -> None:
    assert client.get("/api/v1/schools").status_code == 400

def test_schools_are_isolated_by_tenant(client: TestClient) -> None:
    first = client.get("/api/v1/schools", headers={"X-Tenant-ID": TEST_TENANT})
    other = client.get("/api/v1/schools", headers={"X-Tenant-ID": OTHER_TENANT})
    assert [school["name_ar"] for school in first.json()] == ["مدرسة الفجر", "مدرسة النور"]
    assert [school["name_ar"] for school in other.json()] == ["مدرسة أخرى"]
    assert first.json()[0]["tenant_id"] != other.json()[0]["tenant_id"]

def test_cross_tenant_dashboard_is_not_visible(client: TestClient) -> None:
    school = client.get("/api/v1/schools", headers={"X-Tenant-ID": TEST_TENANT}).json()[0]
    response = client.get(f"/api/v1/dashboard/{school['id']}", headers={"X-Tenant-ID": OTHER_TENANT})
    assert response.status_code == 404


def test_one_canonical_teacher_can_belong_to_two_schools(client: TestClient) -> None:
    headers = {"X-Tenant-ID": TEST_TENANT}
    for school_id in (FIRST_SCHOOL, SECOND_SCHOOL):
        response = client.post(
            "/api/v1/teacher-school-memberships",
            headers=headers,
            json={"teacher_id": SHARED_TEACHER, "school_id": school_id},
        )
        assert response.status_code == 201
        assert response.json()["teacher_id"] == SHARED_TEACHER


def test_multi_school_timetable_project_has_relational_scope(client: TestClient) -> None:
    response = client.post(
        "/api/v1/timetable-projects",
        headers={"X-Tenant-ID": TEST_TENANT},
        json={
            "name_ar": "جدول المدارس المشتركة",
            "scope_type": "schools",
            "schools": [
                {"school_id": FIRST_SCHOOL, "term_id": FIRST_TERM},
                {"school_id": SECOND_SCHOOL, "term_id": SECOND_TERM},
            ],
        },
    )
    assert response.status_code == 201
    assert {scope["school_id"] for scope in response.json()["schools"]} == {
        FIRST_SCHOOL,
        SECOND_SCHOOL,
    }


def test_complex_project_uses_per_school_terms(client: TestClient) -> None:
    response = client.post(
        "/api/v1/timetable-projects",
        headers={"X-Tenant-ID": TEST_TENANT},
        json={
            "name_ar": "جدول المجمع",
            "scope_type": "complex",
            "complex_id": TEST_COMPLEX,
            "schools": [
                {"school_id": FIRST_SCHOOL, "term_id": FIRST_TERM},
                {"school_id": SECOND_SCHOOL, "term_id": SECOND_TERM},
            ],
        },
    )
    assert response.status_code == 201
    assert {scope["term_id"] for scope in response.json()["schools"]} == {
        FIRST_TERM,
        SECOND_TERM,
    }


def test_dashboard_counts_only_selected_school(client: TestClient) -> None:
    headers = {"X-Tenant-ID": TEST_TENANT}
    client.post(
        "/api/v1/teacher-school-memberships",
        headers=headers,
        json={"teacher_id": SHARED_TEACHER, "school_id": FIRST_SCHOOL},
    )
    first = client.get(f"/api/v1/dashboard/{FIRST_SCHOOL}", headers=headers).json()
    second = client.get(f"/api/v1/dashboard/{SECOND_SCHOOL}", headers=headers).json()
    assert first["teachers"] == 1
    assert first["subjects"] == 1
    assert first["sections"] == 1
    assert first["resources"] == 1
    assert second["teachers"] == 0
    assert second["subjects"] == 1
    assert second["sections"] == 0
    assert second["resources"] == 1


def test_cross_tenant_teacher_relationship_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/teacher-school-memberships",
        headers={"X-Tenant-ID": TEST_TENANT},
        json={"teacher_id": OTHER_TEACHER, "school_id": FIRST_SCHOOL},
    )
    assert response.status_code == 422


def test_cross_tenant_project_school_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/timetable-projects",
        headers={"X-Tenant-ID": TEST_TENANT},
        json={
            "name_ar": "نطاق غير صالح",
            "scope_type": "schools",
            "schools": [
                {"school_id": FIRST_SCHOOL, "term_id": FIRST_TERM},
                {"school_id": OTHER_SCHOOL, "term_id": OTHER_TERM},
            ],
        },
    )
    assert response.status_code == 422


def test_wrong_school_term_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/timetable-projects",
        headers={"X-Tenant-ID": TEST_TENANT},
        json={
            "name_ar": "تقويم غير مطابق",
            "scope_type": "schools",
            "schools": [
                {"school_id": FIRST_SCHOOL, "term_id": SECOND_TERM},
                {"school_id": SECOND_SCHOOL, "term_id": FIRST_TERM},
            ],
        },
    )
    assert response.status_code == 422


def test_cross_tenant_term_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/timetable-projects",
        headers={"X-Tenant-ID": TEST_TENANT},
        json={
            "name_ar": "فصل من مستأجر آخر",
            "scope_type": "school",
            "schools": [{"school_id": FIRST_SCHOOL, "term_id": OTHER_TERM}],
        },
    )
    assert response.status_code == 422

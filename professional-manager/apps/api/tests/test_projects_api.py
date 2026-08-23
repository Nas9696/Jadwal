from fastapi.testclient import TestClient
from conftest import FIRST_SCHOOL, FIRST_TERM, SHARED_TEACHER, TEST_TENANT

HEADERS = {"X-Tenant-ID": TEST_TENANT}


def test_project_scope_rule_registry_and_preflight_are_server_side(client: TestClient) -> None:
    created = client.post(
        "/api/v1/timetable-projects",
        headers=HEADERS,
        json={
            "name_ar": "مشروع الاختبار",
            "scope_type": "school",
            "schools": [
                {"school_id": FIRST_SCHOOL, "term_id": FIRST_TERM, "cycle_phase_offset": 0}
            ],
        },
    )
    assert created.status_code == 201, created.text
    project = created.json()
    assert project["schools"][0]["term_id"] == FIRST_TERM
    body = client.post(
        f"/api/v1/timetable-projects/{project['id']}/preflight", headers=HEADERS
    ).json()
    assert body["readiness"] == "توجد أخطاء تمنع التوليد", body
    assert (
        client.post(
            f"/api/v1/timetable-projects/{project['id']}/rules",
            headers=HEADERS,
            json={
                "label": "مجهولة",
                "rule_type": "unknown",
                "severity": "hard",
                "selector": {"teacher_id": SHARED_TEACHER},
                "parameters": {},
            },
        ).status_code
        == 422
    )
    catalog = client.get("/api/v1/timetable-projects/rule-catalog", headers=HEADERS).json()
    assert len(catalog) == 9


def test_term_and_phase_are_validated(client: TestClient) -> None:
    bad = client.post(
        "/api/v1/timetable-projects",
        headers=HEADERS,
        json={
            "name_ar": "خاطئ",
            "scope_type": "school",
            "schools": [
                {"school_id": FIRST_SCHOOL, "term_id": FIRST_TERM, "cycle_phase_offset": 1}
            ],
        },
    )
    assert bad.status_code == 422

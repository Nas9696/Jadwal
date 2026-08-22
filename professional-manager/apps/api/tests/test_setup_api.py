from fastapi.testclient import TestClient

from conftest import FIRST_SCHOOL, OTHER_SCHOOL, OTHER_TENANT, TEST_TENANT


def url(resource: str, school: str = FIRST_SCHOOL) -> str:
    return f"/api/v1/schools/{school}/setup/{resource}"


def headers(tenant: str = TEST_TENANT) -> dict[str, str]:
    return {"X-Tenant-ID": tenant}


def create_calendar_prerequisites(client: TestClient) -> tuple[str, str, str]:
    shift = client.post(
        url("shifts"),
        headers=headers(),
        json={"code": "AM", "name_ar": "صباحي", "order": 0},
    ).json()
    pattern = client.post(
        url("patterns"),
        headers=headers(),
        json={"code": "A", "name_ar": "الأسبوع أ", "cycle_week_index": 0},
    ).json()
    day = client.post(
        url("days"),
        headers=headers(),
        json={
            "shift_id": shift["id"],
            "week_pattern_id": pattern["id"],
            "weekday_index": 0,
            "enabled": True,
        },
    ).json()
    return shift["id"], pattern["id"], day["id"]


def test_invalid_year_and_term_dates_are_rejected(client: TestClient) -> None:
    invalid = client.post(
        url("years"),
        headers=headers(),
        json={"name": "1449", "starts_on": "2027-06-01", "ends_on": "2027-01-01"},
    )
    assert invalid.status_code == 422
    year = client.post(
        url("years"),
        headers=headers(),
        json={"name": "1449", "starts_on": "2027-01-01", "ends_on": "2027-12-31"},
    ).json()
    outside = client.post(
        url("terms"),
        headers=headers(),
        json={
            "academic_year_id": year["id"],
            "name_ar": "فصل غير صالح",
            "order": 1,
            "starts_on": "2026-12-01",
            "ends_on": "2027-03-01",
        },
    )
    assert outside.status_code == 422
    assert outside.json()["detail"]["code"] == "term_outside_year"


def test_single_and_abc_week_patterns_are_contiguous_and_persisted(client: TestClient) -> None:
    for index, code in enumerate(("A", "B", "C")):
        response = client.post(
            url("patterns"),
            headers=headers(),
            json={"code": code, "name_ar": f"الأسبوع {code}", "cycle_week_index": index},
        )
        assert response.status_code == 201
    gap = client.post(
        url("patterns"),
        headers=headers(),
        json={"code": "E", "name_ar": "الأسبوع E", "cycle_week_index": 4},
    )
    assert gap.status_code == 422
    duplicate = client.post(
        url("patterns"),
        headers=headers(),
        json={"code": "C", "name_ar": "مكرر", "cycle_week_index": 2},
    )
    assert duplicate.status_code == 409
    snapshot = client.get(
        f"/api/v1/schools/{FIRST_SCHOOL}/setup", headers=headers()
    ).json()
    assert [pattern["cycle_week_index"] for pattern in snapshot["patterns"]] == [0, 1, 2]


def test_day_links_and_overlapping_blocks_are_validated(client: TestClient) -> None:
    _, _, day_id = create_calendar_prerequisites(client)
    first = client.post(
        url("blocks"),
        headers=headers(),
        json={
            "school_day_id": day_id,
            "block_order": 0,
            "block_type": "lesson",
            "period_number": 1,
            "label_ar": "الحصة الأولى",
            "starts_at": "08:00:00",
            "ends_at": "08:45:00",
            "attendance_mode": "onsite",
        },
    )
    assert first.status_code == 201
    overlap = client.post(
        url("blocks"),
        headers=headers(),
        json={
            "school_day_id": day_id,
            "block_order": 1,
            "block_type": "break",
            "starts_at": "08:30:00",
            "ends_at": "09:00:00",
            "attendance_mode": "hybrid",
        },
    )
    assert overlap.status_code == 422
    assert overlap.json()["detail"]["code"] == "day_block_overlap"


def test_wrong_school_shift_and_pattern_are_rejected(client: TestClient) -> None:
    other_shift = client.post(
        url("shifts", OTHER_SCHOOL),
        headers=headers(OTHER_TENANT),
        json={"code": "PM", "name_ar": "مسائي", "order": 0},
    ).json()
    pattern = client.post(
        url("patterns"),
        headers=headers(),
        json={"code": "A", "name_ar": "أسبوع واحد", "cycle_week_index": 0},
    ).json()
    response = client.post(
        url("days"),
        headers=headers(),
        json={
            "shift_id": other_shift["id"],
            "week_pattern_id": pattern["id"],
            "weekday_index": 1,
        },
    )
    assert response.status_code == 422


def test_stage_grade_section_ownership_and_crud(client: TestClient) -> None:
    stage = client.post(
        url("stages"),
        headers=headers(),
        json={"code": "CUSTOM", "name_ar": "المسار المرن", "order": 1},
    ).json()
    grade = client.post(
        url("grades"),
        headers=headers(),
        json={"stage_id": stage["id"], "name_ar": "المستوى الأول", "order": 0},
    ).json()
    section = client.post(
        url("sections"),
        headers=headers(),
        json={"grade_id": grade["id"], "name_ar": "101", "capacity": 25},
    )
    assert section.status_code == 201
    blocked_delete = client.delete(
        f"{url('stages')}/{stage['id']}", headers=headers()
    )
    assert blocked_delete.status_code == 409
    snapshot = client.get(
        f"/api/v1/schools/{FIRST_SCHOOL}/setup", headers=headers()
    ).json()
    assert any(item["name_ar"] == "المسار المرن" for item in snapshot["stages"])
    assert any(item["name_ar"] == "المستوى الأول" for item in snapshot["grades"])
    assert any(item["name_ar"] == "101" for item in snapshot["sections"])

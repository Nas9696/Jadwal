from typing import Any

from fastapi.testclient import TestClient

from conftest import (
    FIRST_SCHOOL,
    FIRST_TERM,
    SECOND_SCHOOL,
    SECOND_TERM,
    SHARED_TEACHER,
    TEST_TENANT,
)

HEADERS = {"X-Tenant-ID": TEST_TENANT}


def setup_url(school: str, resource: str = "") -> str:
    return f"/api/v1/schools/{school}/setup/{resource}".rstrip("/")


def assignment_url(school: str = FIRST_SCHOOL, suffix: str = "") -> str:
    return f"/api/v1/schools/{school}/assignments{suffix}"


def prepare_school(client: TestClient, school: str, term: str) -> dict[str, Any]:
    setup = client.get(setup_url(school), headers=HEADERS).json()
    shift = client.post(
        setup_url(school, "shifts"),
        headers=HEADERS,
        json={"code": "AM", "name_ar": "صباحي", "order": 0, "is_active": True},
    ).json()
    section = setup["sections"][0]
    offering = client.put(
        assignment_url(school, "/section-offerings"),
        headers=HEADERS,
        json={
            "offerings": [
                {
                    "term_id": term,
                    "section_id": section["id"],
                    "shift_id": shift["id"],
                    "is_active": True,
                }
            ]
        },
    ).json()[0]
    subject = client.get(f"/api/v1/schools/{school}/catalog", headers=HEADERS).json()["subjects"][0]
    return {
        "setup": setup,
        "shift": shift,
        "section": section,
        "offering": offering,
        "subject": subject,
    }


def activate_teacher(
    client: TestClient, school: str, teacher: str = SHARED_TEACHER
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/schools/{school}/teacher-memberships",
        headers=HEADERS,
        json={"teacher_id": teacher, "is_active": True, "is_home_school": False},
    )
    assert response.status_code == 201
    return response.json()


def create_teacher(client: TestClient, code: str, limit: int = 24) -> str:
    response = client.post(
        f"/api/v1/schools/{FIRST_SCHOOL}/teachers",
        headers=HEADERS,
        json={
            "canonical_code": code,
            "name_ar": f"معلم {code}",
            "specialty_reference": "تخصص مختلف",
            "base_workload": 0,
            "teaching_workload_limit": limit,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return response.json()["teacher_id"]


def create_requirement(client: TestClient, grade_id: str, subject_id: str, count: int = 6) -> None:
    response = client.post(
        f"/api/v1/schools/{FIRST_SCHOOL}/catalog/requirements",
        headers=HEADERS,
        json={"grade_id": grade_id, "subject_id": subject_id, "weekly_occurrences": count},
    )
    assert response.status_code == 201


def assign(
    client: TestClient,
    term: str,
    subject: str,
    offerings: list[str],
    teachers: list[str],
    count: int,
    resources: list[str] | None = None,
    school: str = FIRST_SCHOOL,
) -> Any:
    return client.post(
        assignment_url(school),
        headers=HEADERS,
        json={
            "term_id": term,
            "subject_id": subject,
            "weekly_occurrences": count,
            "teacher_ids": teachers,
            "section_offering_ids": offerings,
            "resource_ids": resources or [],
        },
    )


def test_term_and_section_offering_school_shift_validation(client: TestClient) -> None:
    data = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    wrong_term = client.put(
        assignment_url(FIRST_SCHOOL, "/section-offerings"),
        headers=HEADERS,
        json={
            "offerings": [
                {
                    "term_id": SECOND_TERM,
                    "section_id": data["section"]["id"],
                    "shift_id": data["shift"]["id"],
                    "is_active": True,
                }
            ]
        },
    )
    assert wrong_term.status_code == 422
    assert wrong_term.json()["detail"]["code"] == "term_not_in_school"
    snapshot = client.get(assignment_url() + f"?term_id={FIRST_TERM}", headers=HEADERS).json()
    assert snapshot["selected_term"]["id"] == FIRST_TERM
    assert snapshot["offerings"][0]["shift_id"] == data["shift"]["id"]


def test_inactive_membership_and_cross_school_references_are_rejected(client: TestClient) -> None:
    data = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    rejected_teacher = assign(
        client,
        FIRST_TERM,
        data["subject"]["id"],
        [data["offering"]["id"]],
        [SHARED_TEACHER],
        2,
    )
    assert rejected_teacher.status_code == 409
    activate_teacher(client, FIRST_SCHOOL)
    second_subject = client.get(f"/api/v1/schools/{SECOND_SCHOOL}/catalog", headers=HEADERS).json()[
        "subjects"
    ][0]
    wrong_subject = assign(
        client,
        FIRST_TERM,
        second_subject["id"],
        [data["offering"]["id"]],
        [SHARED_TEACHER],
        2,
    )
    assert wrong_subject.status_code == 422
    assert wrong_subject.json()["detail"]["code"] == "subject_not_in_school"


def test_split_assignments_sum_coverage_and_specialty_never_blocks(client: TestClient) -> None:
    data = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    activate_teacher(client, FIRST_SCHOOL)
    second_teacher = create_teacher(client, "SPLIT")
    create_requirement(client, data["section"]["grade_id"], data["subject"]["id"], 6)
    assert (
        assign(
            client,
            FIRST_TERM,
            data["subject"]["id"],
            [data["offering"]["id"]],
            [SHARED_TEACHER],
            4,
        ).status_code
        == 201
    )
    assert (
        assign(
            client,
            FIRST_TERM,
            data["subject"]["id"],
            [data["offering"]["id"]],
            [second_teacher],
            2,
        ).status_code
        == 201
    )
    snapshot = client.get(assignment_url() + f"?term_id={FIRST_TERM}", headers=HEADERS).json()
    cell = next(
        item
        for item in snapshot["cells"]
        if item["offering_id"] == data["offering"]["id"]
        and item["subject_id"] == data["subject"]["id"]
    )
    assert (cell["required"], cell["assigned"], cell["status"]) == (6, 6, "complete")
    workloads = {item["id"]: item["assigned_workload"] for item in snapshot["teachers"]}
    assert workloads[SHARED_TEACHER] == 4
    assert workloads[second_teacher] == 2


def test_combined_sections_and_co_teachers_have_correct_coverage_and_workload(
    client: TestClient,
) -> None:
    data = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    second_section = client.post(
        setup_url(FIRST_SCHOOL, "sections"),
        headers=HEADERS,
        json={"grade_id": data["section"]["grade_id"], "name_ar": "ب", "capacity": 30},
    ).json()
    second_offering = client.put(
        assignment_url(FIRST_SCHOOL, "/section-offerings"),
        headers=HEADERS,
        json={
            "offerings": [
                {
                    "term_id": FIRST_TERM,
                    "section_id": second_section["id"],
                    "shift_id": data["shift"]["id"],
                    "is_active": True,
                }
            ]
        },
    ).json()[0]
    activate_teacher(client, FIRST_SCHOOL)
    co_teacher = create_teacher(client, "CO")
    response = assign(
        client,
        FIRST_TERM,
        data["subject"]["id"],
        [data["offering"]["id"], second_offering["id"]],
        [SHARED_TEACHER, co_teacher],
        5,
    )
    assert response.status_code == 201
    snapshot = client.get(assignment_url() + f"?term_id={FIRST_TERM}", headers=HEADERS).json()
    cells = [
        item
        for item in snapshot["cells"]
        if item["subject_id"] == data["subject"]["id"]
        and item["offering_id"] in {data["offering"]["id"], second_offering["id"]}
    ]
    assert [item["assigned"] for item in cells] == [5, 5]
    workloads = {item["id"]: item["assigned_workload"] for item in snapshot["teachers"]}
    assert workloads[SHARED_TEACHER] == 5
    assert workloads[co_teacher] == 5
    group = snapshot["assignments"][0]
    assert len(group["teacher_ids"]) == 2 and len(group["section_offering_ids"]) == 2


def test_over_assignment_and_workload_are_warnings_not_blocks(client: TestClient) -> None:
    data = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    teacher = create_teacher(client, "OVER", limit=2)
    create_requirement(client, data["section"]["grade_id"], data["subject"]["id"], 3)
    response = assign(
        client,
        FIRST_TERM,
        data["subject"]["id"],
        [data["offering"]["id"]],
        [teacher],
        5,
    )
    assert response.status_code == 201
    codes = {item["code"] for item in response.json()["warnings"]}
    assert codes == {"curriculum_over_assigned", "teacher_workload_exceeded"}


def test_relational_resource_dependency_and_assignment_delete(client: TestClient) -> None:
    data = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    activate_teacher(client, FIRST_SCHOOL)
    resource = client.get(f"/api/v1/schools/{FIRST_SCHOOL}/catalog", headers=HEADERS).json()[
        "resources"
    ][0]
    created = assign(
        client,
        FIRST_TERM,
        data["subject"]["id"],
        [data["offering"]["id"]],
        [SHARED_TEACHER],
        2,
        [resource["id"]],
    ).json()
    blocked = client.delete(
        f"/api/v1/schools/{FIRST_SCHOOL}/catalog/resources/{resource['id']}", headers=HEADERS
    )
    assert blocked.status_code == 409
    assert (
        client.delete(
            assignment_url(FIRST_SCHOOL, f"/{created['assignment_id']}"), headers=HEADERS
        ).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/v1/schools/{FIRST_SCHOOL}/catalog/resources/{resource['id']}", headers=HEADERS
        ).status_code
        == 204
    )


def test_assignments_are_isolated_between_terms(client: TestClient) -> None:
    data = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    activate_teacher(client, FIRST_SCHOOL)
    year = data["setup"]["years"][0]
    second_term = client.post(
        setup_url(FIRST_SCHOOL, "terms"),
        headers=HEADERS,
        json={
            "academic_year_id": year["id"],
            "name_ar": "الفصل الثاني",
            "order": 2,
            "starts_on": "2027-01-01",
            "ends_on": "2027-05-01",
        },
    ).json()
    offering = client.put(
        assignment_url(FIRST_SCHOOL, "/section-offerings"),
        headers=HEADERS,
        json={
            "offerings": [
                {
                    "term_id": second_term["id"],
                    "section_id": data["section"]["id"],
                    "shift_id": data["shift"]["id"],
                    "is_active": True,
                }
            ]
        },
    ).json()[0]
    assert (
        assign(
            client,
            second_term["id"],
            data["subject"]["id"],
            [offering["id"]],
            [SHARED_TEACHER],
            3,
        ).status_code
        == 201
    )
    first = client.get(assignment_url() + f"?term_id={FIRST_TERM}", headers=HEADERS).json()
    second = client.get(assignment_url() + f"?term_id={second_term['id']}", headers=HEADERS).json()
    assert first["assignments"] == []
    assert len(second["assignments"]) == 1


def test_inactive_subject_and_relational_membership_dependency(client: TestClient) -> None:
    data = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    membership = activate_teacher(client, FIRST_SCHOOL)
    subject = data["subject"]
    disabled = client.put(
        f"/api/v1/schools/{FIRST_SCHOOL}/catalog/subjects/{subject['id']}",
        headers=HEADERS,
        json={
            "code": subject["code"],
            "name_ar": subject["name_ar"],
            "name_en": subject["name_en"],
            "is_active": False,
        },
    )
    assert disabled.status_code == 200
    rejected = assign(
        client,
        FIRST_TERM,
        subject["id"],
        [data["offering"]["id"]],
        [SHARED_TEACHER],
        2,
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "subject_inactive"
    client.put(
        f"/api/v1/schools/{FIRST_SCHOOL}/catalog/subjects/{subject['id']}",
        headers=HEADERS,
        json={
            "code": subject["code"],
            "name_ar": subject["name_ar"],
            "name_en": subject["name_en"],
            "is_active": True,
        },
    )
    assert (
        assign(
            client,
            FIRST_TERM,
            subject["id"],
            [data["offering"]["id"]],
            [SHARED_TEACHER],
            2,
        ).status_code
        == 201
    )
    blocked = client.put(
        f"/api/v1/schools/{FIRST_SCHOOL}/teacher-memberships/{membership['id']}",
        headers=HEADERS,
        json={"local_employee_code": None, "is_home_school": False, "is_active": False},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "teacher_membership_has_assignments"


def test_cross_school_resource_is_rejected(client: TestClient) -> None:
    data = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    activate_teacher(client, FIRST_SCHOOL)
    local_resource = client.get(f"/api/v1/schools/{FIRST_SCHOOL}/catalog", headers=HEADERS).json()[
        "resources"
    ][0]
    client.put(
        f"/api/v1/schools/{FIRST_SCHOOL}/catalog/resources/{local_resource['id']}",
        headers=HEADERS,
        json={
            "code": local_resource["code"],
            "name_ar": local_resource["name_ar"],
            "resource_type": local_resource["resource_type"],
            "capacity": local_resource["capacity"],
            "exclusive": local_resource["exclusive"],
            "is_active": False,
        },
    )
    inactive = assign(
        client,
        FIRST_TERM,
        data["subject"]["id"],
        [data["offering"]["id"]],
        [SHARED_TEACHER],
        2,
        [local_resource["id"]],
    )
    assert inactive.status_code == 409
    assert inactive.json()["detail"]["code"] == "resource_inactive"
    other_resource = client.get(f"/api/v1/schools/{SECOND_SCHOOL}/catalog", headers=HEADERS).json()[
        "resources"
    ][0]
    rejected = assign(
        client,
        FIRST_TERM,
        data["subject"]["id"],
        [data["offering"]["id"]],
        [SHARED_TEACHER],
        2,
        [other_resource["id"]],
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "resource_not_in_school"


def test_shared_teacher_can_be_assigned_in_each_active_school(client: TestClient) -> None:
    first = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    activate_teacher(client, FIRST_SCHOOL)
    activate_teacher(client, SECOND_SCHOOL)
    shift = client.post(
        setup_url(SECOND_SCHOOL, "shifts"),
        headers=HEADERS,
        json={"code": "AM", "name_ar": "صباحي", "order": 0, "is_active": True},
    ).json()
    stage = client.post(
        setup_url(SECOND_SCHOOL, "stages"),
        headers=HEADERS,
        json={"code": "I", "name_ar": "المتوسطة", "order": 0},
    ).json()
    grade = client.post(
        setup_url(SECOND_SCHOOL, "grades"),
        headers=HEADERS,
        json={"stage_id": stage["id"], "name_ar": "الأول المتوسط", "order": 0},
    ).json()
    section = client.post(
        setup_url(SECOND_SCHOOL, "sections"),
        headers=HEADERS,
        json={"grade_id": grade["id"], "name_ar": "أ", "capacity": 30},
    ).json()
    second_offering = client.put(
        assignment_url(SECOND_SCHOOL, "/section-offerings"),
        headers=HEADERS,
        json={
            "offerings": [
                {
                    "term_id": SECOND_TERM,
                    "section_id": section["id"],
                    "shift_id": shift["id"],
                    "is_active": True,
                }
            ]
        },
    ).json()[0]
    second_subject = client.get(f"/api/v1/schools/{SECOND_SCHOOL}/catalog", headers=HEADERS).json()[
        "subjects"
    ][0]
    assert (
        assign(
            client,
            FIRST_TERM,
            first["subject"]["id"],
            [first["offering"]["id"]],
            [SHARED_TEACHER],
            3,
        ).status_code
        == 201
    )
    assert (
        assign(
            client,
            SECOND_TERM,
            second_subject["id"],
            [second_offering["id"]],
            [SHARED_TEACHER],
            2,
            school=SECOND_SCHOOL,
        ).status_code
        == 201
    )
    first_snapshot = client.get(assignment_url() + f"?term_id={FIRST_TERM}", headers=HEADERS).json()
    teacher = next(item for item in first_snapshot["teachers"] if item["id"] == SHARED_TEACHER)
    assert teacher["assigned_workload"] == 3
    assert teacher["other_school_overlapping_workload"] == 2


def test_bulk_teacher_change_and_delete_are_term_scoped(client: TestClient) -> None:
    data = prepare_school(client, FIRST_SCHOOL, FIRST_TERM)
    activate_teacher(client, FIRST_SCHOOL)
    replacement = create_teacher(client, "BULK")
    created = assign(
        client,
        FIRST_TERM,
        data["subject"]["id"],
        [data["offering"]["id"]],
        [SHARED_TEACHER],
        2,
    ).json()
    changed = client.post(
        assignment_url(FIRST_SCHOOL, "/bulk/teachers"),
        headers=HEADERS,
        json={
            "term_id": FIRST_TERM,
            "assignment_ids": [created["assignment_id"]],
            "teacher_ids": [replacement],
        },
    )
    assert changed.status_code == 200
    snapshot = client.get(assignment_url() + f"?term_id={FIRST_TERM}", headers=HEADERS).json()
    assert snapshot["assignments"][0]["teacher_ids"] == [replacement]
    deleted = client.post(
        assignment_url(FIRST_SCHOOL, "/bulk/delete"),
        headers=HEADERS,
        json={"term_id": FIRST_TERM, "assignment_ids": [created["assignment_id"]]},
    )
    assert deleted.status_code == 200 and deleted.json()["deleted"] == 1

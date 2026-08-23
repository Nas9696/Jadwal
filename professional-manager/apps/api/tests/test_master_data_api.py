from fastapi.testclient import TestClient

from conftest import (
    FIRST_SCHOOL,
    OTHER_TEACHER,
    SECOND_SCHOOL,
    SHARED_TEACHER,
    TEST_TENANT,
)

HEADERS = {"X-Tenant-ID": TEST_TENANT}


def teacher_url(path: str = "", school: str = FIRST_SCHOOL) -> str:
    return f"/api/v1/schools/{school}/teachers{path}"


def memberships_url(school: str = FIRST_SCHOOL) -> str:
    return f"/api/v1/schools/{school}/teacher-memberships"


def catalog_url(kind: str = "", school: str = FIRST_SCHOOL) -> str:
    suffix = f"/{kind}" if kind else ""
    return f"/api/v1/schools/{school}/catalog{suffix}"


def link(client: TestClient, school: str, home: bool = False) -> dict[str, object]:
    response = client.post(
        memberships_url(school),
        headers=HEADERS,
        json={
            "teacher_id": SHARED_TEACHER,
            "local_employee_code": f"LOCAL-{school[-3:]}",
            "is_home_school": home,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_one_canonical_teacher_links_to_two_schools_and_lists_as_shared(client: TestClient) -> None:
    link(client, FIRST_SCHOOL, True)
    link(client, SECOND_SCHOOL)
    first = client.get(teacher_url(), headers=HEADERS).json()
    assert len(first["teachers"]) == 1
    card = first["teachers"][0]
    assert card["teacher"]["id"] == SHARED_TEACHER
    assert card["is_shared"] is True
    assert {school["id"] for school in card["schools"]} == {FIRST_SCHOOL, SECOND_SCHOOL}


def test_school_teacher_list_excludes_unlinked_and_cross_tenant_link_is_rejected(
    client: TestClient,
) -> None:
    assert client.get(teacher_url(), headers=HEADERS).json()["teachers"] == []
    rejected = client.post(
        memberships_url(),
        headers=HEADERS,
        json={"teacher_id": OTHER_TEACHER, "is_home_school": False},
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "teacher_not_in_tenant"


def test_duplicate_membership_rejected_and_home_school_moves_atomically(client: TestClient) -> None:
    first = link(client, FIRST_SCHOOL, True)
    second = link(client, SECOND_SCHOOL)
    duplicate = client.post(memberships_url(), headers=HEADERS, json={"teacher_id": SHARED_TEACHER})
    assert duplicate.status_code == 409
    changed = client.put(
        f"{memberships_url(SECOND_SCHOOL)}/{second['id']}",
        headers=HEADERS,
        json={"local_employee_code": "SECOND", "is_home_school": True, "is_active": True},
    )
    assert changed.status_code == 200
    cards = client.get(teacher_url(), headers=HEADERS).json()["teachers"]
    assert cards[0]["membership"]["id"] == first["id"]
    assert cards[0]["membership"]["is_home_school"] is False
    second_card = client.get(teacher_url(school=SECOND_SCHOOL), headers=HEADERS).json()["teachers"][
        0
    ]
    assert second_card["membership"]["is_home_school"] is True


def test_unlinking_one_school_preserves_canonical_teacher_and_other_membership(
    client: TestClient,
) -> None:
    first = link(client, FIRST_SCHOOL)
    link(client, SECOND_SCHOOL, True)
    response = client.delete(f"{memberships_url()}/{first['id']}", headers=HEADERS)
    assert response.status_code == 204
    assert client.get(teacher_url(), headers=HEADERS).json()["teachers"] == []
    assert (
        client.get(teacher_url(school=SECOND_SCHOOL), headers=HEADERS).json()["teachers"][0][
            "teacher"
        ]["id"]
        == SHARED_TEACHER
    )


def test_create_and_edit_teacher_keeps_specialty_descriptive_only(client: TestClient) -> None:
    created = client.post(
        teacher_url(),
        headers=HEADERS,
        json={
            "canonical_code": "NEW-1",
            "name_ar": "أحمد",
            "specialty_reference": "تربية بدنية",
            "base_workload": 18,
            "teaching_workload_limit": 24,
            "local_employee_code": "E-1",
            "is_home_school": True,
        },
    )
    assert created.status_code == 201
    teacher = client.get(teacher_url(), headers=HEADERS).json()["teachers"][0]["teacher"]
    updated = client.put(
        teacher_url(f"/{teacher['id']}"),
        headers=HEADERS,
        json={
            "canonical_code": "NEW-1",
            "name_ar": "أحمد محمد",
            "specialty_reference": "مرجع وصفي مختلف عن المواد",
            "base_workload": 20,
            "teaching_workload_limit": 25,
            "is_active": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["specialty_reference"] == "مرجع وصفي مختلف عن المواد"


def test_subject_curriculum_crud_scope_counts_and_dependency_delete(client: TestClient) -> None:
    catalog = client.get(catalog_url(), headers=HEADERS).json()
    grade = catalog["grades"][0]
    existing_subject = catalog["subjects"][0]
    subject = client.post(
        catalog_url("subjects"),
        headers=HEADERS,
        json={"code": "AR", "name_ar": "لغتي", "is_active": True},
    )
    assert subject.status_code == 201
    requirement = client.post(
        catalog_url("requirements"),
        headers=HEADERS,
        json={"grade_id": grade["id"], "subject_id": subject.json()["id"], "weekly_occurrences": 6},
    )
    assert requirement.status_code == 201
    edited = client.put(
        f"{catalog_url('requirements')}/{requirement.json()['id']}",
        headers=HEADERS,
        json={"grade_id": grade["id"], "subject_id": subject.json()["id"], "weekly_occurrences": 7},
    )
    assert edited.status_code == 200 and edited.json()["weekly_occurrences"] == 7
    duplicate = client.post(
        catalog_url("requirements"),
        headers=HEADERS,
        json={"grade_id": grade["id"], "subject_id": subject.json()["id"], "weekly_occurrences": 2},
    )
    assert duplicate.status_code == 409
    zero = client.post(
        catalog_url("requirements"),
        headers=HEADERS,
        json={
            "grade_id": grade["id"],
            "subject_id": existing_subject["id"],
            "weekly_occurrences": 0,
        },
    )
    assert zero.status_code == 422
    blocked = client.delete(f"{catalog_url('subjects')}/{subject.json()['id']}", headers=HEADERS)
    assert (
        blocked.status_code == 409
        and blocked.json()["detail"]["code"] == "subject_has_dependencies"
    )


def test_curriculum_rejects_wrong_school_grade_and_subject(client: TestClient) -> None:
    first = client.get(catalog_url(), headers=HEADERS).json()
    second = client.get(catalog_url(school=SECOND_SCHOOL), headers=HEADERS).json()
    wrong_subject = second["subjects"][0]
    rejected = client.post(
        catalog_url("requirements"),
        headers=HEADERS,
        json={
            "grade_id": first["grades"][0]["id"],
            "subject_id": wrong_subject["id"],
            "weekly_occurrences": 4,
        },
    )
    assert (
        rejected.status_code == 422 and rejected.json()["detail"]["code"] == "subject_not_in_school"
    )


def test_resource_crud_and_wrong_school_mutation_rejected(client: TestClient) -> None:
    created = client.post(
        catalog_url("resources"),
        headers=HEADERS,
        json={
            "code": "GYM",
            "name_ar": "الصالة الرياضية",
            "resource_type": "gym",
            "capacity": 80,
            "exclusive": True,
            "is_active": True,
        },
    )
    assert created.status_code == 201
    edited = client.put(
        f"{catalog_url('resources')}/{created.json()['id']}",
        headers=HEADERS,
        json={
            "code": "GYM",
            "name_ar": "الصالة الكبرى",
            "resource_type": "gym",
            "capacity": 100,
            "exclusive": True,
            "is_active": True,
        },
    )
    assert edited.status_code == 200
    wrong = client.put(
        f"{catalog_url('resources', SECOND_SCHOOL)}/{created.json()['id']}",
        headers=HEADERS,
        json={
            "code": "X",
            "name_ar": "خاطئ",
            "resource_type": "other",
            "exclusive": True,
            "is_active": True,
        },
    )
    assert wrong.status_code == 404
    assert (
        client.delete(
            f"{catalog_url('resources')}/{created.json()['id']}", headers=HEADERS
        ).status_code
        == 204
    )

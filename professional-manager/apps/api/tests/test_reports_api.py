import io
import json
import uuid
import zipfile

from fastapi.testclient import TestClient
from openpyxl import load_workbook  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Resource,
    Subject,
    TeacherSchoolMembership,
    TeachingAssignment,
    TimetableProjectSchool,
    WorkingTimetable,
    WorkingTimetableEntry,
    WorkingTimetableEntryResource,
    WorkingTimetableEntryTeacher,
)
from app.report_exports import build_qr, export_png
from app.report_schemas import ReportDataset
from conftest import (
    OTHER_TENANT,
    SECOND_SCHOOL,
    SECOND_TERM,
    SHARED_TEACHER,
    TEST_TENANT,
)
from test_solve_api import HEADERS
from test_substitutions_api import SUNDAY, _absence, _candidate
from test_timetable_editor_api import derive


def _payload(report_type: str, working: dict[str, object], **filters: object) -> dict[str, object]:
    return {
        "report_type": report_type,
        "source": {"kind": "working", "expected_revision": working["revision"]},
        "filters": filters,
        "print_options": {
            "paper": "A4",
            "orientation": "landscape",
            "density": "compact",
            "theme": "color",
            "show_heading": True,
            "show_period_time": True,
            "show_resource": True,
        },
        "branding": {
            "qr_payload": "https://school.example/revision/1",
            "footer_text": "اعتماد مدير المدرسة",
            "signature_labels": ["مدير المدرسة"],
        },
    }


def _preview(client: TestClient, project_id: str, payload: dict[str, object]) -> dict[str, object]:
    response = client.post(
        f"/api/v1/timetable-projects/{project_id}/reports/preview",
        headers=HEADERS,
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_report_types_use_current_working_source_and_server_side_filters(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    entry = working["entries"][0]  # type: ignore[index]
    db_entry = session.scalar(select(WorkingTimetableEntry))
    resource = session.scalar(select(Resource).where(Resource.tenant_id == uuid.UUID(TEST_TENANT)))
    assert db_entry is not None and resource is not None
    session.add(
        WorkingTimetableEntryResource(
            tenant_id=uuid.UUID(TEST_TENANT),
            working_timetable_entry_id=db_entry.id,
            resource_id=resource.id,
        )
    )
    session.commit()
    filters = {
        "section_timetable": {"section_id": entry["sections"][0]["id"]},
        "teacher_timetable": {"teacher_id": entry["teachers"][0]["id"]},
        "subject_timetable": {"subject_id": entry["subject"]["id"]},
        "resource_timetable": {"resource_id": str(resource.id)},
    }
    for report_type in ("general_timetable", *filters):
        result = _preview(client, project_id, _payload(report_type, working, **filters.get(report_type, {})))
        assert result["source"]["kind"] == "working"
        assert result["source"]["revision"] == working["revision"]
        assert result["row_count"] == 1


def test_report_scope_and_revision_conflicts_are_authoritative(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    stale = _payload("general_timetable", working)
    stale["source"] = {"kind": "working", "expected_revision": 999}
    response = client.post(
        f"/api/v1/timetable-projects/{project_id}/reports/preview", headers=HEADERS, json=stale
    )
    assert response.status_code == 409
    response = client.post(
        f"/api/v1/timetable-projects/{project_id}/reports/preview",
        headers={"X-Tenant-ID": OTHER_TENANT},
        json=_payload("general_timetable", working),
    )
    assert response.status_code == 404


def test_teacher_report_spans_all_project_schools_for_canonical_teacher(
    client: TestClient, session: Session
) -> None:
    project_id, working_json = derive(client, session)
    working = session.get(WorkingTimetable, uuid.UUID(str(working_json["id"])))
    subject = session.scalar(
        select(Subject).where(Subject.school_id == uuid.UUID(SECOND_SCHOOL))
    )
    assert working is not None and subject is not None
    session.add_all(
        [
            TimetableProjectSchool(
                tenant_id=uuid.UUID(TEST_TENANT),
                timetable_project_id=uuid.UUID(project_id),
                school_id=uuid.UUID(SECOND_SCHOOL),
                term_id=uuid.UUID(SECOND_TERM),
                cycle_phase_offset=0,
            ),
            TeacherSchoolMembership(
                tenant_id=uuid.UUID(TEST_TENANT),
                teacher_id=uuid.UUID(SHARED_TEACHER),
                school_id=uuid.UUID(SECOND_SCHOOL),
                is_home_school=False,
                is_active=True,
            ),
        ]
    )
    assignment = TeachingAssignment(
        tenant_id=uuid.UUID(TEST_TENANT),
        school_id=uuid.UUID(SECOND_SCHOOL),
        term_id=uuid.UUID(SECOND_TERM),
        subject_id=subject.id,
        weekly_occurrences=1,
        distribution={},
    )
    session.add(assignment)
    session.flush()
    entry = WorkingTimetableEntry(
        tenant_id=uuid.UUID(TEST_TENANT),
        working_timetable_id=working.id,
        occurrence_id=f"{assignment.id}:0",
        assignment_id=assignment.id,
        subject_id=subject.id,
        slot_id="second-school-slot@project-week-0",
        school_id=uuid.UUID(SECOND_SCHOOL),
        project_cycle_week_index=0,
        weekday_index=1,
        starts_at_minute=540,
        ends_at_minute=585,
    )
    session.add(entry)
    session.flush()
    session.add(
        WorkingTimetableEntryTeacher(
            tenant_id=uuid.UUID(TEST_TENANT),
            working_timetable_entry_id=entry.id,
            teacher_id=uuid.UUID(SHARED_TEACHER),
        )
    )
    session.commit()
    report = _preview(
        client,
        project_id,
        _payload("teacher_timetable", working_json, teacher_id=SHARED_TEACHER),
    )
    assert report["row_count"] == 2
    assert {row["school_id"] for row in report["rows"]} == {
        working_json["entries"][0]["school"]["id"],  # type: ignore[index]
        SECOND_SCHOOL,
    }


def test_candidate_source_is_used_only_when_explicit(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    payload = _payload("general_timetable", working)
    payload["source"] = {"kind": "candidate", "candidate_id": working["source_candidate_id"]}
    report = _preview(client, project_id, payload)
    assert report["source"]["kind"] == "candidate"
    assert report["source"]["revision"] is None


def test_real_xlsx_pdf_and_png_exports_include_source_revision(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    payload = _payload("general_timetable", working)
    xlsx = client.post(
        f"/api/v1/timetable-projects/{project_id}/reports/export",
        headers=HEADERS,
        json={**payload, "format": "xlsx"},
    )
    assert xlsx.status_code == 200 and xlsx.content.startswith(b"PK\x03\x04")
    workbook = load_workbook(io.BytesIO(xlsx.content), data_only=True)
    assert workbook["بيانات المصدر"]["B5"].value == working["revision"]
    assert workbook["بيانات المصدر"].sheet_state == "hidden"
    pdf = client.post(
        f"/api/v1/timetable-projects/{project_id}/reports/export",
        headers=HEADERS,
        json={**payload, "format": "pdf"},
    )
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    assert int(pdf.headers["x-report-pages"]) >= 1
    png = client.post(
        f"/api/v1/timetable-projects/{project_id}/reports/export",
        headers=HEADERS,
        json={**payload, "format": "png"},
    )
    assert png.status_code == 200 and png.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert xlsx.headers["x-source-revision"] == str(working["revision"])


def test_png_multi_page_contract_never_silently_crops(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    raw = _preview(client, project_id, _payload("general_timetable", working))
    dataset = ReportDataset.model_validate(raw)
    rows = dataset.rows * 100
    expanded = dataset.model_copy(update={"rows": rows, "row_count": len(rows)})
    exported = export_png(expanded)
    assert exported.metadata.multi_page is True
    assert exported.metadata.content_type == "application/zip"
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        page_files = [name for name in archive.namelist() if name.endswith(".png")]
        assert manifest["pages"] == exported.metadata.pages == len(page_files)
        assert all(archive.read(name).startswith(b"\x89PNG") for name in page_files)


def test_qr_is_real_and_unsafe_logo_is_rejected(
    client: TestClient, session: Session
) -> None:
    qr, _image = build_qr("PM-REVISION-7")
    assert qr.data_list[0].data == b"PM-REVISION-7"
    project_id, working = derive(client, session)
    payload = _payload("general_timetable", working)
    payload["branding"] = {"logo_data_url": "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="}
    response = client.post(
        f"/api/v1/timetable-projects/{project_id}/reports/export",
        headers=HEADERS,
        json={**payload, "format": "pdf"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unsafe_logo_type"


def test_beta_smoke_general_teacher_section_absence_and_waiting(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    entry = working["entries"][0]  # type: ignore[index]
    _absence(client, project_id, working)
    cases = [
        _payload("general_timetable", working),
        _payload("teacher_timetable", working, teacher_id=entry["teachers"][0]["id"]),
        _payload("section_timetable", working, section_id=entry["sections"][0]["id"]),
        _payload("daily_substitutions", working, on_date=SUNDAY.isoformat()),
        _payload("waiting_workload", working, on_date=SUNDAY.isoformat()),
    ]
    for payload in cases:
        preview = _preview(client, project_id, payload)
        assert preview["source"]["revision"] == working["revision"]
    for format_name, signature in (("xlsx", b"PK"), ("pdf", b"%PDF"), ("png", b"\x89PNG")):
        response = client.post(
            f"/api/v1/timetable-projects/{project_id}/reports/export",
            headers=HEADERS,
            json={**cases[0], "format": format_name},
        )
        assert response.status_code == 200 and response.content.startswith(signature)


def test_waiting_report_preserves_explicit_zero_workload_limit(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    response = client.put(
        f"/api/v1/timetable-projects/{project_id}/substitutions/profiles/{SHARED_TEACHER}",
        headers=HEADERS,
        json={"custom_combined_limit": 0, "exempt": False},
    )
    assert response.status_code == 200, response.text
    report = _preview(
        client,
        project_id,
        _payload("waiting_workload", working, on_date=SUNDAY.isoformat()),
    )
    row = next(item for item in report["rows"] if item["teacher_ids"] == [SHARED_TEACHER])
    assert row["effective_limit"] == 0
    assert row["remaining_capacity"] == 0


def test_daily_substitution_report_reads_covered_authoritative_assignment(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    substitute = _candidate(session, code="REPORT-SUB", name="المعلم البديل")
    absence = _absence(client, project_id, working)
    need = absence["needs"][0]
    assigned = client.post(
        f"/api/v1/timetable-projects/{project_id}/substitutions/needs/{need['id']}/assign",
        headers=HEADERS,
        json={
            "substitute_teacher_id": str(substitute.id),
            "need_version": need["version"],
            "working_timetable_revision": working["revision"],
            "mode": "manual_override",
        },
    )
    assert assigned.status_code == 200, assigned.text
    report = _preview(
        client,
        project_id,
        _payload("daily_substitutions", working, on_date=SUNDAY.isoformat()),
    )
    assert report["rows"][0]["coverage_status"] == "مغطاة"
    assert report["rows"][0]["substitute_teacher_name"] == "المعلم البديل"


def test_export_requires_revision_and_preview_does_not_mutate_working(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    payload = _payload("general_timetable", working)
    payload["source"] = {"kind": "working"}
    before = session.scalar(select(WorkingTimetableEntry).where(WorkingTimetableEntry.tenant_id == uuid.UUID(TEST_TENANT)))
    assert before is not None
    response = client.post(
        f"/api/v1/timetable-projects/{project_id}/reports/export",
        headers=HEADERS,
        json={**payload, "format": "pdf"},
    )
    assert response.status_code == 422
    _preview(client, project_id, payload)
    assert session.get(WorkingTimetableEntry, before.id) is before

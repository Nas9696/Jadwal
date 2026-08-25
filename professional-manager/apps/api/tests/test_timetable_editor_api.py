from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    TimetableAuditEvent,
    TimetableEntry,
    TimetableRepairPreview,
    WorkingTimetableEntry,
)
from conftest import OTHER_TENANT
from test_solve_api import HEADERS, ready_project


def derive(client: TestClient, session: Session) -> tuple[str, dict[str, object]]:
    project = ready_project(session)
    started = client.post(
        f"/api/v1/timetable-projects/{project.id}/solve",
        headers=HEADERS,
        json={"candidate_count": 1, "time_limit_seconds": 1, "seed": 4},
    ).json()
    run = client.get(
        f"/api/v1/timetable-projects/{project.id}/solve-runs/{started['id']}", headers=HEADERS
    ).json()
    candidate_id = run["candidates"][0]["id"]
    response = client.post(
        f"/api/v1/timetable-projects/{project.id}/working-timetable/from-candidate/{candidate_id}",
        headers=HEADERS,
    )
    assert response.status_code == 201, response.text
    return str(project.id), response.json()


def test_candidate_and_working_quality_and_explanation_are_factual(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    occurrence = working["entries"][0]  # type: ignore[index]
    candidate_id = working["source_candidate_id"]
    candidate_quality = client.get(
        f"/api/v1/timetable-projects/{project_id}/candidates/{candidate_id}/quality",
        headers=HEADERS,
    )
    assert candidate_quality.status_code == 200, candidate_quality.text
    assert "total_weighted_penalty" in candidate_quality.json()
    quality = client.get(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/quality", headers=HEADERS
    )
    assert quality.status_code == 200
    assert quality.json()["hard_violations"] == []
    explanation = client.get(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/explanations",
        headers=HEADERS,
        params={"occurrence_id": occurrence["occurrence_id"]},  # type: ignore[index]
    )
    assert explanation.status_code == 200, explanation.text
    assert explanation.json()["chosen_slot"]["id"] == occurrence["slot_id"]  # type: ignore[index]
    assert all("penalty_delta" in item for item in explanation.json()["alternatives"])


def test_candidate_is_immutable_move_revision_and_persisted_undo_redo(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    candidate_before = session.scalar(select(TimetableEntry))
    assert candidate_before is not None
    original_candidate_slot = candidate_before.slot_id
    occurrence = working["entries"][0]
    problem = client.get(f"/api/v1/timetable-projects/{project_id}/problem", headers=HEADERS).json()
    target = next(slot for slot in problem["slots"] if slot["id"] != occurrence["slot_id"])
    payload = {
        "revision": working["revision"],
        "occurrence_id": occurrence["occurrence_id"],
        "target_slot_id": target["id"],
    }
    analysis = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/moves/analyze",
        headers=HEADERS,
        json=payload,
    )
    assert analysis.status_code == 200 and analysis.json()["valid"] is True
    moved = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/moves/apply",
        headers=HEADERS,
        json=payload,
    ).json()
    assert moved["entries"][0]["slot_id"] == target["id"]
    assert session.scalar(select(TimetableEntry)).slot_id == original_candidate_slot  # type: ignore[union-attr]
    stale = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/moves/apply",
        headers=HEADERS,
        json=payload,
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "timetable_version_conflict"
    undone = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/undo",
        headers=HEADERS,
        json={"revision": moved["revision"]},
    ).json()
    assert undone["entries"][0]["slot_id"] == original_candidate_slot
    reloaded = client.get(
        f"/api/v1/timetable-projects/{project_id}/working-timetable", headers=HEADERS
    ).json()
    redone = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/redo",
        headers=HEADERS,
        json={"revision": reloaded["revision"]},
    ).json()
    assert redone["entries"][0]["slot_id"] == target["id"]
    assert session.scalar(select(func.count()).select_from(TimetableAuditEvent)) == 3


def test_lock_blocks_move_unlock_permits_and_tenant_isolated(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    occurrence = working["entries"][0]
    target = next(
        slot
        for slot in client.get(
            f"/api/v1/timetable-projects/{project_id}/problem", headers=HEADERS
        ).json()["slots"]
        if slot["id"] != occurrence["slot_id"]
    )
    locked = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/locks",
        headers=HEADERS,
        json={"revision": working["revision"], "lock_type": "occurrence", "occurrence_id": occurrence["occurrence_id"], "label": "قفل الحصة"},
    ).json()
    analysis = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/moves/analyze",
        headers=HEADERS,
        json={"revision": locked["revision"], "occurrence_id": occurrence["occurrence_id"], "target_slot_id": target["id"]},
    ).json()
    assert analysis["valid"] is False
    assert analysis["lock_violations"]
    unlocked = client.delete(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/locks/{locked['lock']['id']}?revision={locked['revision']}",
        headers=HEADERS,
    ).json()
    analysis["revision"] = unlocked["revision"]
    permitted = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/moves/analyze",
        headers=HEADERS,
        json={"revision": unlocked["revision"], "occurrence_id": occurrence["occurrence_id"], "target_slot_id": target["id"]},
    )
    assert permitted.json()["valid"] is True
    assert client.get(
        f"/api/v1/timetable-projects/{project_id}/working-timetable",
        headers={"X-Tenant-ID": OTHER_TENANT},
    ).status_code == 404


def test_repair_preview_zero_schedule_writes_and_snapshot_restore_new_version(
    client: TestClient, session: Session
) -> None:
    project_id, working = derive(client, session)
    occurrence = working["entries"][0]
    target = next(
        slot for slot in client.get(f"/api/v1/timetable-projects/{project_id}/problem", headers=HEADERS).json()["slots"]
        if slot["id"] != occurrence["slot_id"]
    )
    before = session.scalar(select(func.count()).select_from(WorkingTimetableEntry))
    preview = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/repair/preview",
        headers=HEADERS,
        json={"revision": working["revision"], "occurrence_id": occurrence["occurrence_id"], "target_slot_id": target["id"], "time_limit_seconds": 2},
    )
    assert preview.status_code == 201, preview.text
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(WorkingTimetableEntry)) == before
    assert session.scalar(select(func.count()).select_from(TimetableRepairPreview)) == 0
    assert client.get(f"/api/v1/timetable-projects/{project_id}/working-timetable", headers=HEADERS).json()["revision"] == working["revision"]
    snapshot = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/snapshots",
        headers=HEADERS,
        json={"revision": working["revision"], "name": "قبل التعديل"},
    ).json()
    latest = client.get(f"/api/v1/timetable-projects/{project_id}/working-timetable", headers=HEADERS).json()
    restored = client.post(
        f"/api/v1/timetable-projects/{project_id}/working-timetable/snapshots/{snapshot['id']}/restore",
        headers=HEADERS,
        json={"revision": latest["revision"]},
    )
    assert restored.status_code == 201
    assert restored.json()["version_number"] == 2

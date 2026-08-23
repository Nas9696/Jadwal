import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.editor_schemas import (
    LockInput,
    MoveInput,
    RepairApplyInput,
    RepairInput,
    RevisionInput,
    SnapshotInput,
    SnapshotRestoreInput,
    SwapInput,
)
from app.editor_services import (
    analyze_move,
    apply_move,
    apply_repair,
    apply_swap,
    audit_list,
    compare_snapshot,
    create_from_candidate,
    create_lock,
    create_snapshot,
    delete_lock,
    list_snapshots,
    repair_preview,
    restore_snapshot,
    serialize_working,
    undo_redo,
    _working,
)
from app.tenant import tenant_context
from app.quality_services import compare_quality, working_explanation, working_quality

router = APIRouter(prefix="/api/v1/timetable-projects", tags=["timetable-editor"])


@router.get("/{project_id}/working-timetable/quality")
def quality(project_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    return working_quality(db, tenant, project_id)


@router.get("/{project_id}/working-timetable/quality/compare/{candidate_id}")
def quality_compare(project_id: uuid.UUID, candidate_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    return compare_quality(db, tenant, project_id, candidate_id)


@router.get("/{project_id}/working-timetable/explanations")
def explain_working(project_id: uuid.UUID, occurrence_id: str, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    return working_explanation(db, tenant, project_id, occurrence_id)


@router.post("/{project_id}/working-timetable/from-candidate/{candidate_id}", status_code=201)
def derive(
    project_id: uuid.UUID,
    candidate_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return create_from_candidate(db, tenant, project_id, candidate_id)


@router.get("/{project_id}/working-timetable")
def read(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return serialize_working(db, _working(db, tenant, project_id))


@router.post("/{project_id}/working-timetable/moves/analyze")
def move_analysis(
    project_id: uuid.UUID,
    payload: MoveInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return analyze_move(
        db, tenant, project_id, payload.occurrence_id, payload.target_slot_id, payload.revision
    )


@router.post("/{project_id}/working-timetable/moves/apply")
def move_apply(
    project_id: uuid.UUID,
    payload: MoveInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return apply_move(
        db, tenant, project_id, payload.occurrence_id, payload.target_slot_id, payload.revision
    )


@router.post("/{project_id}/working-timetable/swaps/apply")
def swap_apply(
    project_id: uuid.UUID,
    payload: SwapInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return apply_swap(
        db,
        tenant,
        project_id,
        payload.first_occurrence_id,
        payload.second_occurrence_id,
        payload.revision,
    )


@router.post("/{project_id}/working-timetable/locks", status_code=201)
def lock_create(
    project_id: uuid.UUID,
    payload: LockInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return create_lock(db, tenant, project_id, payload)


@router.delete("/{project_id}/working-timetable/locks/{lock_id}")
def lock_delete(
    project_id: uuid.UUID,
    lock_id: uuid.UUID,
    revision: Annotated[int, Query(ge=1)],
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return delete_lock(db, tenant, project_id, lock_id, revision)


@router.post("/{project_id}/working-timetable/undo")
def undo(
    project_id: uuid.UUID,
    payload: RevisionInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return undo_redo(db, tenant, project_id, payload.revision, redo=False)


@router.post("/{project_id}/working-timetable/redo")
def redo(
    project_id: uuid.UUID,
    payload: RevisionInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return undo_redo(db, tenant, project_id, payload.revision, redo=True)


@router.get("/{project_id}/working-timetable/audit")
def audit(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    return audit_list(db, tenant, project_id)


@router.post("/{project_id}/working-timetable/repair/preview", status_code=201)
def repair_preview_route(
    project_id: uuid.UUID,
    payload: RepairInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return repair_preview(db, tenant, project_id, payload)


@router.post("/{project_id}/working-timetable/repair/apply")
def repair_apply_route(
    project_id: uuid.UUID,
    payload: RepairApplyInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return apply_repair(
        db,
        tenant,
        project_id,
        payload.occurrence_id,
        payload.target_slot_id,
        payload.changes,
        payload.time_limit_seconds,
        payload.fingerprint,
        payload.revision,
    )


@router.post("/{project_id}/working-timetable/snapshots", status_code=201)
def snapshot_create(
    project_id: uuid.UUID,
    payload: SnapshotInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return create_snapshot(db, tenant, project_id, payload.revision, payload.name)


@router.get("/{project_id}/working-timetable/snapshots")
def snapshots(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    return list_snapshots(db, tenant, project_id)


@router.get("/{project_id}/working-timetable/snapshots/{snapshot_id}/compare")
def snapshot_compare(
    project_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return compare_snapshot(db, tenant, project_id, snapshot_id)


@router.post("/{project_id}/working-timetable/snapshots/{snapshot_id}/restore", status_code=201)
def snapshot_restore(
    project_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    payload: SnapshotRestoreInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return restore_snapshot(
        db, tenant, project_id, snapshot_id, payload.revision, payload.change_summary
    )

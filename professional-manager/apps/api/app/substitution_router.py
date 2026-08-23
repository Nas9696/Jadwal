import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.substitution_schemas import (
    AbsenceCreate,
    AbsenceRead,
    AbsenceRefresh,
    CandidateListRead,
    DailySummaryRead,
    SubstituteAssign,
    SubstituteUnassign,
    WaitingPolicyInput,
    WaitingPolicyRead,
    WaitingProfileInput,
    WaitingProfileRead,
    WorkloadRead,
    SubstitutionNeedRead,
)
from app.substitution_services import (
    assign_substitute,
    cancel_absence,
    create_absence,
    daily_summary,
    get_policy,
    list_absences,
    rank_candidates,
    refresh_absence,
    save_policy,
    save_profile,
    unassign_substitute,
    workload_summary,
)
from app.tenant import tenant_context

router = APIRouter(prefix="/api/v1/timetable-projects", tags=["waiting-substitutions"])


@router.get("/{project_id}/substitutions/policy", response_model=WaitingPolicyRead)
def policy_read(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return get_policy(db, tenant, project_id)


@router.put("/{project_id}/substitutions/policy", response_model=WaitingPolicyRead)
def policy_update(
    project_id: uuid.UUID,
    payload: WaitingPolicyInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return save_policy(db, tenant, project_id, payload)


@router.put("/{project_id}/substitutions/profiles/{teacher_id}", response_model=WaitingProfileRead)
def profile_update(
    project_id: uuid.UUID,
    teacher_id: uuid.UUID,
    payload: WaitingProfileInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return save_profile(db, tenant, project_id, teacher_id, payload)


@router.get("/{project_id}/substitutions/workloads", response_model=list[WorkloadRead])
def workloads(
    project_id: uuid.UUID,
    on_date: Annotated[date, Query(alias="date")],
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    return workload_summary(db, tenant, project_id, on_date)


@router.post("/{project_id}/substitutions/absences", status_code=201, response_model=AbsenceRead)
def absence_create(
    project_id: uuid.UUID,
    payload: AbsenceCreate,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return create_absence(db, tenant, project_id, payload)


@router.get("/{project_id}/substitutions/absences", response_model=list[AbsenceRead])
def absence_list(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
    on_date: Annotated[date | None, Query(alias="date")] = None,
    school_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    return list_absences(db, tenant, project_id, on_date, school_id)


@router.post("/{project_id}/substitutions/absences/{absence_id}/refresh", response_model=AbsenceRead)
def absence_refresh(
    project_id: uuid.UUID,
    absence_id: uuid.UUID,
    payload: AbsenceRefresh,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return refresh_absence(db, tenant, project_id, absence_id, payload.working_timetable_revision)


@router.post("/{project_id}/substitutions/absences/{absence_id}/cancel", response_model=AbsenceRead)
def absence_cancel(
    project_id: uuid.UUID,
    absence_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return cancel_absence(db, tenant, project_id, absence_id)


@router.get("/{project_id}/substitutions/needs/{need_id}/candidates", response_model=CandidateListRead)
def candidates(
    project_id: uuid.UUID,
    need_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return rank_candidates(db, tenant, project_id, need_id)


@router.post("/{project_id}/substitutions/needs/{need_id}/assign", response_model=SubstitutionNeedRead)
def assignment_create(
    project_id: uuid.UUID,
    need_id: uuid.UUID,
    payload: SubstituteAssign,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return assign_substitute(db, tenant, project_id, need_id, payload)


@router.post("/{project_id}/substitutions/needs/{need_id}/unassign", response_model=SubstitutionNeedRead)
def assignment_cancel(
    project_id: uuid.UUID,
    need_id: uuid.UUID,
    payload: SubstituteUnassign,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return unassign_substitute(db, tenant, project_id, need_id, payload)


@router.get("/{project_id}/substitutions/daily-summary", response_model=DailySummaryRead)
def summary(
    project_id: uuid.UUID,
    on_date: Annotated[date, Query(alias="date")],
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return daily_summary(db, tenant, project_id, on_date)

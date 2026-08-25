import uuid
from typing import Annotated, Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import SchedulingRule, TimetableProject
from app.project_schemas import ProjectInput, RuleInput
from app.project_services import (
    _project,
    build_problem,
    preflight,
    save_project,
    save_rule,
    serialize_project,
    serialize_rule,
)
from pm_scheduler.rules import RULE_REGISTRY
from app.solve_schemas import SolveRequest
from app.solve_services import (
    create_solve_run,
    execute_solve_run,
    get_latest_run,
    get_run,
    serialize_candidate,
    serialize_run,
)
from app.tenant import tenant_context
from app.quality_services import candidate_explanation, candidate_quality

router = APIRouter(prefix="/api/v1/timetable-projects", tags=["timetable-projects"])


@router.get("")
def projects(
    tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]
) -> list[dict[str, Any]]:
    return [
        serialize_project(db, x)
        for x in db.scalars(
            select(TimetableProject)
            .where(TimetableProject.tenant_id == tenant)
            .order_by(TimetableProject.created_at.desc())
        )
    ]


@router.post("", status_code=201)
def create(
    payload: ProjectInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return serialize_project(db, save_project(db, tenant, payload))


@router.put("/{project_id}")
def update(
    project_id: uuid.UUID,
    payload: ProjectInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return serialize_project(db, save_project(db, tenant, payload, project_id))


@router.delete("/{project_id}", status_code=204)
def delete(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    project = _project(db, tenant, project_id)
    if project.status != "draft":
        raise HTTPException(409, detail={"code": "project_has_dependencies"})
    db.delete(project)
    db.commit()
    return Response(status_code=204)


@router.get("/rule-catalog")
def catalog() -> list[dict[str, Any]]:
    return [
        {
            "rule_type": k,
            "targets": list(v.target_keys),
            "allowed_severity": sorted(v.severities),
            "label_ar": v.label_ar,
            "category": v.category,
            "translator": "pm004a-cp-sat",
        }
        for k, v in RULE_REGISTRY.items()
    ]


@router.get("/{project_id}/rules")
def rules(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    _project(db, tenant, project_id)
    return [serialize_rule(rule) for rule in db.scalars(
            select(SchedulingRule)
            .where(
                SchedulingRule.tenant_id == tenant,
                SchedulingRule.timetable_project_id == project_id,
            )
            .order_by(SchedulingRule.created_at.desc())
        )]


@router.post("/{project_id}/rules", status_code=201)
def create_project_rule(
    project_id: uuid.UUID,
    payload: RuleInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    return serialize_rule(save_rule(db, tenant, project_id, payload))


@router.put("/{project_id}/rules/{rule_id}")
def update_project_rule(
    project_id: uuid.UUID,
    rule_id: uuid.UUID,
    payload: RuleInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    return serialize_rule(save_rule(db, tenant, project_id, payload, rule_id))


@router.post("/{project_id}/rules/{rule_id}/duplicate", status_code=201)
def duplicate(
    project_id: uuid.UUID,
    rule_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    rule = db.scalar(
        select(SchedulingRule).where(
            SchedulingRule.id == rule_id,
            SchedulingRule.tenant_id == tenant,
            SchedulingRule.timetable_project_id == project_id,
        )
    )
    if rule is None:
        raise HTTPException(404, detail={"code": "rule_not_found"})
    return serialize_rule(save_rule(
        db,
        tenant,
        project_id,
        RuleInput.model_validate(
            {
                "label": f"نسخة من {rule.label}",
                "description": rule.description,
                "rule_type": rule.rule_type,
                "severity": rule.severity,
                "weight": rule.weight,
                "selector": rule.selector,
                "parameters": rule.parameters,
                "enabled": rule.enabled,
            }
        ),
    ))


@router.delete("/{project_id}/rules/{rule_id}", status_code=204)
def delete_rule(
    project_id: uuid.UUID,
    rule_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    rule = db.scalar(
        select(SchedulingRule).where(
            SchedulingRule.id == rule_id,
            SchedulingRule.tenant_id == tenant,
            SchedulingRule.timetable_project_id == project_id,
        )
    )
    if rule:
        db.delete(rule)
        db.commit()
    return Response(status_code=204)


@router.post("/{project_id}/preflight")
def run_preflight(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return preflight(db, tenant, project_id)


@router.get("/{project_id}/problem")
def problem(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    return build_problem(db, tenant, project_id)


@router.post("/{project_id}/solve", status_code=202)
def start_solve(
    project_id: uuid.UUID,
    payload: SolveRequest,
    background_tasks: BackgroundTasks,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    run = create_solve_run(db, tenant, project_id, payload)
    background_tasks.add_task(execute_solve_run, db.get_bind(), run.id)
    return serialize_run(db, run)


@router.get("/{project_id}/solve-runs/latest")
def latest_solve_run(
    project_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any] | None:
    run = get_latest_run(db, tenant, project_id)
    return serialize_run(db, run) if run is not None else None


@router.get("/{project_id}/solve-runs/{run_id}")
def solve_run(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return serialize_run(db, get_run(db, tenant, project_id, run_id))


@router.get("/{project_id}/candidates/{candidate_id}")
def candidate_detail(
    project_id: uuid.UUID,
    candidate_id: uuid.UUID,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return serialize_candidate(db, tenant, project_id, candidate_id)


@router.get("/{project_id}/candidates/{candidate_id}/quality")
def candidate_quality_report(project_id: uuid.UUID, candidate_id: uuid.UUID, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    return candidate_quality(db, tenant, project_id, candidate_id)


@router.get("/{project_id}/candidates/{candidate_id}/explanations")
def explain_candidate_placement(project_id: uuid.UUID, candidate_id: uuid.UUID, occurrence_id: str, tenant: Annotated[uuid.UUID, Depends(tenant_context)], db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    return candidate_explanation(db, tenant, project_id, candidate_id, occurrence_id)

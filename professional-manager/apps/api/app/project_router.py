import uuid
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import SchedulingRule, TimetableProject
from app.project_schemas import ProjectInput, RuleInput
from app.project_services import (
    RULE_REGISTRY,
    _project,
    build_problem,
    preflight,
    save_project,
    save_rule,
    serialize_project,
)
from app.tenant import tenant_context

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
            "target": v[0],
            "allowed_severity": sorted(v[1]),
            "label_ar": v[2],
            "translator": "pm003b",
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
    return list(
        db.scalars(
            select(SchedulingRule)
            .where(
                SchedulingRule.tenant_id == tenant,
                SchedulingRule.timetable_project_id == project_id,
            )
            .order_by(SchedulingRule.created_at.desc())
        )
    )


@router.post("/{project_id}/rules", status_code=201)
def create_project_rule(
    project_id: uuid.UUID,
    payload: RuleInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    return save_rule(db, tenant, project_id, payload)


@router.put("/{project_id}/rules/{rule_id}")
def update_project_rule(
    project_id: uuid.UUID,
    rule_id: uuid.UUID,
    payload: RuleInput,
    tenant: Annotated[uuid.UUID, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    return save_rule(db, tenant, project_id, payload, rule_id)


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
    return save_rule(
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
    )


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

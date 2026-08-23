from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant_parser import DeterministicArabicRuleParser, ProjectEntityResolver
from app.assistant_schemas import AssistantConfirmRequest, AssistantParseRequest
from app.models import AssistantRuleDraft
from app.project_schemas import RuleInput
from app.project_services import _project, save_rule, serialize_rule, validate_rule

DRAFT_TTL = timedelta(minutes=30)
logger = logging.getLogger(__name__)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _rule_input(proposal: dict[str, Any]) -> RuleInput:
    try:
        return RuleInput.model_validate(
            {
                "label": proposal["arabic_summary"],
                "description": "اقتراح مؤكد من المساعد العربي للجدولة.",
                "rule_type": proposal["rule_type"],
                "severity": proposal["severity"],
                "weight": proposal.get("weight"),
                "selector": proposal["selector"],
                "parameters": proposal["parameters"],
                "enabled": True,
            }
        )
    except (KeyError, ValidationError) as exc:
        raise HTTPException(422, detail={"code": "invalid_assistant_proposal"}) from exc


def parse_assistant_request(
    db: Session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: AssistantParseRequest,
) -> dict[str, Any]:
    project = _project(db, tenant_id, project_id)
    parser = DeterministicArabicRuleParser()
    resolver = ProjectEntityResolver(db, tenant_id, project, payload.resolutions)
    parsed = parser.parse(payload.text, resolver)

    # The registry and authoritative project-scope validator are the only
    # acceptance path. Parsing never substitutes an approximate rule type.
    if parsed["status"] == "ready":
        for proposal in parsed["proposals"]:
            validate_rule(db, tenant_id, project, _rule_input(proposal))

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + DRAFT_TTL
    draft = AssistantRuleDraft(
        tenant_id=tenant_id,
        timetable_project_id=project_id,
        token_hash=_token_hash(token),
        source_text=payload.text,
        parser_type=parser.provider_type,
        status=parsed["status"],
        proposals=parsed["proposals"],
        clarifications=parsed["clarifications"],
        warnings=parsed["warnings"],
        expires_at=expires_at,
    )
    db.add(draft)
    db.commit()
    logger.info(
        "assistant preview parsed provider=%s project_id=%s status=%s proposal_count=%d",
        parser.provider_type,
        project_id,
        parsed["status"],
        len(parsed["proposals"]),
    )
    return {
        "source_text": payload.text,
        "status": parsed["status"],
        "parser_type": parser.provider_type,
        "preview_token": token,
        "expires_at": expires_at.isoformat(),
        "proposals": parsed["proposals"],
        "clarifications": parsed["clarifications"],
        "warnings": parsed["warnings"],
    }


def confirm_assistant_request(
    db: Session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: AssistantConfirmRequest,
) -> dict[str, Any]:
    project = _project(db, tenant_id, project_id)
    draft = db.scalar(
        select(AssistantRuleDraft)
        .where(
            AssistantRuleDraft.tenant_id == tenant_id,
            AssistantRuleDraft.timetable_project_id == project_id,
            AssistantRuleDraft.token_hash == _token_hash(payload.preview_token),
        )
        .with_for_update()
    )
    if not draft:
        raise HTTPException(409, detail={"code": "assistant_preview_tampered"})
    now = datetime.now(UTC)
    expires_at = draft.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if draft.consumed_at is not None:
        raise HTTPException(409, detail={"code": "assistant_preview_already_consumed"})
    if expires_at <= now:
        raise HTTPException(409, detail={"code": "assistant_preview_expired"})
    if draft.status != "ready":
        raise HTTPException(409, detail={"code": "assistant_preview_not_ready"})

    by_id = {proposal["id"]: proposal for proposal in draft.proposals}
    if any(proposal_id not in by_id for proposal_id in payload.proposal_ids):
        raise HTTPException(409, detail={"code": "assistant_preview_tampered"})

    created = []
    try:
        for proposal_id in payload.proposal_ids:
            rule_input = _rule_input(by_id[proposal_id])
            # Revalidate current registry, tenant and project scope. This also
            # catches references that became stale after preview.
            validate_rule(db, tenant_id, project, rule_input)
            created.append(save_rule(db, tenant_id, project_id, rule_input, commit=False))
        draft.status = "consumed"
        draft.consumed_at = now
        draft.created_rule_ids = [str(rule.id) for rule in created]
        db.add(draft)
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info(
        "assistant preview confirmed provider=%s project_id=%s created_rule_ids=%s",
        draft.parser_type,
        project_id,
        draft.created_rule_ids,
    )
    return {"created_rules": [serialize_rule(rule) for rule in created], "consumed": True}

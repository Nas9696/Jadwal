from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class AssistantParseRequest(BaseModel):
    text: str = Field(min_length=2, max_length=2000)
    resolutions: dict[str, str] = Field(default_factory=dict)


class AssistantConfirmRequest(BaseModel):
    preview_token: str = Field(min_length=24, max_length=200)
    proposal_ids: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_proposals(self) -> "AssistantConfirmRequest":
        if len(set(self.proposal_ids)) != len(self.proposal_ids):
            raise ValueError("duplicate_proposal_ids")
        return self


class AssistantProposal(BaseModel):
    id: str
    rule_type: str
    severity: Literal["hard", "soft"]
    weight: int | None = None
    selector: dict[str, Any]
    parameters: dict[str, Any]
    resolved_labels: dict[str, Any]
    arabic_summary: str
    evidence: list[str]


class ClarificationChoice(BaseModel):
    id: str
    label: str
    context: str | None = None


class AssistantClarification(BaseModel):
    key: str
    reference_type: str
    mention: str
    question: str
    choices: list[ClarificationChoice]


class AssistantParseResponse(BaseModel):
    source_text: str
    status: Literal["ready", "needs_clarification", "unsupported", "invalid"]
    parser_type: str
    preview_token: str
    expires_at: str
    proposals: list[AssistantProposal]
    clarifications: list[AssistantClarification]
    warnings: list[dict[str, Any]]


class AssistantConfirmResponse(BaseModel):
    created_rules: list[dict[str, Any]]
    consumed: bool = True

"""Strict, framework-independent contracts for dialogue interpretations."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConditionDraft(StrictModel):
    scope: str = Field(default="notices", min_length=1, max_length=80)
    polarity: Literal["include", "exclude"]
    strength: Literal["preferred", "required"] = "preferred"
    text: str = Field(min_length=1, max_length=300)


class ConfirmedCondition(ConditionDraft):
    condition_id: str = Field(min_length=1, max_length=128)


class ConfirmedPreferences(StrictModel):
    conditions: list[ConfirmedCondition] = Field(default_factory=list, max_length=100)


class ChangeOperation(StrictModel):
    operation: Literal["add", "update", "remove"]
    target_condition_id: str | None = Field(default=None, max_length=128)
    condition: ConditionDraft | None = None

    @model_validator(mode="after")
    def check_target_and_payload(self) -> "ChangeOperation":
        if self.operation == "add" and (self.target_condition_id or self.condition is None):
            raise ValueError("add requires a condition and no target_condition_id")
        if self.operation == "update" and (not self.target_condition_id or self.condition is None):
            raise ValueError("update requires target_condition_id and condition")
        if self.operation == "remove" and (not self.target_condition_id or self.condition is not None):
            raise ValueError("remove requires only target_condition_id")
        return self


class RecentTurn(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class PendingProposal(StrictModel):
    proposal_id: str = Field(min_length=1, max_length=128)
    base_preference_version: int = Field(ge=0)
    operations: list[ChangeOperation] = Field(min_length=1, max_length=8)


class DialogueRequest(StrictModel):
    message: str = Field(min_length=1, max_length=2000)
    preference_version: int = Field(ge=0)
    confirmed_preferences: ConfirmedPreferences = Field(default_factory=ConfirmedPreferences)
    recent_history: list[RecentTurn] = Field(default_factory=list, max_length=12)
    pending_proposal: PendingProposal | None = None
    unresolved_question: str | None = Field(default=None, max_length=500)
    trace_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")


class DialogueInterpretation(StrictModel):
    decision: Literal["ask", "propose", "no_change"]
    assistant_message: str = Field(min_length=1, max_length=2000)
    proposed_changes: list[ChangeOperation] = Field(default_factory=list, max_length=8)
    clarification: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def check_decision_consistency(self) -> "DialogueInterpretation":
        if self.decision == "propose":
            if not self.proposed_changes or self.clarification is not None:
                raise ValueError("propose requires changes and no clarification")
        elif self.decision == "ask":
            if self.proposed_changes or not self.clarification:
                raise ValueError("ask requires clarification and no proposed changes")
        elif self.proposed_changes or self.clarification is not None:
            raise ValueError("no_change must not propose changes or ask a clarification")
        return self


class DialogueResponse(DialogueInterpretation):
    trace_id: str = Field(min_length=1, max_length=64)


def validate_proposed_targets(request: DialogueRequest, result: DialogueInterpretation) -> None:
    """Reject made-up existing IDs; final user ownership is still Backend's job."""
    confirmed = {c.condition_id for c in request.confirmed_preferences.conditions}
    seen: set[str] = set()
    for change in result.proposed_changes:
        if change.operation in ("update", "remove"):
            target = change.target_condition_id
            if target not in confirmed:
                raise ValueError("proposed change targets a nonexistent confirmed condition")
            if target in seen:
                raise ValueError("same confirmed condition targeted more than once")
            seen.add(target)

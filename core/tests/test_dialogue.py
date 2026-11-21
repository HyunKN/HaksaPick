"""Executable dialogue domain and actual LangGraph routing tests (no Claude key)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.dialogue.workflow import BasicDialogueRunner, LangGraphDialogueRunner
from app.schemas.dialogue import (
    ChangeOperation,
    ConfirmedCondition,
    ConfirmedPreferences,
    DialogueInterpretation,
    DialogueRequest,
)


class FakeInterpreter:
    def __init__(self, data):
        self.data = data
        self.calls = 0

    def interpret(self, request):
        self.calls += 1
        return self.data


def request_with_confirmed() -> DialogueRequest:
    return DialogueRequest(
        message="그 조건을 수정하고 싶어",
        preference_version=3,
        confirmed_preferences=ConfirmedPreferences(
            conditions=[
                ConfirmedCondition(
                    condition_id="cond-intern",
                    polarity="include",
                    text="현장실습",
                )
            ]
        ),
        trace_id="trace-001",
    )


@pytest.mark.parametrize("runner", [LangGraphDialogueRunner, BasicDialogueRunner])
def test_propose_add_multiple_changes_without_saving(runner):
    parsed = DialogueInterpretation(
        decision="propose",
        assistant_message="두 조건을 추가할까요?",
        proposed_changes=[
            ChangeOperation(
                operation="add", condition={"polarity": "include", "text": "현장실습"}
            ),
            ChangeOperation(
                operation="add",
                condition={"polarity": "exclude", "strength": "required", "text": "국가장학금 신청 안내"},
            ),
        ],
    )
    fake = FakeInterpreter(parsed)
    result = runner(fake).run(DialogueRequest(
        message="현장실습은 포함하고 국가장학금 신청 안내는 제외해줘",
        preference_version=1,
        trace_id="trace-multi",
    ))
    assert result.decision == "propose"
    assert result.trace_id == "trace-multi"
    assert len(result.proposed_changes) == 2
    assert result.proposed_changes[1].condition.strength == "required"
    assert fake.calls == 1


@pytest.mark.parametrize("runner", [LangGraphDialogueRunner, BasicDialogueRunner])
def test_ask_clarification(runner):
    fake = FakeInterpreter(DialogueInterpretation(
        decision="ask",
        assistant_message="어떤 조건을 삭제할까요?",
        clarification="삭제할 조건을 지정해 주세요.",
    ))
    result = runner(fake).run(request_with_confirmed())
    assert result.decision == "ask"
    assert result.proposed_changes == []
    assert result.clarification


@pytest.mark.parametrize("runner", [LangGraphDialogueRunner, BasicDialogueRunner])
def test_chat_acknowledgement_is_not_approval(runner):
    fake = FakeInterpreter(DialogueInterpretation(
        decision="no_change",
        assistant_message="저장하려면 변경안의 승인 버튼을 눌러 주세요.",
    ))
    result = runner(fake).run(DialogueRequest(
        message="응",
        preference_version=4,
    ))
    assert result.decision == "no_change"
    assert result.proposed_changes == []


@pytest.mark.parametrize("runner", [LangGraphDialogueRunner, BasicDialogueRunner])
def test_unknown_target_id_rejected(runner):
    fake = FakeInterpreter(DialogueInterpretation(
        decision="propose",
        assistant_message="기존 조건을 지울까요?",
        proposed_changes=[
            ChangeOperation(operation="remove", target_condition_id="someone-elses-id")
        ],
    ))
    with pytest.raises(ValueError, match="nonexistent"):
        runner(fake).run(request_with_confirmed())


@pytest.mark.parametrize("runner", [LangGraphDialogueRunner, BasicDialogueRunner])
def test_existing_target_update_allowed_as_uncommitted_proposal(runner):
    fake = FakeInterpreter(DialogueInterpretation(
        decision="propose",
        assistant_message="현장실습과 인턴을 포함하도록 바꿀까요?",
        proposed_changes=[ChangeOperation(
            operation="update",
            target_condition_id="cond-intern",
            condition={"polarity": "include", "text": "현장실습 및 인턴"},
        )],
    ))
    original = request_with_confirmed()
    result = runner(fake).run(original)
    assert result.proposed_changes[0].target_condition_id == "cond-intern"
    assert original.confirmed_preferences.conditions[0].text == "현장실습"


def test_malformed_decision_refused_by_pydantic():
    with pytest.raises(ValidationError):
        DialogueInterpretation.model_validate({
            "decision": "propose",
            "assistant_message": "추가할게요",
            "proposed_changes": [],
        })


def test_invalid_change_operation_refused():
    with pytest.raises(ValidationError):
        ChangeOperation(operation="remove", target_condition_id="cond-intern",
                        condition={"polarity": "exclude", "text": "임의 조건"})


def test_extra_user_id_is_not_accepted_by_core_contract():
    with pytest.raises(ValidationError):
        DialogueRequest(message="테스트", preference_version=1, user_id="forged-user")


def test_duplicate_target_operations_rejected():
    fake = FakeInterpreter(DialogueInterpretation(
        decision="propose",
        assistant_message="두 번 수정할까요?",
        proposed_changes=[
            ChangeOperation(operation="remove", target_condition_id="cond-intern"),
            ChangeOperation(operation="remove", target_condition_id="cond-intern"),
        ],
    ))
    with pytest.raises(ValueError, match="more than once"):
        LangGraphDialogueRunner(fake).run(request_with_confirmed())

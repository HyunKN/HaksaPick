"""Internal API tests use a fake interpreter; never contact Claude."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.dialogue import DialogueInterpretation


class FakeInterpreter:
    def __init__(self, output=None, error=None):
        self.output = output or DialogueInterpretation(
            decision="no_change", assistant_message="설정 변경이 없습니다."
        )
        self.error = error

    def interpret(self, request):
        if self.error:
            raise self.error
        return self.output


def test_internal_route_requires_authentication(monkeypatch):
    monkeypatch.setenv("HAKSAPICK_CORE_INTERNAL_TOKEN", "unit-test-token")
    with TestClient(create_app(FakeInterpreter())) as client:
        body = {"message": "안녕", "preference_version": 0}
        assert client.post("/internal/haksapick/interpret", json=body).status_code == 401
        assert client.post("/internal/haksapick/interpret", json=body, headers={
            "X-HaksaPick-Internal-Token": "wrong-token"
        }).status_code == 401


def test_internal_auth_is_fail_closed_when_unconfigured(monkeypatch):
    monkeypatch.delenv("HAKSAPICK_CORE_INTERNAL_TOKEN", raising=False)
    with TestClient(create_app(FakeInterpreter())) as client:
        res = client.post("/internal/haksapick/interpret",
                          headers={"X-HaksaPick-Internal-Token": "anything"},
                          json={"message": "안녕", "preference_version": 0})
    assert res.status_code == 503
    assert res.json()["detail"] == "internal_auth_not_configured"


def test_chat_response_with_fake_interpreter(monkeypatch):
    monkeypatch.setenv("HAKSAPICK_CORE_INTERNAL_TOKEN", "unit-test-token")
    with TestClient(create_app(FakeInterpreter())) as client:
        res = client.post("/internal/haksapick/interpret",
                          headers={"X-HaksaPick-Internal-Token": "unit-test-token"},
                          json={"message": "고마워", "preference_version": 3,
                                "confirmed_preferences": {"conditions": []},
                                "trace_id": "trace-test"})
    assert res.status_code == 200
    assert res.json()["decision"] == "no_change"
    assert res.json()["trace_id"] == "trace-test"
    assert res.json()["proposed_changes"] == []


def test_model_failure_never_claims_success(monkeypatch):
    monkeypatch.setenv("HAKSAPICK_CORE_INTERNAL_TOKEN", "unit-test-token")
    with TestClient(create_app(FakeInterpreter(error=RuntimeError("fake outage")))) as client:
        res = client.post("/internal/haksapick/interpret",
                          headers={"X-HaksaPick-Internal-Token": "unit-test-token"},
                          json={"message": "현장실습 추가", "preference_version": 3})
    assert res.status_code == 503
    assert res.json()["detail"] == "llm_unavailable"


def test_forged_existing_condition_id_is_rejected(monkeypatch):
    monkeypatch.setenv("HAKSAPICK_CORE_INTERNAL_TOKEN", "unit-test-token")
    fake = FakeInterpreter(output=DialogueInterpretation(
        decision="propose", assistant_message="삭제할까요?",
        proposed_changes=[{"operation": "remove", "target_condition_id": "not-owned"}],
    ))
    with TestClient(create_app(fake)) as client:
        res = client.post("/internal/haksapick/interpret",
                          headers={"X-HaksaPick-Internal-Token": "unit-test-token"},
                          json={"message": "삭제해", "preference_version": 1})
    assert res.status_code == 502
    assert res.json()["detail"] == "invalid_llm_output"


def test_invalid_payload_is_422_without_running_llm(monkeypatch):
    monkeypatch.setenv("HAKSAPICK_CORE_INTERNAL_TOKEN", "unit-test-token")
    with TestClient(create_app(FakeInterpreter())) as client:
        res = client.post("/internal/haksapick/interpret",
                          headers={"X-HaksaPick-Internal-Token": "unit-test-token"},
                          json={"message": "", "preference_version": -1})
    assert res.status_code == 422

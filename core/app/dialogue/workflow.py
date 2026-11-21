"""Minimal LangGraph state machine: interpret -> ask/propose/no_change."""
from __future__ import annotations

import json
import logging
import time
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.llm.adapter import DialogueInterpreter
from app.schemas.dialogue import (
    DialogueInterpretation,
    DialogueRequest,
    DialogueResponse,
    validate_proposed_targets,
)

logger = logging.getLogger("haksapick.dialogue")


class DialogueState(TypedDict, total=False):
    request: DialogueRequest
    parsed: DialogueInterpretation
    response: DialogueResponse


def _response(request: DialogueRequest, parsed: DialogueInterpretation) -> DialogueResponse:
    validate_proposed_targets(request, parsed)
    return DialogueResponse(**parsed.model_dump(), trace_id=request.trace_id or uuid4().hex)


def _record(trace_id: str | None, stage: str, status: str, **metadata: object) -> None:
    """Metadata only; never log raw chat text, preferences or tokens."""
    logger.info(json.dumps({
        "trace_id": trace_id,
        "stage": stage,
        "status": status,
        **metadata,
    }, ensure_ascii=False))


class LangGraphDialogueRunner:
    def __init__(self, interpreter: DialogueInterpreter):
        self.interpreter = interpreter
        builder = StateGraph(DialogueState)

        def analyze(state: DialogueState) -> dict:
            request = state["request"]
            started = time.monotonic()
            try:
                parsed = DialogueInterpretation.model_validate(interpreter.interpret(request))
                validate_proposed_targets(request, parsed)
            except Exception:
                _record(request.trace_id, "analyze", "error")
                raise
            _record(request.trace_id, "analyze", "ok",
                    decision=parsed.decision,
                    duration_ms=round((time.monotonic() - started) * 1000))
            return {"parsed": parsed}

        def route(state: DialogueState) -> str:
            return state["parsed"].decision

        def present(state: DialogueState) -> dict:
            response = _response(state["request"], state["parsed"])
            _record(response.trace_id, "branch", "ok", decision=response.decision)
            return {"response": response}

        builder.add_node("analyze", analyze)
        for name in ("ask", "propose", "no_change"):
            builder.add_node(name, present)
            builder.add_edge(name, END)
        builder.add_edge(START, "analyze")
        builder.add_conditional_edges(
            "analyze", route,
            {"ask": "ask", "propose": "propose", "no_change": "no_change"},
        )
        self.graph = builder.compile()

    def run(self, request: DialogueRequest) -> DialogueResponse:
        result = self.graph.invoke({"request": request}, {"recursion_limit": 10})
        return DialogueResponse.model_validate(result["response"])


class BasicDialogueRunner:
    """Non-graph fallback with an identical domain contract."""

    def __init__(self, interpreter: DialogueInterpreter):
        self.interpreter = interpreter

    def run(self, request: DialogueRequest) -> DialogueResponse:
        parsed = DialogueInterpretation.model_validate(self.interpreter.interpret(request))
        return _response(request, parsed)

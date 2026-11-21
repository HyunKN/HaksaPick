"""Internal Core HTTP boundary. Only an authenticated Backend should call this."""
from __future__ import annotations

import logging
import os
import secrets

from fastapi import FastAPI, Header, HTTPException
from pydantic import ValidationError

from app.dialogue.workflow import LangGraphDialogueRunner
from app.llm.adapter import DialogueInterpreter, LangChainClaudeInterpreter
from app.schemas.dialogue import DialogueRequest, DialogueResponse

logger = logging.getLogger("haksapick.api")


def create_app(interpreter: DialogueInterpreter | None = None) -> FastAPI:
    app = FastAPI(title="HaksaPick B Core", version="0.1.0")

    @app.post("/internal/haksapick/interpret", response_model=DialogueResponse)
    def interpret(
        request: DialogueRequest,
        x_haksapick_internal_token: str | None = Header(
            default=None, alias="X-HaksaPick-Internal-Token"
        ),
    ) -> DialogueResponse:
        expected_token = os.getenv("HAKSAPICK_CORE_INTERNAL_TOKEN")
        if not expected_token:
            raise HTTPException(status_code=503, detail="internal_auth_not_configured")
        if not x_haksapick_internal_token or not secrets.compare_digest(
            x_haksapick_internal_token, expected_token
        ):
            raise HTTPException(status_code=401, detail="unauthorized")

        try:
            adapter = interpreter if interpreter is not None else LangChainClaudeInterpreter()
            return LangGraphDialogueRunner(adapter).run(request)
        except (ValueError, ValidationError):
            logger.warning("Core dialogue output rejected; trace_id=%s", request.trace_id)
            raise HTTPException(status_code=502, detail="invalid_llm_output") from None
        except Exception as exc:
            # Do not print exception text/tracebacks: providers may echo private inputs.
            logger.error(
                "Core dialogue processing failed; trace_id=%s error_type=%s",
                request.trace_id, type(exc).__name__,
            )
            raise HTTPException(status_code=503, detail="llm_unavailable") from None

    return app


app = create_app()

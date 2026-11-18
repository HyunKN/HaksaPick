# Development context for HaksaPick

## Source of truth

1. **Read [docs/PRD.md](docs/PRD.md) before making product or AI-personalization decisions.**
2. Keep the PRD v0.1 baseline intact unless the user/team explicitly approves a change.
3. Treat **확정 / 제안 / 미결정** separately. Never turn a proposal into a requirement without approval.
4. Keep new work narrowly scoped: no unnecessary framework, agent graph, vector DB, or schema proliferation.

## Architecture guardrails

- Frontend → Spring Boot Backend (/api) → Python FastAPI Core → Claude Haiku.
- Backend handles identity, authorization, approved DB writes, optimistic version checking.
- Core handles context selection, LLM invocation, output validation, notice relevance analysis.
- LLM output is an **untrusted proposed change**, never a direct DB command.
- Start with Anthropic SDK + Pydantic; LangChain/LangGraph are optional replaceable experiments.

## Engineering and tests

- Write a small test case before/with each significant AI behavior.
- Test context retention, user approval, cross-user access denial, conflicts, invalid model output, and token usage.
- Report tests actually run separately from planned tests; never invent a PASS.
- Use UTF-8. Keep secrets, .env values, production URLs, private guides, private samples, and personal data out of commits.
- Do not modify unrelated project documents or the old roadmap without a request.

## Working notes

If the next step is unclear, identify the smallest PRD requirement not yet implemented, its input/output contract, acceptance test, and current blocker. Prefer a small code change and test to a broad redesign.

# HaksaPick B Core — 첫 실행 단위

범위: **사용자 메시지 → LangChain(Claude) 구조화 조건 해석 → LangGraph ask/propose/no_change 분기 → 변경안 반환**.

- 실제 DB 수정/승인 기능은 **없음**. Core가 반환한 변경안은 반드시 Spring Backend에서 검증·보관·명시적 사용자 승인 후 저장해야 합니다.
- Core API 경로와 JSON 필드명은 B 파트의 **초안**입니다. `docs/API_SPEC.md`, `docs/B_DIALOGUE_APPROVAL_DESIGN.md` 및 팀 공통 계약과 최종 합의 전까지 외부 확정 API로 간주하지 않습니다.
- 인증은 내부 Backend-to-Core용 공유 토큰의 **임시 최소 방어**입니다. 공개 인터넷에 Core를 노출하지 말고 실제 배포 시 네트워크 제한/인증 체계를 검토해야 합니다.
- LangGraph는 이 첫 단계에서 요청마다 새로 실행하며 영속 체크포인트를 사용하지 않습니다. 이전 대화·미해결 질문·승인 대기 제안은 Backend가 필요한 범위만 전달합니다.
- 별도 LangSmith/벡터 DB는 사용하지 않습니다.

## 설치와 실행

Python 3.11 권장. Poetry의 가상환경에 설치해 프로젝트 간 의존성 충돌을 피합니다.

```bash
cd core
poetry install
poetry run pytest tests -q
```

실제 Claude 연결 시 **서버 환경변수**로 설정합니다(값은 GitHub에 커밋하지 않음).

```bash
export HAKSAPICK_CLAUDE_MODEL=claude-haiku-4-5-20251001
export ANTHROPIC_API_KEY="<securely-provisioned-key>"
export HAKSAPICK_CORE_INTERNAL_TOKEN="<random-server-secret>"
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend 내부 호출의 예시(개발용 Mock 입력; 실제 계정/개인정보 사용 금지):

```bash
curl -X POST http://127.0.0.1:8000/internal/haksapick/interpret \
  -H "Content-Type: application/json" \
  -H "X-HaksaPick-Internal-Token: $HAKSAPICK_CORE_INTERNAL_TOKEN" \
  -d '{"message":"현장실습 모집은 포함하고 국가장학금 신청 안내는 제외해줘","preference_version":0,"confirmed_preferences":{"conditions":[]},"trace_id":"dev-test-01"}'
```

**테스트는 Claude API 키가 필요 없습니다.** `tests/test_dialogue.py`는 Mock 의도 결과로 실제 LangGraph 분기를 검증하고 기본 Python 대체 실행도 같은 계약으로 검증합니다. `tests/test_api.py`는 내부 인증/실패 응답을 확인합니다.

## 다음 구현 경계

1. Backend의 사용자 인증·소유권·변경안 보관 및 승인 트랜잭션
2. 실제 Claude 구조화 출력 평가 및 프롬프트 안정성 테스트
3. A 공지와 개인화 추천 모듈 연동

`poetry.lock`은 의존성을 실제 해결할 수 있는 개발/CI 환경에서 생성하고 검토해 커밋해야 합니다. Lock 파일 생성 전에는 설치 버전이 완전히 고정됐다고 주장하지 않습니다.

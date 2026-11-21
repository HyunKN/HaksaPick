# HaksaPick B 파트 — 기능별 모듈화 및 LangChain/LangGraph 적용 원칙

- 작성: 2026-11-21
- 상태: **개발 설계 원칙**. 코드 구현/테스트 완료를 의미하지 않음
- 기준: [PRD v0.3](PRD.md), [API 계약](API_SPEC.md), [데이터 모델](DATA_MODEL.md), [개발 프로세스](DEVELOPMENT_PROCESS.md), [AGENTS.md](../AGENTS.md)
- 관련 작업: 추천 설계 PR #7, 평가 설계 PR #8 (둘 다 작성 당시 Draft, `main` 미병합)
- 원칙: **기능 단위로 독립 모듈을 만들고, LangChain/LangGraph를 필요한 경계에만 적용**. 프레임워크 채택 자체가 목표가 아니며, 변경 용이성·테스트 용이성·품질·비용으로 효과 확인
- 소유: 사용자는 **B 파트의 Frontend·Spring Backend·Python Core 전반**을 기능 단위로 개발하며, A 공지 원본·공통 DB/API 및 C 알림 UI 연동은 별도 합의

## 1. 반드시 지킬 모듈화 원칙

1. **단일 책임**: 각 모듈은 한 가지 비즈니스 책임을 갖는다. 예: 의도 분석, 조건 변경안 생성, 공지 후보 검색, 근거 검증, 추천 정책 적용, 평가 기록.
2. **안정된 데이터 계약**: 모듈 사이에는 Pydantic 도메인 모델/명시적 DTO를 사용한다. LangGraph의 내부 State나 LangChain 메시지 객체를 Backend API나 DB 스키마에 노출하지 않는다.
3. **의존성 방향**: 도메인 정책 및 검증 함수는 LangChain/LangGraph·외부 LLM SDK에 의존하지 않는다. 프레임워크를 교체해도 추천 정책과 승인 규칙은 변하지 않는다.
4. **부작용 분리**: LLM은 `ask / propose / no_change` 및 근거를 제안한다. **로그인 사용자 승인, 소유권, 설정 버전, 중복 승인, DB 저장은 인증된 Spring Backend**가 처리한다. 그래프의 상태와 DB의 확정 설정은 다르다.
5. **테스트 우선**: 모듈 단위 Mock 테스트 → 모듈 간 계약 테스트 → 일부 실제 모델 평가 순서. 실패·경계·악성 입력 테스트를 함께 둔다.
6. **추적성**: 요청마다 공통 `trace_id`, 노드/단계 ID, 입력 버전, 모델·프롬프트 버전, 결과, 오류, 소요 시간(가능하면 토큰)을 기록한다. 개인 대화/학적 정보 전체를 자동 저장하는 기본값은 두지 않는다.
7. **작게 시작**: 노드 수나 프레임워크 컴포넌트를 늘리는 것 자체가 개선은 아니다. 변경 이유가 설명되는 단위만 분리한다.

## 2. 기능 책임과 권장 구현 방식

| 경계 | 기능 | 권장 구현 | 테스트 |
|---|---|---|---|
| `dialogue/intent` | 사용자 요청 의도/모호함 해석 | LangChain + Claude를 **LLMAdapter** 뒤에서 호출 | ask/propose/no_change, 모호한 발언 |
| `dialogue/proposal` | 기존 확정 조건과 비교해 add/update/remove 제안 | 순수 Python 규칙 + 필요할 때 LLM | 중복·충돌·조건 보존 |
| `dialogue/workflow` | 의도 분석→추가 질문/제안/일반 답변으로 분기 | **작은 LangGraph StateGraph** | 분기·상태 복원·동일 입력 계약 |
| `notice/candidates` | A 원문/메타데이터에서 후보 선택 | 일반 Python 필터/검색 인터페이스 | 후보 검색 누락 Recall |
| `notice/analysis` | 공지 자격/기한/관심 관련성 의미 판단 | LangChain Claude structured output 또는 어댑터 | 근거·미확인·형식 오류 |
| `recommendation/policy` | DEC-001~006 적용, 추천/확인/자격미충족/지난공지 분류 | **순수 Python 결정론적 함수** | 우선순위·복수 사유·마감 비교 |
| `evaluation` | QA 개선 사례·Gold 데이터·회귀 평가 | JSONL/pytest + 선택적 보관 API | 정답 대비 비교·개인정보 제외 |
| `observability` | 요청 실행/단계 결과 추적 | 공통 구조화 JSON 로그; 필요 시 OpenTelemetry 확장 | trace_id 연계·민감정보 마스킹 |

**LangGraph 범위:** 우선 대화형 설정의 명확한 분기에서 활용한다. 추천은 단순한 경우 일반 Python 파이프라인 또는 최소한의 그래프 노드만 사용하고, 단순 경로를 억지로 다단계 Agent로 만들지 않는다. PRD의 WorkflowRunner 인터페이스를 유지하고 같은 도메인 응답을 제공한다.

**LangChain 범위:** 프롬프트/Claude 연동, 구조화 출력, 필요 시 검색기 추상화에 사용한다. 조건 검증, DB 승인, 권한 검증 등 결정적 책임은 맡기지 않는다.

## 3. Core 디렉터리 구조 초안 (아직 생성된 실제 파일이 아님)

```text
core/
  app/
    routers/                  # HTTP 진입점, 입력/응답 DTO 연결
    schemas/                  # 외부 계약과 프레임워크 독립 도메인 모델
    dialogue/
      intent.py               # 의도·모호성 추출 (adapter 호출)
      proposal.py             # 변경안 생성/검증
      workflow.py             # 작은 LangGraph 대화 그래프
      state.py                # LangGraph 내부 상태(외부 API 미노출)
    notice/
      adapters.py             # A의 실제 공지 필드를 내부 모델로 변환
      candidates.py           # 후보 검색
      analysis.py             # Claude 공지 의미 분석
    recommendation/
      policy.py               # 순수 Python 분류·우선순위·사유 보존
    llm/
      interface.py            # LLMAdapter 프로토콜
      langchain_adapter.py    # 기본 Claude 연동
      anthropic_adapter.py    # 대체 경로
    workflow/
      interface.py            # WorkflowRunner 프로토콜
      basic_runner.py         # 기본 Python 대체 실행
    evaluation/               # 별도 제한된 실제 모델 평가 / QA 연결
    observability/            # 구조화 로그, trace_id
  tests/
    dialogue/
    notice/
    recommendation/
    contracts/
    evaluation/
```

실제 프로젝트 트리와 통합할 때 경로명은 조정할 수 있다. 각 기능 디렉터리에는 로직·테스트를 가까이 배치하고, 의미 없이 파일/계층을 증식하지 않는다.

## 4. 실행 흐름별 경계

### A. 대화형 관심 조건 설정 (LangGraph 활용)

`Frontend → Backend 인증 및 확정 조건 버전 조회 → Core dialogue workflow → [의도 분석 → 명확? → 추가 질문 / 변경안 생성 / 일반 답변] → Core 구조 검증 → Backend → UI`

- 추가 질문은 **대화 상태**로 관리하되, 사용자 확정 조건은 Backend DB를 진실의 원천으로 사용한다.
- 승인/취소 버튼 뒤 DB 쓰기는 **Graph 노드가 아닌 Backend 서비스**가 최종 수행한다.
- 인젝션·잘못된 JSON·LLM 시간 초과·승인 충돌 시 명시적으로 실패/재검토 처리한다.
- 다중 턴에 필요한 정보는 Backend가 전달하는 확정 조건/최근 대화/대기 변경안을 우선 사용한다. 운영 영속 체크포인트는 실제 중단·재개 필요가 검증될 때만 도입한다.

### B. 개인화 공지 추천 (최소 단계)

`Backend 확정 설정 조회 → A 공지 어댑터 → 후보 검색 → Claude 의미 분석 → Pydantic 검증 → Python 정책 함수 → Backend/Frontend`

- 후보 누락, 모델의 의미 해석 오류, 정책 결정 오류를 **서로 다른 단계**에서 식별한다.
- **LLM 분석 결과와 최종 추천 분류**는 분리해 테스트한다.
- 원문 인용/모델 판단에는 근거 및 불확실성 표시를 요구한다. 근거 인용 존재 검사만으로 의미 정확성을 확정하지 않는다.
- 마감일·자격·제외 충돌·다중 사유는 추천 설계 PR #7을 기준으로 구현한다. 다만 PR #7이 미병합 상태이면 아직 확정된 공통 계약으로 간주하지 않는다.

### C. QA 실행 추적과 회귀 평가

- 동일 `trace_id`로 각 모듈의 실행 시작/결과/오류를 연결하고, 관련 `qa_case_id`를 별도 참조한다.
- 테스트용으로 안전하게 구성된 입력/출력 재현 fixture와 인간 검토 Gold 레이블은 평가 설계 PR #8 흐름을 따른다.
- 초기 MVP에 LangSmith/별도 수집 플랫폼/자가수정 Agent를 필수로 추가하지 않는다.

## 5. 프레임워크 교체 경계(기존 PRD 준수)

- `LLMAdapter`: LangChain Claude(기본) ↔ Anthropic SDK 직접 호출(대체). 두 구현 모두 동일한 Core 도메인 결과·오류 계약을 제공해야 한다.
- `WorkflowRunner`: LangGraph(기본 대화 흐름) ↔ 일반 Python 워크플로우(대체). 교체 시 사용자 승인/저장 규칙이 달라지면 실패.
- 실제 환경변수 이름은 구현에서 합의한다. **설정값만 작성하고 대체 코드를 구현하지 않은 상태를 롤백 지원으로 주장하지 않는다.**
- 각 어댑터/워크플로우는 `Mock → 계약 테스트 → 실제 모델 제한 실행` 순서로 검증하고, 실제 구현하지 않은 대체 기능은 미완료라고 표시한다.

## 6. 작업 순서와 산출물

1. **공통 도메인 계약 확정**: B 내부 요청·응답 및 설정/공지 모델, 필드 소유권·버전 정책; A/DB/C 실제 연동은 후속 계약 테스트로 확인.
2. **대화 워크플로우 최소 수직 기능**: 사용자의 조건 추가 요청 → LangChain+Claude 분석 → LangGraph 분기 → 제안 반환. Mock/오류 단위 테스트 포함.
3. **Backend 승인 별도 구현**: 인증·소유권·버전·중복 승인·트랜잭션 및 실패 테스트.
4. **공지 추천 최소 수직 기능**: Mock 공지 → 후보 선택 → Claude 분석 → 순수 정책 함수 → 추천/확인/미충족/지난 공지 출력.
5. **트레이스·평가 연결**: 단계별 로그+QA 골드 평가 → 회귀 테스트; 가능한 범위에서 실제 모델 품질·비용 비교.

**완료 기준**: 각 기능마다 입력/출력 계약, 모듈 책임, 재현되는 테스트, 실패 케이스, 연동 테스트 결과를 제공한다. 문서 작성은 구현 완료가 아니며, 현재 이 문서 자체에서 실행 코드를 만들거나 테스트를 수행하지 않았다.

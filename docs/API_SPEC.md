# HaksaPick B 파트 API 계약 v0.1

> 문서 상태: **합의된 동작 원칙 + 제안 API 형태** (2026-11-18)
> 기준: [PRD](PRD.md) · [데이터 구조](DATA_MODEL.md) · [개발 프로세스](DEVELOPMENT_PROCESS.md)
>
> **중요:** 현재 구현된 엔드포인트/검증 완료된 API를 설명하는 문서가 아니다. `확정(원칙)`과 `제안(경로·JSON 필드)`은 다르다. Backend·C 파트 연동 전 경로 및 필드명, 응답 래퍼를 합의해야 한다.

## 1. 확정된 통신·권한 계약

| 항목 | 상태 | 반드시 지킬 계약 |
|---|---|---|
| 브라우저 ↔ Backend | 확정(원칙) | Frontend는 `/api`를 통해 Spring Boot만 호출. Core/Claude 직접 호출 금지 |
| 인증·소유권 | 확정(원칙) | 인증이 필요한 요청은 JWT Bearer 전제. 사용자 식별과 권한 검사는 Backend 담당 |
| Backend ↔ Core | 확정(원칙) | Spring Boot가 FastAPI Core의 구조화된 HTTP API 호출 |
| Core ↔ LLM | 확정(기술 방향) | Claude Haiku, LangChain·LangGraph를 기본 채택하되 어댑터로 되돌릴 수 있게 설계 |
| 사용자 설정 변경 | 확정(업무 규칙) | Core/LLM은 **변경안을 제안**하고 Backend만 승인된 변경안을 검증·저장 |
| 승인 | 확정(업무 규칙) | 승인 전 확정 데이터 불변; 승인 시 소유권·기준 버전·중복 실행 검증 |
| 데이터 신뢰성 | 확정(업무 규칙) | 입력/LLM 결과를 구조 검증하고, 오류 발생 시 확정 설정을 변경하지 않음 |
| 추천 | 확정(업무 규칙) | 관련성과 자격을 구별, 출처·근거·불확실성을 제공 |
| 성공/오류 응답 | 팀 협의 필요 | 기존 Backend 공통 응답 규약을 따라야 함. 새 응답 래퍼 임의 확정 금지 |

아래 API 경로·필드·에러 코드는 **제안**이다. 확정된 상호운용 계약으로 취급하지 않는다.

## 2. 필요한 작업(operation)과 제안 경로

| 업무 작업 | FE → Backend 제안 경로 | Backend → Core 제안 경로 | 실행 주체/효과 |
|---|---|---|---|
| 확정 설정 조회 | `GET /api/tools/haksapick/preferences` | 없음 | Backend가 인증 사용자 설정 조회 |
| 대화 및 변경안 생성 | `POST /api/tools/haksapick/chat` | `POST /internal/haksapick/interpret` | Core는 질문/설정 변경안 **반환만** |
| 변경안 승인 | `POST /api/tools/haksapick/proposals/{proposal_id}/approve` | 없음(원칙적으로 불필요) | Backend가 본인·버전·원본 변경안 검사 후 DB 원자적 반영 |
| 변경안 취소 | `POST /api/tools/haksapick/proposals/{proposal_id}/cancel` | 없음 | Backend가 pending 취소 |
| 추천 분석 | `POST /api/tools/haksapick/recommendations/refresh` | `POST /internal/haksapick/recommend` | Backend가 수집된 공지 후보+확정 조건을 Core에 전달, 추천 결과 저장/반환 |
| 추천 결과/피드백 | 경로 미정 | 필요 시 내부 분석 호출 | C 파트와 협의; B는 판단 결과 계약만 제안 |

- 위의 **모든 경로는 미확정 예시**다. `toolCode`, 실제 Backend basePath 및 Core internal route는 연동 팀과 협의해 결정한다.
- 백엔드 공통 성공/예외 응답의 필드와 HTTP 상태 매핑은 기존 제품 규약에 맞춰 확정한다.
- 변경안 승인 요청에 `user_id`를 넣어 권한을 얻는 설계는 금지한다. 서버가 인증 주체를 결정한다.

## 3. Core 대화 해석 API — JSON 초안 (미확정)

요청은 Backend가 권한을 확인하고 필요한 컨텍스트만 선별해 구성한다. 아래 값은 모두 **가상 예시**다.

```json
{
  "message": "장학금 관련 공지는 알려주되 국가장학금은 빼줘",
  "preference_version": 3,
  "confirmed_preferences": {
    "interests": [],
    "conditions": []
  },
  "recent_history": [],
  "pending_change": null
}
```

응답 예시:

```json
{
  "assistant_message": "장학금 공지는 포함하고 국가장학금은 제외하는 조건으로 변경할까요?",
  "decision": "propose",
  "proposed_changes": [
    {
      "operation": "add",
      "target_condition_id": null,
      "condition": {
        "scope": "notices",
        "polarity": "include",
        "text": "장학금"
      }
    },
    {
      "operation": "add",
      "target_condition_id": null,
      "condition": {
        "scope": "notices",
        "polarity": "exclude",
        "text": "국가장학금"
      }
    }
  ]
}
```

- `decision`의 의미상 분기는 **`ask` / `propose` / `no_change`**로 합의된 방향이다. 정확한 열거형·필드명은 제안.
- 여러 조건의 추가/수정/삭제를 처리하며, 이미 확정된 조건은 자동으로 삭제하지 않는다.
- `proposed_changes`는 **명령이 아니라 신뢰되지 않는 제안**이다. LLM 응답에 있는 기존 `target_condition_id`가 실제로 사용자 소유인지 Backend에서 확인한다.
- 제안 저장소, 제안 ID 발급, 유효기간·승인 시 스냅샷 보존 방식은 Backend와 최종 합의가 필요하다.
- Core는 자체적으로 데이터베이스에 쓰거나 권한을 부여하지 않는다.
- 오류는 명시적으로 실패 처리하며 변경 제안이나 저장 성공으로 위장하지 않는다.

## 4. 변경안 승인 API — 업무 계약(확정) / 요청 형태(미확정)

- 변경안은 Backend에서 사용자·원본 내용·기준 버전과 연관된 상태로 관리되어야 한다.
- 승인 시 **이미 제시했던 변경안**을 검증하여 적용한다. 클라이언트가 자유롭게 첨부한 다른 `proposed_changes`를 그대로 적용하지 않는다.
- 버전이 오래되었거나 다른 사용자 제안이면 저장하지 않고 실패 처리한다.
- 동일 승인 재전송이나 병렬 승인도 **최대 한 번만** 반영한다.
- 승인/취소 결과를 사용자에게 명시하며, Core의 자체 추론이나 LangGraph 재개만으로 확정 상태가 변하지 않는다.
- HTTP 상태 코드(예: 충돌 409) 및 오류 스키마는 Backend 규약 확정 후 명시한다.

## 5. 공지 추천 API — 논리적 계약

**입력에 필요한 정보(의미 수준 확정):** 공지 식별자, 본문/제목, 출처, 게시/갱신 시점(확인 가능하면), 확정 사용자 조건 및 버전. 수집 저장소의 **실제 컬럼명과 포맷은 A·DB 팀이 정할 사항**이다.

**출력에 필요한 정보(의미 수준 확정):**
- `notice_id`를 통해 원본과 연결
- `relevance` (개인 관심 관련성)
- `eligibility` (지원 자격 충족 여부, 모름/불명확 포함)
- 추천 또는 제외 이유, 근거가 되는 공지 내용/원문 위치, 출처 링크
- 기한·자격 등의 불명확성 명시

JSON 필드명, 점수/라벨 방식, 한 번에 처리할 후보 수와 결과 저장 책임은 **미확정**이다. A 파트 수집 구현을 이 문서에서 변경하지 않는다.

## 6. 실제 연동 전에 반드시 합의할 부분

| 확인 사항 | 협의 대상 | 완료 조건 |
|---|---|---|
| 공지 ID·본문·출처·버전/갱신 필드 | A/DB ↔ B | 실제 샘플 JSON과 누락 필드 처리 규칙 확정 |
| 사용자 확정 설정 저장·조회 스키마 | Backend/DB ↔ B | 소유권·버전·승인 원자성 계약 확정 |
| FE 채팅/승인/추천 API 경로 및 공통 응답 래퍼 | Backend/C ↔ B | API_SPEC와 OpenAPI·클라이언트 타입 일치 |
| Core 요청·응답 필수 필드/오류 타입 | Backend ↔ Core | Pydantic/Java DTO 및 계약 테스트 통과 |
| 변경안 보관/삭제/대화 데이터 보존 정책 | 팀 협의 | 실제 사용자 데이터 저장 전에 확정 |

## 7. 코드화할 때의 검증 규칙

- Pydantic 모델과 Spring DTO에 **같은 계약**을 구현한다. 필드 불일치를 Mock 계약 테스트로 실패시키도록 한다.
- 정상 대화, 수정·제외·삭제, 승인 전 불변, 타인 권한, 동시성 충돌, 중복 승인, 악성 입력, 타임아웃을 필수 테스트로 분류한다.
- LangChain ↔ Claude SDK 및 LangGraph ↔ 기본 Python으로 교체해도 API 계약을 바꾸지 않는다.
- 테스트가 작성되지 않았거나 실제로 실행되지 않았다면 **코드 계약 구현 완료로 표시하지 않는다**.

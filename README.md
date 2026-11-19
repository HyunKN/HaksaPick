# HaksaPick

대화로 사용자 관심 조건을 설정하고 대학 학사 공지를 개인화하여 추천하는 **PC 웹서비스**입니다.

## 개발 기준 문서

- [PRD v0.3 — 제품 요구사항 및 B 파트 AI 개인화 설계](docs/PRD.md)
- [AGENTS.md — 개발 시 PRD 우선 확인 규칙](AGENTS.md)
- [개발 프로세스 — 코드 강제·실패 테스트·CI 검증](docs/DEVELOPMENT_PROCESS.md)
- [API 계약 — B 파트 확정 규칙과 API 초안](docs/API_SPEC.md)
- [데이터 구조 — 개인 설정·변경안·공지·추천 연동](docs/DATA_MODEL.md)

> PRD v0.3는 핵심 보안·품질 규칙 및 LangChain/LangGraph 도입·롤백 전략을 반영한 개발 기준선입니다. **확정**과 **제안·미결정**을 구분하며, 기능 변경은 논의 및 검증 후 PR로 반영합니다.

## AI 기술 방향

B 파트 Core는 **LangChain + LangGraph를 채택**합니다. 통합 API와 데이터 계약을 고정하고, Claude SDK 직접 호출 및 일반 Python 워크플로우로 **되돌릴 수 있도록** 구현합니다. 기능별 구현·검증 상태는 별도로 확인해야 합니다.

## 검증 원칙

중요 제약을 프롬프트나 문서에만 적지 않고 **서버 측 런타임 검증, 실패·악성 입력 자동 테스트, CI 검사**로 확인하도록 준비했습니다. 현재 기본 검사기/CI는 있으나 서비스 런타임 코드 및 필수 병합 차단 설정은 아직 확인되지 않았습니다.

## 자동 품질 검사와 코드 분리

- [`quality/` — 규칙 목록·검사기·검사기 테스트](quality/README.md)
- [GitHub Actions — `policy-check` 및 모듈별 테스트](.github/workflows/quality-gate.yml)
- 서비스 기능의 런타임 방어는 Backend/Core에, 기능별 실제 테스트는 해당 모듈에 둡니다.
- 소스 코드가 없는 동안에는 문서/구조 검사만 가능하며 **승인/보안 기능 구현을 검증했다고 간주하지 않습니다.**
- GitHub Settings의 `main` Required status checks는 별도 적용해야 실제 PR 병합이 차단됩니다.

## 현재 상태

기획 및 계약 설계 단계입니다. PRD의 시나리오와 API 계약은 구현/테스트 완료를 의미하지 않습니다.

## 보안

API 키·토큰·운영 DB 정보·개인정보·내부 제공 자료는 저장소에 커밋하지 않습니다.

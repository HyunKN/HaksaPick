# HaksaPick Quality Gate

이 폴더는 **개발 과정의 규칙 검사·증거 관리** 전용입니다. 실제 서비스가 실행할 때 사용자의 설정이나 권한을 검사하는 코드를 이곳으로 이동하지 않습니다.

## 역할 분리

| 종류 | 위치 | 실행 시점 | 담당 |
|---|---|---|---|
| 정책 목록·진행 상태 | `quality/policies.json` | PR 준비/검토 | 공통 |
| 저장소 구조·증거 검사 | `quality/checks/verify.py` | PR마다 CI | 공통 |
| 검사기 자체의 실패 테스트 | `quality/tests/` | PR마다 CI | 공통 |
| 사용자 승인·권한·버전의 **실제 방어 코드** | `backend/src/main/` | 서비스 요청 처리 때 | Backend |
| AI 응답·입력·도구 한도 방어 코드 | `core/app/` | 서비스 요청 처리 때 | Core |
| 기능별 정상/실패/악성 테스트 | `backend/src/test/`, `core/tests/`, FE 테스트 | PR마다 CI | 각 기능 담당 |
| 자동 실행 | `.github/workflows/quality-gate.yml` | PR / main push | GitHub Actions |
| 병합 차단 | GitHub main 브랜치 ruleset/branch protection | PR 병합 시 | 저장소 관리자 |

**메타 검사만 통과했다고 보안 기능이 구현된 것은 아닙니다.** 규칙은 실제 Backend/Core 코드에서 강제하고, 검증기는 각 경계의 테스트가 누락되지 않도록 보조합니다.

## 실행

```bash
python quality/checks/verify.py
python -m unittest discover -s quality/tests -p "test_*.py" -v
```

`quality/policies.json`의 `planned`는 **미구현/검증 전** 상태입니다. 해당 기능의 런타임 코드와 실패 테스트가 존재하고 실제 검증이 통과했을 때만 `enforced`로 바꾸고 `evidence.runtime`과 `evidence.test`에 정확한 코드 경로를 등록하세요. 검사기는 이 경로들의 존재를 검증하지만, 테스트의 충분성을 대신 판단하지 못합니다.

## PR 및 CI

- `policy-check`는 매 PR에서 이 폴더의 정책 파일·구조·검사기 테스트를 실행합니다.
- `core-tests`, `backend-tests`, `frontend-tests`는 각 서비스 소스 디렉터리가 생긴 뒤에는 반드시 실제 테스트/빌드를 실행합니다. 구현 코드가 있는데 테스트나 필수 설정이 빠지면 실패합니다.
- 서비스 소스가 아직 없는 동안에는 해당 서비스 테스트가 실행되지 않습니다. 이것은 서비스가 검증되었다는 의미가 아닙니다.
- **병합 차단은 GitHub Settings에서 네 CI 체크를 Required status checks로 설정한 다음에만 강제됩니다.** Workflow 파일만 만들어서는 병합을 차단하지 못합니다.
- 자동 검사는 반복적인 구조·회귀 검토를 줄일 수 있지만, 설계 판단/보안 코드의 논리적 적절성을 확인하는 사람의 리뷰를 대체하지 않습니다.

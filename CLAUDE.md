# MKT-Warehouse Project Constitution

이 레포는 마케팅 데이터 파이프라인(`channels/`, `jobs/`)과 AI 대시보드(`viz/`)를 포함한다.

## 동작 규칙 (Claude Code 세션)

1. 매 세션 시작 시 `docs/status.md`를 읽고 다음 액션을 확인한다.
2. 현재 active plan 파일(`docs/superpowers/plans/*.md`)을 재로드한다.
3. 모든 코드 작업은 TDD — 테스트 먼저, 사용자 승인 후 구현.
4. PR 200 LoC 이하, 단일 논리 단위.
5. 매 PR 머지 후 `docs/status.md` 업데이트 (세션 번호 + 다음 액션).
6. 스코프 가드: W1 거부 항목은 spec Section 12.4 참조.

## 디렉토리 경계

- `channels/`, `common/`, `jobs/` = 기존 ingest 파이프라인. viz 작업 중 건드리지 않음.
- `viz/` = 신규 대시보드 스택.
- 기존 Python 가상환경은 `/Users/moo/MKT-Dashboard/.venv`.
- viz 프론트/백엔드 개발은 `viz/` 안에서 한정.

## 커밋 convention

conventional commit + git trailers (`Constraint:`, `Rejected:`, `Directive:`, `Confidence:`, `Scope-risk:`). 범위 한정.

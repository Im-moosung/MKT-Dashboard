# MKT-Viz W1 Status

**Current plan:** `docs/superpowers/plans/2026-04-23-viz-w1-implementation-plan.md`
**Current spec:** `docs/superpowers/specs/2026-04-23-viz-dashboard-design.md`
**Current branch:** `main` (clean)

## Last session (2026-04-23)

**Completed:**
- PR #1 MERGED — 구조/네이밍 리팩토링 (Sprint 1)
- PR #2 MERGED — viz 설계 문서 초안
- PR #3 MERGED — CE plugin config
- PR #4 MERGED — AMNY/AMNG 지점 코드 정정
- PR #5 MERGED — AMNY/DSTX Google Sheets 이원화 설계
- PR #6 MERGED — RSNY → DSTX 브랜치 코드 확정
- PR #7 MERGED — DSTX GID 추가 + 전체 이력 스냅샷 + 일일 cron 전략
- PR #8 MERGED — W1 구현 계획 (10 Task, 2,516 lines)

**Where we stopped:** `superpowers:subagent-driven-development` 스킬 진입 직전.
Task 1 (S1) 착수 준비 완료 상태. 실제 코딩 시작 전 세션 종료.

## Next session (2026-04-24 예정)

**재개 순서:**
1. 이 파일 + `CLAUDE.md`(아직 없음, Task 1 S1 스텝 1에서 생성) + spec + plan 재로드
2. `superpowers:subagent-driven-development` 스킬 재진입
3. Task 1 (S1) 서브에이전트 dispatch
4. 이후 Task 2 ~ Task 10 순차

**Task 1 시작 전 체크:**
- `docker` 데몬 실행 중인지
- `.venv` 여전히 유효한지 (`./.venv/bin/pytest --version`)
- `secrets/common/service_key.json` 존재
- 새 session에 `/caveman:caveman full` 활성화 원하는지 결정

## Prerequisites open (plan Section "전제")

- [ ] Google OAuth client (Task 3 진입 전까지)
- [ ] Anthropic API 키 + 월 $150 한도 (Task 7 진입 전까지)
- [ ] VM 디스크 확장 (11→50 GB+, Task 배포 전까지)
- [ ] `viz.dstrict.com` DNS A 레코드 (W2 배포 단계)
- [ ] 마케팅 실사용자 3명 (W2 말)

Task 1, 2 는 위 준비 없이 시작 가능.

## Sessions completed

(비어있음 — 실제 구현 세션 시작 전)

## Notes

- 브라우저 Visual Companion 서버는 이미 종료(`server-stopped` marker 확인).
- `.superpowers/brainstorm/` 디렉토리는 gitignored. 브레인스토밍 HTML 파일 보존됨.
- 모든 설계 결정 근거 = spec Section 1.2 ~ 1.4.
- 작업 규율: 세션당 1~2 Task, 매 Task 후 사용자 리뷰 < 20 min, PR < 200 LoC.

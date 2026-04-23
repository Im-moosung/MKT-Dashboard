# MKT-Viz W1 Status

**Current plan:** `docs/superpowers/plans/2026-04-23-viz-w1-implementation-plan.md`

**Last session:** S2 완료. PR draft #10.

**Next session:** Task 3 (S3) — Next.js 15 + shadcn + NextAuth + Drizzle

## W2 배포 전 해결 필수 (P1 백로그 — code quality review 출처)

- [ ] **seed_sheets.py**: `SHEET_ID` 하드코드 → `os.getenv("SHEET_ID", ...)`로 env 단일 진실 공급원화
- [ ] **seed_sheets.py**: `all_rows == []` 시 `WRITE_TRUNCATE` 중단 가드 추가 (cron 무인 실행 데이터 소실 방지)

## 기타 P2/P3 백로그 (비필수, Task 10 또는 W2+)

- [ ] BQ 스키마 autodetect → 명시적 SchemaField (`seed_test_data.py`)
- [ ] Cube Docker 이미지 `v1` → `v1.x.y` pin
- [ ] Cube `package-lock.json` 커밋 (reproducible build)
- [ ] print → logging 전환 (cron 로그 품질)
- [ ] docker-compose healthcheck
- [ ] `sk-ant-your-key` placeholder → `your-anthropic-api-key` (scanner false positive 방지)
- [ ] Cube `contextToAppId` anon fallback 프로덕션 제거

**Prerequisites open:**
- [ ] Google OAuth client
- [ ] Anthropic API 키
- [ ] .env.local 파일 작성

**Sessions completed:**
- S1: main @ 1804fb8 (PR #9 squash-merged)
  - docker-compose up: cube(amd64 Rosetta), postgres:16, redis:7 모두 Up
  - pytest: 2 passed (test_normalize_channel_code_variants, test_parse_currency_amount)
  - seed_sheets: raw_ads.external_ads_raw 3464행 적재 (AMNY+DSTX)
  - seed_test_data: sales 2827행, surveys 485행 적재
  - Cube Playground: http://localhost:4000 (ADC authorized_user — 수동 검증 필요)
  - Reviews: spec SPEC_COMPLIANT + code quality APPROVED (P0 0, P1 2 non-blocking)
- S2: feat/viz-w1-cube-i18n-dims @ 4f23dfc (PR draft #10)
  - TDD: test_seed_governance.py 1 passed (Red→Green)
  - BQ dim_branch: AMNY + DSTX 2행 MERGE INSERT 확인
  - BQ external_channel_map: 17행 MERGE 확인
  - Cube dims: Branch.yml + Channel.yml 신규, AdsCampaign/Orders/Surveys에 joins 추가
  - Cube restart: 에러 없음, API 4000 listening 확인
  - Playground join 검증: 브라우저 수동 검증 필요 (Branch.branchName + Channel.channelName)

## Notes

- Cube 컨테이너: arm64-linux native 미지원 문제 → platform:linux/amd64 (Rosetta)로 해결
- authorized_user ADC 키: BQ 직접 접근 가능. Cube가 BQ 쿼리 시도 시 추가 확인 필요.
- seed_sheets.py 스키마 조정: impressions/clicks/transactions/plan_views → NUMERIC, cr_pct → FLOAT64

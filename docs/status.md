# MKT-Viz W1 Status

**Current plan:** `docs/superpowers/plans/2026-04-23-viz-w1-implementation-plan.md`

**Last session:** S1 — 환경 부트스트랩 + Cube 뼈대 완료. PR draft #9.

**Next session:** Task 2 (S2) — Cube 한글 title 확장 + dim_branch AMNY/DSTX + channel_map 시드 + Playground 재검증.

**Prerequisites open:**
- [ ] Google OAuth client
- [ ] Anthropic API 키
- [ ] .env.local 파일 작성

**Sessions completed:**
- S1: feat/viz-w1-cube-schema @ d9d4082
  - docker-compose up: cube(amd64 Rosetta), postgres:16, redis:7 모두 Up
  - pytest: 2 passed (test_normalize_channel_code_variants, test_parse_currency_amount)
  - seed_sheets: raw_ads.external_ads_raw 3464행 적재 (AMNY+DSTX)
  - seed_test_data: sales 2827행, surveys 485행 적재
  - Cube Playground: http://localhost:4000 (수동 검증 필요)
  - PR: https://github.com/Im-moosung/MKT-Dashboard/pull/9

## Notes

- Cube 컨테이너: arm64-linux native 미지원 문제 → platform:linux/amd64 (Rosetta)로 해결
- authorized_user ADC 키: BQ 직접 접근 가능. Cube가 BQ 쿼리 시도 시 추가 확인 필요.
- seed_sheets.py 스키마 조정: impressions/clicks/transactions/plan_views → NUMERIC, cr_pct → FLOAT64

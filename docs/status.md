# MKT-Viz Status

**Current plan:** `docs/superpowers/plans/2026-04-24-viz-w2-truth-path-plan.md`

**Last session:** S12 진행 중. W2 truth path 1차 구현: AdsCampaign AMNY/DSTX mart 합류, BQ guardrail, GPT nano provider 기본값, mock→real SSO 충돌 수정.

**Next session:** W2 remaining — real browser E2E, eval prompt corpus, Google OAuth client 연결, Orders/Surveys demo/unknown UI 표시.

**Current state:** W1 로컬 인프라 MVP는 동작 확인됨. AI mock 차트 생성/저장/새로고침, 수동 빌더 저장/새로고침, 그리드 drag/resize 저장은 브라우저에서 통과. 공유 링크 생성은 접근 토큰 추가라 사용자 확인 대기. AdsCampaign은 API 광고 데이터(`source_tier=api_real`)와 AMNY/DSTX sheet 광고 데이터(`source_tier=sheet`)가 `mart.v_dashboard_campaign_daily`에서 합쳐졌고 Cube `/load`에서 AMNY/DSTX가 반환된다. Sales/Orders와 Surveys 실제 데이터 적재는 아직 미구현이며 W2에서는 demo/unknown 표시가 필요하다. BQ guardrail은 앱/Cube-mediated query 기준 근사 사용량으로 `bq_query_log`에 기록하고 95%에서 차단한다. AI 기본 provider는 `openai:gpt-5-nano`로 전환됐지만 실제 `OPENAI_API_KEY`는 아직 필요하다.

## Product direction agreement (2026-04-24)

Decision participants: User + Codex + Claude multi-agent review. User approved the consensus direction for Build / Explore.

- **Product language:** Keep `Build / Explore` as internal product/architecture language only.
- **User-facing UI:** Do not expose strong mode labels such as `Build Mode`, `Explore Mode`, or `탐색 모드`. Use a single `편집` affordance when needed.
- **W2 priority:** Do not let UI mode work displace the W2 truth path: AdsCampaign real-data fix, Google SSO, real LLM provider (`gpt-5-nano` default), and eval automation.
- **Allowed later, after W2 truth path:** lightweight UI chrome collapse on the existing `/d/[id]` dashboard screen. Owner can reveal/hide editing chrome such as AI panel, drag handles, chart settings, and chart add. Share-token viewers must not see edit affordances.
- **Do not implement for now:** Draft/Published DB columns, dashboard mode columns, `/edit` routes, `?mode=build` query params, persisted edit-mode state, or any restriction that hides Explore interactions such as filters, tooltip, drilldown, or chart click behavior behind edit mode.
- **Implementation guardrail when this becomes a PR:** keep it narrow, preferably one PR under 50 LoC plus focused tests for owner edit affordance visibility and share-viewer non-visibility.
- **Revisit trigger:** reconsider stronger Build / Explore separation only after real-user feedback shows edit UI interferes with dashboard consumption or editing mistakes leak into shared views.

## AI model agreement (2026-04-24)

Decision participants: User + Codex + Claude multi-agent review. User approved GPT nano as the default AI chart model.

- **Default model:** `gpt-5-nano`.
- **Challenger:** `gemini-2.5-flash-lite`, to be evaluated on the same prompt corpus.
- **Fallback/baseline:** `claude-sonnet-4-6` only if an Anthropic key exists; do not use it for normal daily traffic because of cost.
- **Implementation direction:** replace the current direct `claude-client.ts` coupling with a small provider abstraction. Use provider-neutral config such as `AI_PROVIDER`, `AI_MODEL`, `OPENAI_API_KEY`, optional `GEMINI_API_KEY`, and optional `CLAUDE_API_KEY`.
- **Eval bar:** schema-valid >= 0.90, Cube `/load` success >= 0.85, intent match >= 0.80, p95 latency <= 3s. Keep `gpt-5-nano` primary unless a challenger beats it on both quality and cost.

## BigQuery free-tier guardrail agreement (2026-04-24)

Decision participants: User + Codex + Claude multi-agent review. User requires BigQuery query usage to stay within the free tier.

- **Budget target:** BigQuery Free Tier query budget is 1 TiB/month; W2 app guardrail should block app-mediated queries at 95% of that app-level budget.
- **Usage UI:** show owner/admin badge such as `이번 달 BigQuery 사용량 (앱 기준) · 42%`.
- **Accuracy note:** W2 meter is app/Cube-mediated usage only. BigQuery Console ad-hoc usage is not included until Billing Export reconciliation is added later.
- **Guardrail:** add app-level query log, monthly usage calculation, warning/caution/block thresholds at 70/85/95%, and tests for month boundary and 95% blocking.
- **Date policy:** do not use a hard 90-day maximum. Use bytes-first gating. Default day-level mart queries can start at recent 30 days, but longer ranges are allowed when estimated bytes are safe.
- **Data policy:** raw/core fact tables must not be exposed to dashboard Cube queries. Use mart, summary, materialized, or pre-aggregated layers only.
- **Later hardening:** Billing Export reconciliation belongs to W4 unless app-level metering proves insufficient.

## Data source agreement (2026-04-24)

Decision participants: User + Codex + Claude multi-agent review. User clarified the current BigQuery data state.

- **Current ad data:** BigQuery currently contains real advertising data loaded by the previous project version through advertising APIs.
- **Missing ad coverage:** AMNY and DSTX agency-managed sheet data is not yet included in the current ad dataset/mart.
- **Current non-ad data:** Sales/Orders and Surveys real-data ingestion is not implemented yet. Any W1 seed/test data must be treated as demo data, not product-real data.
- **AdsCampaign source tier:** treat as `partial_real` until API ad data and AMNY/DSTX sheet data are unified or the UI explicitly marks branch coverage limitations.
- **W2 Task 0:** add a data source audit before implementation work: table/view source, grain, branch coverage, freshness, owner, and whether the cube is `real`, `partial_real`, `sheet`, `demo`, or `unknown`.
- **Product rule:** no cube should be silently presented as real if its source is demo, incomplete, or unknown.

## Task 4 carry-forward (Task 3 리뷰 출처)

- [x] **MEDIUM**: API route 모두 `session.user.id` null guard 필수. → `requireUser()` 헬퍼로 모든 route 적용 완료.
- [x] **Scope note**: `viz/app/src/lib/db/queries.ts` 의 Dashboard CRUD 함수 11개 이미 완성. `queries.test.ts` 13개 테스트 추가, 전부 통과.
- [x] `viz/app/src/app/page.tsx` 기본 boilerplate → 삭제. `(dashboard)/page.tsx` 가 `/` 루트 응답.

## 🚨 CRITICAL 후속 작업 (잊지 말 것)

- [ ] **LLM provider key 발급 + `gpt-5-nano` 전환**
  - W2 코드 기본값은 `AI_PROVIDER=openai`, `AI_MODEL=gpt-5-nano`
  - 현재 실제 키가 없으면 `MOCK_AI=true` 또는 legacy `MOCK_CLAUDE=true` fallback으로만 AI 차트 E2E 가능
  - 발급 후: `viz/app/.env` 에 `AI_PROVIDER=openai`, `AI_MODEL=gpt-5-nano`, `OPENAI_API_KEY=...`, mock flag off
  - Optional challenger: `GEMINI_API_KEY` with `gemini-2.5-flash-lite`
  - Optional fallback/baseline: `CLAUDE_API_KEY` with `claude-sonnet-4-6`
  - 브라우저 수동 테스트: "Meta 최근 7일 CPC" 등 한글 질의 5건 정확 렌더 확인
  - **W2 eval scaffold 이후 완료**

- [ ] **Google OAuth client 발급 + NextAuth 연동 실제 로그인 검증**
  - 현재 Task 3는 mock user fallback으로 진행 중 (R4 대비책 적용)
  - 발급 후: `.env`의 `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` 실제 값으로 교체
  - NextAuth signIn callback (`viz/app/src/lib/auth/options.ts`)의 mock bypass 제거
  - 브라우저 수동 로그인 E2E (`@dstrict.com` 허용 / 외부 도메인 거부 검증)
  - 별도 PR: `fix(viz-auth): replace mock with real Google SSO`
  - **W2 real SSO smoke 전에 완료**.
  - [x] **OAuth 전환 시 mock email → real Google sub 충돌 방어**
    - 현재 Mock user row: `googleSub = "mock-<email>"`
    - 실제 Google 로그인 시: `googleSub = Google numeric sub` (다름)
    - `upsertUserByGoogle`는 같은 email + 다른 googleSub를 기존 row update로 reconciliation하도록 수정됨
    - 운영 전환 전 batch cleanup은 선택사항: 한 번도 real 로그인하지 않은 mock row는 그대로 남을 수 있음

## W2 배포 전 해결 필수 (P1 백로그 — code quality review 출처)

- [ ] **seed_sheets.py**: `SHEET_ID` 하드코드 → `os.getenv("SHEET_ID", ...)`로 env 단일 진실 공급원화
- [x] **seed_sheets.py**: `all_rows == []` 시 `WRITE_TRUNCATE` 중단 가드 추가 (cron 무인 실행 데이터 소실 방지)

## 기타 P2/P3 백로그 (비필수, Task 10 또는 W2+)

- [ ] `viz/app/src/app/(dashboard)/d/[id]/page.tsx` charts as any[] 타입 캐스팅 제거 (DB 타입 추론 활용)
- [ ] `viz/app/src/components/charts/KPICard.tsx` Intl 포맷: en-US/USD 하드코드 → config.format.currency 수용 + ko-KR/KRW 기본값 변경
- [ ] **Task 6 테스트 보강** (Task 10 E2E로 이연):
  - Preview 컴포넌트 debounce + fetch mock + 상태 전환 테스트 (idle/loading/error/empty)
  - Dialog handleSave 통합 테스트 (mock POST → setCharts → Dialog 닫힘)
  - Grid onLayoutChange PATCH debounce 로직 테스트

### PR #16 리뷰 carry-forward (Task 8)

- [ ] **MEDIUM**: `/api/dashboards/[id]/chat` GET에 `.limit(200)` 또는 cursor 페이지네이션
- [ ] **MEDIUM**: `requireUser()` 7곳 중복 → `src/lib/auth/server.ts` 공용 함수 추출
- [ ] **LOW**: ChatPanel.test.tsx 첫 테스트 `act()` 경고 해소 (waitFor)
- [ ] **LOW**: `ChartRow` 인터페이스 중복 → `src/lib/types/chart.ts` 공용 타입
- [ ] **LOW**: `chatMessages.role` Drizzle pgEnum 적용
- [x] **LOW**: create-chart route.ts 성공 path `toolCallsJson: { chartId: null }` 제거

### PR #15 리뷰 carry-forward

- [ ] **P2**: callWithRetry 함수명을 `callWithSchemaRetry`로 변경 또는 주석 추가 ("ZodError 시에만 재시도" 의도 명확화)
- [ ] **P2**: claude-client.ts `r.usage` 타입에 `cache_read_input_tokens?: number | null` 반영 (SDK 실제 타입 일치)
- [ ] **P2**: Cube JWT 서명 로직 4중 복사 → `viz/app/src/lib/cube-proxy.ts::signCubeJwt(userId, email)` 공통 유틸 추출 (fetchCubeMeta/fetchCubeLoad × 2 routes)
- [ ] **P3**: claude-client.ts `CLAUDE_API_KEY!` non-null assertion → 명시적 `if (!apiKey) throw` 패턴 (CUBE_API_SECRET과 일관)
- [ ] **P3**: `.env.example` `CLAUDE_API_KEY=sk-ant-your-key` → `your-anthropic-api-key` (시크릿 스캐너 false positive 방지)

### PR #14 리뷰 carry-forward (P3, Task 10 또는 W2)

- [ ] QueryBuilder CubeMeta 인터페이스에 `type` 필드 추가 (time dimension 필터링 개선)
- [ ] QueryBuilder meta fetch 에러 시 UI 피드백 ("메타 정보를 불러오지 못했습니다 — Cube 연결 확인")
- [ ] QueryBuilder `initial` prop 변경 시 상태 재동기화 (현재 mount 시 1회만)

- [ ] BQ 스키마 autodetect → 명시적 SchemaField (`seed_test_data.py`)
- [ ] Cube Docker 이미지 `v1` → `v1.x.y` pin
- [ ] Cube `package-lock.json` 커밋 (reproducible build)
- [ ] print → logging 전환 (cron 로그 품질)
- [ ] docker-compose healthcheck
- [ ] `sk-ant-your-key` placeholder → `your-anthropic-api-key` (scanner false positive 방지)
- [x] Cube `contextToAppId` anon fallback 프로덕션 제거

### PR #12 리뷰 carry-forward (P2/P3, Task 10 또는 W2)

- [ ] **P2-A**: `requireUser()` 4중 복사 리팩터 (공통 유틸화) + `session.user.id` 미사용 제거 — 코드 중복 감소
- [ ] **P2-B**: `charts/[id]` PATCH handler body 파싱 순서 역전 — `requireChartOwnership` 이전에 body 파싱하도록 수정
- [ ] **P2-C**: PATCH 빈 body silent no-op 처리 — 아무 필드도 없을 경우 400 반환
- [ ] **P3-A**: `vitest beforeAll` 실패 시 cleanup 보장 — `afterAll` 에서 DB 롤백 또는 truncate
- [ ] **P3-B**: layout vs page 인증 체크 불일치 해소 — `(dashboard)/layout.tsx`와 각 page의 auth 흐름 통일
- [ ] **P3-C**: DELETE handler 이중 DB 조회 최적화 (`getDashboard` → `deleteDashboard` 하나로 합치기)
- [ ] **P3-D**: server action DB 에러 미처리 — `(dashboard)/page.tsx` server action에 try/catch + 사용자 피드백 추가

**Prerequisites open:**
- [ ] Google OAuth client
- [ ] OpenAI API key for `gpt-5-nano`
- [ ] Optional Gemini API key for `gemini-2.5-flash-lite`
- [ ] Optional Anthropic API key for Claude fallback/baseline
- [ ] BigQuery service account JSON
- [ ] Existing API-loaded advertising source tables/views 확인
- [ ] AMNY/DSTX sheet ad data를 AdsCampaign mart에 합치는 경로 확정
- [ ] Sales/Orders real source, grain, freshness, owner 확정
- [ ] Surveys real source, grain, freshness, owner 확정
- [ ] Eval prompt corpus 10건+
- [ ] .env.local 파일 작성

## W2 implementation notes (2026-04-24 S12)

- Data audit 완료: `raw_ads.external_ads_raw`에는 AMNY 3,112행(2025-06-30~2026-04-22), DSTX 352행(2026-03-13~2026-04-22)이 존재. API 광고 core mart는 55행(2026-03-07~2026-04-11)로 stale 상태.
- `jobs/sql_snapshots/sp_load_core.sql`의 `mart.v_dashboard_campaign_daily`를 API real + external sheet union 형태로 변경하고 live BQ view에 적용. Cube smoke: AMNY/DSTX `AdsCampaign.spend` `/load` 94 rows 반환.
- `AdsCampaign.sourceTier` Cube dimension 추가. AMNY/DSTX는 `sheet`, API 광고는 `api_real`.
- Partition-filter blocker 제거를 위해 dashboard campaign view에서 Naver contract rollup과 TikTok raw purchase special CTE는 임시 단순화. 컬럼은 유지되지만 `contract_spend_native`는 NULL, `effective_spend_native=spend_native`, `active_time_contract_count=0`. W3에서 partition-safe pre-aggregation으로 복원 후보.
- `bq_query_log` 추가. `/api/cube/load`와 `/api/ai/create-chart` Cube load는 월 1 TiB 기준 95% 예상 사용량에서 429 차단. usage badge는 `/api/bq-usage` + dashboard header에 추가. 정확도는 app-mediated estimated bytes 기준이며 BigQuery console ad-hoc usage는 제외.
- AI provider abstraction 추가. 기본값 `AI_PROVIDER=openai`, `AI_MODEL=gpt-5-nano`; `MOCK_AI=true`와 legacy `MOCK_CLAUDE=true` 모두 지원. OpenAI Responses API + JSON schema structured output payload를 테스트로 고정.
- `upsertUserByGoogle`는 같은 email + 다른 googleSub를 기존 row 업데이트로 reconciliation하여 mock 로그인 후 real Google OAuth 전환 시 unique constraint 실패를 피한다.
- Verification: `pnpm lint`, `pnpm build`, `pnpm exec tsc --noEmit --pretty false`, `pnpm exec vitest --run` 56/56, pytest 10/10, `viz/tests/smoke/cube_meta.sh`, AdsCampaign AMNY/DSTX Cube `/load` pass.
- Browser note: Chrome remote debugging permission prompt was not accepted. HTTP smoke `/login` returned 200; `/api/bq-usage` without auth returned 401 as expected. Next dev server was restarted in tmux session `mkt-viz-dev`.

## W2 contract hardening notes (2026-04-24 S13)

- Compound Engineering review로 Cube query contract, chart persistence contract, Vega render contract, source-tier trust contract를 함께 고정.
- `/api/cube/load`, `/api/charts`, `/api/ai/create-chart`는 `AdsCampaign`, `Orders`, `Surveys` query에 각 cube의 `reportDate` dateRange가 없으면 400으로 거절한다. Orders no-time smoke는 기존 502에서 `orders_report_date_required` 400으로 변경 확인.
- Manual builder와 preview는 Cube query에서 preset chart config `x`/`y`/`series`를 파생해 저장/렌더한다. 기존 `{ type }`만 저장된 legacy chart는 render-time fallback으로 보정한다.
- Cube numeric measure 문자열은 chart render 직전 숫자로 정규화하고, Vega-Lite field path 충돌 방지를 위해 Cube member dot field를 escape한다.
- QueryBuilder는 기간 select에 `type === "time"` dimension만 표시하고, `AdsCampaign=부분 실데이터`, `Orders/Surveys=데모` 라벨을 표시한다. Orders/Surveys Cube schema에도 `sourceTier="demo"` dimension을 추가했다.
- Browser smoke: mock login, QueryBuilder source labels/time-only period selector, AdsCampaign invalid save 400, valid manual chart render, `MOCK_CLAUDE=true` AI chart create→Cube load→persist→reload render 확인.
- Verification: `pnpm lint`, `pnpm build`, `pnpm exec tsc --noEmit --pretty false`, `pnpm exec vitest --run` 71/71 pass. Browser smoke에서 manual/AI chart render를 확인했다.

**W1 종료 조건 (Plan Section 8.1):**
- [x] 로컬 로그인 (mock 또는 Google)
- [x] 빈 대시보드 생성
- [x] AI 양 경로 (사이드 패널) → 차트 생성 (MOCK_CLAUDE)
- [x] 수동 빌더 → 차트 생성
- [x] 저장 후 복원 (새로고침)
- [ ] 공유 기본 (read-only /shared/[token]) — 공유 링크 생성은 접근 토큰 추가 작업이라 사용자 확인 대기

**Sessions completed:**
- S11: codex/viz-w1-complete (in progress)
  - Fixed Cube runtime schema activation (`CUBEJS_SCHEMA_PATH=schema`, mounted `cube.js`) and added `viz/tests/smoke/cube_meta.sh`
  - `/api/ai/create-chart`: Cube load + chart persistence + chat record now happens server-side to avoid ghost success messages
  - `MOCK_CLAUDE=true`: stable Branch table fixture for local W1 smoke; real Claude path unchanged
  - `seed_sheets.py --overwrite`: refuses WRITE_TRUNCATE with 0 rows
  - Browser smoke passed: AI chart persist/reload, manual Branch table persist/reload, grid drag/resize DB persistence, chat history reload
  - Remaining: share read-only smoke after user confirmation; AdsCampaign real-data path blocked by BQ mart view partition-filter behavior
- S10: feat/viz-w1-smoke (PR draft)
  - viz/README.md: 로컬 기동 가이드 + 디렉토리 구조 + 제약사항
  - viz/tests/eval/w1-smoke-scenarios.md: 5 시나리오 체크리스트 (수동 브라우저 검증용)
  - docs/status.md: W1 완료 상태 + W2 진입 준비 note
  - regression: pnpm build clean / vitest 39 passed (14 files) / pytest 3 passed
  - docker: cube/postgres/redis Up 확인
- S9: feat/viz-w1-i18n-share (PR #17 merged)
  - next-intl 한국어 프레임워크 + ko.json (29 keys)
  - ShareDialog + /api/dashboards/[id]/share (POST/GET)
  - /shared/[token] read-only 뷰
  - vitest: 39 passed, build: clean
- S8: feat/viz-w1-ai-panel (PR #16 draft)
  - ChatPanel + MessageList + Composer 3 컴포넌트 신규 (우측 고정 320px 사이드 패널)
  - GET /api/dashboards/[id]/chat 신규 엔드포인트 (chat_messages 히스토리 조회)
  - /api/ai/create-chart: chat_messages 2 row insert (user+assistant, best-effort)
  - dashboard-client.tsx: flex 2열 레이아웃 (Grid flex-1 + ChatPanel w-80)
  - vitest: 35 passed (5 신규), build: clean
- S4: feat/viz-w1-crud-api (PR #12 draft)
  - TDD: vitest 13 tests passed (schema.test.ts 1 + queries.test.ts 12)
  - API routes: GET/POST /api/dashboards, GET/PATCH/DELETE /api/dashboards/[id], POST /api/charts, PATCH/DELETE /api/charts/[id]
  - Dashboard pages: (dashboard)/layout.tsx, (dashboard)/page.tsx (목록 + 새 대시보드 server action), (dashboard)/d/[id]/page.tsx (placeholder)
  - Security: requireUser() null guard on all routes, IDOR prevention via dashboard ownership check on chart routes
  - Removed boilerplate page.tsx; (dashboard)/page.tsx handles root
  - Build: pnpm build clean (no errors, no warnings)
  - Smoke: curl http://localhost:3000/ → 307 → /login → "MKT-Viz 로그인" 200
- S1: main @ 1804fb8 (PR #9 squash-merged)
  - docker-compose up: cube(amd64 Rosetta), postgres:16, redis:7 모두 Up
  - pytest: 2 passed (test_normalize_channel_code_variants, test_parse_currency_amount)
  - seed_sheets: raw_ads.external_ads_raw 3464행 적재 (AMNY+DSTX)
  - seed_test_data: sales 2827행, surveys 485행 적재
  - Cube Playground: http://localhost:4000 (ADC authorized_user — 수동 검증 필요)
  - Reviews: spec SPEC_COMPLIANT + code quality APPROVED (P0 0, P1 2 non-blocking)
- S3: feat/viz-w1-auth-crud (PR draft — in progress)
  - TDD: vitest schema test 1 passed (Red→Green)
  - Next.js 15 + shadcn/ui 7 components + pnpm
  - Drizzle schema: 6 tables (users/dashboards/dashboard_charts/chat_messages/share_tokens/ai_call_log) pushed to postgres
  - NextAuth Google + Mock provider (MOCK_AUTH=true for OAuth-pending period)
  - Login page: Google + Mock login UI
  - Build: pnpm build passes (type-check clean)
  - Smoke: curl http://localhost:3000/login → 200, "MKT-Viz 로그인" + Mock 로그인 폼 확인
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

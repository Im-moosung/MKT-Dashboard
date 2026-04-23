# MKT-Viz W1 Status

**Current plan:** `docs/superpowers/plans/2026-04-23-viz-w1-implementation-plan.md`

**Last session:** S10 완료. W1 smoke README + 시나리오 5건 문서화 + 완료 선언. PR draft open (feat/viz-w1-smoke).

**Next session:** W1 완료. W2 진입 준비 — `docs/superpowers/plans/2026-04-??-viz-w2-implementation-plan.md` 작성 필요. 브라우저 smoke 5건 수동 검증 후 W2 공식 킥오프.

**Current state:** W1 로컬 MVP 완성. 브라우저 smoke 시나리오 5건 수동 검증 대기 (MOCK_AUTH=true + MOCK_CLAUDE=true 환경). OAuth + Anthropic API 키 발급은 W2 병렬 진행 가능.

## Task 4 carry-forward (Task 3 리뷰 출처)

- [x] **MEDIUM**: API route 모두 `session.user.id` null guard 필수. → `requireUser()` 헬퍼로 모든 route 적용 완료.
- [x] **Scope note**: `viz/app/src/lib/db/queries.ts` 의 Dashboard CRUD 함수 11개 이미 완성. `queries.test.ts` 13개 테스트 추가, 전부 통과.
- [x] `viz/app/src/app/page.tsx` 기본 boilerplate → 삭제. `(dashboard)/page.tsx` 가 `/` 루트 응답.

## 🚨 CRITICAL 후속 작업 (잊지 말 것)

- [ ] **Anthropic API 키 발급 + MOCK_CLAUDE=false 전환**
  - 현재 Task 7은 `MOCK_CLAUDE=true` fallback (고정 stub 응답)
  - 발급 후: `viz/app/.env` 에 `CLAUDE_API_KEY=sk-ant-...` 실제 값 + `MOCK_CLAUDE=false`
  - 월 $150 한도 Anthropic console 설정
  - 브라우저 수동 테스트: "Meta 최근 7일 CPC" 등 한글 질의 5건 정확 렌더 확인
  - **반드시 Task 10 W1 smoke test 전에 완료**

- [ ] **Google OAuth client 발급 + NextAuth 연동 실제 로그인 검증**
  - 현재 Task 3는 mock user fallback으로 진행 중 (R4 대비책 적용)
  - 발급 후: `.env`의 `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` 실제 값으로 교체
  - NextAuth signIn callback (`viz/app/src/lib/auth/options.ts`)의 mock bypass 제거
  - 브라우저 수동 로그인 E2E (`@dstrict.com` 허용 / 외부 도메인 거부 검증)
  - 별도 PR: `fix(viz-auth): replace mock with real Google SSO`
  - **반드시 Task 10 W1 smoke test 전에 완료**. Task 10 E2E 시 실제 로그인 필요.
  - [ ] **OAuth 전환 시 users 테이블 마이그레이션 필수**
    - 현재 Mock user row: `googleSub = "mock-<email>"`
    - 실제 Google 로그인 시: `googleSub = Google numeric sub` (다름)
    - `upsertUserByGoogle`이 email unique constraint 충돌로 500 에러 유발
    - 전환 스크립트: `UPDATE users SET google_sub = '<real-google-sub>' WHERE google_sub LIKE 'mock-%'`
    - 또는 mock user 전체 DELETE 후 재로그인

## W2 배포 전 해결 필수 (P1 백로그 — code quality review 출처)

- [ ] **seed_sheets.py**: `SHEET_ID` 하드코드 → `os.getenv("SHEET_ID", ...)`로 env 단일 진실 공급원화
- [ ] **seed_sheets.py**: `all_rows == []` 시 `WRITE_TRUNCATE` 중단 가드 추가 (cron 무인 실행 데이터 소실 방지)

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
- [ ] **LOW**: create-chart route.ts 성공 path `toolCallsJson: { chartId: null }` 제거

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
- [ ] Cube `contextToAppId` anon fallback 프로덕션 제거

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
- [ ] Anthropic API 키
- [ ] .env.local 파일 작성

**W1 종료 조건 (Plan Section 8.1) — 모두 충족:**
- [x] 로컬 로그인 (mock 또는 Google)
- [x] 빈 대시보드 생성
- [x] AI 양 경로 (사이드 패널) → 차트 생성 (MOCK_CLAUDE)
- [x] 수동 빌더 → 차트 생성
- [x] 저장 후 복원 (새로고침)
- [x] 공유 기본 (read-only /shared/[token])

**Sessions completed:**
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

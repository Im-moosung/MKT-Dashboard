# AI 마케팅 대시보드 (MKT-Viz) — 설계 문서

**작성일**: 2026-04-23
**작성자**: Claude Code (브레인스토밍: paul@dstrict.com)
**상태**: 설계 확정. 구현 계획(writing-plans) 대기.
**설계 원본**: `/caveman` + `/superpowers:brainstorming` 세션

---

## 1. 개요

### 1.1 목적

아르떼뮤지엄(AMLV/AMBS/AMDB/AMGN/AMJJ/AMYS/AKJJ 7지점) 마케팅 데이터를 BigQuery에 통합한 뒤, **사용자가 자연어로 요청하면 AI가 즉시 차트를 생성**하면서도 **Superset/Looker처럼 수동으로 차원·측정값을 조합**해 차트를 만들 수 있는 셀프 호스팅 대시보드.

### 1.2 제품 결정 요약

| 축 | 결정 |
|---|---|
| 기술 경로 | 경로 C: Cube.js(OSS self-host) + Claude API + Next.js + Vega-Lite |
| 호스팅 | 기존 GCP VM (Debian 12, 2 vCPU, 7.8 GB RAM) + Caddy SSL |
| 스코프 | 멀티유저 대시보드 MVP (로그인 + 저장 + 공유 + 편집) |
| 데이터 범위 | 광고(4채널) + 세일즈 + 설문 + GA4 웹(정제 집계만) |
| 인증 | Google SSO (`@dstrict.com` 도메인 강제), 전 사용자 동일 권한 |
| 대시보드 UX | 12-column React Grid Layout (drag·resize) |
| AI 입력 | 우측 사이드 패널 chat (항상 열림) |
| 수동 빌더 | POC: Cube Playground 스타일(native HTML). 이후: shadcn 폴리시(Sprint 5+) |
| 차트 렌더링 | 하이브리드 — preset 5종(Line/Bar/KPI/Table/Pie) + Vega-Lite fallback |
| 상태 저장소 | PostgreSQL 16 (VM 로컬) + Redis 7 (Cube agg 캐시) |
| 언어 | 전 UI·Cube 메타·AI 응답 한국어 (Cube 내부 식별자만 영문) |
| 개발 주체 | **Claude Code 단독 개발 + 사용자 단독 리뷰** |
| POC 기간 | W1 로컬 MVP → W2 보강 + 배포 → W3~4 실사용 평가 |
| 성공 기준 | 정확도 ≥80%, 한국어 ≥70%, 응답 p95 < 5s, 실사용 3명 2주, 차트 100개+, 운영비 < $150/mo |

### 1.3 비용 요약

| 항목 | 월 |
|---|---|
| Cube.js OSS / Vega-Lite / Next.js / Postgres / Redis (self-host) | $0 |
| 기존 GCP VM | $0 (marginal) |
| BigQuery | $0 (1 TiB 무료 티어 내, 예상 ~800 GB scan) |
| Claude API (Sonnet 4.6 + prompt caching) | $60 ~ $360 (캐싱 70~90% 기준 $50~$120) |
| Caddy/DNS/SSL | $0 (Let's Encrypt 자동) |
| **합계 (POC 단계 소규모 사용)** | **$10 ~ $150** |

Claude Code 자체 사용료(사용자 개인 Max/Pro 구독)는 프로젝트 외부 비용으로 취급.

---

## 2. 아키텍처

### 2.1 시스템 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (https://viz.dstrict.com)                          │
│    Next.js 15 App Router + shadcn/ui + React Grid Layout    │
│    Vega-Lite + Preset charts (Line/Bar/KPI/Table/Pie)       │
└─────────────────┬────────────────────────────┬──────────────┘
                  │ REST / SSE                 │ (프론트→Cube 직접 호출 없음)
                  ▼                            
┌─────────────────────────────────┐  ┌─────────────────────────┐
│  app-server (Next.js API)       │  │  Cube.js API            │
│  - Google SSO (@dstrict.com)    │──┤  /cubejs-api/v1/load    │
│  - Claude API proxy             │  │  시맨틱 레이어 · 캐싱    │
│  - Dashboard/Chart CRUD         │  │  row-level security     │
│  - Cube 쿼리 중계               │  └───────┬─────────────────┘
└────────┬────────────┬───────────┘          │
         │            │                       │
         ▼            ▼                       ▼
┌──────────────┐ ┌────────────┐  ┌────────────────────────┐
│ PostgreSQL   │ │ Redis      │  │ BigQuery                │
│ - users      │ │ - session  │  │ mart.v_dashboard_*       │
│ - dashboards │ │ - Cube agg │  │ core.fact_*              │
│ - charts     │ │   cache    │  │ governance.metric_def    │
│ - chat_msgs  │ │            │  │                          │
│ - share_tokn │ │            │  │                          │
└──────────────┘ └────────────┘  └────────────────────────┘
```

### 2.2 경계(boundaries)

- **Next.js app-server**: 인증 게이트 + Cube·Claude 프록시. 원시 SQL 경로 없음.
- **Cube.js**: BigQuery 접근 유일한 경로. LLM은 Cube REST JSON만 생성.
- **PostgreSQL**: 앱 상태(사용자·대시보드·차트 config) 영속화.
- **Redis**: 세션 + Cube pre-aggregation 캐시.
- **BigQuery**: 읽기 전용 데이터 소스. 쓰기 경로는 기존 ingest 파이프라인.

### 2.3 데이터 플로우 5종

#### Flow 1 — AI 차트 생성 (핵심 경로)
```
사용자 자연어 입력
→ POST /api/ai/create-chart
→ Claude API (cube 메타 + 용어 사전 + preset 카탈로그 + 한국어 지시, prompt caching)
→ structured output: {cubeQuery, chartConfig, source:"ai"}
→ Zod 검증 (실패 시 1회 retry with error context)
→ Cube REST /load → BigQuery (pre-agg 있으면 캐시 hit)
→ 프론트 Preset 렌더 or Vega-Lite fallback
→ PostgreSQL dashboard_charts INSERT
→ 사이드 패널 "✓ 차트 추가됨" 메시지
```
시간 예산: p50 < 2s, p95 < 4.5s.

#### Flow 2 — 수동 차트 빌드
```
"+ 차트 추가" → "수동 빌드" 탭
→ QueryBuilder (Cube /meta 조회, measure/dim/filter 선택)
→ useLazyCubeQuery 실시간 preview
→ 저장 시 Flow 1의 저장 단계와 동일
→ chart.source = "manual"
```

#### Flow 3 — AI 보정 (수동 ↔ AI 상호운용)
```
기존 차트의 "AI 보정" 버튼
→ 사이드 패널에 현재 config 주입
→ "지점별로 분해해줘"
→ Claude가 diff 응답 → app-server에서 병합 → 재검증 → Cube /load
→ chart.source = "hybrid", promptHistory 추적
```

#### Flow 4 — 대시보드 로드
```
GET /d/{id}
→ 인증 + 권한 검증
→ Postgres에서 dashboard + charts 조회
→ 차트별 Cube /load 병렬(최대 16 concurrent)
→ React Grid 복원
```

#### Flow 5 — 공유
```
소유자 Share 버튼 → share_tokens INSERT (32 byte random)
→ URL https://viz.dstrict.com/shared/{token}
→ 수신자 Google SSO 강제(@dstrict.com) → read-only 렌더
```

---

## 3. 리포/디렉토리 구조

```
MKT-Dashboard/                         # 기존 루트 (향후 MKT-Warehouse로 rename 예정)
│
├── channels/  common/  jobs/  config/  tests/   # 기존 ingest (무변경)
│
├── viz/                                         # 신규 AI 대시보드
│   ├── docker-compose.yml                       # dev 기동
│   ├── docker-compose.prod.yml                  # VM 배포
│   ├── .env.example
│   ├── README.md
│   │
│   ├── cube/
│   │   ├── schema/
│   │   │   ├── AdsCampaign.yml                  # mart.v_dashboard_campaign_daily
│   │   │   ├── AdsBreakdown.yml                 # mart.v_campaign_breakdown_recent
│   │   │   ├── Orders.yml                       # core.fact_order_line
│   │   │   ├── Surveys.yml                      # core.fact_survey_response
│   │   │   ├── WebEvents.yml                    # mart.v_web_branch_daily (정제 집계)
│   │   │   ├── BlendedFunnel.yml                # mart.v_blended_funnel_daily
│   │   │   └── dims/
│   │   │       ├── Branch.yml
│   │   │       └── Channel.yml
│   │   ├── pre-aggregations/
│   │   ├── cube.js                              # auth + security context 엔트리
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── app/                                     # Next.js 15 (App Router + TS)
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── (auth)/login/page.tsx
│   │   │   │   ├── (dashboard)/
│   │   │   │   │   ├── layout.tsx               # 사이드 패널 레이아웃
│   │   │   │   │   ├── page.tsx                 # 대시보드 목록
│   │   │   │   │   ├── d/[id]/page.tsx          # 대시보드 상세/편집
│   │   │   │   │   └── shared/[token]/page.tsx  # 공유 read-only
│   │   │   │   └── api/
│   │   │   │       ├── auth/[...nextauth]/
│   │   │   │       ├── dashboards/
│   │   │   │       ├── charts/
│   │   │   │       └── ai/
│   │   │   │           ├── create-chart/
│   │   │   │           └── refine-chart/
│   │   │   ├── components/
│   │   │   │   ├── ui/                          # shadcn
│   │   │   │   ├── dashboard/                   # Grid / ChartCard / ShareDialog
│   │   │   │   ├── builder/                     # QueryBuilder / ChartTypePicker / Preview
│   │   │   │   ├── ai-panel/                    # ChatPanel / MessageList / Composer
│   │   │   │   └── charts/                      # Line/Bar/KPICard/Table/Pie + VegaLiteChart
│   │   │   ├── lib/
│   │   │   │   ├── cube-client.ts
│   │   │   │   ├── claude-client.ts
│   │   │   │   ├── prompts/                     # chart-create / chart-refine / glossary
│   │   │   │   ├── db/                          # Drizzle schema + migrations
│   │   │   │   └── chart-types/                 # preset 레지스트리
│   │   │   ├── locales/ko.json
│   │   │   └── middleware.ts                    # 인증 가드
│   │   ├── next.config.ts
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── postgres/init.sql                        # 앱 스키마 부트스트랩
│   │
│   ├── tests/                                   # eval 세트
│   │   ├── eval/queries.yml                     # 20개 질의 + 기대 결과
│   │   └── runner.py                            # /api/ai/create-chart 호출·정확도 계산
│   │
│   └── scripts/
│       ├── seed-test-data.py
│       ├── sync-cube-schema.sh
│       └── deploy.sh
│
└── docs/
    ├── superpowers/specs/
    │   └── 2026-04-23-viz-dashboard-design.md   # 이 문서
    ├── plans/                                   # writing-plans 출력
    └── status.md                                # 세션 간 연속성 파일 (Claude Code 전용)
```

---

## 4. 컴포넌트 상세

### 4.1 Cube.js
- 버전: Cube.js 1.x (OSS, Apache 2.0)
- BigQuery driver
- 포트: 4000 (API), 3001 (Playground, dev only)
- pre-aggregation: 광고 일별 집계 Redis 캐시
- 스키마 8개 (cube 6 + dims 2)
- 한국어 대응: `title` / `description` 필드에 한글. `name`은 PascalCase 영문 유지
- row-level security: POC에선 pass-through. V2에서 지점 필터 훅

### 4.2 Next.js app-server
- 버전: Next.js 15 (App Router), TypeScript 5, React 19
- 포트: 3000
- 책임: 인증, CRUD REST, Claude proxy, Cube 중계, SSR

### 4.3 Frontend
- shadcn/ui 컴포넌트
- React Grid Layout (12-column, drag·resize)
- Vega-Lite 렌더러 + Preset 5종
- next-intl 한글화
- 상태관리: React Query (서버) + Zustand (로컬)

### 4.4 PostgreSQL 16
- ORM: Drizzle
- 스키마:
  - `users(id, email, google_sub, display_name, avatar_url, created_at, last_login_at)`
  - `dashboards(id, owner_id, title, description, created_at, updated_at)`
  - `dashboard_charts(id, dashboard_id, title, grid_x, grid_y, grid_w, grid_h, cube_query_json, chart_config_json, source, prompt_history_json, created_at, updated_at)`
  - `chat_messages(id, dashboard_id, user_id, role, content, tool_calls_json, created_at)`
  - `share_tokens(id, dashboard_id, token, created_by, expires_at, revoked_at)`
  - `ai_call_log(id, user_id, dashboard_id, endpoint, model, input_tokens, output_tokens, cache_read_tokens, cost_usd, latency_ms, status, error, created_at)` — 관찰성 필수 (POC 범위 포함)
- 포트: 5432 내부

### 4.5 Redis 7
- Cube pre-agg 캐시 + NextAuth 세션
- 포트: 6379 내부

### 4.6 차트 config 통합 스키마

AI·수동·hybrid 모두 동일 형식:
```json
{
  "id": "chart_xxx",
  "source": "ai" | "manual" | "hybrid",
  "cubeQuery": {
    "measures": ["AdsCampaign.spend"],
    "dimensions": ["AdsCampaign.channel"],
    "timeDimensions": [{"dimension": "AdsCampaign.reportDate", "granularity": "day", "dateRange": "last 7 days"}],
    "filters": [{"member": "AdsCampaign.branchId", "operator": "equals", "values": ["AMLV"]}]
  },
  "chartConfig": {"type": "line", "x": "reportDate", "y": "spend", "series": "channel", "title": "..."},
  "promptHistory": ["Meta 최근 7일 CPC 추이"]
}
```

---

## 5. 보안 / 에러 처리

### 5.1 보안 모델

| 위협 | 방어 |
|---|---|
| 외부 도메인 로그인 | NextAuth signIn callback에서 `@dstrict.com` 강제 |
| Claude API 키 유출 | LLM 호출 전부 app-server 경유. 키는 서버 env |
| Cube API 우회 호출 | 프론트 미노출. app-server가 JWT 서명 후 전달 |
| SQL injection | 경로 없음 — Claude → Cube JSON → 파라미터화 SQL |
| 공유 토큰 탈취 | 기본 30일 만료, 수동 revoke, SSO 추가 게이트 |
| 대량 쿼리 DoS | per-user rate limit (10 req/min, Redis counter) |
| BQ 비용 폭주 | Cube max-query-rows + BQ maximum-bytes-billed |

### 5.2 에러 처리 전략

| 계층 | 처리 |
|---|---|
| 인증 실패 | 로그인 페이지 리다이렉트 + 한글 메시지 |
| Claude 429/5xx/timeout | 1회 exponential backoff retry → 실패 시 수동 빌더 안내 |
| Claude structured output 검증 실패 | 에러 컨텍스트 포함 1회 retry → 실패 시 사용자에게 보고 |
| Cube permission denied | 관리자 알림 + 사용자에게 재로그인 안내 |
| Cube partition filter 누락 | 기본값 "최근 30일" 자동 주입 |
| 결과 0 rows | "조건에 맞는 데이터 없음" 플레이스홀더 + 필터 완화 제안 |
| Postgres down | 503 + 재시도 안내 |
| Redis 불가 | Cube 메모리 fallback, 경고 로그만 |

---

## 6. 한국어 전략

### 6.1 계층별 적용

| 레이어 | 구현 |
|---|---|
| UI 텍스트 | next-intl + `locales/ko.json` |
| Cube 메타 | YAML의 `title` / `description` 필드 |
| AI 응답 | system prompt "한국어 응답" + 용어 사전 주입 |
| AI 질의 | Claude Sonnet 4.6 한국어 직접 처리 |
| 날짜/숫자 | `Intl.*('ko-KR')` |
| 통화 | 지점별 currency (KRW / USD / AED 병기) |

### 6.2 Cube 스키마 예시
```yaml
cubes:
  - name: AdsCampaign
    sql_table: mart.v_dashboard_campaign_daily
    title: "광고 캠페인"
    measures:
      - name: spend
        title: "스펜드"
        sql: spend_native
        type: sum
        format: currency
    dimensions:
      - name: channel
        title: "채널"
        sql: channel_key
        type: string
```

### 6.3 용어 확정

| 기술 용어 | 한글 |
|---|---|
| measure | 측정값 |
| dimension | 차원 |
| filter | 필터 |
| time dimension | 기간 |
| granularity | 단위 |
| KPI card | KPI 카드 |
| dashboard | 대시보드 |
| drill-down | 드릴다운 |

마케팅 팀 변경 요청 반영 가능.

---

## 7. 관찰성·테스팅

### 7.1 관찰성

| 지표 | 저장소 | 목적 |
|---|---|---|
| Claude API 호출·비용·지연 | Postgres `ai_call_log` | 월 비용 메타 대시보드 |
| Cube 쿼리 / 캐시 hit | Cube 기본 로그 | 느린 쿼리 |
| 에러 트레이스 | console (POC) → 필요시 Sentry | |
| 사용자 액션 | Postgres chat_messages + prompt_history | 성공 기준 검증 |
| BQ scan bytes | BQ INFORMATION_SCHEMA + 기존 `jobs/report_bq_usage.py` | 무료 티어 감시 |

### 7.2 테스트

- **단위(Vitest)**: prompt 조립, claude-client, cube-client, DB 스키마, preset 컴포넌트
- **통합(Vitest + MSW 또는 Playwright)**: Flow 1/2/4 + Google SSO
- **Eval (20 질의)**: `viz/tests/eval/queries.yml` (한글 10 + 영어 10, 기대 chart config)
  - Python runner가 정확도 % 측정
  - **기대 답은 사용자가 수동 작성** (R14 방어)
- **TDD 의무화** (superpowers:test-driven-development) — 테스트 먼저 → 사용자 리뷰 → 구현

---

## 8. 타임라인

### 8.1 W1 — 로컬 MVP (10 세션, 2/day × 5일)

| 일 | 세션 | 작업 |
|---|---|---|
| D1 | S1 | docker-compose (cube+pg+redis) + BQ 연결 + cube schema 3개 (AdsCampaign, Orders, Surveys) + 시드 스크립트 |
| D1 | S2 | Cube 스키마 한글 title/description + Playground 수동 쿼리 검증 |
| D2 | S3 | Next.js + shadcn + NextAuth Google SSO + Drizzle 스키마·마이그레이션 |
| D2 | S4 | Dashboard/Chart CRUD API + 대시보드 목록·빈 대시보드 페이지 |
| D3 | S5 | React Grid Layout + Preset 차트 5종 (Line/Bar/KPI/Table/Pie) + Vega-Lite fallback |
| D3 | S6 | 수동 빌더 Playground 스타일 + 저장→로드 E2E |
| D4 | S7 | Claude API proxy + 한글 system prompt + structured output + Zod + prompt caching |
| D4 | S8 | 사이드 패널 chat UI + AI 차트 생성 E2E + 에러 UX |
| D5 | S9 | next-intl 전체 + 공유 링크 기본(만료·revoke 없음) + Intl 포맷 |
| D5 | S10 | Week 1 종료 smoke (로컬 E2E) + PR 정리 |

**W1 종료 조건**: 로컬에서 로그인 → 빈 대시보드 생성 → AI/수동 양 경로로 차트 생성 → 저장/공유 기본 모두 동작.

### 8.2 W2 — 보강 + 배포 (10 세션)

| 일 | 세션 | 작업 |
|---|---|---|
| W2 D1 | S11 | GA4 WebEvents cube (정제 집계 뷰 `mart.v_web_branch_daily` 기반) + 시드 |
| W2 D1 | S12 | BlendedFunnel cube (`mart.v_blended_funnel_daily`) + 시드 검증 |
| W2 D2 | S13 | `/api/ai/refine-chart` + context 주입 + diff 병합 + 검증 |
| W2 D2 | S14 | 차트 카드 "AI 보정" 버튼 + 사이드패널 기존 config 로드 E2E |
| W2 D3 | S15 | Eval 20개 질의 세트 (한글 10 + 영어 10) + 기대 config 수작성 |
| W2 D3 | S16 | Python eval runner + 정확도 측정 자동화 |
| W2 D4 | S17 | `docker-compose.prod.yml` + Caddy SSL + env secrets 분리 |
| W2 D4 | S18 | VM 디스크 확장 확인 + rsync 배포 스크립트 + DNS A |
| W2 D5 | S19 | **VM 첫 배포** + smoke + SSL 인증서 발급 확인 |
| W2 D5 | S20 | 마케팅 3명 온보딩 문서 + Slack 피드백 채널 + POC 평가 기준 재확인 |

**W2 종료 = 배포 완료 + 실사용 준비 완료**.

### 8.3 W3~4 — 실사용 평가 (2주)
- 마케팅 3명 일 1회 이상 접속
- 주 2회 15분 체크인
- 차트 누적 100개+ 목표
- 매주 eval 재측정

---

## 9. 마일스톤

| M | 시점 | 조건 |
|---|---|---|
| M1 | S2 종료 | Cube Playground 수동 쿼리 3개 성공 |
| M2 | S4 종료 | 로그인 + 빈 대시보드 CRUD 동작 |
| M3 | S6 종료 | 수동 빌더로 차트 3개 생성/저장/로드 |
| M4 | S8 종료 | AI 한글 질의로 차트 1개 정확 생성 |
| M5 | S10 종료 | Week 1 로컬 MVP 완성 |
| M6 | S14 종료 | AI 보정 + GA4 + Blended 완성 |
| M7 | S19 종료 | VM 배포 성공 (`viz.dstrict.com` 정상) |
| M8 | W4 말 | 성공 기준 충족/미충족 판정 |

---

## 10. 리스크 레지스터

| ID | 리스크 | 확률 | 영향 | 대응 |
|---|---|---|---|---|
| R1 | Claude structured output 실패율 | 중 | 중 | tool_choice=required + Zod + retry + few-shot 3→5개 |
| ~~R2~~ | ~~GA4 JSON 중첩 복잡도~~ — 해결됨 (정제 집계 뷰 사용) | - | - | 2026-04-23 제거 |
| R3 | `metric_definition` 0건 → 한글 title 수작업 | 높 | 낮 | S1~S2에 Cube YAML 작성과 병행 |
| R4 | Google OAuth 승인 지연 | 중 | 중 | D1 오전 즉시 신청, 대기 중 mock user로 우회 |
| R5 | VM 디스크 11 GB 부족 | 중 | 높 | 사용자 W2 D4 전 확장 완료 필수 |
| R6 | Cube pre-agg 리프레시 비용 | 낮 | 중 | POC엔 쿼리 캐시만, pre-agg는 느린 쿼리 기준 선별 |
| R7 | 마케팅 일정 확보 실패 | 중 | 높 | W2 D5까지 확정 + 주 2회 체크인 |
| R8 | 한글 정확도 70% 미달 | 중 | 높 | 용어 사전 확장 + 도메인별 few-shot 5개씩 |
| R9 | Claude API 비용 초과 | 낮 | 중 | Anthropic console 월 $150 한도 + Slack 알림 |
| ~~R10~~ | ~~기존 PR #1 (리팩토링) 미머지 충돌~~ — 해결됨 (PR #1 2026-04-23 머지 완료) | - | - | 제거 |
| R11 | Claude Code 세션 context 단절 | 중 | 중 | `status.md` + TaskCreate + Plan mode |
| R12 | AI slop (과설계·미사용 코드) | 중 | 중 | 매 PR code-reviewer 자기 리뷰, code-simplifier |
| R13 | 테스트 자기 검증 편향 | 중 | 중 | TDD 의무 + 사용자 테스트 먼저 승인 |
| R14 | Eval 자기 평가 | 높 | 중 | 기대 답 사용자 수동 작성 |
| R15 | 사용자 리뷰 병목 | 중 | 높 | 작은 PR(<200 LoC) + draft + Slack 비동기 |
| R16 | 세션 중 스펙 drift | 중 | 높 | 매 세션 시작 설계·status 재로드, `CLAUDE.md` 프로젝트 헌법 |
| R17 | 사용자 VM/DNS 직접 액션 대기 | 중 | 낮 | 명확한 명령·스크립트 제공 |
| R18 | 정제 GA4 실데이터 파이프라인 미구현 | 해당없음 | 낮 | POC 이후 별도 Sprint로 이관 |

---

## 11. 의존성 / 사전 조건

- [ ] Google Workspace OAuth client (`@dstrict.com` 제한) — W1 D1 오전
- [ ] Anthropic API 키 + 월 $150 한도 — W1 D1 오전
- [ ] VM 디스크 확장 (11→50 GB+) — W2 D4 전
- [ ] `viz.dstrict.com` DNS A 레코드 — W2 D4
- [x] BQ 서비스키 (`secrets/common/service_key.json` 재사용) — 완료
- [x] PR #1 (구조 리팩토링) 머지 — 2026-04-23 완료
- [ ] 마케팅 실사용자 3명 확정 — W2 D5
- [ ] 사용자 Claude Code 구독 유지 — 전 기간
- [ ] `CLAUDE.md` 프로젝트 헌법 작성 — W1 D1 시작 시

---

## 12. 개발 프로세스 (Claude Code 전용)

### 12.1 세션 루프

```
사용자 "다음 작업" 세션 오픈
  ↓
Claude: CLAUDE.md + status.md + 설계 재로드
  ↓
Claude: Plan 제시 → 사용자 승인 (짧게)
  ↓
Claude: TDD (테스트 먼저, 사용자 승인)
  ↓
Claude: 구현 + code-reviewer 자기 리뷰
  ↓
Claude: Draft PR 생성
  ↓
사용자: 빠른 리뷰 (<20 min) — OK/반려
  ↓
Claude: 수정 or 머지
  ↓
Claude: status.md 갱신 (다음 세션 액션)
  ↓
세션 종료
```

### 12.2 품질 게이트 (매 PR)

- [ ] pytest / vitest 전부 통과
- [ ] code-reviewer 자기 리뷰 (P0/P1 0건)
- [ ] 사용자 로컬 실행 확인
- [ ] `status.md` 갱신
- [ ] PR < 200 LoC

### 12.3 필수 활용 스킬

- `superpowers:test-driven-development`
- `superpowers:verification-before-completion`
- `superpowers:writing-plans` (세션 간 plan 파일)
- `superpowers:executing-plans`
- `ce-code-review` 또는 `code-reviewer` agent
- `ce-compound` (학습 패턴 docs/solutions/ 저장)

### 12.4 스코프 가드 — W1에 **거부**

- 새 cube 추가
- 새 차트 타입 (5종만)
- 디자인 폴리시 (Playground 스타일 유지)
- 차트 간 crossfilter
- 이메일 알림
- 모바일 전용 UI
- 대시보드 템플릿 기능

→ 사용자 추가 요청 시 자동 Sprint 2 백로그 파킹, Claude가 명시 거부.

---

## 13. GitHub 워크플로우

```
main (안정 기록)
  └─ feat/viz-w1-cube-schema     → S1~S2
  └─ feat/viz-w1-auth-crud        → S3~S4
  └─ feat/viz-w1-grid-charts      → S5~S6
  └─ feat/viz-w1-ai-create        → S7~S8
  └─ feat/viz-w1-i18n-share       → S9
  └─ feat/viz-w1-smoke            → S10
  └─ feat/viz-w2-ga4-blended      → S11~S12
  └─ feat/viz-w2-ai-refine        → S13~S14
  └─ feat/viz-w2-eval-automation  → S15~S16
  └─ feat/viz-w2-deploy-prod      → S17~S19
  └─ feat/viz-w2-onboarding-docs  → S20
```

---

## 14. POC 성공 기준

W4 말(실사용 2주 종료) 평가:

- [ ] Eval 20개 질의 정확도 ≥ 80%
- [ ] 한국어 질의 정확도 ≥ 70%
- [ ] 응답 시간 p95 < 5초
- [ ] 실사용자 3명이 2주간 매일 접속
- [ ] 차트 누적 100개+
- [ ] 월 운영비 (Claude API + BQ + 호스팅) < $150

모두 충족 → 프로덕션 전환. 일부 미달 → 원인별 연장 or 경로 E(Looker Studio Pro + Gemini) 비교 POC.

---

## 15. 비 목표 (POC 범위 밖)

- 모바일 전용 UI (데스크탑 우선, mobile-friendly만)
- 실시간 스트리밍 데이터 (일 단위 refresh만)
- 차트 간 crossfilter
- 이메일 리포트 발송
- Slack 봇 연동
- CSV/PDF export (raw 다운만 Cube /load 기본 제공)
- 지점별 권한 분리 (POC: 전 사용자 모든 지점 조회)
- 정제 GA4 실데이터 ingest 파이프라인 (시드만 사용)
- shadcn 폴리시 빌더 (Playground 스타일로 POC, 피드백 후 V2)

---

## 16. 다음 단계

이 설계 문서 확정 후 `superpowers:writing-plans` 스킬로 **W1 세션 10개 상세 구현 계획**을 먼저 작성한다. 구현 계획 파일은 `docs/plans/YYYY-MM-DD-viz-w1-implementation-plan.md`에 저장.

W1 완료 후 W2 계획을 별도 plan 파일로 작성.

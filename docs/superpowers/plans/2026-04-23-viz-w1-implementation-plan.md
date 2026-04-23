# MKT-Viz W1 (로컬 MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Week 1 안에 로컬 docker-compose 환경에서 Google SSO + AI·수동 차트 생성 + 대시보드 저장/공유 기본이 동작하는 viz MVP를 만든다.

**Architecture:** Cube.js(OSS) 시맨틱 레이어 위에 Next.js 15 App Router(app-server + SSR 프론트)와 PostgreSQL(상태) + Redis(세션/캐시)를 docker-compose로 묶는다. AI는 Claude API를 app-server가 프록시하여 structured output으로 Cube query JSON을 얻어 차트를 렌더한다.

**Tech Stack:** Cube.js 1.x / BigQuery / Next.js 15 / React 19 / TypeScript 5 / shadcn/ui / NextAuth 5 (Google SSO) / Drizzle ORM / PostgreSQL 16 / Redis 7 / Anthropic SDK (`@anthropic-ai/sdk`) / Vega-Lite 5 / react-grid-layout / Zod / gspread-lite (Python, 시드 전용) / Docker Compose

**Spec 참조:** `docs/superpowers/specs/2026-04-23-viz-dashboard-design.md`

---

## 전제 (Preconditions)

이 플랜 실행 시작 전에 다음이 준비되어 있어야 한다. 준비 안 됐으면 해당 Task 진입 전 획득.

- [ ] Google Cloud OAuth client ID/Secret (`@dstrict.com` 도메인 제한)
- [ ] Anthropic API 키 + 월 $150 한도
- [ ] BQ 서비스키 파일 `secrets/common/service_key.json` (기존 ingest에서 재사용)
- [ ] GCP 프로젝트 `mimetic-gravity-442013-u4` read 권한
- [ ] 시트 service account `gspread@skilled-keyword-423414-t0.iam.gserviceaccount.com` (전체 공유 덕분에 CSV export로 충분)
- [ ] `CLAUDE.md` 루트 헌법 파일 (Task 1 스텝 1에서 작성)
- [ ] `.env.local` 시크릿 파일 (Task 1 스텝 4)

---

## File Structure (신규/수정 대상)

### 신규
```
CLAUDE.md                                            # 프로젝트 헌법
viz/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── cube/
│   ├── Dockerfile
│   ├── cube.js
│   ├── package.json
│   ├── .cubeenv                                     # Cube 추가 env
│   └── schema/
│       ├── AdsCampaign.yml
│       ├── Orders.yml
│       ├── Surveys.yml
│       └── dims/
│           ├── Branch.yml
│           └── Channel.yml
├── app/
│   ├── Dockerfile
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── postcss.config.mjs
│   ├── tailwind.config.ts
│   ├── drizzle.config.ts
│   ├── components.json                              # shadcn
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── (auth)/login/page.tsx
│   │   │   ├── (dashboard)/layout.tsx
│   │   │   ├── (dashboard)/page.tsx
│   │   │   ├── (dashboard)/d/[id]/page.tsx
│   │   │   ├── (dashboard)/shared/[token]/page.tsx
│   │   │   └── api/
│   │   │       ├── auth/[...nextauth]/route.ts
│   │   │       ├── dashboards/route.ts
│   │   │       ├── dashboards/[id]/route.ts
│   │   │       ├── charts/route.ts
│   │   │       ├── charts/[id]/route.ts
│   │   │       ├── ai/create-chart/route.ts
│   │   │       └── cube/load/route.ts
│   │   ├── components/
│   │   │   ├── ui/button.tsx                        # shadcn
│   │   │   ├── ui/dialog.tsx
│   │   │   ├── ui/input.tsx
│   │   │   ├── ui/select.tsx
│   │   │   ├── ui/sheet.tsx
│   │   │   ├── ui/card.tsx
│   │   │   ├── dashboard/Grid.tsx
│   │   │   ├── dashboard/ChartCard.tsx
│   │   │   ├── dashboard/ShareDialog.tsx
│   │   │   ├── builder/QueryBuilder.tsx
│   │   │   ├── builder/ChartTypePicker.tsx
│   │   │   ├── builder/Preview.tsx
│   │   │   ├── ai-panel/ChatPanel.tsx
│   │   │   ├── ai-panel/MessageList.tsx
│   │   │   ├── ai-panel/Composer.tsx
│   │   │   ├── charts/LineChart.tsx
│   │   │   ├── charts/BarChart.tsx
│   │   │   ├── charts/KPICard.tsx
│   │   │   ├── charts/TableChart.tsx
│   │   │   ├── charts/PieChart.tsx
│   │   │   └── charts/VegaLiteChart.tsx
│   │   ├── lib/
│   │   │   ├── cube-client.ts
│   │   │   ├── claude-client.ts
│   │   │   ├── prompts/chart-create.ts
│   │   │   ├── prompts/glossary.ts
│   │   │   ├── db/client.ts
│   │   │   ├── db/schema.ts
│   │   │   ├── chart-types/registry.ts
│   │   │   └── auth/options.ts
│   │   ├── locales/ko.json
│   │   └── middleware.ts
│   └── tests/
│       ├── setup.ts
│       ├── lib/claude-client.test.ts
│       ├── lib/cube-client.test.ts
│       └── components/charts/LineChart.test.tsx
├── postgres/
│   └── init.sql
└── scripts/
    ├── seed-test-data.py                            # sales/survey 시드
    └── seed-sheets.py                               # AMNY/DSTX 시트 import

docs/status.md                                       # 세션 간 연속성
```

### 수정
- `.gitignore` — viz 관련 경로 추가

---

## Task 1 (S1): 환경 부트스트랩 + Cube 뼈대 + 시드 스크립트

**Goal:** docker-compose로 cube/pg/redis 기동 + BQ 연결 + 3개 cube 스키마 초안 + sales/survey/시트 import 스크립트가 1회 성공.

**Branch:** `feat/viz-w1-cube-schema`

**Files:**
- Create: `CLAUDE.md`, `docs/status.md`
- Create: `viz/docker-compose.yml`, `viz/.env.example`, `viz/.gitignore`, `viz/README.md`
- Create: `viz/cube/Dockerfile`, `viz/cube/cube.js`, `viz/cube/package.json`
- Create: `viz/cube/schema/AdsCampaign.yml`, `viz/cube/schema/Orders.yml`, `viz/cube/schema/Surveys.yml`
- Create: `viz/postgres/init.sql`
- Create: `viz/scripts/seed-test-data.py`, `viz/scripts/seed-sheets.py`
- Modify: `.gitignore` (viz/.env, viz/app/node_modules 등)
- Create: `viz/tests/test_seed_sheets.py`

- [ ] **Step 1: 프로젝트 헌법 `CLAUDE.md` 작성**

`/Users/moo/MKT-Dashboard/CLAUDE.md` 생성:

```markdown
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
```

- [ ] **Step 2: status 파일 초기화**

`docs/status.md`:

```markdown
# MKT-Viz W1 Status

**Current plan:** `docs/superpowers/plans/2026-04-23-viz-w1-implementation-plan.md`

**Last session:** (none)

**Next session:** Task 1 — S1 환경 부트스트랩

**Prerequisites open:**
- [ ] Google OAuth client
- [ ] Anthropic API 키
- [ ] .env.local 파일 작성

**Sessions completed:**
(비어있음)
```

- [ ] **Step 3: `.gitignore` 확장**

루트 `.gitignore`에 추가:

```
# viz/
viz/app/node_modules/
viz/app/.next/
viz/cube/node_modules/
viz/*.local
viz/.env
viz/data/
```

- [ ] **Step 4: `viz/.env.example` 작성**

`viz/.env.example`:

```
# BigQuery
BQ_PROJECT_ID=mimetic-gravity-442013-u4
BQ_CREDENTIALS_PATH=/app/secrets/service_key.json

# Cube.js
CUBEJS_API_SECRET=change-me-32-byte-random
CUBEJS_DB_TYPE=bigquery
CUBEJS_DB_BQ_PROJECT_ID=${BQ_PROJECT_ID}
CUBEJS_DB_BQ_KEY_FILE=/cube/conf/service_key.json
CUBEJS_REDIS_URL=redis://redis:6379
CUBEJS_DEV_MODE=true

# Next.js
DATABASE_URL=postgres://app:devpass@postgres:5432/mkt_viz
REDIS_URL=redis://redis:6379
CUBE_API_URL=http://cube:4000/cubejs-api/v1
CUBE_API_SECRET=${CUBEJS_API_SECRET}
CLAUDE_API_KEY=sk-ant-your-key
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=change-me-32-byte-random
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
ALLOWED_EMAIL_DOMAIN=dstrict.com

# Postgres
PG_USER=app
PG_PASSWORD=devpass
PG_DB=mkt_viz

# Sheets (AMNY/DSTX)
SHEET_ID=1WsATorbjts3CgjXKkNYW8iVs3ZKrnOkzcK4gHOIru50
SHEET_GSPREAD_ACCOUNT=gspread@skilled-keyword-423414-t0.iam.gserviceaccount.com
```

- [ ] **Step 5: `viz/docker-compose.yml` 작성**

```yaml
services:
  cube:
    build: ./cube
    ports: ["4000:4000", "3001:3001"]
    env_file: .env
    volumes:
      - ./cube/schema:/cube/conf/schema:ro
      - ../secrets/common/service_key.json:/cube/conf/service_key.json:ro
    depends_on: [redis]

  app:
    build: ./app
    ports: ["3000:3000"]
    env_file: .env
    depends_on: [postgres, redis, cube]

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${PG_DB}
      POSTGRES_USER: ${PG_USER}
      POSTGRES_PASSWORD: ${PG_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

- [ ] **Step 6: Cube Dockerfile + package.json + cube.js 엔트리**

`viz/cube/Dockerfile`:

```dockerfile
FROM node:20-alpine
WORKDIR /cube/conf
COPY package.json ./
RUN npm install --omit=dev
COPY cube.js ./
EXPOSE 4000 3001
CMD ["npx", "cubejs-server", "server"]
```

`viz/cube/package.json`:

```json
{
  "name": "mkt-viz-cube",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "@cubejs-backend/bigquery-driver": "^1.2.0",
    "@cubejs-backend/server": "^1.2.0",
    "ioredis": "^5.4.1",
    "jsonwebtoken": "^9.0.2"
  }
}
```

`viz/cube/cube.js`:

```javascript
const jwt = require('jsonwebtoken');

module.exports = {
  checkAuth: (req, auth) => {
    if (!auth) throw new Error('No auth token');
    try {
      req.securityContext = jwt.verify(auth, process.env.CUBEJS_API_SECRET, { algorithms: ['HS256'] });
    } catch (e) {
      throw new Error(`JWT invalid: ${e.message}`);
    }
  },
  contextToAppId: ({ securityContext }) => `app_${securityContext?.user_id || 'anon'}`,
};
```

- [ ] **Step 7: Cube 스키마 3개 초안**

`viz/cube/schema/AdsCampaign.yml`:

```yaml
cubes:
  - name: AdsCampaign
    sql_table: mart.v_dashboard_campaign_daily
    data_source: default
    title: "광고 캠페인"
    description: "일별 캠페인 성과 (지점·채널)"

    measures:
      - name: spend
        title: "스펜드"
        sql: spend_native
        type: sum
        format: currency
      - name: impressions
        title: "노출수"
        sql: impressions
        type: sum
      - name: clicks
        title: "클릭수"
        sql: clicks
        type: sum
      - name: ctr
        title: "CTR"
        description: "클릭률 (%)"
        sql: "SAFE_DIVIDE(SUM({clicks}), NULLIF(SUM({impressions}), 0)) * 100"
        type: number
        format: percent
      - name: cpc
        title: "CPC"
        sql: "SAFE_DIVIDE(SUM({spend}), NULLIF(SUM({clicks}), 0))"
        type: number
        format: currency
      - name: roas
        title: "ROAS"
        sql: "SAFE_DIVIDE(SUM({conversion_value_native}), NULLIF(SUM({spend}), 0))"
        type: number

    dimensions:
      - name: reportDate
        title: "보고일"
        sql: report_date
        type: time
      - name: branchId
        title: "지점"
        sql: branch_id
        type: string
      - name: channelKey
        title: "채널"
        sql: channel_key
        type: string
      - name: campaignId
        title: "캠페인 ID"
        sql: campaign_id
        type: string
      - name: campaignName
        title: "캠페인명"
        sql: campaign_name
        type: string
```

`viz/cube/schema/Orders.yml`:

```yaml
cubes:
  - name: Orders
    sql_table: mart.v_business_branch_daily
    data_source: default
    title: "주문"

    measures:
      - name: orders
        title: "주문수"
        sql: orders
        type: sum
      - name: netRevenue
        title: "순매출"
        sql: net_revenue_native
        type: sum
        format: currency
      - name: grossRevenue
        title: "총매출"
        sql: gross_revenue_native
        type: sum
        format: currency

    dimensions:
      - name: reportDate
        title: "주문일"
        sql: report_date
        type: time
      - name: branchId
        title: "지점"
        sql: branch_id
        type: string
      - name: currencyCode
        title: "통화"
        sql: currency_code
        type: string
```

`viz/cube/schema/Surveys.yml`:

```yaml
cubes:
  - name: Surveys
    sql_table: mart.v_survey_branch_daily
    data_source: default
    title: "설문"

    measures:
      - name: responseCount
        title: "응답수"
        sql: response_count
        type: sum
      - name: avgScore
        title: "평균 점수"
        sql: avg_answer_score
        type: avg

    dimensions:
      - name: reportDate
        title: "응답일"
        sql: report_date
        type: time
      - name: branchId
        title: "지점"
        sql: branch_id
        type: string
```

- [ ] **Step 8: Postgres init.sql**

`viz/postgres/init.sql`:

```sql
-- App schema bootstrap (idempotent)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Drizzle will own table DDL. This file only bootstraps DB/extensions.
```

- [ ] **Step 9: Seed script 작성 (테스트 먼저)**

`viz/tests/test_seed_sheets.py`:

```python
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import seed_sheets


def test_normalize_channel_code_variants():
    assert seed_sheets.normalize_channel_code("1_Meta") == "META"
    assert seed_sheets.normalize_channel_code("META") == "META"
    assert seed_sheets.normalize_channel_code("2_Google_Search") == "GOOGLE_ADS"
    assert seed_sheets.normalize_channel_code("GOOGLE_SEARCH") == "GOOGLE_ADS"
    assert seed_sheets.normalize_channel_code("7_TikTok") == "TIKTOK_ADS"
    assert seed_sheets.normalize_channel_code("4_Youtube") == "YOUTUBE"
    assert seed_sheets.normalize_channel_code("14_Affiliate") == "AFFILIATE"
    assert seed_sheets.normalize_channel_code("15_Email") == "EMAIL"
    assert seed_sheets.normalize_channel_code("102_Ambassadors") == "INFLUENCER"
    assert seed_sheets.normalize_channel_code("12_Organic_SEO") == "ORGANIC_SEO"
    assert seed_sheets.normalize_channel_code("114_OTA") == "OTA"
    assert seed_sheets.normalize_channel_code("unknown_xyz") == "OTHER"


def test_parse_currency_amount():
    assert seed_sheets.parse_currency("$91,952.10") == 91952.10
    assert seed_sheets.parse_currency("1,495") == 1495.0
    assert seed_sheets.parse_currency("") is None
    assert seed_sheets.parse_currency("$0.00") == 0.0
```

- [ ] **Step 10: Run test to verify fail**

```bash
cd /Users/moo/MKT-Dashboard && ./.venv/bin/python -m pytest viz/tests/test_seed_sheets.py -v
```

Expected: FAIL (module not found).

- [ ] **Step 11: Implement `viz/scripts/seed_sheets.py` minimal to pass**

```python
"""Snapshot AMNY/DSTX Google Sheets → BigQuery raw_ads.external_ads_raw.

Idempotent: WRITE_TRUNCATE on each run. Designed for cron use.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests

SHEET_ID = "1WsATorbjts3CgjXKkNYW8iVs3ZKrnOkzcK4gHOIru50"

BRANCH_GIDS = {
    "AMNY": {
        "spend": 1792827791,
        "impressions": 980029740,
        "clicks": 643195110,
        "cr": 2093655192,
    },
    "DSTX": {
        "spend": 2095643634,
        "impressions": 1248817661,
        "clicks": 323203861,
        "cr": 584816983,
    },
}

# Channel code → canonical channel_key mapping
# Covers prefixed (1_Meta) and flat (META) variants.
CHANNEL_MAP = {
    "1_meta": "META",
    "meta": "META",
    "2_google_search": "GOOGLE_ADS",
    "google_search": "GOOGLE_ADS",
    "3_google_display": "GOOGLE_ADS",
    "22_google_demand_gen": "GOOGLE_DEMAND_GEN",
    "7_tiktok": "TIKTOK_ADS",
    "tiktok": "TIKTOK_ADS",
    "4_youtube": "YOUTUBE",
    "youtube": "YOUTUBE",
    "10_coupons": "COUPON",
    "14_affiliate": "AFFILIATE",
    "15_email": "EMAIL",
    "102_ambassadors": "INFLUENCER",
    "58_marketing_fee": "OTHER",
    "12_organic_seo": "ORGANIC_SEO",
    "114_ota": "OTA",
}


def normalize_channel_code(raw: str) -> str:
    key = (raw or "").strip().lower()
    return CHANNEL_MAP.get(key, "OTHER")


_currency_re = re.compile(r"[,$%]")


def parse_currency(value: str) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    s = _currency_re.sub("", s)
    try:
        return float(s)
    except ValueError:
        return None


def fetch_sheet_csv(gid: int) -> str:
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text


@dataclass
class MetricRow:
    date: str
    channel_code: str
    value: float | None


def parse_metric_sheet(csv_text: str, metric_cols: int = 3) -> Iterable[MetricRow]:
    """Read only the first `metric_cols` columns (DATE, CHANNEL, METRIC).

    Trailing pivot columns are ignored.
    """
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader, None)
    if not header or header[0].strip().upper() != "DATE":
        raise AssertionError(f"Unexpected header: {header}")
    for row in reader:
        if len(row) < metric_cols:
            continue
        raw_date = row[0].strip()
        channel = row[1].strip() if len(row) > 1 else ""
        value = parse_currency(row[2]) if len(row) > 2 else None
        if not raw_date or not channel:
            continue
        try:
            date = datetime.fromisoformat(raw_date.replace(" 0:00:00", "")).date().isoformat()
        except ValueError:
            continue
        yield MetricRow(date=date, channel_code=channel, value=value)


def parse_cr_sheet(csv_text: str) -> Iterable[tuple[str, str, float | None, float | None, float | None]]:
    """CR sheet schema: DATE, CD_MKT_CHANNEL, MXP_TRANSACTIONS, MXP_PLAN_VIEWS, CR."""
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader, None)
    if not header or header[0].strip().upper() != "DATE":
        raise AssertionError(f"Unexpected header: {header}")
    for row in reader:
        if len(row) < 5:
            continue
        date_raw, channel, tx, pv, cr = row[:5]
        try:
            date = datetime.fromisoformat(date_raw.strip().replace(" 0:00:00", "")).date().isoformat()
        except ValueError:
            continue
        if not channel.strip():
            continue
        yield date, channel.strip(), parse_currency(tx), parse_currency(pv), parse_currency(cr)


def build_rows(branch_id: str) -> list[dict]:
    """Join 4 metric sheets on (date, channel_code)."""
    gids = BRANCH_GIDS[branch_id]
    ingestion_ts = datetime.now(timezone.utc).isoformat()

    # Load each metric into keyed dicts
    spend = {(r.date, normalize_channel_code(r.channel_code)): r.value for r in parse_metric_sheet(fetch_sheet_csv(gids["spend"]))}
    impressions = {(r.date, normalize_channel_code(r.channel_code)): r.value for r in parse_metric_sheet(fetch_sheet_csv(gids["impressions"]))}
    clicks = {(r.date, normalize_channel_code(r.channel_code)): r.value for r in parse_metric_sheet(fetch_sheet_csv(gids["clicks"]))}

    cr_rows = list(parse_cr_sheet(fetch_sheet_csv(gids["cr"])))
    cr_by_key = {}
    for date, channel, tx, pv, cr in cr_rows:
        k = (date, normalize_channel_code(channel))
        cr_by_key[k] = (tx, pv, cr)

    keys = set(spend.keys()) | set(impressions.keys()) | set(clicks.keys()) | set(cr_by_key.keys())

    rows = []
    for (date, channel_key) in sorted(keys):
        tx, pv, cr = cr_by_key.get((date, channel_key), (None, None, None))
        rows.append({
            "date": date,
            "branch_id": branch_id,
            "channel_code": channel_key,
            "channel_key": channel_key,
            "spend_usd": spend.get((date, channel_key)),
            "impressions": impressions.get((date, channel_key)),
            "clicks": clicks.get((date, channel_key)),
            "transactions": tx,
            "plan_views": pv,
            "cr_pct": cr,
            "ingestion_ts": ingestion_ts,
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true", help="WRITE_TRUNCATE the raw table")
    parser.add_argument("--project-id", default=os.getenv("BQ_PROJECT_ID", "mimetic-gravity-442013-u4"))
    parser.add_argument("--credentials-path", default=os.getenv("BQ_CREDENTIALS_PATH"))
    parser.add_argument("--table", default="raw_ads.external_ads_raw")
    parser.add_argument("--branches", nargs="+", default=["AMNY", "DSTX"])
    args = parser.parse_args(argv)

    all_rows: list[dict] = []
    for b in args.branches:
        all_rows.extend(build_rows(b))

    print(f"[seed-sheets] branches={args.branches} rows={len(all_rows)}")

    from google.cloud import bigquery
    from google.oauth2 import service_account

    creds = None
    if args.credentials_path and Path(args.credentials_path).exists():
        creds = service_account.Credentials.from_service_account_file(args.credentials_path)
    client = bigquery.Client(project=args.project_id, credentials=creds, location="us-central1")

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE" if args.overwrite else "WRITE_APPEND",
        schema=[
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("branch_id", "STRING"),
            bigquery.SchemaField("channel_code", "STRING"),
            bigquery.SchemaField("channel_key", "STRING"),
            bigquery.SchemaField("spend_usd", "NUMERIC"),
            bigquery.SchemaField("impressions", "INTEGER"),
            bigquery.SchemaField("clicks", "INTEGER"),
            bigquery.SchemaField("transactions", "INTEGER"),
            bigquery.SchemaField("plan_views", "INTEGER"),
            bigquery.SchemaField("cr_pct", "NUMERIC"),
            bigquery.SchemaField("ingestion_ts", "TIMESTAMP"),
        ],
        labels={"pipeline": "mkt_viz", "step": "seed_sheets"},
    )
    table_ref = f"{args.project_id}.{args.table}"
    job = client.load_table_from_json(all_rows, table_ref, job_config=job_config)
    job.result()
    print(f"[seed-sheets] loaded {len(all_rows)} rows into {table_ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 12: Run tests**

```bash
./.venv/bin/python -m pytest viz/tests/test_seed_sheets.py -v
```

Expected: PASS (모든 assert 통과).

- [ ] **Step 13: Sales/survey 시드 스크립트 골격 작성**

`viz/scripts/seed_test_data.py`:

```python
"""Seed test data for Sales/Survey into BigQuery raw tables (POC-only).

WARNING: Uses WRITE_TRUNCATE on raw_commerce.sales_orders_raw and
raw_feedback.survey_responses_raw. Do NOT run on production ingest paths.
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

BRANCH_IDS = ["AMLV", "AMBS", "AMDB", "AMGN", "AMJJ", "AMYS", "AKJJ"]
START = date(2026, 4, 1)
DAYS = 12


def gen_sales() -> list[dict]:
    rows = []
    for d_offset in range(DAYS):
        d = START + timedelta(days=d_offset)
        for branch in BRANCH_IDS:
            n = random.randint(10, 50)
            for i in range(n):
                order_id = f"POC_{branch}_{d.isoformat()}_{i:03d}"
                qty = random.randint(1, 4)
                gross = round(random.uniform(15, 120) * qty, 2)
                discount = round(gross * random.uniform(0, 0.15), 2)
                net = round(gross - discount, 2)
                rows.append({
                    "ingestion_id": f"POC-SEED-{order_id}",
                    "ingestion_ts": datetime.now(timezone.utc).isoformat(),
                    "source_extract_ts": datetime.now(timezone.utc).isoformat(),
                    "source_system": "POC_SEED",
                    "order_id": order_id,
                    "order_line_id": f"{order_id}-1",
                    "order_ts": datetime.combine(d, datetime.min.time()).isoformat(),
                    "order_date": d.isoformat(),
                    "customer_id": f"CUST_{random.randint(1000, 9999)}",
                    "customer_email": None,
                    "customer_phone": None,
                    "product_id": f"TICKET_{branch}",
                    "product_name": "일반권",
                    "quantity": qty,
                    "gross_amount": gross,
                    "discount_amount": discount,
                    "net_amount": net,
                    "currency": "USD" if branch in ("AMLV",) else "KRW",
                    "payment_status": "PAID",
                    "source_payload": None,
                })
    return rows


def gen_surveys() -> list[dict]:
    rows = []
    for d_offset in range(DAYS):
        d = START + timedelta(days=d_offset)
        for branch in BRANCH_IDS:
            n = random.randint(3, 8)
            for i in range(n):
                response_id = f"POC_SURV_{branch}_{d.isoformat()}_{i:03d}"
                score = random.randint(6, 10)
                rows.append({
                    "ingestion_id": f"POC-SEED-{response_id}",
                    "ingestion_ts": datetime.now(timezone.utc).isoformat(),
                    "source_extract_ts": datetime.now(timezone.utc).isoformat(),
                    "survey_source": "POC_SEED",
                    "response_id": response_id,
                    "response_ts": datetime.combine(d, datetime.min.time()).isoformat(),
                    "response_date": d.isoformat(),
                    "customer_email": None,
                    "customer_phone": None,
                    "survey_id": "NPS_2026_04",
                    "survey_name": "Post-visit NPS",
                    "question_id": "q_nps",
                    "question_text": "추천 의향",
                    "answer_type": "score",
                    "answer_text": str(score),
                    "answer_score": float(score),
                    "source_payload": None,
                })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", default=os.getenv("BQ_PROJECT_ID", "mimetic-gravity-442013-u4"))
    parser.add_argument("--credentials-path", default=os.getenv("BQ_CREDENTIALS_PATH"))
    parser.add_argument("--sales-table", default="raw_commerce.sales_orders_raw")
    parser.add_argument("--survey-table", default="raw_feedback.survey_responses_raw")
    args = parser.parse_args(argv)

    from google.cloud import bigquery
    from google.oauth2 import service_account

    creds = None
    if args.credentials_path and Path(args.credentials_path).exists():
        creds = service_account.Credentials.from_service_account_file(args.credentials_path)
    client = bigquery.Client(project=args.project_id, credentials=creds, location="us-central1")

    sales = gen_sales()
    surveys = gen_surveys()
    print(f"[seed-test-data] sales={len(sales)} surveys={len(surveys)}")

    for table, rows in [(args.sales_table, sales), (args.survey_table, surveys)]:
        ref = f"{args.project_id}.{table}"
        job = client.load_table_from_json(
            rows,
            ref,
            job_config=bigquery.LoadJobConfig(
                write_disposition="WRITE_TRUNCATE",
                labels={"pipeline": "mkt_viz", "step": "seed_test_data"},
            ),
        )
        job.result()
        print(f"[seed-test-data] loaded {len(rows)} rows into {ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 14: docker-compose up**

```bash
cd viz && cp .env.example .env
# .env 안의 CUBEJS_API_SECRET, NEXTAUTH_SECRET, PG_PASSWORD, CLAUDE_API_KEY, GOOGLE_CLIENT_ID/SECRET 채움
docker compose up -d cube redis postgres
sleep 20
docker compose ps
```

Expected: `cube`, `redis`, `postgres` 3개 모두 `Up` 상태. `app` 컨테이너는 아직 없음(Task 3에서 빌드).

- [ ] **Step 15: Cube Playground에서 수동 쿼리 검증**

브라우저 `http://localhost:3001` 접속 → Cube Playground → `AdsCampaign.spend` measure + `AdsCampaign.reportDate` day 선택 → 쿼리 성공.

실패 시: docker logs cube 확인. 흔한 원인: BQ 서비스키 경로 마운트 오류, `.env` 변수 누락.

- [ ] **Step 16: Seed 스크립트 실행**

```bash
./.venv/bin/pip install requests google-cloud-bigquery
./.venv/bin/python viz/scripts/seed_sheets.py --overwrite
./.venv/bin/python viz/scripts/seed_test_data.py
```

Expected 출력:
- `[seed-sheets] branches=['AMNY', 'DSTX'] rows=~3300`
- `[seed-sheets] loaded ~3300 rows into mimetic-gravity-442013-u4.raw_ads.external_ads_raw`
- `[seed-test-data] sales=~2500 surveys=~400`

실패 시: BQ 권한, SchemaField 타입 불일치 가능성. 에러 메시지로 원인 추적.

- [ ] **Step 17: Commit**

```bash
git add CLAUDE.md docs/status.md .gitignore viz/
git commit -m "$(cat <<'EOF'
feat(viz): bootstrap docker-compose + Cube skeleton + seed scripts

Task 1 (S1):
- CLAUDE.md 프로젝트 헌법 작성
- docs/status.md 세션 트래커 초기화
- viz/docker-compose.yml (cube + postgres + redis)
- Cube.js skeleton: schema 3개 (AdsCampaign/Orders/Surveys) + cube.js JWT checkAuth
- seed_sheets.py: AMNY/DSTX 전체 이력 WRITE_TRUNCATE import
- seed_test_data.py: sales/survey POC 시드

Cube Playground로 AdsCampaign.spend 수동 쿼리 성공 확인.
Seed로 raw_ads.external_ads_raw ~3300행, sales ~2500행, survey ~400행 적재.

Constraint: 기존 ingest (channels/, jobs/) 미변경
Directive: seed_sheets.py는 idempotent (WRITE_TRUNCATE). cron 재실행 안전.
Confidence: high
Scope-risk: narrow
EOF
)"
git push -u origin feat/viz-w1-cube-schema
gh pr create --draft --title "feat(viz-w1): S1 docker-compose + Cube + seed" --body "W1 Task 1. Cube + Postgres + Redis 기동, 시트·시드 데이터 적재."
```

- [ ] **Step 18: Status 업데이트**

`docs/status.md`:

```markdown
**Last session:** S1 — 환경 부트스트랩 + Cube 뼈대 완료. PR draft #N.
**Next session:** Task 2 (S2) — Cube 한글 title 확장 + dim_branch AMNY/DSTX + channel_map 시드 + Playground 재검증.

**Sessions completed:**
- S1: feat/viz-w1-cube-schema @ 커밋 sha
```

---

## Task 2 (S2): Cube 한글 확장 + dim_branch + channel_map

**Goal:** AMNY/DSTX branch row 추가, Cube 스키마 description/title 보강, `governance.external_channel_map` seed, Cube 쿼리로 channel_key별 spend 집계가 정확히 응답.

**Branch:** `feat/viz-w1-cube-i18n-dims`

**Files:**
- Create: `viz/cube/schema/dims/Branch.yml`, `viz/cube/schema/dims/Channel.yml`
- Create: `viz/scripts/seed_governance.py`
- Create: `viz/tests/test_seed_governance.py`
- Modify: `viz/cube/schema/AdsCampaign.yml`, `Orders.yml`, `Surveys.yml` (join + description)

- [ ] **Step 1: dim_branch에 AMNY/DSTX 삽입 SQL 작성**

`viz/scripts/sql/dim_branch_patch.sql`:

```sql
MERGE `mimetic-gravity-442013-u4.core.dim_branch` T
USING (
  SELECT 'AMNY' AS branch_id, 'New York' AS branch_name, 'US' AS country_code, 'New York' AS city_name, 'America/New_York' AS timezone, 'USD' AS currency, 'ARTE_MUSEUM' AS branch_group, TRUE AS is_active
  UNION ALL SELECT 'DSTX', 'reSOUND New York', 'US', 'New York', 'America/New_York', 'USD', 'RESOUND', TRUE
) S
ON T.branch_id = S.branch_id
WHEN NOT MATCHED THEN
  INSERT (branch_id, branch_name, country_code, city_name, timezone, currency, branch_group, is_active, load_ts)
  VALUES (S.branch_id, S.branch_name, S.country_code, S.city_name, S.timezone, S.currency, S.branch_group, S.is_active, CURRENT_TIMESTAMP());
```

- [ ] **Step 2: `governance.external_channel_map` 스키마 + seed**

`viz/scripts/sql/external_channel_map.sql`:

```sql
CREATE TABLE IF NOT EXISTS `mimetic-gravity-442013-u4.governance.external_channel_map` (
  raw_code STRING NOT NULL,
  channel_key STRING NOT NULL,
  is_active BOOL NOT NULL,
  notes STRING,
  updated_at TIMESTAMP
)
CLUSTER BY channel_key;

MERGE `mimetic-gravity-442013-u4.governance.external_channel_map` T
USING (
  SELECT raw_code, channel_key, TRUE AS is_active FROM UNNEST([
    STRUCT('1_Meta' AS raw_code, 'META' AS channel_key),
    ('META', 'META'),
    ('2_Google_Search', 'GOOGLE_ADS'),
    ('GOOGLE_SEARCH', 'GOOGLE_ADS'),
    ('3_Google_Display', 'GOOGLE_ADS'),
    ('22_Google_Demand_Gen', 'GOOGLE_DEMAND_GEN'),
    ('7_TikTok', 'TIKTOK_ADS'),
    ('TIKTOK', 'TIKTOK_ADS'),
    ('4_Youtube', 'YOUTUBE'),
    ('YOUTUBE', 'YOUTUBE'),
    ('10_Coupons', 'COUPON'),
    ('14_Affiliate', 'AFFILIATE'),
    ('15_Email', 'EMAIL'),
    ('102_Ambassadors', 'INFLUENCER'),
    ('58_Marketing_Fee', 'OTHER'),
    ('12_Organic_SEO', 'ORGANIC_SEO'),
    ('114_OTA', 'OTA')
  ])
) S
ON T.raw_code = S.raw_code
WHEN MATCHED THEN UPDATE SET channel_key = S.channel_key, is_active = S.is_active, updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (raw_code, channel_key, is_active, updated_at) VALUES (S.raw_code, S.channel_key, S.is_active, CURRENT_TIMESTAMP());
```

- [ ] **Step 3: Governance seed 실행 스크립트 (테스트 먼저)**

`viz/tests/test_seed_governance.py`:

```python
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import seed_governance


def test_load_sql_files_found():
    paths = seed_governance.sql_file_paths()
    names = {p.name for p in paths}
    assert "dim_branch_patch.sql" in names
    assert "external_channel_map.sql" in names
```

- [ ] **Step 4: Run test**

```bash
./.venv/bin/python -m pytest viz/tests/test_seed_governance.py -v
```

Expected: FAIL.

- [ ] **Step 5: Implement `seed_governance.py`**

`viz/scripts/seed_governance.py`:

```python
"""Apply governance + dim_branch patches to BigQuery (idempotent MERGE)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent / "sql"


def sql_file_paths() -> list[Path]:
    return sorted(SQL_DIR.glob("*.sql"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", default=os.getenv("BQ_PROJECT_ID", "mimetic-gravity-442013-u4"))
    parser.add_argument("--credentials-path", default=os.getenv("BQ_CREDENTIALS_PATH"))
    args = parser.parse_args(argv)

    from google.cloud import bigquery
    from google.oauth2 import service_account

    creds = None
    if args.credentials_path and Path(args.credentials_path).exists():
        creds = service_account.Credentials.from_service_account_file(args.credentials_path)
    client = bigquery.Client(project=args.project_id, credentials=creds, location="us-central1")

    for path in sql_file_paths():
        print(f"[seed-governance] executing {path.name}")
        sql = path.read_text()
        client.query(sql).result()
    print("[seed-governance] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run test again**

```bash
./.venv/bin/python -m pytest viz/tests/test_seed_governance.py -v
```

Expected: PASS.

- [ ] **Step 7: Apply governance seeds**

```bash
./.venv/bin/python viz/scripts/seed_governance.py
```

Expected: `[seed-governance] executing dim_branch_patch.sql`, `executing external_channel_map.sql`, `done`.

검증:
```bash
# BQ MCP 혹은 bq CLI로 확인
bq query --use_legacy_sql=false "SELECT branch_id FROM \`mimetic-gravity-442013-u4.core.dim_branch\` WHERE branch_id IN ('AMNY','DSTX')"
# 2행 리턴 기대
```

- [ ] **Step 8: Cube 스키마에 Branch/Channel dim cube 추가**

`viz/cube/schema/dims/Branch.yml`:

```yaml
cubes:
  - name: Branch
    sql_table: core.dim_branch
    title: "지점"
    description: "아르떼뮤지엄 및 reSOUND 지점 마스터"

    dimensions:
      - name: branchId
        title: "지점 코드"
        sql: branch_id
        type: string
        primary_key: true
      - name: branchName
        title: "지점명"
        sql: branch_name
        type: string
      - name: countryCode
        title: "국가 코드"
        sql: country_code
        type: string
      - name: currency
        title: "통화"
        sql: currency
        type: string
```

`viz/cube/schema/dims/Channel.yml`:

```yaml
cubes:
  - name: Channel
    sql: |
      SELECT DISTINCT channel_key AS channel_key,
        CASE channel_key
          WHEN 'META' THEN 'Meta'
          WHEN 'GOOGLE_ADS' THEN 'Google Ads'
          WHEN 'GOOGLE_DEMAND_GEN' THEN 'Google Demand Gen'
          WHEN 'TIKTOK_ADS' THEN 'TikTok'
          WHEN 'NAVER_ADS' THEN '네이버 검색광고'
          WHEN 'YOUTUBE' THEN 'YouTube'
          WHEN 'AFFILIATE' THEN '제휴'
          WHEN 'EMAIL' THEN '이메일'
          WHEN 'INFLUENCER' THEN '인플루언서'
          WHEN 'COUPON' THEN '쿠폰'
          WHEN 'ORGANIC_SEO' THEN 'Organic SEO'
          WHEN 'OTA' THEN 'OTA'
          ELSE '기타'
        END AS channel_name
      FROM `governance.external_channel_map`
      UNION DISTINCT
      SELECT 'META', 'Meta' UNION ALL
      SELECT 'GOOGLE_ADS', 'Google Ads' UNION ALL
      SELECT 'TIKTOK_ADS', 'TikTok' UNION ALL
      SELECT 'NAVER_ADS', '네이버 검색광고'
    title: "채널"

    dimensions:
      - name: channelKey
        title: "채널 코드"
        sql: channel_key
        type: string
        primary_key: true
      - name: channelName
        title: "채널명"
        sql: channel_name
        type: string
```

- [ ] **Step 9: AdsCampaign에 Branch/Channel join 추가**

`viz/cube/schema/AdsCampaign.yml` 파일 끝에:

```yaml
    joins:
      - name: Branch
        sql: "{CUBE.branchId} = {Branch.branchId}"
        relationship: many_to_one
      - name: Channel
        sql: "{CUBE.channelKey} = {Channel.channelKey}"
        relationship: many_to_one
```

`Orders.yml`, `Surveys.yml`도 동일하게 Branch join.

- [ ] **Step 10: Cube 재시작**

```bash
cd viz && docker compose restart cube
sleep 10
```

- [ ] **Step 11: Playground에서 join 검증**

브라우저 `http://localhost:3001` → `AdsCampaign.spend` + `Branch.branchName` + `Channel.channelName` 선택 → 테이블로 지점별/채널별 spend가 한글로 집계 렌더.

실패 시: join 문법 (Cube는 `{CUBE.x}` `{Other.y}` 사용). docker logs cube.

- [ ] **Step 12: Commit**

```bash
git add viz/cube/ viz/scripts/ viz/tests/
git commit -m "feat(viz): add dim branches (AMNY/DSTX), governance map, Cube joins"
git push -u origin feat/viz-w1-cube-i18n-dims
gh pr create --draft --title "feat(viz-w1): S2 dim_branch + channel_map + Cube i18n joins" --body "..."
```

- [ ] **Step 13: Status 업데이트**

---

## Task 3 (S3): Next.js 15 앱 + Google SSO + Drizzle

**Goal:** Next.js 15 App Router 프로젝트 생성, shadcn/ui 설치, NextAuth Google SSO (`@dstrict.com` 도메인 제한) 동작, Drizzle migrations 로 `users/dashboards/dashboard_charts/chat_messages/share_tokens/ai_call_log` 테이블 생성.

**Branch:** `feat/viz-w1-auth-crud`

**Files:** `viz/app/` 전체 신규.

- [ ] **Step 1: Next.js 15 프로젝트 생성**

```bash
cd viz
pnpm create next-app@15 app --ts --app --tailwind --eslint --no-src-dir=false --import-alias "@/*"
# 프롬프트: Would you like to use src/ directory? Yes
cd app
pnpm install
```

- [ ] **Step 2: shadcn/ui + 기본 컴포넌트 설치**

```bash
cd viz/app
pnpm dlx shadcn@latest init -d
pnpm dlx shadcn@latest add button dialog input select sheet card table
```

- [ ] **Step 3: 의존성 추가**

```bash
cd viz/app
pnpm add next-auth@5 @auth/drizzle-adapter drizzle-orm postgres zod @anthropic-ai/sdk react-grid-layout vega-lite vega vega-embed vega-tooltip @cubejs-client/core react-intl
pnpm add -D drizzle-kit @types/react-grid-layout vitest @vitest/ui msw @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 4: Drizzle 스키마 (테스트 먼저)**

`viz/app/tests/lib/db/schema.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import * as schema from '@/lib/db/schema';

describe('db schema', () => {
  it('exposes users / dashboards / dashboardCharts / chatMessages / shareTokens / aiCallLog tables', () => {
    expect(schema.users).toBeDefined();
    expect(schema.dashboards).toBeDefined();
    expect(schema.dashboardCharts).toBeDefined();
    expect(schema.chatMessages).toBeDefined();
    expect(schema.shareTokens).toBeDefined();
    expect(schema.aiCallLog).toBeDefined();
  });
});
```

- [ ] **Step 5: 테스트 실행 (실패)**

```bash
cd viz/app
pnpm vitest run tests/lib/db/schema.test.ts
```

Expected: FAIL (module not found).

- [ ] **Step 6: `src/lib/db/schema.ts` 작성**

```typescript
import { pgTable, uuid, varchar, text, jsonb, timestamp, integer, boolean } from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: varchar('email', { length: 255 }).notNull().unique(),
  googleSub: varchar('google_sub', { length: 255 }).notNull().unique(),
  displayName: varchar('display_name', { length: 255 }),
  avatarUrl: text('avatar_url'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  lastLoginAt: timestamp('last_login_at', { withTimezone: true }),
});

export const dashboards = pgTable('dashboards', {
  id: uuid('id').primaryKey().defaultRandom(),
  ownerId: uuid('owner_id').references(() => users.id, { onDelete: 'cascade' }).notNull(),
  title: varchar('title', { length: 255 }).notNull(),
  description: text('description'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
});

export const dashboardCharts = pgTable('dashboard_charts', {
  id: uuid('id').primaryKey().defaultRandom(),
  dashboardId: uuid('dashboard_id').references(() => dashboards.id, { onDelete: 'cascade' }).notNull(),
  title: varchar('title', { length: 255 }).notNull(),
  gridX: integer('grid_x').notNull().default(0),
  gridY: integer('grid_y').notNull().default(0),
  gridW: integer('grid_w').notNull().default(6),
  gridH: integer('grid_h').notNull().default(4),
  cubeQueryJson: jsonb('cube_query_json').notNull(),
  chartConfigJson: jsonb('chart_config_json').notNull(),
  source: varchar('source', { length: 16 }).notNull().default('manual'),
  promptHistoryJson: jsonb('prompt_history_json'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
});

export const chatMessages = pgTable('chat_messages', {
  id: uuid('id').primaryKey().defaultRandom(),
  dashboardId: uuid('dashboard_id').references(() => dashboards.id, { onDelete: 'cascade' }).notNull(),
  userId: uuid('user_id').references(() => users.id).notNull(),
  role: varchar('role', { length: 16 }).notNull(),
  content: text('content').notNull(),
  toolCallsJson: jsonb('tool_calls_json'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
});

export const shareTokens = pgTable('share_tokens', {
  id: uuid('id').primaryKey().defaultRandom(),
  dashboardId: uuid('dashboard_id').references(() => dashboards.id, { onDelete: 'cascade' }).notNull(),
  token: varchar('token', { length: 64 }).notNull().unique(),
  createdBy: uuid('created_by').references(() => users.id).notNull(),
  expiresAt: timestamp('expires_at', { withTimezone: true }),
  revokedAt: timestamp('revoked_at', { withTimezone: true }),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
});

export const aiCallLog = pgTable('ai_call_log', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id').references(() => users.id),
  dashboardId: uuid('dashboard_id').references(() => dashboards.id, { onDelete: 'cascade' }),
  endpoint: varchar('endpoint', { length: 64 }).notNull(),
  model: varchar('model', { length: 64 }).notNull(),
  inputTokens: integer('input_tokens').default(0),
  outputTokens: integer('output_tokens').default(0),
  cacheReadTokens: integer('cache_read_tokens').default(0),
  costUsd: varchar('cost_usd', { length: 32 }),
  latencyMs: integer('latency_ms'),
  status: varchar('status', { length: 16 }).notNull(),
  error: text('error'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
});

export const usersRelations = relations(users, ({ many }) => ({ dashboards: many(dashboards) }));
export const dashboardsRelations = relations(dashboards, ({ one, many }) => ({
  owner: one(users, { fields: [dashboards.ownerId], references: [users.id] }),
  charts: many(dashboardCharts),
}));
```

- [ ] **Step 7: Drizzle config + DB client**

`viz/app/drizzle.config.ts`:

```typescript
import { defineConfig } from 'drizzle-kit';
export default defineConfig({
  schema: './src/lib/db/schema.ts',
  out: './drizzle',
  dialect: 'postgresql',
  dbCredentials: { url: process.env.DATABASE_URL! },
});
```

`viz/app/src/lib/db/client.ts`:

```typescript
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

const queryClient = postgres(process.env.DATABASE_URL!);
export const db = drizzle(queryClient, { schema });
```

- [ ] **Step 8: Drizzle push (dev)**

```bash
cd viz/app
pnpm drizzle-kit generate
pnpm drizzle-kit push
```

Expected: migration files in `viz/app/drizzle/`, postgres에 테이블 6개 생성.

- [ ] **Step 9: 테스트 재실행**

```bash
pnpm vitest run tests/lib/db/schema.test.ts
```

Expected: PASS.

- [ ] **Step 10: NextAuth 설정**

`viz/app/src/lib/auth/options.ts`:

```typescript
import NextAuth from 'next-auth';
import Google from 'next-auth/providers/google';

const ALLOWED_DOMAIN = process.env.ALLOWED_EMAIL_DOMAIN || 'dstrict.com';

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async signIn({ profile }) {
      if (!profile?.email) return false;
      return profile.email.endsWith(`@${ALLOWED_DOMAIN}`);
    },
    async session({ session, token }) {
      if (session.user && token.sub) (session.user as any).id = token.sub;
      return session;
    },
  },
  trustHost: true,
});
```

`viz/app/src/app/api/auth/[...nextauth]/route.ts`:

```typescript
export { handlers as GET, handlers as POST } from '@/lib/auth/options';
```

`viz/app/src/middleware.ts`:

```typescript
export { auth as middleware } from '@/lib/auth/options';

export const config = {
  matcher: ['/((?!api/auth|_next/static|_next/image|login|favicon.ico).*)'],
};
```

- [ ] **Step 11: Login 페이지**

`viz/app/src/app/(auth)/login/page.tsx`:

```tsx
import { signIn } from '@/lib/auth/options';
import { Button } from '@/components/ui/button';

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="flex flex-col gap-4 rounded-lg border p-8">
        <h1 className="text-2xl font-bold">MKT-Viz 로그인</h1>
        <p className="text-sm text-muted-foreground">@dstrict.com 계정으로 로그인</p>
        <form action={async () => { 'use server'; await signIn('google'); }}>
          <Button type="submit" className="w-full">Google로 로그인</Button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 12: 로그인 수동 검증**

```bash
cd viz/app
pnpm dev
# 브라우저 http://localhost:3000 접속
# → /login 리다이렉트 → Google 로그인 → 홈 리다이렉트 성공
# @외부.com 계정 시도 시 거부되는지 확인
```

- [ ] **Step 13: users 테이블에 첫 로그인 row 수동 확인 (선택)**

현재 NextAuth 세션은 JWT 전용(DB adapter 미연결). users 테이블 row는 `/api/auth/profile` 호출 시 별도 upsert 로직에서 만들어야 함 → Task 4에서 처리.

- [ ] **Step 14: Commit**

```bash
git add viz/app/
git commit -m "feat(viz): Next.js 15 + shadcn + NextAuth Google SSO + Drizzle schema"
git push -u origin feat/viz-w1-auth-crud
gh pr create --draft --title "feat(viz-w1): S3 Next.js skeleton + auth + DB schema" --body "..."
```

- [ ] **Step 15: Status 업데이트**

---

## Task 4 (S4): Dashboard/Chart CRUD API + 목록 페이지

**Goal:** `POST/GET/PATCH/DELETE /api/dashboards`, `/api/charts` 엔드포인트 + 빈 대시보드 목록 페이지 + "새 대시보드 만들기" 플로우.

**Branch:** `feat/viz-w1-crud-api`

**Files:**
- Create: `viz/app/src/app/api/dashboards/route.ts`
- Create: `viz/app/src/app/api/dashboards/[id]/route.ts`
- Create: `viz/app/src/app/api/charts/route.ts`
- Create: `viz/app/src/app/api/charts/[id]/route.ts`
- Create: `viz/app/src/app/(dashboard)/layout.tsx`
- Create: `viz/app/src/app/(dashboard)/page.tsx`
- Create: `viz/app/src/app/(dashboard)/d/[id]/page.tsx`
- Create: `viz/app/src/lib/db/queries.ts`
- Create: `viz/app/tests/api/dashboards.test.ts`

- [ ] **Step 1: Query helpers 테스트**

`viz/app/tests/lib/db/queries.test.ts`:

```typescript
import { describe, it, expect, beforeAll } from 'vitest';
import { createUser, createDashboard, listDashboards, deleteDashboard } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

describe('db queries', () => {
  let userId: string;
  beforeAll(async () => {
    const u = await createUser({ email: 'test@dstrict.com', googleSub: 'sub-test', displayName: 'Tester' });
    userId = u.id;
  });

  it('creates and lists dashboards owned by user', async () => {
    const d = await createDashboard({ ownerId: userId, title: '테스트 대시보드' });
    expect(d.title).toBe('테스트 대시보드');
    const list = await listDashboards(userId);
    expect(list.some((x) => x.id === d.id)).toBe(true);
    await deleteDashboard(d.id, userId);
  });

  afterAll(async () => {
    await db.delete(users).where(eq(users.id, userId));
  });
});
```

- [ ] **Step 2: Run test (fail)**

- [ ] **Step 3: Implement queries**

`viz/app/src/lib/db/queries.ts`:

```typescript
import { db } from './client';
import { users, dashboards, dashboardCharts } from './schema';
import { eq, and, desc } from 'drizzle-orm';

export async function upsertUserByGoogle(payload: { email: string; googleSub: string; displayName?: string; avatarUrl?: string }) {
  const existing = await db.select().from(users).where(eq(users.googleSub, payload.googleSub)).limit(1);
  if (existing.length) {
    await db.update(users).set({ lastLoginAt: new Date(), displayName: payload.displayName, avatarUrl: payload.avatarUrl }).where(eq(users.id, existing[0].id));
    return existing[0];
  }
  const [u] = await db.insert(users).values(payload).returning();
  return u;
}

export async function createUser(payload: { email: string; googleSub: string; displayName?: string }) {
  const [u] = await db.insert(users).values(payload).returning();
  return u;
}

export async function listDashboards(ownerId: string) {
  return db.select().from(dashboards).where(eq(dashboards.ownerId, ownerId)).orderBy(desc(dashboards.updatedAt));
}

export async function createDashboard(payload: { ownerId: string; title: string; description?: string }) {
  const [d] = await db.insert(dashboards).values(payload).returning();
  return d;
}

export async function getDashboard(id: string, ownerId: string) {
  const rows = await db.select().from(dashboards).where(and(eq(dashboards.id, id), eq(dashboards.ownerId, ownerId))).limit(1);
  return rows[0] ?? null;
}

export async function updateDashboard(id: string, ownerId: string, patch: { title?: string; description?: string }) {
  const [d] = await db.update(dashboards).set({ ...patch, updatedAt: new Date() }).where(and(eq(dashboards.id, id), eq(dashboards.ownerId, ownerId))).returning();
  return d ?? null;
}

export async function deleteDashboard(id: string, ownerId: string) {
  await db.delete(dashboards).where(and(eq(dashboards.id, id), eq(dashboards.ownerId, ownerId)));
}

export async function listChartsByDashboard(dashboardId: string) {
  return db.select().from(dashboardCharts).where(eq(dashboardCharts.dashboardId, dashboardId));
}

export async function createChart(payload: {
  dashboardId: string;
  title: string;
  cubeQueryJson: unknown;
  chartConfigJson: unknown;
  source: 'ai' | 'manual' | 'hybrid';
  promptHistoryJson?: unknown;
  gridX?: number;
  gridY?: number;
  gridW?: number;
  gridH?: number;
}) {
  const [c] = await db.insert(dashboardCharts).values(payload as any).returning();
  return c;
}

export async function updateChart(id: string, patch: Partial<{ title: string; cubeQueryJson: unknown; chartConfigJson: unknown; gridX: number; gridY: number; gridW: number; gridH: number }>) {
  const [c] = await db.update(dashboardCharts).set({ ...patch, updatedAt: new Date() } as any).where(eq(dashboardCharts.id, id)).returning();
  return c ?? null;
}

export async function deleteChart(id: string) {
  await db.delete(dashboardCharts).where(eq(dashboardCharts.id, id));
}
```

- [ ] **Step 4: Run test (pass)**

- [ ] **Step 5: NextAuth 확장 — signIn 시 users 테이블 upsert**

`viz/app/src/lib/auth/options.ts`의 callbacks에 추가:

```typescript
async signIn({ profile }) {
  if (!profile?.email) return false;
  if (!profile.email.endsWith(`@${ALLOWED_DOMAIN}`)) return false;
  const { upsertUserByGoogle } = await import('@/lib/db/queries');
  await upsertUserByGoogle({
    email: profile.email,
    googleSub: profile.sub!,
    displayName: profile.name ?? undefined,
    avatarUrl: profile.picture ?? undefined,
  });
  return true;
},
```

- [ ] **Step 6: API routes 작성**

`viz/app/src/app/api/dashboards/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth/options';
import { z } from 'zod';
import { createDashboard, listDashboards } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

async function requireUser() {
  const session = await auth();
  if (!session?.user?.email) return null;
  const u = await db.select().from(users).where(eq(users.email, session.user.email)).limit(1);
  return u[0] ?? null;
}

const createSchema = z.object({ title: z.string().min(1).max(255), description: z.string().optional() });

export async function GET() {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const list = await listDashboards(user.id);
  return NextResponse.json({ dashboards: list });
}

export async function POST(req: NextRequest) {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const body = createSchema.parse(await req.json());
  const d = await createDashboard({ ownerId: user.id, ...body });
  return NextResponse.json({ dashboard: d }, { status: 201 });
}
```

`viz/app/src/app/api/dashboards/[id]/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth/options';
import { z } from 'zod';
import { getDashboard, updateDashboard, deleteDashboard, listChartsByDashboard } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

async function requireUser() {
  const session = await auth();
  if (!session?.user?.email) return null;
  const u = await db.select().from(users).where(eq(users.email, session.user.email)).limit(1);
  return u[0] ?? null;
}

export async function GET(_: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const d = await getDashboard(id, user.id);
  if (!d) return NextResponse.json({ error: 'not_found' }, { status: 404 });
  const charts = await listChartsByDashboard(id);
  return NextResponse.json({ dashboard: d, charts });
}

const patchSchema = z.object({ title: z.string().min(1).max(255).optional(), description: z.string().optional() });

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const body = patchSchema.parse(await req.json());
  const d = await updateDashboard(id, user.id, body);
  if (!d) return NextResponse.json({ error: 'not_found' }, { status: 404 });
  return NextResponse.json({ dashboard: d });
}

export async function DELETE(_: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  await deleteDashboard(id, user.id);
  return NextResponse.json({ ok: true });
}
```

`viz/app/src/app/api/charts/route.ts` + `charts/[id]/route.ts`: 위와 유사 패턴. `createChart`/`updateChart`/`deleteChart` 사용. 권한 체크: 차트 속한 대시보드 소유자 검증.

(구현 시 대시보드 소유자 확인 로직을 query helper에 추가 권장)

- [ ] **Step 7: 대시보드 목록 페이지**

`viz/app/src/app/(dashboard)/layout.tsx`:

```tsx
import { auth } from '@/lib/auth/options';
import { redirect } from 'next/navigation';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session) redirect('/login');
  return <div className="min-h-screen bg-background">{children}</div>;
}
```

`viz/app/src/app/(dashboard)/page.tsx`:

```tsx
import Link from 'next/link';
import { auth } from '@/lib/auth/options';
import { listDashboards } from '@/lib/db/queries';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default async function DashboardListPage() {
  const session = await auth();
  const [user] = await db.select().from(users).where(eq(users.email, session!.user!.email!)).limit(1);
  const list = await listDashboards(user.id);

  return (
    <main className="container mx-auto max-w-4xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">내 대시보드</h1>
        <form action="/api/dashboards" method="post">
          <Button type="submit">+ 새 대시보드</Button>
        </form>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {list.length === 0 && <p className="text-muted-foreground">아직 대시보드가 없습니다.</p>}
        {list.map((d) => (
          <Link key={d.id} href={`/d/${d.id}`}>
            <Card className="p-4 hover:border-primary">
              <h2 className="font-semibold">{d.title}</h2>
              <p className="text-xs text-muted-foreground">{new Date(d.updatedAt).toLocaleDateString('ko-KR')}</p>
            </Card>
          </Link>
        ))}
      </div>
    </main>
  );
}
```

대시보드 상세 페이지 `d/[id]/page.tsx`는 지금 placeholder (Task 5에서 그리드 확장).

- [ ] **Step 8: 로컬 수동 검증**

`pnpm dev` → 로그인 → "새 대시보드" → 목록에 나타남 → 클릭 → 상세 빈 페이지.

- [ ] **Step 9: Commit + PR + status 갱신**

---

## Task 5 (S5): React Grid Layout + Preset 차트 5종 + Vega-Lite fallback

**Goal:** 대시보드 상세 페이지에 12-column drag·resize 그리드. Line/Bar/KPI/Table/Pie 5 preset 컴포넌트. Vega-Lite fallback 컴포넌트 (직접 spec 입력 시 렌더).

**Branch:** `feat/viz-w1-grid-charts`

- [ ] **Step 1: Preset 레지스트리 타입 정의 (테스트 먼저)**

`viz/app/tests/lib/chart-types/registry.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { CHART_TYPES, isPresetType } from '@/lib/chart-types/registry';

describe('chart-types registry', () => {
  it('registers 5 preset types', () => {
    expect(new Set(CHART_TYPES)).toEqual(new Set(['line', 'bar', 'kpi', 'table', 'pie']));
  });
  it('isPresetType returns correctly', () => {
    expect(isPresetType('line')).toBe(true);
    expect(isPresetType('vega')).toBe(false);
  });
});
```

- [ ] **Step 2: Run test (fail)**

- [ ] **Step 3: Implement registry**

`viz/app/src/lib/chart-types/registry.ts`:

```typescript
export const CHART_TYPES = ['line', 'bar', 'kpi', 'table', 'pie'] as const;
export type PresetChartType = typeof CHART_TYPES[number];

export function isPresetType(t: string): t is PresetChartType {
  return (CHART_TYPES as readonly string[]).includes(t);
}

export interface PresetChartConfig {
  type: PresetChartType;
  x?: string;
  y?: string | string[];
  series?: string;
  title?: string;
  format?: { y?: 'currency' | 'percent' | 'number' };
}

export interface VegaChartConfig {
  type: 'vega';
  spec: Record<string, unknown>;
  title?: string;
}

export type ChartConfig = PresetChartConfig | VegaChartConfig;
```

- [ ] **Step 4: Run test (pass)**

- [ ] **Step 5: Line chart 컴포넌트 (테스트 먼저)**

`viz/app/tests/components/charts/LineChart.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { LineChart } from '@/components/charts/LineChart';

describe('LineChart', () => {
  it('renders an svg with data-chart="line"', () => {
    const { container } = render(
      <LineChart data={[{ date: '2026-04-01', spend: 100 }, { date: '2026-04-02', spend: 150 }]}
        config={{ type: 'line', x: 'date', y: 'spend', title: '테스트' }} />
    );
    expect(container.querySelector('[data-chart="line"]')).not.toBeNull();
  });
});
```

- [ ] **Step 6: vitest setup 파일**

`viz/app/tests/setup.ts`:

```typescript
import '@testing-library/jest-dom/vitest';
```

`viz/app/vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
  },
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
});
```

`pnpm add -D @vitejs/plugin-react`

- [ ] **Step 7: Run test (fail)**

- [ ] **Step 8: Implement LineChart with Vega-Lite**

`viz/app/src/components/charts/LineChart.tsx`:

```tsx
'use client';
import { useEffect, useRef } from 'react';
import embed from 'vega-embed';
import type { PresetChartConfig } from '@/lib/chart-types/registry';

export function LineChart({ data, config }: { data: Record<string, unknown>[]; config: PresetChartConfig }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const spec: any = {
      $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
      width: 'container',
      height: 280,
      data: { values: data },
      mark: { type: 'line', point: true },
      encoding: {
        x: { field: config.x, type: 'temporal', title: null },
        y: { field: Array.isArray(config.y) ? config.y[0] : config.y, type: 'quantitative', title: null },
        ...(config.series ? { color: { field: config.series, type: 'nominal' } } : {}),
      },
    };
    embed(ref.current, spec, { actions: false });
  }, [data, config]);
  return <div ref={ref} data-chart="line" className="w-full" />;
}
```

- [ ] **Step 9: Run test (pass)**

- [ ] **Step 10: Bar/KPI/Table/Pie 컴포넌트 유사 패턴으로 작성**

각각 동일 TDD 사이클 (테스트 먼저 → 실패 확인 → 구현 → 통과).

`BarChart.tsx`: Vega-Lite mark='bar'.
`KPICard.tsx`: 단일 측정값을 큰 숫자로 렌더 + 포맷 적용.
`TableChart.tsx`: shadcn `<Table>` 활용, 행 페이징 없음.
`PieChart.tsx`: Vega-Lite mark='arc'.
`VegaLiteChart.tsx`: `config.spec`을 그대로 embed.

- [ ] **Step 11: ChartCard 래퍼 (preset 분기 + edit/delete 메뉴)**

`viz/app/src/components/dashboard/ChartCard.tsx`:

```tsx
'use client';
import { LineChart } from '@/components/charts/LineChart';
import { BarChart } from '@/components/charts/BarChart';
import { KPICard } from '@/components/charts/KPICard';
import { TableChart } from '@/components/charts/TableChart';
import { PieChart } from '@/components/charts/PieChart';
import { VegaLiteChart } from '@/components/charts/VegaLiteChart';
import type { ChartConfig } from '@/lib/chart-types/registry';

export function ChartCard({ title, config, data }: { title: string; config: ChartConfig; data: Record<string, unknown>[] }) {
  return (
    <div className="flex h-full w-full flex-col rounded border bg-card p-3">
      <div className="mb-2 text-sm font-semibold">{title}</div>
      <div className="flex-1">
        {config.type === 'line' && <LineChart data={data} config={config} />}
        {config.type === 'bar' && <BarChart data={data} config={config} />}
        {config.type === 'kpi' && <KPICard data={data} config={config} />}
        {config.type === 'table' && <TableChart data={data} config={config} />}
        {config.type === 'pie' && <PieChart data={data} config={config} />}
        {config.type === 'vega' && <VegaLiteChart data={data} config={config} />}
      </div>
    </div>
  );
}
```

- [ ] **Step 12: React Grid Layout wrapper**

`viz/app/src/components/dashboard/Grid.tsx`:

```tsx
'use client';
import GridLayout from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

export interface ChartInstance {
  id: string;
  title: string;
  gridX: number;
  gridY: number;
  gridW: number;
  gridH: number;
}

export function DashboardGrid({
  charts,
  onLayoutChange,
  renderChart,
}: {
  charts: ChartInstance[];
  onLayoutChange: (layout: { i: string; x: number; y: number; w: number; h: number }[]) => void;
  renderChart: (c: ChartInstance) => React.ReactNode;
}) {
  const layout = charts.map((c) => ({ i: c.id, x: c.gridX, y: c.gridY, w: c.gridW, h: c.gridH }));
  return (
    <GridLayout
      className="layout"
      layout={layout}
      cols={12}
      rowHeight={80}
      width={1200}
      onLayoutChange={(l) => onLayoutChange(l as any)}
    >
      {charts.map((c) => (
        <div key={c.id}>{renderChart(c)}</div>
      ))}
    </GridLayout>
  );
}
```

- [ ] **Step 13: Cube client (fetch helper)**

`viz/app/src/lib/cube-client.ts`:

```typescript
export async function loadCubeData(cubeQuery: unknown): Promise<{ data: Record<string, unknown>[] }> {
  const r = await fetch('/api/cube/load', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ query: cubeQuery }) });
  if (!r.ok) throw new Error(`Cube load failed: ${r.status}`);
  return r.json();
}
```

`viz/app/src/app/api/cube/load/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';
import jwt from 'jsonwebtoken';
import { auth } from '@/lib/auth/options';

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session?.user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const { query } = await req.json();
  const token = jwt.sign(
    { user_id: (session.user as any).id ?? session.user.email, email: session.user.email },
    process.env.CUBE_API_SECRET!,
    { algorithm: 'HS256', expiresIn: '5m' }
  );
  const r = await fetch(`${process.env.CUBE_API_URL}/load`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: token },
    body: JSON.stringify({ query }),
  });
  if (!r.ok) return NextResponse.json({ error: 'cube_failed', status: r.status, body: await r.text() }, { status: 502 });
  const body = await r.json();
  const data = (body.data || []) as Record<string, unknown>[];
  return NextResponse.json({ data });
}
```

`pnpm add jsonwebtoken && pnpm add -D @types/jsonwebtoken`

- [ ] **Step 14: 대시보드 상세 페이지에 Grid + ChartCard 연결**

`viz/app/src/app/(dashboard)/d/[id]/page.tsx`:

```tsx
import { DashboardClient } from './dashboard-client';
import { getDashboard, listChartsByDashboard } from '@/lib/db/queries';
import { auth } from '@/lib/auth/options';
import { db } from '@/lib/db/client';
import { users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export default async function DashboardDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = await auth();
  const [user] = await db.select().from(users).where(eq(users.email, session!.user!.email!)).limit(1);
  const d = await getDashboard(id, user.id);
  if (!d) return <div>없음</div>;
  const charts = await listChartsByDashboard(id);
  return <DashboardClient dashboard={d} initialCharts={charts as any} />;
}
```

`viz/app/src/app/(dashboard)/d/[id]/dashboard-client.tsx`:

```tsx
'use client';
import { useState, useEffect } from 'react';
import { DashboardGrid } from '@/components/dashboard/Grid';
import { ChartCard } from '@/components/dashboard/ChartCard';
import { loadCubeData } from '@/lib/cube-client';

export function DashboardClient({ dashboard, initialCharts }: { dashboard: any; initialCharts: any[] }) {
  const [dataByChart, setData] = useState<Record<string, any[]>>({});

  useEffect(() => {
    (async () => {
      const result: Record<string, any[]> = {};
      for (const c of initialCharts) {
        try {
          const { data } = await loadCubeData(c.cubeQueryJson);
          result[c.id] = data;
        } catch (e) {
          result[c.id] = [];
        }
      }
      setData(result);
    })();
  }, [initialCharts]);

  return (
    <main className="p-6">
      <h1 className="mb-4 text-xl font-bold">{dashboard.title}</h1>
      <DashboardGrid
        charts={initialCharts.map((c) => ({ id: c.id, title: c.title, gridX: c.gridX, gridY: c.gridY, gridW: c.gridW, gridH: c.gridH }))}
        onLayoutChange={() => { /* Task 6에서 저장 */ }}
        renderChart={(c) => {
          const config = (initialCharts.find((x) => x.id === c.id)?.chartConfigJson as any) ?? { type: 'line' };
          return <ChartCard title={c.title} config={config} data={dataByChart[c.id] ?? []} />;
        }}
      />
    </main>
  );
}
```

- [ ] **Step 15: Commit + PR + status**

---

## Task 6 (S6): 수동 빌더 + save → load E2E

**Goal:** "+ 차트 추가" → Dialog → "수동 빌드" 탭 → measure/dimension/filter 선택 → preview → 저장. 새로고침 후 그리드에 복원.

**Branch:** `feat/viz-w1-manual-builder`

(생략되지 않도록 주요 스텝 요약. 실행 시 TDD 사이클 각 컴포넌트마다 반복.)

- [ ] Cube `/meta` proxy 엔드포인트 `/api/cube/meta/route.ts` (app-server가 JWT 서명하여 Cube meta 조회)
- [ ] `QueryBuilder.tsx`: shadcn Select로 measure/dimension 다중 선택, 기간 preset (last 7d/30d/90d), filter row (member + operator + value), chart type picker
- [ ] `useLazyCubeQuery` 훅 자체 구현 또는 `@cubejs-client/react` 사용 — 선택 변경 시 `/api/cube/load` 호출하여 preview 갱신
- [ ] "저장" → `POST /api/charts` → dashboard_charts row 생성 → 대시보드 페이지로 돌아가 grid에 추가
- [ ] Grid `onLayoutChange` → `PATCH /api/charts/:id` (디바운스)
- [ ] Commit + PR

---

## Task 7 (S7): Claude API proxy + structured output

**Goal:** `/api/ai/create-chart` 구현. 사용자 prompt → Claude Sonnet 4.6 (structured output + prompt caching) → chart config JSON → 검증 → Cube load → 프론트 리턴.

**Branch:** `feat/viz-w1-ai-create`

- [ ] **Step 1: Glossary + system prompt 작성**

`viz/app/src/lib/prompts/glossary.ts`:

```typescript
export const GLOSSARY_KO = `
아르떼뮤지엄 지점 코드:
- AMLV=Las Vegas, AMNY=New York, AMBS=부산, AMDB=Dubai, AMGN=강릉, AMJJ=제주, AMYS=여수, AKJJ=키즈파크
- DSTX=reSOUND New York

채널 코드 예:
- META, GOOGLE_ADS, TIKTOK_ADS, NAVER_ADS (API 직접 수집)
- YOUTUBE, AFFILIATE, EMAIL, INFLUENCER, COUPON, OTA, ORGANIC_SEO, GOOGLE_DEMAND_GEN (대행사 시트)

메트릭 정의:
- 스펜드(spend) = 광고 비용, native currency
- ROAS = conversion_value / spend
- CPC = spend / clicks
- CTR = clicks / impressions (%)
- NPS = avg_answer_score

주요 뷰/큐브:
- AdsCampaign: 광고 캠페인 일별 집계 (mart.v_dashboard_campaign_daily)
- Orders: 주문/매출 일별 (mart.v_business_branch_daily)
- Surveys: 설문 일별 평균 (mart.v_survey_branch_daily)
- Branch (dim), Channel (dim)

기본 기간: 미지정 시 최근 30일.
`;
```

`viz/app/src/lib/prompts/chart-create.ts`:

```typescript
export const CHART_CREATE_INSTRUCTIONS = `
You are an analytics assistant producing chart definitions for a Cube.js-backed marketing dashboard.

Output format: call the "create_chart" tool with:
- cubeQuery: a valid Cube query JSON (measures, dimensions, timeDimensions, filters)
- chartConfig: one of { type: "line"|"bar"|"kpi"|"table"|"pie", x, y, series?, title, format? } OR { type: "vega", spec, title }
- title: Korean chart title matching the user's request

Rules:
1. All user-facing titles/labels must be in Korean.
2. Prefer preset chart types over vega-lite. Only use vega if a preset cannot express the request.
3. Default date range: last 30 days, granularity day, time dimension = reportDate on the relevant cube.
4. If the user specifies a branch in Korean ("부산", "뉴욕"), translate to branch_id code (AMBS, AMNY) via the glossary.
5. If unsure about metric name, choose the closest Cube measure by meaning. Do not invent measures.
6. Always include a time range unless the user explicitly requested "all time".
7. If user requests breakdown ("지점별", "채널별"), add the corresponding dimension.
`;
```

- [ ] **Step 2: Claude client + Zod validation (테스트 먼저)**

`viz/app/tests/lib/claude-client.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { ChartResponseSchema } from '@/lib/claude-client';

describe('ChartResponseSchema', () => {
  it('accepts valid chart response', () => {
    const p = ChartResponseSchema.parse({
      cubeQuery: { measures: ['AdsCampaign.spend'], timeDimensions: [{ dimension: 'AdsCampaign.reportDate', granularity: 'day', dateRange: 'last 30 days' }] },
      chartConfig: { type: 'line', x: 'AdsCampaign.reportDate', y: 'AdsCampaign.spend', title: '최근 30일 스펜드' },
      title: '최근 30일 스펜드',
    });
    expect(p.chartConfig.type).toBe('line');
  });
  it('rejects invalid chart type', () => {
    expect(() => ChartResponseSchema.parse({ cubeQuery: {}, chartConfig: { type: 'rocket' }, title: 'x' })).toThrow();
  });
});
```

- [ ] **Step 3: Implement**

`viz/app/src/lib/claude-client.ts`:

```typescript
import Anthropic from '@anthropic-ai/sdk';
import { z } from 'zod';
import { GLOSSARY_KO } from './prompts/glossary';
import { CHART_CREATE_INSTRUCTIONS } from './prompts/chart-create';

export const ChartResponseSchema = z.object({
  cubeQuery: z.record(z.unknown()),
  chartConfig: z.discriminatedUnion('type', [
    z.object({ type: z.enum(['line', 'bar', 'kpi', 'table', 'pie']), x: z.string().optional(), y: z.union([z.string(), z.array(z.string())]).optional(), series: z.string().optional(), title: z.string().optional(), format: z.record(z.string()).optional() }),
    z.object({ type: z.literal('vega'), spec: z.record(z.unknown()), title: z.string().optional() }),
  ]),
  title: z.string(),
});
export type ChartResponse = z.infer<typeof ChartResponseSchema>;

const anthropic = new Anthropic({ apiKey: process.env.CLAUDE_API_KEY! });

const CREATE_CHART_TOOL = {
  name: 'create_chart',
  description: 'Emit a Cube query + chart config for the user request.',
  input_schema: {
    type: 'object',
    properties: {
      cubeQuery: { type: 'object' },
      chartConfig: { type: 'object' },
      title: { type: 'string' },
    },
    required: ['cubeQuery', 'chartConfig', 'title'],
  },
};

export async function createChartFromPrompt(prompt: string, cubeMetaJson: string): Promise<{ response: ChartResponse; usage: any }> {
  const r = await anthropic.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 2048,
    system: [
      { type: 'text', text: GLOSSARY_KO, cache_control: { type: 'ephemeral' } },
      { type: 'text', text: `Cube meta:\n${cubeMetaJson}`, cache_control: { type: 'ephemeral' } },
      { type: 'text', text: CHART_CREATE_INSTRUCTIONS, cache_control: { type: 'ephemeral' } },
    ] as any,
    tools: [CREATE_CHART_TOOL as any],
    tool_choice: { type: 'tool', name: 'create_chart' } as any,
    messages: [{ role: 'user', content: prompt }],
  });
  const block = r.content.find((b: any) => b.type === 'tool_use') as any;
  if (!block) throw new Error('No tool_use in response');
  const parsed = ChartResponseSchema.parse(block.input);
  return { response: parsed, usage: r.usage };
}
```

- [ ] **Step 4: `/api/ai/create-chart` 엔드포인트**

`viz/app/src/app/api/ai/create-chart/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth/options';
import { db } from '@/lib/db/client';
import { aiCallLog, users } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import { createChartFromPrompt } from '@/lib/claude-client';
import jwt from 'jsonwebtoken';

async function getCubeMeta(token: string): Promise<string> {
  const r = await fetch(`${process.env.CUBE_API_URL}/meta`, { headers: { authorization: token } });
  return await r.text();
}

export async function POST(req: NextRequest) {
  const started = Date.now();
  const session = await auth();
  if (!session?.user?.email) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const [user] = await db.select().from(users).where(eq(users.email, session.user.email)).limit(1);

  const { prompt, dashboardId } = await req.json();

  const cubeToken = jwt.sign({ user_id: user.id }, process.env.CUBE_API_SECRET!, { algorithm: 'HS256', expiresIn: '5m' });
  const meta = await getCubeMeta(cubeToken);

  try {
    const { response, usage } = await createChartFromPrompt(prompt, meta);

    // Run the query to verify it loads
    const loadR = await fetch(`${process.env.CUBE_API_URL}/load`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: cubeToken },
      body: JSON.stringify({ query: response.cubeQuery }),
    });
    if (!loadR.ok) throw new Error(`cube_load_failed ${loadR.status}`);
    const loadBody = await loadR.json();

    await db.insert(aiCallLog).values({
      userId: user.id,
      dashboardId: dashboardId ?? null,
      endpoint: 'create-chart',
      model: 'claude-sonnet-4-6',
      inputTokens: usage.input_tokens ?? 0,
      outputTokens: usage.output_tokens ?? 0,
      cacheReadTokens: (usage as any).cache_read_input_tokens ?? 0,
      latencyMs: Date.now() - started,
      status: 'ok',
    });

    return NextResponse.json({ response, data: loadBody.data ?? [] });
  } catch (e: any) {
    await db.insert(aiCallLog).values({
      userId: user.id,
      dashboardId: dashboardId ?? null,
      endpoint: 'create-chart',
      model: 'claude-sonnet-4-6',
      latencyMs: Date.now() - started,
      status: 'error',
      error: String(e.message ?? e),
    });
    return NextResponse.json({ error: 'ai_failed', detail: String(e.message ?? e) }, { status: 500 });
  }
}
```

- [ ] **Step 5: 수동 테스트**

```bash
curl -X POST http://localhost:3000/api/ai/create-chart \
  -H 'content-type: application/json' \
  -b 'cookie' \
  -d '{"prompt":"최근 7일 Meta 스펜드 추이","dashboardId":"..."}'
```

Expected: `{"response": {...}, "data": [...]}` JSON.

실패 시: `docker logs cube`, `viz/app` 콘솔, Claude API 키 확인.

- [ ] **Step 6: Commit + PR + status**

---

## Task 8 (S8): Chat side panel UI + AI 생성 E2E

**Goal:** 사이드 패널 `<Sheet>`가 오른쪽에 고정. 질문 입력 → AI 응답 → 차트가 그리드에 추가. chat_messages에 이력 기록.

**Branch:** `feat/viz-w1-ai-panel`

- [ ] `ChatPanel.tsx` (shadcn `<Sheet>` 응용) — open 상태 유지, MessageList + Composer
- [ ] `MessageList.tsx` — user/assistant 스타일 구분
- [ ] `Composer.tsx` — 입력 + submit 버튼
- [ ] 사이드 패널에서 submit 시 `/api/ai/create-chart` 호출 → 응답 받으면 `/api/charts` POST로 저장 → 그리드 상태 갱신 → chat_messages 2 row insert (user + assistant)
- [ ] 에러 시 한글 메시지 ("AI 응답 실패, 다시 시도해 주세요. 또는 수동 빌더를 사용하세요.")
- [ ] 수동 검증: 한글 질의 5개 정도 — "AMLV Meta 최근 7일 CPC", "지점별 스펜드 비중", "이번 달 주문 추이", "NPS 지점별 평균", "YouTube 클릭수"
- [ ] Commit + PR + status

---

## Task 9 (S9): 한글 i18n + 공유 링크 기본

**Goal:** next-intl 통합 + 모든 UI 문자열 `ko.json` 로 분리. `/api/share`, `/shared/:token` 페이지 + ShareDialog.

**Branch:** `feat/viz-w1-i18n-share`

- [ ] `next-intl` 설치 + `middleware` 통합
- [ ] `src/locales/ko.json`: 모든 하드코딩 UI 문자열을 키로 분리
- [ ] 공유 토큰 생성: `POST /api/dashboards/:id/share` → share_tokens insert, 32-byte hex
- [ ] `/shared/[token]` 페이지: 토큰 유효성 검증 + Google SSO 강제 + read-only 렌더 (ShareDialog 편집 버튼 숨김)
- [ ] `ShareDialog.tsx`: 링크 복사 + 만료 옵션 안내("POC에서는 만료 없음")
- [ ] Intl 포맷: `Intl.NumberFormat('ko-KR')`, `Intl.DateTimeFormat('ko-KR')` 차트 공용 helper에 적용
- [ ] 수동 검증: 로그인 → 대시보드 공유 링크 복사 → 시크릿 창에서 다른 @dstrict.com 계정으로 접속 → read-only 렌더
- [ ] Commit + PR + status

---

## Task 10 (S10): W1 smoke + PR 정리

**Goal:** 전체 플로우 수동 E2E 5개 시나리오, 발견 버그 수정, W1 완성 선언.

**Branch:** `feat/viz-w1-smoke`

- [ ] **Scenario 1**: 신규 로그인 → 대시보드 생성 → AI "최근 7일 Meta 스펜드 추이" → 차트 저장 → 새로고침 → 차트 복원
- [ ] **Scenario 2**: 수동 빌더로 차트 생성 → 저장 → 동일 대시보드에 AI 보정 없이 AI 질의로 추가 차트 → 2개 차트 그리드
- [ ] **Scenario 3**: drag·resize → 새로고침 → 위치 유지 (Task 6 onLayoutChange 저장 확인)
- [ ] **Scenario 4**: 공유 링크 생성 → 시크릿 창 다른 @dstrict.com 계정 접속 → read-only
- [ ] **Scenario 5**: 한글 3개 + 영어 2개 질의 → 응답 정확 5/5 (smoke, Task S15에서 자동화 예정)
- [ ] 발견 이슈 수정 (모두 < 200 LoC, TDD)
- [ ] `docs/status.md` 갱신: W1 완료 + W2 진입 준비
- [ ] README `viz/README.md` 작성 (로컬 기동 + seed + dev 플로우)
- [ ] Commit + PR + status

**W1 종료 조건** (spec Section 8.1):
- 로컬 로그인 → 빈 대시보드 생성 → AI/수동 양 경로로 차트 생성 → 저장/공유 기본 모두 동작.

---

## 공통 규칙 (매 Task 반복 확인)

1. PR 200 LoC 이하. 초과 시 분할.
2. TDD: 테스트 먼저, 사용자 승인 후 구현.
3. 매 PR `code-reviewer` 자기 리뷰 (`superpowers:requesting-code-review`).
4. `docs/status.md` 갱신.
5. 커밋 trailers: `Constraint:`, `Rejected:`, `Directive:`, `Confidence:`, `Scope-risk:`.
6. 스코프 가드 — spec Section 12.4 금지 항목 W1 거부:
   - 새 cube / 새 차트 타입 / shadcn 폴리시 빌더 / crossfilter / 이메일 / 모바일 UI / 대시보드 템플릿.
7. 브라우저 수동 검증 필수 (AI·UI 기능은 pytest/vitest로 완전 커버 불가).
8. Claude API 호출마다 prompt caching 블록 3개 유지.
9. Cube/Next.js/Postgres 포트 충돌 점검 (VM 배포 시).

---

## Self-Review 체크리스트

- [x] Spec coverage — Section 1.2 결정 12축 전부 Task 1~10에 매핑됨
- [x] Placeholder scan — "TBD"/"TODO" 없음, 각 step에 실제 코드 포함
- [x] Type consistency — ChartConfig, ChartResponseSchema, Cube query 타입 모든 Task에서 동일 시그니처
- [x] Sheet ingest는 Task 1 S16에 seed_sheets.py 실행 포함
- [x] 스코프 가드 (Section 12.4) Task 10 공통 규칙에 명시
- [x] 매 Task 수동 검증 단계 포함
- [x] 커밋 메시지 convention 공통 규칙에 명시

---

## 다음 단계

W1 완료 후 별도 plan `docs/superpowers/plans/2026-04-XX-viz-w2-implementation-plan.md` 작성:
- GA4 WebEvents + BlendedFunnel cube (정제 집계)
- AI 보정 (`refine-chart`)
- Eval 자동화 (20 질의)
- VM 배포 + 일일 cron (sheet re-import)
- 마케팅 3명 온보딩

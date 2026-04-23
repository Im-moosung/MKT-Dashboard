# MKT-Viz

AI 대시보드 POC — 마케팅 데이터를 Cube.js로 집계하고 Claude AI로 차트를 생성·저장하는 로컬 MVP.

## 사전 조건

| 도구 | 버전 |
|------|------|
| Docker Desktop | 최신 (linux/amd64 Rosetta 지원 필수, Apple Silicon) |
| Node.js | 20+ |
| pnpm | 9+ (`npm i -g pnpm`) |
| Python venv | `/Users/moo/MKT-Dashboard/.venv` (기존 공용) |
| BQ 서비스 키 | `secrets/common/service_key.json` |
| ADC (Application Default Credentials) | `gcloud auth application-default login` |

> Google OAuth client 및 Anthropic API 키 미발급 상태. 로컬 개발은 `MOCK_AUTH=true` + `MOCK_CLAUDE=true` 경로를 사용.

## 로컬 기동 순서

### 1. 환경 변수 준비

```bash
cd viz/app
# .env 파일이 없으면 아래 내용으로 새로 생성
touch .env
```

`.env` 필수 항목 (전체 작성):

```env
# DB
DATABASE_URL=postgres://app:devpass@localhost:5432/mkt_viz
PG_DB=mkt_viz
PG_USER=app
PG_PASSWORD=devpass

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=<openssl rand -base64 32>

# Google OAuth (미발급 시 mock 사용)
GOOGLE_CLIENT_ID=mock-client-id
GOOGLE_CLIENT_SECRET=mock-client-secret
ALLOWED_EMAIL_DOMAIN=dstrict.com

# 개발용 mock 플래그
MOCK_AUTH=true
MOCK_CLAUDE=true

# Cube.js
CUBE_API_URL=http://localhost:4000/cubejs-api/v1
CUBEJS_API_SECRET=<openssl rand -base64 32>

# Claude (MOCK_CLAUDE=false 시 필요)
# CLAUDE_API_KEY=sk-ant-...
```

### 2. Docker 서비스 기동

```bash
cd viz
docker compose up -d cube redis postgres
```

서비스 확인:
```bash
docker compose ps
# cube, postgres, redis 모두 Up 이어야 함
```

### 3. Python 의존성 설치 (필요 시)

```bash
# 레포 루트에서
./.venv/bin/pip install requests google-cloud-bigquery
```

### 4. 시드 데이터 적재

```bash
# 레포 루트에서 실행
./.venv/bin/python viz/scripts/seed_sheets.py --overwrite
./.venv/bin/python viz/scripts/seed_test_data.py
./.venv/bin/python viz/scripts/seed_governance.py
```

### 5. Next.js 앱 설치 및 DB 마이그레이션

```bash
cd viz/app
pnpm install
pnpm drizzle-kit push
```

### 6. 개발 서버 기동

```bash
cd viz/app
pnpm dev
```

브라우저: `http://localhost:3000`

- Mock 이메일(`you@dstrict.com`)로 로그인
- 새 대시보드 생성
- AI 사이드 패널 또는 수동 빌더로 차트 추가
- 저장 후 새로고침 → 차트 복원 확인

## 디렉토리 구조

```
viz/
├── app/                    # Next.js 15 앱
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/login/       # Mock + Google 로그인 페이지
│   │   │   ├── (dashboard)/
│   │   │   │   ├── page.tsx        # 대시보드 목록 (루트 /)
│   │   │   │   ├── d/[id]/         # 개별 대시보드
│   │   │   │   └── shared/[token]/ # read-only 공유 뷰
│   │   │   └── api/
│   │   │       ├── ai/create-chart/  # Claude 차트 생성 프록시
│   │   │       ├── auth/             # NextAuth
│   │   │       ├── charts/           # 차트 CRUD
│   │   │       ├── cube/             # Cube.js meta/load 프록시
│   │   │       └── dashboards/       # 대시보드 CRUD + chat + share
│   │   ├── components/
│   │   │   ├── ai-panel/       # ChatPanel + MessageList + Composer
│   │   │   ├── builder/        # QueryBuilder (수동 차트 빌더)
│   │   │   ├── charts/         # Bar/Line/Area/Scatter/KPI + Vega-Lite
│   │   │   └── dashboard/      # DashboardGrid (react-grid-layout)
│   │   ├── lib/
│   │   │   ├── auth/           # NextAuth options + mock provider
│   │   │   ├── claude-client.ts # Anthropic SDK wrapper (MOCK_CLAUDE 분기)
│   │   │   └── db/             # Drizzle schema + queries + client
│   │   └── locales/ko.json     # 한국어 next-intl 번역
│   ├── drizzle/               # 마이그레이션 파일
│   ├── tests/                 # vitest 테스트
│   └── .env                   # 로컬 환경 변수 (git 제외)
├── cube/                   # Cube.js 설정 + BQ 스키마 YAML
├── postgres/               # init.sql
├── scripts/                # Python seed 스크립트
│   ├── seed_sheets.py      # BQ → raw_ads
│   ├── seed_test_data.py   # 테스트용 sales/surveys 데이터
│   └── seed_governance.py  # dim_branch + channel_map
├── tests/
│   └── eval/
│       └── w1-smoke-scenarios.md  # W1 smoke 시나리오 체크리스트
└── docker-compose.yml
```

## 주요 명령어

```bash
# 개발 서버
cd viz/app && pnpm dev

# 프로덕션 빌드 (타입 체크 포함)
cd viz/app && pnpm build

# 단위 테스트
cd viz/app && pnpm vitest run

# Python 테스트
./.venv/bin/python -m pytest viz/tests/ -v

# DB 스키마 push (Drizzle)
cd viz/app && pnpm drizzle-kit push

# Docker 서비스 재시작
cd viz && docker compose restart cube

# Docker 로그 확인
cd viz && docker compose logs -f cube
```

## 현재 제약사항

| 항목 | 상태 | 해결 방법 |
|------|------|-----------|
| Google OAuth 미발급 | MOCK_AUTH=true (Mock 로그인 사용) | GCP Console에서 OAuth client 발급 후 .env 교체 |
| Anthropic API 키 미발급 | MOCK_CLAUDE=true (고정 [MOCK] Line chart 반환) | Anthropic console에서 API 키 발급 후 CLAUDE_API_KEY 설정 |
| Cube ARM64 네이티브 미지원 | platform: linux/amd64 (Rosetta) | Cube 공식 ARM 이미지 출시 대기 |
| BQ 서비스 키 | secrets/common/service_key.json 필요 | ADC 또는 서비스 계정 키 파일 배치 |

## W1 smoke 시나리오

`viz/tests/eval/w1-smoke-scenarios.md` 참조. MOCK_AUTH=true + MOCK_CLAUDE=true 환경에서 5개 시나리오 수동 브라우저 검증.

> `.env.example`: viz/app/.gitignore에 `.env*` 전체 제외 규칙이 있으므로 git 미추적. 위 env 템플릿을 참고해 직접 작성.

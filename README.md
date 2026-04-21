# New_Data_flow

`New_Data_flow`는 **raw 적재 전용 파이프라인**입니다.

- 역할: 외부 API/원천 데이터 -> `raw_*` 테이블 적재
- 범위: 정규화/모델링(`stg`, `core`, `mart`)은 포함하지 않음
- 후속: raw 적재 후 `ops.sp_load_all`(warehouse) 호출

## 현재 상태

- 공통 모듈(`common/`): 설정, 로깅, 날짜 범위 계산
- 채널 인터페이스(`channels/base.py`) 및 레지스트리(`channels/registry.py`)
- 광고 채널 어댑터 구현
  - `meta_ads`, `google_ads`, `tiktok_ads`, `naver_ads`
  - V1 canonical grain은 `ad daily`이며, 요약용 `campaign daily` mart를 함께 운영
  - breakdown은 메인 KPI 경로에서 분리하고 최근 30일 + 핵심 축만 유지
- 엔트리 CLI(`jobs/ingest_raw.py`)
  - 기존 `--channel` 실행 지원
  - `ops.ingest_source_config` 기반 source 실행 지원

## V1 운영 원칙 (2026-03-06)

- 자격증명은 V1 동안 `.env` 우선입니다. Secret Manager는 선택 기능으로만 남기고 기본 운영 경로에서는 사용하지 않습니다.
- 광고 성과는 `ad daily`를 유지합니다. 메인 대시보드/AI 기본 질의는 `campaign daily`와 `ad daily` mart를 사용합니다.
- breakdown은 상세 분석 전용입니다.
  - 최근 30일만 유지
  - Meta: `age`, `gender`, `country`, `region`
  - Google: `age`, `gender`, `geo_target_country`, `geo_target_region`
  - TikTok/Naver breakdown은 V1 범위에서 제외
- Naver Ads는 V1 paid media 본선에 포함합니다. 범위는 `performance + creative + ad/campaign mart`까지입니다.
- 글로벌 금액은 V1에서 native currency 기준으로만 운영합니다. cross-currency 총합 KPI는 기본 화면에 노출하지 않습니다.
- 메인 dashboard/AI 표준 mart
  - `mart.v_dashboard_branch_channel_daily`
  - `mart.v_dashboard_campaign_daily`
  - `mart.v_dashboard_ad_daily`
  - breakdown view는 기본 질의 레이어에서 제외

## 환경 설정

```bash
cd /path/to/data_flow

# 가상환경 생성(최초 1회)
python3 -m venv .venv

# 의존성 설치
./.venv/bin/pip install -r requirements.txt
```

- 모든 기본 경로는 저장소 루트 기준 상대경로로 해석됩니다.
- 기본 secrets 경로:
  - `secrets/meta_ads/.env`
  - `secrets/google_ads/.env`
  - `secrets/tiktok_ads/.env`
  - `secrets/naver_ads/.env`
  - `secrets/common/service_key.json`
- 다른 위치를 쓰려면 환경변수로 override 가능합니다.
  - 공통 BigQuery 키: `NEW_DATA_FLOW_BQ_CREDENTIALS_PATH`
  - 채널별 `.env`: `NEW_DATA_FLOW_META_ADS_ENV_FILE`, `NEW_DATA_FLOW_GOOGLE_ADS_ENV_FILE`, `NEW_DATA_FLOW_TIKTOK_ADS_ENV_FILE`, `NEW_DATA_FLOW_NAVER_ADS_ENV_FILE`

### 자격증명 fallback 정책

- 각 채널 `providers.*`는 V1 동안 `.env` 또는 OS env를 기준으로 동작합니다.
- `allow_env_fallback = true`는 유지하되, V1 표준 운영 경로는 `providers.*.env_file`입니다.
- `secret_ref`는 선택 기능이며, Secret Manager 패키지가 없어도 CLI와 테스트는 동작하도록 유지합니다.

```toml
[providers.meta_ads]
allow_env_fallback = true
```

### BigQuery 서비스키 정책 (공용)

- 이 프로젝트는 채널별 키 분리 대신 BigQuery 서비스키 1개를 공용으로 사용합니다.
- 기본 경로: `secrets/common/service_key.json`
- `config/dev.toml`, `config/prod.toml`의 `providers.*.bq_credentials_path`는 모두 위 상대경로를 참조합니다.

### 채널 실패 정책 (통일)

- 계정 단위 API 실패: `error` 로그 후 다음 계정으로 계속 진행
- 광고/소재/브레이크다운 하위 호출 실패: `warning` 로그 후 해당 항목만 스킵
- 인증정보 누락/초기화 실패: 즉시 `raise`
- 전 계정 실패 시: 채널 실행을 실패 처리(`raise`)하여 오케스트레이터에서 감지

## Secret Manager 전환 (V1 범위 밖, 선택)

### 사전 조건

1. `secretmanager.googleapis.com` API 활성화
2. 실행 주체(로컬 계정 또는 VM 서비스계정)에 최소 권한 부여
   - Secret Manager: `roles/secretmanager.secretAccessor`, `roles/secretmanager.secretVersionAdder`, `roles/secretmanager.admin`(초기 생성 시)
   - BigQuery: `roles/bigquery.jobUser`, `roles/bigquery.dataEditor`

### 로컬에서 1개 소스 부트스트랩

```bash
cd /path/to/data_flow

# 1) .env 키 검증만 수행 (비밀 생성/수정 없음)
./.venv/bin/python -m jobs.bootstrap_secret_manager \
  --project-id your-gcp-project-id \
  --source-id VENUE01_META_01 \
  --secret-id ads-meta-venue01-01 \
  --env-file secrets/meta_ads/.env \
  --source-config-table ops.ingest_source_config \
  --dry-run

# 2) 실제 Secret 버전 추가 + source_config.secret_ref 반영
./.venv/bin/python -m jobs.bootstrap_secret_manager \
  --project-id your-gcp-project-id \
  --source-id VENUE01_META_01 \
  --secret-id ads-meta-venue01-01 \
  --env-file secrets/meta_ads/.env \
  --source-config-table ops.ingest_source_config
```

### VM 배포 시 권장 방식

1. VM에 서비스계정 연결 (키 파일 없이 ADC 사용)
2. 위와 동일한 `bootstrap_secret_manager` 명령을 VM에서 실행
3. 이후 `jobs/ingest_raw.py --use-source-config`로 실행하면 `secret_ref` 기준으로 자격증명을 조회
4. 로컬 `.env`는 운영 경로에서 제거

## 실행 예시

```bash
cd /path/to/data_flow

# 가상환경 사용 권장
./.venv/bin/python -m jobs.ingest_raw --env dev --channel meta_ads --refresh-mode daily --api-test-only --api-sample-size 1
./.venv/bin/python -m jobs.ingest_raw --env dev --channel meta_ads --refresh-mode custom --start-date 2026-02-12 --end-date 2026-02-13 --run-warehouse

# source config 기반 실행 (status=ACTIVE 소스 대상)
./.venv/bin/python -m jobs.ingest_raw --env prod --use-source-config --source-config-table ops.ingest_source_config --refresh-mode daily --run-warehouse
./.venv/bin/python -m jobs.ingest_raw --env prod --use-source-config --source-id VENUE01_META_01 --refresh-mode daily --run-warehouse

# 같은 날짜 범위가 이미 warehouse SUCCESS면 자동 스킵됨(기본)
# 강제로 다시 warehouse 실행하려면 아래 옵션 추가
./.venv/bin/python -m jobs.ingest_raw --env prod --use-source-config --refresh-mode daily --run-warehouse --force-warehouse-rerun

# post-warehouse 자동 훅
# - geo_target_map 동기화 (Google source 감지 시)
# - DQ 체크(geo breakdown Unknown 감시)
# 필요 시만 비활성화
./.venv/bin/python -m jobs.ingest_raw --env prod --use-source-config --refresh-mode daily --run-warehouse --skip-geo-sync --skip-dq-checks
```

### 일배치 스케줄 권장

- daily command는 아래 1줄을 스케줄러(cron/Cloud Scheduler)로 실행하면 됩니다.
- `ingest_raw --run-warehouse` 성공 후 `geo sync + DQ`가 자동으로 연동됩니다.

```bash
./.venv/bin/python -m jobs.ingest_raw --env prod --use-source-config --source-config-table ops.ingest_source_config --refresh-mode daily --run-warehouse
```

## BigQuery 비용 모니터링 (root job 기준)

수동 ad-hoc 쿼리 여러 개 대신 아래 스크립트 1회 실행을 권장합니다.

```bash
./.venv/bin/python -m jobs.report_bq_usage --env prod --include-us-region
```

- 기준: `parent_job_id IS NULL` (중복 집계 방지)
- 출력:
  - 사용자별 `billed_bytes` / `billed_gib`
  - 워크로드별(`sp_load_all`, `ad_hoc_select` 등) 사용량 상위
  - 1 TiB 무료 쿼리 대비 사용 비율

## Meta Campaign Breakdown 조회 예시

```sql
SELECT
  stat_date,
  account_id,
  campaign_id,
  campaign_name,
  breakdown_key,
  breakdown_value,
  SUM(spend) AS spend,
  SUM(clicks) AS clicks,
  SUM(impressions) AS impressions
FROM `your-gcp-project-id.raw_ads.meta_ads_campaign_breakdown_raw`
WHERE stat_date BETWEEN DATE('2026-02-01') AND DATE('2026-02-28')
  AND breakdown_key IN ('age', 'gender', 'country', 'region')
GROUP BY stat_date, account_id, campaign_id, campaign_name, breakdown_key, breakdown_value
ORDER BY stat_date DESC, campaign_id, breakdown_key, breakdown_value;
```

- V1에서는 Meta breakdown grain을 `campaign`으로 운영합니다.
- canonical raw 테이블명은 `raw_ads.meta_ads_campaign_breakdown_raw`입니다.

## Google Campaign Breakdown 조회 예시

```sql
SELECT
  stat_date,
  customer_id,
  campaign_id,
  campaign_name,
  breakdown_key,
  breakdown_value,
  SUM(impressions) AS impressions,
  SUM(clicks) AS clicks,
  SUM(cost_micros) / 1000000 AS spend,
  SUM(conversions) AS conversions,
  SUM(conversions_value) AS conversions_value
FROM `your-gcp-project-id.raw_ads.google_ads_campaign_breakdown_raw`
WHERE stat_date BETWEEN DATE('2026-02-01') AND DATE('2026-02-28')
  AND breakdown_key IN ('age_range', 'gender', 'geo_target_country', 'geo_target_region')
GROUP BY stat_date, customer_id, campaign_id, campaign_name, breakdown_key, breakdown_value
ORDER BY stat_date DESC, campaign_id, breakdown_key, impressions DESC;
```

- `geo_target_region` 운영 규칙:
  - 미국/캐나다/멕시코(`US/CA/MX`)는 region id(`geoTargetConstants/...`) 유지
  - 그 외 국가는 `others`로 버킷팅
- 표준화 규칙(warehouse):
  - Google `age_range`는 STG/CORE/MART에서 `age`로 표준화
  - `AGE_RANGE_18_24 -> 18-24`, `AGE_RANGE_65_UP -> 65+`, `AGE_RANGE_UNDETERMINED -> Unknown`
  - 미매핑 age 값은 `Unknown` 처리

## Geo ID 이름 매핑 (governance.geo_target_map)

- `geoTargetConstants/...` ID를 사람이 읽을 수 있는 이름으로 바꾸기 위해 `governance.geo_target_map` 테이블을 사용합니다.
- `mart.v_campaign_breakdown_recent`는 `breakdown_value_name` 컬럼을 제공하며, 대시보드는 이 컬럼 사용을 권장합니다.
- 한글 대시보드용으로 `display_name_ko` / `breakdown_value_name_ko` 컬럼이 추가되었습니다.

```bash
# Google geo target map 동기화 (권장: 배치 후 1회)
./.venv/bin/python -m jobs.sync_geo_target_map --env prod --source-id VENUE01_GOOGLE_ADS_01
```

## Breakdown 전용 STG/CORE/MART 경로

- `ops.sp_load_all` 실행 시 아래 경로가 함께 갱신됩니다.
  - `stg.ads_campaign_breakdown_daily`
  - `core.fact_marketing_campaign_breakdown_daily`
  - `mart.v_campaign_breakdown_recent`

```sql
SELECT
  report_date,
  branch_id,
  branch_name,
  channel_key,
  campaign_id,
  campaign_name,
  breakdown_key,
  breakdown_value,
  breakdown_value_name,
  breakdown_value_name_ko,
  impressions,
  clicks,
  spend_native,
  ctr,
  cpc
FROM `your-gcp-project-id.mart.v_campaign_breakdown_recent`
WHERE report_date BETWEEN DATE('2026-02-01') AND DATE('2026-02-28')
  AND branch_id = 'VENUE_01'
  AND channel_key = 'META'
  AND breakdown_key = 'age'
ORDER BY report_date DESC, campaign_id, spend_native DESC;
```

## DQ 체크 (Unknown geo name 알림)

- 체크명: `geo_breakdown_value_name_unknown`
- 조건: `mart.v_campaign_breakdown_recent`에서 geo breakdown(`geo_target_country`, `geo_target_region`)의 `breakdown_value_name = 'Unknown'`
- 결과 저장: `ops.dq_check_result`

```bash
./.venv/bin/python -m jobs.run_dq_checks --env prod --start-date 2026-02-19 --end-date 2026-02-20
```

- 주의: breakdown 테이블/뷰는 `breakdown_key` long-format입니다.
  - `breakdown_key` 조건 없이 합계를 내면 중복 합산됩니다.
  - V1에서는 campaign 단위 집계만 canonical breakdown 경로로 유지합니다.
  - breakdown 보관 기간은 최근 30일입니다.

## Google Ads Asset 성과 경로 (하이브리드: SEARCH 텍스트 + 비검색/PMax 이미지·영상)

- `ops.sp_load_all` 실행 시 아래 경로가 함께 갱신됩니다.
  - `raw_ads.google_ads_asset_performance_raw`
  - `stg.ads_asset_performance_daily`
  - `core.fact_marketing_asset_daily`
  - `mart.v_asset_performance_daily`

- 수집 규칙 (비용 최적화)
  - `SEARCH`: `HEADLINE`, `DESCRIPTION`만 수집
  - 비검색(non-search: `DEMAND_GEN`, `DISPLAY`, `VIDEO`)은 이미지/영상만 수집
    - `MARKETING_IMAGE`, `SQUARE_MARKETING_IMAGE`, `PORTRAIT_MARKETING_IMAGE`, `YOUTUBE_VIDEO`
  - `PERFORMANCE_MAX`: 이미지/영상만 수집
    - `MARKETING_IMAGE`, `SQUARE_MARKETING_IMAGE`, `PORTRAIT_MARKETING_IMAGE`, `YOUTUBE_VIDEO`
  - 즉, 비검색/PMax 텍스트 자산(`HEADLINE`, `DESCRIPTION`)은 의도적으로 제외
  - raw/stg/core에 `campaign_channel_type`을 함께 저장하여 조회 시 채널 타입 필터를 명시적으로 적용 가능
  - 분석 편의를 위해 `stg.ads_asset_performance_daily` / `core.fact_marketing_asset_daily` / `mart.v_asset_performance_daily`에 `campaign_channel_type` 컬럼 제공

```sql
SELECT
  stat_date,
  branch_id,
  channel_key,
  campaign_channel_type,
  is_pmax,
  field_type,
  asset_id,
  impressions,
  clicks,
  conversion_count,
  conversion_value,
  ctr,
  cpa
FROM `your-gcp-project-id.mart.v_asset_performance_daily`
WHERE stat_date BETWEEN DATE('2026-02-01') AND DATE('2026-02-28')
  AND branch_id = 'VENUE_01'
  AND channel_key = 'GOOGLE_ADS'
ORDER BY stat_date DESC, conversion_count DESC;
```

## Creative 자산 정책 (전 채널 공통, 2026-02-20 적용)

- 정책: 크리에이티브는 이미지/영상 자산 중심으로 운영
- 반영 내용:
  - `ops.sp_load_stg`에서 `stg.ads_creative_text` 적재 비활성화
  - `stg.ads_creative_snapshot` / `stg.ads_creative_asset`의 `valid_from_ts`를 `collected_date` 기준으로 고정(일자 단위 latest-only)
- 효과:
  - 같은 날짜 재실행 시 creative STG 행수 비정상 누적 방지
  - 텍스트 long-format 확장(`ads_creative_text`)으로 인한 행수 급증 방지
- 운영 조회 권장 경로:
  - `stg.ads_creative_asset`
  - `core.dim_creative_asset_scd2`
  - `core.fact_marketing_asset_daily`
  - `mart.v_asset_performance_daily`

## 다음 단계

1. 지점/채널별 `ops.ingest_source_config` 활성화(`status=ACTIVE`, `run_warehouse_after_ingest=TRUE`)
2. `governance.account_branch_map` 운영 매핑 확대(계정별 branch_id 필수)
3. DQ/알림(행수 급감, 지연, NULL 비율) 자동화

## STG TTL 정책 (2026-02-20 적용)

- 목적: STG 저장비 제어 + 운영 안정성 확보
- 적용 내용:
  - `stg` 데이터셋 `default_table_expiration_days` 제거
  - `stg` 데이터셋 `default_partition_expiration_days = 45` 적용
  - STG 파티션 테이블 전체에 `partition_expiration_days = 45` 적용
- 이유:
  - 기존 테이블 단위 2일 만료는 테이블 자체 삭제를 유발해 운영 리스크가 큼
  - 파티션 TTL은 최근 데이터만 유지하면서 테이블 구조는 안정적으로 유지 가능

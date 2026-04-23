-- V1 governance / ops metadata changes
-- Apply manually in BigQuery when promoting the V1 warehouse structure.

ALTER TABLE `your-gcp-project-id.ops.ingest_source_config`
ADD COLUMN IF NOT EXISTS credential_mode STRING;

UPDATE `your-gcp-project-id.ops.ingest_source_config`
SET credential_mode = 'ENV'
WHERE credential_mode IS NULL;

CREATE TABLE IF NOT EXISTS `your-gcp-project-id.governance.ga4_property_branch_map` (
  property_id STRING,
  branch_id STRING,
  effective_start_date DATE,
  effective_end_date DATE,
  is_active BOOL,
  mapping_source STRING,
  updated_at TIMESTAMP
)
CLUSTER BY property_id, branch_id;

CREATE TABLE IF NOT EXISTS `your-gcp-project-id.governance.fever_event_branch_map` (
  event_id STRING,
  venue_name STRING,
  branch_id STRING,
  effective_start_date DATE,
  effective_end_date DATE,
  is_active BOOL,
  mapping_source STRING,
  updated_at TIMESTAMP
)
CLUSTER BY event_id, venue_name, branch_id;

CREATE TABLE IF NOT EXISTS `your-gcp-project-id.governance.sales_source_branch_map` (
  source_system STRING,
  branch_id STRING,
  effective_start_date DATE,
  effective_end_date DATE,
  is_active BOOL,
  mapping_source STRING,
  updated_at TIMESTAMP
)
CLUSTER BY source_system, branch_id;

CREATE TABLE IF NOT EXISTS `your-gcp-project-id.governance.survey_source_branch_map` (
  survey_source STRING,
  survey_id STRING,
  branch_id STRING,
  effective_start_date DATE,
  effective_end_date DATE,
  is_active BOOL,
  mapping_source STRING,
  updated_at TIMESTAMP
)
CLUSTER BY survey_source, survey_id, branch_id;

CREATE TABLE IF NOT EXISTS `your-gcp-project-id.governance.naver_adgroup_branch_rule` (
  rule_id STRING,
  branch_id STRING,
  match_keyword STRING,
  priority INT64,
  is_active BOOL,
  notes STRING,
  updated_at TIMESTAMP
)
CLUSTER BY branch_id, priority, match_keyword;

MERGE `your-gcp-project-id.governance.naver_adgroup_branch_rule` t
USING (
  SELECT 'NAVER_VENUE02_KEYWORD_01' AS rule_id, 'VENUE_02' AS branch_id, 'kids park' AS match_keyword, 10 AS priority, TRUE AS is_active, 'venue02 keyword 01' AS notes, CURRENT_TIMESTAMP() AS updated_at
  UNION ALL SELECT 'NAVER_VENUE02_KEYWORD_02', 'VENUE_02', 'venue02 theme', 11, TRUE, 'venue02 keyword 02', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE02_KEYWORD_03', 'VENUE_02', 'kids', 12, TRUE, 'generic kids en', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE02_KEYWORD_04', 'VENUE_02', '키즈파크', 13, TRUE, 'venue02 keyword 04', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE01_KEYWORD_01', 'VENUE_01', 'las vegas', 20, TRUE, 'las vegas full', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE01_KEYWORD_02', 'VENUE_01', 'vegas', 21, TRUE, 'las vegas short', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE01_KEYWORD_03', 'VENUE_01', 'lv', 22, TRUE, 'las vegas abbreviation', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE03_KEYWORD_01', 'VENUE_03', 'dubai', 30, TRUE, 'dubai full', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE03_KEYWORD_02', 'VENUE_03', 'db', 31, TRUE, 'dubai abbreviation', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE04_KEYWORD_01', 'VENUE_04', '부산', 40, TRUE, 'busan ko', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE04_KEYWORD_02', 'VENUE_04', 'busan', 41, TRUE, 'busan en', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE04_KEYWORD_03', 'VENUE_04', 'bs', 42, TRUE, 'busan abbreviation', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE05_KEYWORD_01', 'VENUE_05', '강릉', 50, TRUE, 'gangneung ko', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE05_KEYWORD_02', 'VENUE_05', 'gangneung', 51, TRUE, 'gangneung en', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE05_KEYWORD_03', 'VENUE_05', 'gn', 52, TRUE, 'gangneung abbreviation', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE06_KEYWORD_01', 'VENUE_06', '여수', 60, TRUE, 'yeosu ko', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE06_KEYWORD_02', 'VENUE_06', 'yeosu', 61, TRUE, 'yeosu en', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE06_KEYWORD_03', 'VENUE_06', 'ys', 62, TRUE, 'yeosu abbreviation', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE07_KEYWORD_01', 'VENUE_07', '제주', 70, TRUE, 'jeju ko', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE07_KEYWORD_02', 'VENUE_07', 'jeju', 71, TRUE, 'jeju en', CURRENT_TIMESTAMP()
  UNION ALL SELECT 'NAVER_VENUE07_KEYWORD_03', 'VENUE_07', 'jj', 72, TRUE, 'jeju abbreviation', CURRENT_TIMESTAMP()
) s
ON t.rule_id = s.rule_id
WHEN MATCHED THEN UPDATE SET
  branch_id = s.branch_id,
  match_keyword = s.match_keyword,
  priority = s.priority,
  is_active = s.is_active,
  notes = s.notes,
  updated_at = s.updated_at
WHEN NOT MATCHED THEN INSERT (rule_id, branch_id, match_keyword, priority, is_active, notes, updated_at)
VALUES (s.rule_id, s.branch_id, s.match_keyword, s.priority, s.is_active, s.notes, s.updated_at);

CREATE OR REPLACE VIEW `your-gcp-project-id.ops.v_source_readiness` AS
SELECT
  s.source_id,
  s.branch_id,
  s.channel_key,
  s.provider_key,
  s.status,
  s.tier,
  s.priority,
  s.credential_mode,
  s.account_id_norm,
  s.secret_ref,
  s.run_warehouse_after_ingest,
  s.updated_at,
  s.account_id_norm IS NOT NULL AND TRIM(s.account_id_norm) != '' AS has_account_id,
  s.secret_ref IS NOT NULL AND TRIM(s.secret_ref) != '' AS has_secret_ref,
  CASE
    WHEN s.account_id_norm IS NULL OR TRIM(s.account_id_norm) = '' THEN 'MISSING_SETUP'
    WHEN s.channel_key = 'NAVER_ADS'
      AND NOT EXISTS (
        SELECT 1
        FROM `your-gcp-project-id.governance.naver_adgroup_branch_rule` r
        WHERE r.is_active = TRUE
      ) THEN 'MISSING_SETUP'
    WHEN UPPER(COALESCE(s.credential_mode, 'ENV')) = 'SECRET_MANAGER'
      AND (s.secret_ref IS NULL OR TRIM(s.secret_ref) = '') THEN 'MISSING_SETUP'
    WHEN s.status = 'ACTIVE' THEN 'ACTIVE_READY'
    WHEN s.status = 'PENDING_SETUP' THEN 'MISSING_SETUP'
    ELSE 'REVIEW'
  END AS readiness,
  CASE
    WHEN s.account_id_norm IS NULL OR TRIM(s.account_id_norm) = ''
      THEN 'set account_id_norm first'
    WHEN s.channel_key = 'NAVER_ADS'
      AND NOT EXISTS (
        SELECT 1
        FROM `your-gcp-project-id.governance.naver_adgroup_branch_rule` r
        WHERE r.is_active = TRUE
      )
      THEN 'seed naver_adgroup_branch_rule then API smoke test'
    WHEN UPPER(COALESCE(s.credential_mode, 'ENV')) = 'SECRET_MANAGER'
      AND (s.secret_ref IS NULL OR TRIM(s.secret_ref) = '')
      THEN 'set secret_ref or switch credential_mode to ENV'
    WHEN UPPER(COALESCE(s.credential_mode, 'ENV')) = 'ENV'
      THEN 'verify providers.*.env_file and API smoke test'
    ELSE 'review source setup'
  END AS notes
FROM `your-gcp-project-id.ops.ingest_source_config` s;

CREATE OR REPLACE VIEW `your-gcp-project-id.ops.v_source_activation_candidates` AS
SELECT
  s.source_id,
  s.branch_id,
  s.channel_key,
  s.provider_key,
  s.status,
  s.tier,
  s.priority,
  s.account_id_norm,
  s.secret_ref,
  s.credential_mode,
  s.run_warehouse_after_ingest,
  s.updated_at,
  s.account_id_norm IS NOT NULL AND TRIM(s.account_id_norm) != '' AS has_account_id,
  s.secret_ref IS NOT NULL AND TRIM(s.secret_ref) != '' AS has_secret_ref,
  CASE
    WHEN s.channel_key = 'NAVER_ADS' THEN EXISTS (
      SELECT 1
      FROM `your-gcp-project-id.governance.naver_adgroup_branch_rule` r
      WHERE r.is_active = TRUE
    )
    ELSE EXISTS (
      SELECT 1
      FROM `your-gcp-project-id.governance.account_branch_map` m
      WHERE m.channel_key = s.channel_key
        AND m.account_id_norm = s.account_id_norm
        AND m.is_active = TRUE
    )
  END AS has_active_mapping,
  CASE
    WHEN s.account_id_norm IS NULL OR TRIM(s.account_id_norm) = '' THEN 'MISSING_ACCOUNT_ID'
    WHEN UPPER(COALESCE(s.credential_mode, 'ENV')) = 'SECRET_MANAGER'
      AND (s.secret_ref IS NULL OR TRIM(s.secret_ref) = '') THEN 'MISSING_SECRET_REF'
    WHEN s.channel_key = 'NAVER_ADS'
      AND NOT EXISTS (
        SELECT 1
        FROM `your-gcp-project-id.governance.naver_adgroup_branch_rule` r
        WHERE r.is_active = TRUE
      ) THEN 'MISSING_BRANCH_RULE'
    WHEN s.channel_key != 'NAVER_ADS'
      AND NOT EXISTS (
        SELECT 1
        FROM `your-gcp-project-id.governance.account_branch_map` m
        WHERE m.channel_key = s.channel_key
          AND m.account_id_norm = s.account_id_norm
          AND m.is_active = TRUE
      ) THEN 'MISSING_BRANCH_MAPPING'
    ELSE NULL
  END AS activation_blocker
FROM `your-gcp-project-id.ops.ingest_source_config` s;

CREATE OR REPLACE VIEW `your-gcp-project-id.ops.v_naver_unknown_adgroups_recent` AS
WITH matched AS (
  SELECT
    r.stat_date,
    r.account_id,
    r.campaign_id,
    r.campaign_name,
    r.ad_group_id,
    r.ad_group_name,
    r.impressions,
    r.clicks,
    r.spend,
    ROW_NUMBER() OVER (
      PARTITION BY r.account_id, r.campaign_id, IFNULL(r.ad_group_id, ''), r.stat_date
      ORDER BY rule.priority ASC, LENGTH(rule.match_keyword) DESC, rule.updated_at DESC
    ) AS rule_rank,
    rule.rule_id
  FROM `your-gcp-project-id.raw_ads.naver_ads_performance_raw` r
  LEFT JOIN `your-gcp-project-id.governance.naver_adgroup_branch_rule` rule
    ON rule.is_active = TRUE
   AND STRPOS(LOWER(COALESCE(r.ad_group_name, '')), LOWER(rule.match_keyword)) > 0
  WHERE r.stat_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
)
SELECT
  stat_date,
  account_id,
  campaign_id,
  campaign_name,
  ad_group_id,
  ad_group_name,
  SUM(IFNULL(impressions, 0)) AS impressions,
  SUM(IFNULL(clicks, 0)) AS clicks,
  SUM(IFNULL(spend, 0)) AS spend
FROM matched
WHERE rule_rank = 1
  AND rule_id IS NULL
GROUP BY stat_date, account_id, campaign_id, campaign_name, ad_group_id, ad_group_name;

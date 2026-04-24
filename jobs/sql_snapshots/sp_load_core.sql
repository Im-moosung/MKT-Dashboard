BEGIN
  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.core.dim_channel` (
    channel_key STRING,
    channel_name STRING,
    platform_name STRING,
    is_paid_media BOOL,
    load_ts TIMESTAMP
  )
  CLUSTER BY channel_key;

  MERGE `your-gcp-project-id.core.dim_channel` t
  USING (
    SELECT 'META' AS channel_key, 'Meta Ads' AS channel_name, 'facebook_ads' AS platform_name, TRUE AS is_paid_media, CURRENT_TIMESTAMP() AS load_ts
    UNION ALL SELECT 'GOOGLE_ADS', 'Google Ads', 'google_ads', TRUE, CURRENT_TIMESTAMP()
    UNION ALL SELECT 'TIKTOK_ADS', 'TikTok Ads', 'tiktok_ads', TRUE, CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_ADS', 'Naver Ads', 'naver_ads', TRUE, CURRENT_TIMESTAMP()
    UNION ALL SELECT 'GA4', 'GA4', 'ga4', FALSE, CURRENT_TIMESTAMP()
    UNION ALL SELECT 'FEVER', 'Fever', 'fever', FALSE, CURRENT_TIMESTAMP()
    UNION ALL SELECT 'SALES', 'Sales', 'sales', FALSE, CURRENT_TIMESTAMP()
    UNION ALL SELECT 'SURVEY', 'Survey', 'survey', FALSE, CURRENT_TIMESTAMP()
  ) s
  ON t.channel_key = s.channel_key
  WHEN MATCHED THEN UPDATE SET
    channel_name = s.channel_name,
    platform_name = s.platform_name,
    is_paid_media = s.is_paid_media,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (channel_key, channel_name, platform_name, is_paid_media, load_ts)
  VALUES (s.channel_key, s.channel_name, s.platform_name, s.is_paid_media, s.load_ts);

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.governance.ga4_property_branch_map` (
    property_id STRING,
    branch_id STRING,
    effective_start_date DATE,
    effective_end_date DATE,
    is_active BOOL,
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
    updated_at TIMESTAMP
  )
  CLUSTER BY event_id, branch_id;

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.governance.sales_source_branch_map` (
    source_system STRING,
    branch_id STRING,
    effective_start_date DATE,
    effective_end_date DATE,
    is_active BOOL,
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
    SELECT 'NAVER_VENUE02_KIDS_PARK' AS rule_id, 'VENUE_02' AS branch_id, 'kids park' AS match_keyword, 10 AS priority, TRUE AS is_active, 'arte kids park en' AS notes, CURRENT_TIMESTAMP() AS updated_at
    UNION ALL SELECT 'NAVER_VENUE02_ARTE_KIDS', 'VENUE_02', 'arte kids', 11, TRUE, 'arte kids en', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE02_KIDS', 'VENUE_02', 'kids', 12, TRUE, 'generic kids en', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE02_KO', 'VENUE_02', '키즈파크', 13, TRUE, 'arte kids park ko', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE01_LAS_VEGAS', 'VENUE_01', 'las vegas', 20, TRUE, 'las vegas full', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE01_VEGAS', 'VENUE_01', 'vegas', 21, TRUE, 'las vegas short', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE01_LV', 'VENUE_01', 'lv', 22, TRUE, 'las vegas abbreviation', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE03_DUBAI', 'VENUE_03', 'dubai', 30, TRUE, 'dubai full', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE03_DB', 'VENUE_03', 'db', 31, TRUE, 'dubai abbreviation', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE04_KO', 'VENUE_04', '부산', 40, TRUE, 'busan ko', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE04_EN', 'VENUE_04', 'busan', 41, TRUE, 'busan en', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE04_BS', 'VENUE_04', 'bs', 42, TRUE, 'busan abbreviation', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE05_KO', 'VENUE_05', '강릉', 50, TRUE, 'gangneung ko', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE05_EN', 'VENUE_05', 'gangneung', 51, TRUE, 'gangneung en', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE05_GN', 'VENUE_05', 'gn', 52, TRUE, 'gangneung abbreviation', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE06_KO', 'VENUE_06', '여수', 60, TRUE, 'yeosu ko', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE06_EN', 'VENUE_06', 'yeosu', 61, TRUE, 'yeosu en', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE06_YS', 'VENUE_06', 'ys', 62, TRUE, 'yeosu abbreviation', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE07_KO', 'VENUE_07', '제주', 70, TRUE, 'jeju ko', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE07_EN', 'VENUE_07', 'jeju', 71, TRUE, 'jeju en', CURRENT_TIMESTAMP()
    UNION ALL SELECT 'NAVER_VENUE07_JJ', 'VENUE_07', 'jj', 72, TRUE, 'jeju abbreviation', CURRENT_TIMESTAMP()
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

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.core.fact_marketing_daily` (
    stat_date DATE,
    channel_key STRING,
    account_id_norm STRING,
    campaign_id STRING,
    ad_group_id STRING,
    ad_id STRING,
    impressions INT64,
    clicks INT64,
    spend NUMERIC,
    conversion_count FLOAT64,
    conversion_value NUMERIC,
    load_ts TIMESTAMP,
    branch_id STRING,
    currency_code STRING
  )
  PARTITION BY stat_date
  CLUSTER BY channel_key, account_id_norm, campaign_id, ad_id
  OPTIONS (require_partition_filter = TRUE);

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.core.fact_marketing_action_daily` (
    stat_date DATE,
    channel_key STRING,
    account_id_norm STRING,
    campaign_id STRING,
    ad_group_id STRING,
    ad_id STRING,
    action_type STRING,
    action_count FLOAT64,
    action_value NUMERIC,
    load_ts TIMESTAMP,
    branch_id STRING
  )
  PARTITION BY stat_date
  CLUSTER BY channel_key, account_id_norm, ad_id, action_type
  OPTIONS (require_partition_filter = TRUE);

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.core.fact_web_event_daily` (
    event_date DATE,
    property_id STRING,
    source STRING,
    medium STRING,
    campaign STRING,
    event_name STRING,
    users INT64,
    sessions INT64,
    event_count INT64,
    event_value NUMERIC,
    load_ts TIMESTAMP,
    branch_id STRING
  )
  PARTITION BY event_date
  CLUSTER BY property_id, source, medium, campaign
  OPTIONS (require_partition_filter = TRUE);

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.core.fact_order_line` (
    order_date DATE,
    order_ts TIMESTAMP,
    order_source STRING,
    source_system STRING,
    order_id STRING,
    order_line_id STRING,
    customer_key STRING,
    product_id STRING,
    venue_name STRING,
    quantity INT64,
    gross_amount NUMERIC,
    discount_amount NUMERIC,
    net_amount NUMERIC,
    currency STRING,
    payment_status STRING,
    load_ts TIMESTAMP,
    branch_id STRING
  )
  PARTITION BY order_date
  CLUSTER BY order_source, order_id, order_line_id
  OPTIONS (require_partition_filter = TRUE);

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.core.fact_survey_response` (
    response_date DATE,
    response_ts TIMESTAMP,
    survey_source STRING,
    response_id STRING,
    customer_key STRING,
    survey_id STRING,
    question_id STRING,
    answer_type STRING,
    answer_text STRING,
    answer_score FLOAT64,
    load_ts TIMESTAMP,
    branch_id STRING
  )
  PARTITION BY response_date
  CLUSTER BY survey_source, survey_id, question_id
  OPTIONS (require_partition_filter = TRUE);

  ALTER TABLE `your-gcp-project-id.core.fact_marketing_daily`
    ADD COLUMN IF NOT EXISTS branch_id STRING;
  ALTER TABLE `your-gcp-project-id.core.fact_marketing_daily`
    ADD COLUMN IF NOT EXISTS currency_code STRING;

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.core.fact_marketing_campaign_daily` (
    report_date DATE,
    branch_id STRING,
    channel_key STRING,
    account_id_norm STRING,
    campaign_id STRING,
    campaign_name STRING,
    currency_code STRING,
    impressions INT64,
    clicks INT64,
    spend_native NUMERIC,
    conversions FLOAT64,
    conversion_value_native NUMERIC,
    load_ts TIMESTAMP
  )
  PARTITION BY report_date
  CLUSTER BY branch_id, channel_key, account_id_norm, campaign_id
  OPTIONS (require_partition_filter = TRUE);

  ALTER TABLE `your-gcp-project-id.core.fact_marketing_action_daily`
    ADD COLUMN IF NOT EXISTS branch_id STRING;
  ALTER TABLE `your-gcp-project-id.core.fact_web_event_daily`
    ADD COLUMN IF NOT EXISTS branch_id STRING;
  ALTER TABLE `your-gcp-project-id.core.fact_order_line`
    ADD COLUMN IF NOT EXISTS source_system STRING;
  ALTER TABLE `your-gcp-project-id.core.fact_order_line`
    ADD COLUMN IF NOT EXISTS venue_name STRING;
  ALTER TABLE `your-gcp-project-id.core.fact_order_line`
    ADD COLUMN IF NOT EXISTS branch_id STRING;
  ALTER TABLE `your-gcp-project-id.core.fact_survey_response`
    ADD COLUMN IF NOT EXISTS branch_id STRING;
  -- 1) dim_account
  MERGE `your-gcp-project-id.core.dim_account` t
  USING (
    WITH unioned AS (
      SELECT 'META' AS channel_key, REGEXP_REPLACE(account_id, r'^act_', '') AS account_id_norm, account_name,
             CAST(NULL AS STRING) AS timezone, CAST(NULL AS STRING) AS currency,
             MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP())) AS load_ts
      FROM `your-gcp-project-id.raw_ads.meta_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5
      UNION ALL
      SELECT 'META', account_id, CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING),
             MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.meta_ads_creative_raw`
      WHERE collected_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5
      UNION ALL
      SELECT 'GOOGLE_ADS', customer_id, CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING),
             MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.google_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5
      UNION ALL
      SELECT 'TIKTOK_ADS', advertiser_id, CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING),
             MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.tiktok_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5
      UNION ALL
      SELECT 'NAVER_ADS', account_id, CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING),
             MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.naver_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5
      UNION ALL
      SELECT 'NAVER_ADS', account_id, CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING),
             MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.naver_ads_creative_raw`
      WHERE collected_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5
    )
    , dedup AS (
      SELECT
        channel_key,
        account_id_norm,
        ARRAY_AGG(account_name IGNORE NULLS ORDER BY load_ts DESC LIMIT 1)[SAFE_OFFSET(0)] AS account_name,
        ARRAY_AGG(timezone IGNORE NULLS ORDER BY load_ts DESC LIMIT 1)[SAFE_OFFSET(0)] AS timezone,
        ARRAY_AGG(currency IGNORE NULLS ORDER BY load_ts DESC LIMIT 1)[SAFE_OFFSET(0)] AS currency,
        MAX(load_ts) AS load_ts
      FROM unioned
      WHERE account_id_norm IS NOT NULL AND account_id_norm != ''
      GROUP BY channel_key, account_id_norm
    )
    SELECT *
    FROM dedup
  ) s
  ON t.channel_key = s.channel_key AND t.account_id_norm = s.account_id_norm
  WHEN MATCHED THEN UPDATE SET
    account_name = COALESCE(s.account_name, t.account_name),
    timezone = COALESCE(s.timezone, t.timezone),
    currency = COALESCE(s.currency, t.currency),
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (channel_key, account_id_norm, account_name, timezone, currency, load_ts)
  VALUES (s.channel_key, s.account_id_norm, s.account_name, s.timezone, s.currency, s.load_ts);

  -- 2) dim_campaign_scd2 (current row upsert)
  MERGE `your-gcp-project-id.core.dim_campaign_scd2` t
  USING (
    WITH unioned AS (
      SELECT
        'META' AS channel_key,
        REGEXP_REPLACE(account_id, r'^act_', '') AS account_id_norm,
        campaign_id,
        campaign_name,
        campaign_type,
        CAST(NULL AS STRING) AS status,
        MAX(stat_date) AS effective_from_date,
        MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP())) AS load_ts
      FROM `your-gcp-project-id.raw_ads.meta_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5,6

      UNION ALL

      SELECT
        'GOOGLE_ADS',
        customer_id,
        campaign_id,
        campaign_name,
        CAST(NULL AS STRING),
        CAST(NULL AS STRING),
        MAX(stat_date),
        MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.google_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5,6

      UNION ALL

      SELECT
        'TIKTOK_ADS',
        advertiser_id,
        campaign_id,
        CAST(NULL AS STRING),
        CAST(NULL AS STRING),
        CAST(NULL AS STRING),
        MAX(stat_date),
        MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.tiktok_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5,6

      UNION ALL

      SELECT
        'NAVER_ADS',
        account_id,
        campaign_id,
        campaign_name,
        CAST(NULL AS STRING),
        CAST(NULL AS STRING),
        MAX(stat_date),
        MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.naver_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5,6
    )
    , dedup AS (
      SELECT
        channel_key,
        account_id_norm,
        campaign_id,
        ARRAY_AGG(campaign_name IGNORE NULLS ORDER BY load_ts DESC, effective_from_date DESC LIMIT 1)[SAFE_OFFSET(0)] AS campaign_name,
        ARRAY_AGG(campaign_type IGNORE NULLS ORDER BY load_ts DESC, effective_from_date DESC LIMIT 1)[SAFE_OFFSET(0)] AS campaign_type,
        ARRAY_AGG(status IGNORE NULLS ORDER BY load_ts DESC, effective_from_date DESC LIMIT 1)[SAFE_OFFSET(0)] AS status,
        MAX(effective_from_date) AS effective_from_date,
        MAX(load_ts) AS load_ts
      FROM unioned
      WHERE campaign_id IS NOT NULL AND campaign_id != ''
      GROUP BY channel_key, account_id_norm, campaign_id
    )
    SELECT *
    FROM dedup
  ) s
  ON t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.campaign_id = s.campaign_id
 AND t.is_current = TRUE
 AND t.effective_from_date < DATE_ADD(p_end_date, INTERVAL 1 DAY)
  WHEN MATCHED THEN UPDATE SET
    campaign_name = COALESCE(s.campaign_name, t.campaign_name),
    campaign_type = COALESCE(s.campaign_type, t.campaign_type),
    status = COALESCE(s.status, t.status),
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    channel_key, account_id_norm, campaign_id, campaign_name, campaign_type, status,
    effective_from_date, effective_to_date, is_current, load_ts
  ) VALUES (
    s.channel_key, s.account_id_norm, s.campaign_id, s.campaign_name, s.campaign_type, s.status,
    s.effective_from_date, NULL, TRUE, s.load_ts
  );

  -- 3) dim_ad_scd2 (current row upsert)
  MERGE `your-gcp-project-id.core.dim_ad_scd2` t
  USING (
    WITH unioned AS (
      SELECT
        'META' AS channel_key,
        REGEXP_REPLACE(account_id, r'^act_', '') AS account_id_norm,
        campaign_id,
        ad_group_id,
        ad_id,
        ad_name,
        CAST(NULL AS STRING) AS status,
        MAX(stat_date) AS effective_from_date,
        MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP())) AS load_ts
      FROM `your-gcp-project-id.raw_ads.meta_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5,6,7

      UNION ALL

      SELECT
        'GOOGLE_ADS',
        customer_id,
        campaign_id,
        ad_group_id,
        ad_id,
        ad_name,
        CAST(NULL AS STRING),
        MAX(stat_date),
        MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.google_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5,6,7

      UNION ALL

      SELECT
        'TIKTOK_ADS',
        advertiser_id,
        campaign_id,
        ad_group_id,
        ad_id,
        CAST(NULL AS STRING),
        CAST(NULL AS STRING),
        MAX(stat_date),
        MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.tiktok_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5,6,7

      UNION ALL

      SELECT
        'NAVER_ADS',
        account_id,
        campaign_id,
        ad_group_id,
        ad_id,
        ad_name,
        CAST(NULL AS STRING),
        MAX(stat_date),
        MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()))
      FROM `your-gcp-project-id.raw_ads.naver_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3,4,5,6,7
    )
    , dedup AS (
      SELECT
        channel_key,
        account_id_norm,
        ARRAY_AGG(campaign_id IGNORE NULLS ORDER BY load_ts DESC, effective_from_date DESC LIMIT 1)[SAFE_OFFSET(0)] AS campaign_id,
        ARRAY_AGG(ad_group_id IGNORE NULLS ORDER BY load_ts DESC, effective_from_date DESC LIMIT 1)[SAFE_OFFSET(0)] AS ad_group_id,
        ad_id,
        ARRAY_AGG(ad_name IGNORE NULLS ORDER BY load_ts DESC, effective_from_date DESC LIMIT 1)[SAFE_OFFSET(0)] AS ad_name,
        ARRAY_AGG(status IGNORE NULLS ORDER BY load_ts DESC, effective_from_date DESC LIMIT 1)[SAFE_OFFSET(0)] AS status,
        MAX(effective_from_date) AS effective_from_date,
        MAX(load_ts) AS load_ts
      FROM unioned
      WHERE ad_id IS NOT NULL AND ad_id != ''
      GROUP BY channel_key, account_id_norm, ad_id
    )
    SELECT *
    FROM dedup
  ) s
  ON t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.ad_id = s.ad_id
 AND t.is_current = TRUE
 AND t.effective_from_date < DATE_ADD(p_end_date, INTERVAL 1 DAY)
  WHEN MATCHED THEN UPDATE SET
    campaign_id = COALESCE(s.campaign_id, t.campaign_id),
    ad_group_id = COALESCE(s.ad_group_id, t.ad_group_id),
    ad_name = COALESCE(s.ad_name, t.ad_name),
    status = COALESCE(s.status, t.status),
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    channel_key, account_id_norm, campaign_id, ad_group_id, ad_id, ad_name, status,
    effective_from_date, effective_to_date, is_current, load_ts
  ) VALUES (
    s.channel_key, s.account_id_norm, s.campaign_id, s.ad_group_id, s.ad_id, s.ad_name, s.status,
    s.effective_from_date, NULL, TRUE, s.load_ts
  );

  -- 4) dim_creative_scd2 (hash-based SCD2)
  UPDATE `your-gcp-project-id.core.dim_creative_scd2` t
  SET
    valid_to_ts = TIMESTAMP_SUB(s.valid_from_ts, INTERVAL 1 SECOND),
    is_current = FALSE,
    load_ts = CURRENT_TIMESTAMP()
  FROM (
    SELECT
      channel_key, account_id_norm, creative_id, content_hash, valid_from_ts
    FROM `your-gcp-project-id.stg.ads_creative_snapshot`
    WHERE DATE(valid_from_ts) BETWEEN p_start_date AND p_end_date
  ) s
  WHERE t.channel_key = s.channel_key
    AND t.account_id_norm = s.account_id_norm
    AND t.creative_id = s.creative_id
    AND t.is_current = TRUE
    AND t.valid_from_ts < TIMESTAMP(DATE_ADD(p_end_date, INTERVAL 1 DAY))
    AND IFNULL(t.content_hash, '') != IFNULL(s.content_hash, '');

  INSERT INTO `your-gcp-project-id.core.dim_creative_scd2` (
    channel_key, account_id_norm, creative_id, creative_name, body_text, headline,
    description_text, call_to_action, thumbnail_url, content_hash,
    valid_from_ts, valid_to_ts, is_current, load_ts
  )
  SELECT
    s.channel_key, s.account_id_norm, s.creative_id, s.creative_name, s.body_text, s.headline,
    s.description_text, s.call_to_action, s.thumbnail_url, s.content_hash,
    s.valid_from_ts, NULL, TRUE, s.load_ts
  FROM `your-gcp-project-id.stg.ads_creative_snapshot` s
  LEFT JOIN `your-gcp-project-id.core.dim_creative_scd2` c
    ON c.channel_key = s.channel_key
   AND c.account_id_norm = s.account_id_norm
   AND c.creative_id = s.creative_id
   AND c.is_current = TRUE
   AND c.valid_from_ts < TIMESTAMP(DATE_ADD(p_end_date, INTERVAL 1 DAY))
  WHERE DATE(s.valid_from_ts) BETWEEN p_start_date AND p_end_date
    AND (c.creative_id IS NULL OR IFNULL(c.content_hash, '') != IFNULL(s.content_hash, ''));

  -- 5) dim_creative_text_scd2 (disabled: assets-only creative policy)
  -- no-op

  -- 6) dim_creative_asset_scd2 (SCD2 by asset key)
  UPDATE `your-gcp-project-id.core.dim_creative_asset_scd2` t
  SET
    valid_to_ts = TIMESTAMP_SUB(s.valid_from_ts, INTERVAL 1 SECOND),
    is_current = FALSE,
    load_ts = CURRENT_TIMESTAMP()
  FROM (
    SELECT
      channel_key, account_id_norm, creative_id, asset_type, asset_seq,
      COALESCE(asset_url, video_id, image_hash, thumbnail_url) AS asset_fingerprint,
      valid_from_ts
    FROM `your-gcp-project-id.stg.ads_creative_asset`
    WHERE DATE(valid_from_ts) BETWEEN p_start_date AND p_end_date
  ) s
  WHERE t.channel_key = s.channel_key
    AND t.account_id_norm = s.account_id_norm
    AND t.creative_id = s.creative_id
    AND t.asset_type = s.asset_type
    AND t.asset_seq = s.asset_seq
    AND t.is_current = TRUE
    AND t.valid_from_ts < TIMESTAMP(DATE_ADD(p_end_date, INTERVAL 1 DAY))
    AND COALESCE(t.asset_url, t.video_id, t.image_hash, t.thumbnail_url) != s.asset_fingerprint;

  INSERT INTO `your-gcp-project-id.core.dim_creative_asset_scd2` (
    channel_key, account_id_norm, creative_id, asset_type, asset_seq, asset_url, thumbnail_url,
    image_hash, video_id, width, height, duration_sec, valid_from_ts, valid_to_ts, is_current, load_ts
  )
  SELECT
    s.channel_key, s.account_id_norm, s.creative_id, s.asset_type, s.asset_seq, s.asset_url, s.thumbnail_url,
    s.image_hash, s.video_id, s.width, s.height, s.duration_sec, s.valid_from_ts, NULL, TRUE, s.load_ts
  FROM `your-gcp-project-id.stg.ads_creative_asset` s
  LEFT JOIN `your-gcp-project-id.core.dim_creative_asset_scd2` c
    ON c.channel_key = s.channel_key
   AND c.account_id_norm = s.account_id_norm
   AND c.creative_id = s.creative_id
   AND c.asset_type = s.asset_type
   AND c.asset_seq = s.asset_seq
   AND c.is_current = TRUE
   AND c.valid_from_ts < TIMESTAMP(DATE_ADD(p_end_date, INTERVAL 1 DAY))
  WHERE DATE(s.valid_from_ts) BETWEEN p_start_date AND p_end_date
    AND (
      c.creative_id IS NULL
      OR COALESCE(c.asset_url, c.video_id, c.image_hash, c.thumbnail_url) != COALESCE(s.asset_url, s.video_id, s.image_hash, s.thumbnail_url)
    );

  -- 7) bridge_ad_creative_scd2 (current mapping by ad)
  UPDATE `your-gcp-project-id.core.bridge_ad_creative_scd2` t
  SET
    valid_to_date = DATE_SUB(s.valid_from_date, INTERVAL 1 DAY),
    is_current = FALSE,
    load_ts = CURRENT_TIMESTAMP()
  FROM (
    SELECT channel_key, account_id_norm, ad_id, creative_id, DATE(valid_from_ts) AS valid_from_date
    FROM `your-gcp-project-id.stg.ads_creative_snapshot`
    WHERE DATE(valid_from_ts) BETWEEN p_start_date AND p_end_date
  ) s
  WHERE t.channel_key = s.channel_key
    AND t.account_id_norm = s.account_id_norm
    AND t.ad_id = s.ad_id
    AND t.is_current = TRUE
    AND t.valid_from_date < DATE_ADD(p_end_date, INTERVAL 1 DAY)
    AND t.creative_id != s.creative_id;

  INSERT INTO `your-gcp-project-id.core.bridge_ad_creative_scd2` (
    channel_key, account_id_norm, ad_id, creative_id, valid_from_date, valid_to_date, is_current, load_ts
  )
  SELECT
    s.channel_key, s.account_id_norm, s.ad_id, s.creative_id, DATE(s.valid_from_ts), NULL, TRUE, s.load_ts
  FROM `your-gcp-project-id.stg.ads_creative_snapshot` s
  LEFT JOIN `your-gcp-project-id.core.bridge_ad_creative_scd2` b
    ON b.channel_key = s.channel_key
   AND b.account_id_norm = s.account_id_norm
   AND b.ad_id = s.ad_id
   AND b.is_current = TRUE
   AND b.valid_from_date < DATE_ADD(p_end_date, INTERVAL 1 DAY)
  WHERE DATE(s.valid_from_ts) BETWEEN p_start_date AND p_end_date
    AND (b.ad_id IS NULL OR b.creative_id != s.creative_id);

  -- 8) dim_customer
  MERGE `your-gcp-project-id.core.dim_customer` t
  USING (
    WITH src AS (
      SELECT
        TO_HEX(SHA256(CONCAT(IFNULL(customer_email_hash, ''), '|', IFNULL(customer_phone_hash, '')))) AS customer_key,
        customer_email_hash AS email_hash,
        customer_phone_hash AS phone_hash,
        MIN(order_ts) AS first_seen_ts,
        MAX(order_ts) AS latest_seen_ts,
        MAX(load_ts) AS load_ts
      FROM `your-gcp-project-id.stg.order_line`
      WHERE order_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3
      UNION ALL
      SELECT
        TO_HEX(SHA256(CONCAT(IFNULL(customer_email_hash, ''), '|', IFNULL(customer_phone_hash, '')))),
        customer_email_hash,
        customer_phone_hash,
        MIN(response_ts),
        MAX(response_ts),
        MAX(load_ts)
      FROM `your-gcp-project-id.stg.survey_response`
      WHERE response_date BETWEEN p_start_date AND p_end_date
      GROUP BY 1,2,3
    ),
    dedup AS (
      SELECT
        customer_key,
        ANY_VALUE(email_hash) AS email_hash,
        ANY_VALUE(phone_hash) AS phone_hash,
        MIN(first_seen_ts) AS first_seen_ts,
        MAX(latest_seen_ts) AS latest_seen_ts,
        MAX(load_ts) AS load_ts
      FROM src
      WHERE customer_key IS NOT NULL AND customer_key != TO_HEX(SHA256('|'))
      GROUP BY customer_key
    )
    SELECT * FROM dedup
  ) s
  ON t.customer_key = s.customer_key
 AND t.latest_seen_ts < TIMESTAMP(DATE_ADD(p_end_date, INTERVAL 1 DAY))
  WHEN MATCHED THEN UPDATE SET
    email_hash = COALESCE(t.email_hash, s.email_hash),
    phone_hash = COALESCE(t.phone_hash, s.phone_hash),
    first_seen_ts = LEAST(t.first_seen_ts, s.first_seen_ts),
    latest_seen_ts = GREATEST(t.latest_seen_ts, s.latest_seen_ts),
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (customer_key, email_hash, phone_hash, first_seen_ts, latest_seen_ts, load_ts)
  VALUES (s.customer_key, s.email_hash, s.phone_hash, s.first_seen_ts, s.latest_seen_ts, s.load_ts);

  -- 9) facts
  MERGE `your-gcp-project-id.core.fact_marketing_daily` t
  USING (
    WITH naver_rule_match AS (
      SELECT
        account_id AS account_id_norm,
        campaign_id,
        ad_group_id,
        stat_date,
        branch_id
      FROM (
        SELECT
          r.account_id,
          r.campaign_id,
          r.ad_group_id,
          r.stat_date,
          rule.branch_id,
          ROW_NUMBER() OVER (
            PARTITION BY r.account_id, r.campaign_id, IFNULL(r.ad_group_id, ''), r.stat_date
            ORDER BY rule.priority ASC, LENGTH(rule.match_keyword) DESC, rule.updated_at DESC
          ) AS rule_rank
        FROM `your-gcp-project-id.raw_ads.naver_ads_performance_raw` r
        LEFT JOIN `your-gcp-project-id.governance.naver_adgroup_branch_rule` rule
          ON rule.is_active = TRUE
         AND STRPOS(LOWER(COALESCE(r.ad_group_name, '')), LOWER(rule.match_keyword)) > 0
        WHERE r.stat_date BETWEEN p_start_date AND p_end_date
      )
      WHERE rule_rank = 1
    ),
    resolved_source AS (
      SELECT
        s.stat_date,
        s.channel_key,
        s.account_id_norm,
        s.campaign_id,
        s.ad_group_id,
        s.ad_id,
        s.impressions,
        s.clicks,
        s.spend,
        s.conversion_count,
        s.conversion_value,
        s.load_ts,
        CASE
          WHEN s.channel_key = 'NAVER_ADS' THEN COALESCE(n.branch_id, 'UNKNOWN')
          ELSE COALESCE(m.branch_id, 'UNKNOWN')
        END AS resolved_branch_id,
        s.currency_code
      FROM `your-gcp-project-id.stg.ads_performance_daily` s
      LEFT JOIN `your-gcp-project-id.governance.account_branch_map` m
        ON m.channel_key = s.channel_key
       AND m.account_id_norm = s.account_id_norm
       AND s.stat_date BETWEEN m.effective_start_date AND COALESCE(m.effective_end_date, DATE '9999-12-31')
       AND m.is_active = TRUE
      LEFT JOIN naver_rule_match n
        ON s.channel_key = 'NAVER_ADS'
       AND n.account_id_norm = s.account_id_norm
       AND n.campaign_id = s.campaign_id
       AND IFNULL(n.ad_group_id, '') = IFNULL(s.ad_group_id, '')
       AND n.stat_date = s.stat_date
      WHERE s.stat_date BETWEEN p_start_date AND p_end_date
    ),
    dedup_source AS (
      SELECT
        s.stat_date,
        s.channel_key,
        s.account_id_norm,
        s.campaign_id,
        s.ad_group_id,
        s.ad_id,
        s.impressions,
        s.clicks,
        s.spend,
        s.conversion_count,
        s.conversion_value,
      s.load_ts,
      s.resolved_branch_id AS branch_id,
      COALESCE(
        s.currency_code,
        CASE WHEN s.channel_key = 'NAVER_ADS' THEN 'KRW' ELSE NULL END,
        b.currency,
        'USD'
      ) AS currency_code
      FROM resolved_source s
      LEFT JOIN `your-gcp-project-id.core.dim_branch` b
        ON b.branch_id = s.resolved_branch_id
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY s.stat_date, s.channel_key, s.account_id_norm, s.campaign_id, IFNULL(s.ad_group_id, ''), IFNULL(s.ad_id, '')
        ORDER BY s.load_ts DESC
      ) = 1
    )
    SELECT *
    FROM dedup_source
  ) s
 ON t.stat_date = s.stat_date
 AND t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.campaign_id = s.campaign_id
 AND IFNULL(t.ad_group_id, '') = IFNULL(s.ad_group_id, '')
 AND IFNULL(t.ad_id, '') = IFNULL(s.ad_id, '')
 AND t.stat_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    impressions = s.impressions,
    clicks = s.clicks,
    spend = s.spend,
    conversion_count = s.conversion_count,
    conversion_value = s.conversion_value,
    branch_id = s.branch_id,
    currency_code = s.currency_code,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    stat_date, channel_key, account_id_norm, campaign_id, ad_group_id, ad_id,
    impressions, clicks, spend, conversion_count, conversion_value, load_ts, branch_id, currency_code
  ) VALUES (
    s.stat_date, s.channel_key, s.account_id_norm, s.campaign_id, s.ad_group_id, s.ad_id,
    s.impressions, s.clicks, s.spend, s.conversion_count, s.conversion_value, s.load_ts, s.branch_id, s.currency_code
  );

  DELETE FROM `your-gcp-project-id.core.fact_marketing_campaign_daily`
  WHERE report_date BETWEEN p_start_date AND p_end_date;

  MERGE `your-gcp-project-id.core.fact_marketing_campaign_daily` t
  USING (
    WITH current_campaign_dim AS (
      SELECT *
      FROM `your-gcp-project-id.core.dim_campaign_scd2`
      WHERE effective_from_date < DATE_ADD(p_end_date, INTERVAL 1 DAY)
        AND is_current = TRUE
    ),
    aggregated AS (
      SELECT
        f.stat_date AS report_date,
        f.branch_id,
        f.channel_key,
        f.account_id_norm,
        f.campaign_id,
        ARRAY_AGG(c.campaign_name IGNORE NULLS ORDER BY c.load_ts DESC LIMIT 1)[SAFE_OFFSET(0)] AS campaign_name,
        f.currency_code,
        SUM(IFNULL(f.impressions, 0)) AS impressions,
        SUM(IFNULL(f.clicks, 0)) AS clicks,
        SUM(IFNULL(f.spend, 0)) AS spend_native,
        SUM(IFNULL(f.conversion_count, 0)) AS conversions,
        SUM(IFNULL(f.conversion_value, 0)) AS conversion_value_native,
        MAX(f.load_ts) AS load_ts
      FROM `your-gcp-project-id.core.fact_marketing_daily` f
      LEFT JOIN current_campaign_dim c
        ON c.channel_key = f.channel_key
       AND c.account_id_norm = f.account_id_norm
       AND c.campaign_id = f.campaign_id
      WHERE f.stat_date BETWEEN p_start_date AND p_end_date
      GROUP BY report_date, branch_id, channel_key, account_id_norm, campaign_id, currency_code
    )
    SELECT * FROM aggregated
  ) s
  ON t.report_date = s.report_date
 AND t.branch_id = s.branch_id
 AND t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.campaign_id = s.campaign_id
  WHEN MATCHED THEN UPDATE SET
    campaign_name = COALESCE(s.campaign_name, t.campaign_name),
    currency_code = s.currency_code,
    impressions = s.impressions,
    clicks = s.clicks,
    spend_native = s.spend_native,
    conversions = s.conversions,
    conversion_value_native = s.conversion_value_native,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    report_date, branch_id, channel_key, account_id_norm, campaign_id, campaign_name, currency_code,
    impressions, clicks, spend_native, conversions, conversion_value_native, load_ts
  ) VALUES (
    s.report_date, s.branch_id, s.channel_key, s.account_id_norm, s.campaign_id, s.campaign_name, s.currency_code,
    s.impressions, s.clicks, s.spend_native, s.conversions, s.conversion_value_native, s.load_ts
  );

  MERGE `your-gcp-project-id.core.fact_marketing_action_daily` t
  USING (
    WITH dedup AS (
      SELECT
        s.stat_date,
        s.channel_key,
        s.account_id_norm,
        s.campaign_id,
        s.ad_group_id,
        s.ad_id,
        s.action_type,
        s.action_count,
        s.action_value,
        s.load_ts,
        COALESCE(m.branch_id, 'UNKNOWN') AS branch_id
      FROM `your-gcp-project-id.stg.ads_action_daily` s
      LEFT JOIN `your-gcp-project-id.governance.account_branch_map` m
        ON m.channel_key = s.channel_key
       AND m.account_id_norm = s.account_id_norm
       AND s.stat_date BETWEEN m.effective_start_date AND COALESCE(m.effective_end_date, DATE '9999-12-31')
       AND m.is_active = TRUE
      WHERE s.stat_date BETWEEN p_start_date AND p_end_date
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY s.stat_date, s.channel_key, s.account_id_norm, s.campaign_id, IFNULL(s.ad_group_id, ''), IFNULL(s.ad_id, ''), s.action_type
        ORDER BY s.load_ts DESC
      ) = 1
    )
    SELECT * FROM dedup
  ) s
  ON t.stat_date = s.stat_date
 AND t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.campaign_id = s.campaign_id
 AND IFNULL(t.ad_group_id, '') = IFNULL(s.ad_group_id, '')
 AND IFNULL(t.ad_id, '') = IFNULL(s.ad_id, '')
 AND t.action_type = s.action_type
 AND t.stat_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    action_count = s.action_count,
    action_value = s.action_value,
    branch_id = s.branch_id,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    stat_date, channel_key, account_id_norm, campaign_id, ad_group_id, ad_id,
    action_type, action_count, action_value, load_ts, branch_id
  ) VALUES (
    s.stat_date, s.channel_key, s.account_id_norm, s.campaign_id, s.ad_group_id, s.ad_id,
    s.action_type, s.action_count, s.action_value, s.load_ts, s.branch_id
  );

  MERGE `your-gcp-project-id.core.fact_web_event_daily` t
  USING (
    WITH mapped AS (
      SELECT
        s.event_date,
        s.property_id,
        s.source,
        s.medium,
        s.campaign,
        s.event_name,
        s.users,
        s.sessions,
        s.event_count,
        s.event_value,
        s.load_ts,
        COALESCE(m.branch_id, 'UNKNOWN') AS branch_id,
        m.effective_start_date,
        m.updated_at
      FROM `your-gcp-project-id.stg.web_event_daily` s
      LEFT JOIN `your-gcp-project-id.governance.ga4_property_branch_map` m
        ON m.property_id = s.property_id
       AND s.event_date BETWEEN m.effective_start_date AND COALESCE(m.effective_end_date, DATE '9999-12-31')
       AND m.is_active = TRUE
      WHERE s.event_date BETWEEN p_start_date AND p_end_date
    ),
    dedup AS (
      SELECT *
      FROM mapped
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY event_date, property_id, source, medium, campaign, event_name
        ORDER BY effective_start_date DESC, updated_at DESC, load_ts DESC
      ) = 1
    )
    SELECT * FROM dedup
  ) s
  ON t.event_date = s.event_date
 AND t.property_id = s.property_id
 AND t.source = s.source
 AND t.medium = s.medium
 AND t.campaign = s.campaign
 AND t.event_name = s.event_name
 AND t.event_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    users = s.users,
    sessions = s.sessions,
    event_count = s.event_count,
    event_value = s.event_value,
    branch_id = s.branch_id,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    event_date, property_id, source, medium, campaign, event_name, users, sessions, event_count, event_value, load_ts, branch_id
  ) VALUES (
    s.event_date, s.property_id, s.source, s.medium, s.campaign, s.event_name, s.users, s.sessions, s.event_count, s.event_value, s.load_ts, s.branch_id
  );

  MERGE `your-gcp-project-id.core.fact_order_line` t
  USING (
    WITH base AS (
      SELECT
        order_date,
        order_ts,
        order_source,
        source_system,
        order_id,
        order_line_id,
        IF(
          customer_email_hash IS NULL AND customer_phone_hash IS NULL,
          NULL,
          TO_HEX(SHA256(CONCAT(IFNULL(customer_email_hash, ''), '|', IFNULL(customer_phone_hash, ''))))
        ) AS customer_key,
        product_id,
        venue_name,
        quantity,
        gross_amount,
        discount_amount,
        net_amount,
        currency,
        payment_status,
        load_ts
      FROM `your-gcp-project-id.stg.order_line`
      WHERE order_date BETWEEN p_start_date AND p_end_date
    ),
    mapped AS (
      SELECT
        b.*,
        COALESCE(fe.branch_id, ss.branch_id, 'UNKNOWN') AS branch_id,
        COALESCE(fe.effective_start_date, ss.effective_start_date) AS effective_start_date,
        COALESCE(fe.updated_at, ss.updated_at) AS updated_at
      FROM base b
      LEFT JOIN `your-gcp-project-id.governance.fever_event_branch_map` fe
        ON b.order_source = 'FEVER'
       AND (
         (fe.event_id IS NOT NULL AND fe.event_id = b.product_id)
         OR (fe.event_id IS NULL AND fe.venue_name IS NOT NULL AND fe.venue_name = b.venue_name)
       )
       AND b.order_date BETWEEN fe.effective_start_date AND COALESCE(fe.effective_end_date, DATE '9999-12-31')
       AND fe.is_active = TRUE
      LEFT JOIN `your-gcp-project-id.governance.sales_source_branch_map` ss
        ON b.order_source = 'SALES'
       AND ss.source_system = b.source_system
       AND b.order_date BETWEEN ss.effective_start_date AND COALESCE(ss.effective_end_date, DATE '9999-12-31')
       AND ss.is_active = TRUE
    ),
    dedup AS (
      SELECT *
      FROM mapped
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY order_source, order_id, order_line_id
        ORDER BY effective_start_date DESC, updated_at DESC, load_ts DESC
      ) = 1
    )
    SELECT * FROM dedup
  ) s
  ON t.order_source = s.order_source
 AND t.order_id = s.order_id
 AND t.order_line_id = s.order_line_id
 AND t.order_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    order_date = s.order_date,
    order_ts = s.order_ts,
    source_system = s.source_system,
    customer_key = s.customer_key,
    product_id = s.product_id,
    venue_name = s.venue_name,
    quantity = s.quantity,
    gross_amount = s.gross_amount,
    discount_amount = s.discount_amount,
    net_amount = s.net_amount,
    currency = s.currency,
    payment_status = s.payment_status,
    branch_id = s.branch_id,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    order_date, order_ts, order_source, source_system, order_id, order_line_id, customer_key,
    product_id, venue_name, quantity, gross_amount, discount_amount, net_amount, currency, payment_status, load_ts, branch_id
  ) VALUES (
    s.order_date, s.order_ts, s.order_source, s.source_system, s.order_id, s.order_line_id, s.customer_key,
    s.product_id, s.venue_name, s.quantity, s.gross_amount, s.discount_amount, s.net_amount, s.currency, s.payment_status, s.load_ts, s.branch_id
  );

  MERGE `your-gcp-project-id.core.fact_survey_response` t
  USING (
    WITH base AS (
      SELECT
        response_date,
        response_ts,
        survey_source,
        response_id,
        IF(
          customer_email_hash IS NULL AND customer_phone_hash IS NULL,
          NULL,
          TO_HEX(SHA256(CONCAT(IFNULL(customer_email_hash, ''), '|', IFNULL(customer_phone_hash, ''))))
        ) AS customer_key,
        survey_id,
        question_id,
        answer_type,
        answer_text,
        answer_score,
        load_ts
      FROM `your-gcp-project-id.stg.survey_response`
      WHERE response_date BETWEEN p_start_date AND p_end_date
    ),
    mapped AS (
      SELECT
        b.*,
        COALESCE(m.branch_id, 'UNKNOWN') AS branch_id,
        m.effective_start_date,
        m.updated_at
      FROM base b
      LEFT JOIN `your-gcp-project-id.governance.survey_source_branch_map` m
        ON m.survey_source = b.survey_source
       AND COALESCE(m.survey_id, b.survey_id) = b.survey_id
       AND b.response_date BETWEEN m.effective_start_date AND COALESCE(m.effective_end_date, DATE '9999-12-31')
       AND m.is_active = TRUE
    ),
    dedup AS (
      SELECT *
      FROM mapped
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY survey_source, response_id, question_id
        ORDER BY effective_start_date DESC, updated_at DESC, load_ts DESC
      ) = 1
    )
    SELECT * FROM dedup
  ) s
  ON t.survey_source = s.survey_source
 AND t.response_id = s.response_id
 AND t.question_id = s.question_id
 AND t.response_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    response_date = s.response_date,
    response_ts = s.response_ts,
    customer_key = s.customer_key,
    survey_id = s.survey_id,
    answer_type = s.answer_type,
    answer_text = s.answer_text,
    answer_score = s.answer_score,
    branch_id = s.branch_id,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    response_date, response_ts, survey_source, response_id, customer_key,
    survey_id, question_id, answer_type, answer_text, answer_score, load_ts, branch_id
  ) VALUES (
    s.response_date, s.response_ts, s.survey_source, s.response_id, s.customer_key,
    s.survey_id, s.question_id, s.answer_type, s.answer_text, s.answer_score, s.load_ts, s.branch_id
  );

  CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_dashboard_ad_daily` AS
  WITH current_campaign_dim AS (
    SELECT *
    FROM `your-gcp-project-id.core.dim_campaign_scd2`
    WHERE effective_from_date <= CURRENT_DATE()
      AND is_current = TRUE
  ),
  current_ad_dim AS (
    SELECT *
    FROM `your-gcp-project-id.core.dim_ad_scd2`
    WHERE effective_from_date <= CURRENT_DATE()
      AND is_current = TRUE
  )
  SELECT
    f.stat_date AS report_date,
    f.branch_id,
    b.branch_name,
    f.channel_key,
    f.account_id_norm,
    f.campaign_id,
    c.campaign_name,
    f.ad_group_id,
    f.ad_id,
    a.ad_name,
    f.currency_code,
    f.impressions,
    f.clicks,
    f.spend AS spend_native,
    f.conversion_count AS conversions,
    f.conversion_value AS conversion_value_native,
    SAFE_DIVIDE(f.clicks, NULLIF(f.impressions, 0)) AS ctr,
    SAFE_DIVIDE(f.spend, NULLIF(f.clicks, 0)) AS cpc,
    SAFE_DIVIDE(f.conversion_value, NULLIF(f.spend, 0)) AS roas
  FROM `your-gcp-project-id.core.fact_marketing_daily` f
  LEFT JOIN `your-gcp-project-id.core.dim_branch` b
    ON b.branch_id = f.branch_id
  LEFT JOIN current_campaign_dim c
    ON c.channel_key = f.channel_key
   AND c.account_id_norm = f.account_id_norm
   AND c.campaign_id = f.campaign_id
  LEFT JOIN current_ad_dim a
    ON a.channel_key = f.channel_key
   AND a.account_id_norm = f.account_id_norm
   AND a.ad_id = f.ad_id;

  CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_dashboard_campaign_daily` AS
  WITH purchase_campaign AS (
    SELECT
      stat_date AS report_date,
      branch_id,
      channel_key,
      account_id_norm,
      campaign_id,
      SUM(action_count) AS purchase_count,
      SUM(action_value) AS purchase_value
    FROM `your-gcp-project-id.core.fact_marketing_action_daily`
    WHERE stat_date BETWEEN DATE '2000-01-01' AND DATE '2100-01-01'
      AND action_type = 'purchase'
    GROUP BY stat_date, branch_id, channel_key, account_id_norm, campaign_id
  ),
  base_campaign AS (
    SELECT
      f.report_date,
      f.branch_id,
      b.branch_name,
      f.channel_key,
      f.account_id_norm,
      f.campaign_id,
      f.campaign_name,
      f.currency_code,
      f.impressions,
      f.clicks,
      f.spend_native,
      f.conversions,
      f.conversion_value_native
    FROM `your-gcp-project-id.core.fact_marketing_campaign_daily` f
    LEFT JOIN `your-gcp-project-id.core.dim_branch` b
      ON b.branch_id = f.branch_id
    WHERE f.report_date BETWEEN DATE '2000-01-01' AND DATE '2100-01-01'
  ),
  api_campaign AS (
    SELECT
      b.report_date,
      b.branch_id,
      b.branch_name,
      b.channel_key,
      b.account_id_norm,
      b.campaign_id,
      b.campaign_name,
      b.currency_code,
      b.impressions,
      b.clicks,
      b.spend_native,
      CAST(NULL AS NUMERIC) AS contract_spend_native,
      b.spend_native AS effective_spend_native,
      0 AS active_time_contract_count,
      COALESCE(pc.purchase_count, 0) AS purchase_count,
      COALESCE(pc.purchase_value, 0) AS purchase_value,
      b.conversions,
      b.conversion_value_native,
      SAFE_DIVIDE(b.clicks, NULLIF(b.impressions, 0)) AS ctr,
      SAFE_DIVIDE(b.spend_native, NULLIF(b.clicks, 0)) AS cpc,
      SAFE_DIVIDE(b.spend_native, NULLIF(b.clicks, 0)) AS effective_cpc,
      SAFE_DIVIDE(b.conversion_value_native, NULLIF(b.spend_native, 0)) AS roas,
      SAFE_DIVIDE(b.conversion_value_native, NULLIF(b.spend_native, 0)) AS effective_roas,
      'api_real' AS source_tier
    FROM base_campaign b
    LEFT JOIN purchase_campaign pc
      ON pc.report_date = b.report_date
     AND pc.branch_id = b.branch_id
     AND pc.channel_key = b.channel_key
     AND pc.account_id_norm = b.account_id_norm
     AND pc.campaign_id = b.campaign_id
  ),
  external_sheet_campaign AS (
    SELECT
      e.date AS report_date,
      e.branch_id,
      b.branch_name,
      e.channel_key,
      'external_sheet' AS account_id_norm,
      CONCAT('external_sheet:', e.channel_key) AS campaign_id,
      CONCAT('External Sheet ', e.channel_key) AS campaign_name,
      'USD' AS currency_code,
      CAST(SUM(e.impressions) AS INT64) AS impressions,
      CAST(SUM(e.clicks) AS INT64) AS clicks,
      SUM(e.spend_usd) AS spend_native,
      CAST(NULL AS NUMERIC) AS contract_spend_native,
      SUM(e.spend_usd) AS effective_spend_native,
      0 AS active_time_contract_count,
      CAST(SUM(e.transactions) AS FLOAT64) AS purchase_count,
      CAST(NULL AS FLOAT64) AS purchase_value,
      CAST(SUM(e.transactions) AS FLOAT64) AS conversions,
      CAST(NULL AS NUMERIC) AS conversion_value_native,
      SAFE_DIVIDE(CAST(SUM(e.clicks) AS FLOAT64), NULLIF(CAST(SUM(e.impressions) AS FLOAT64), 0)) AS ctr,
      SAFE_DIVIDE(SUM(e.spend_usd), NULLIF(SUM(e.clicks), 0)) AS cpc,
      SAFE_DIVIDE(SUM(e.spend_usd), NULLIF(SUM(e.clicks), 0)) AS effective_cpc,
      CAST(NULL AS NUMERIC) AS roas,
      CAST(NULL AS NUMERIC) AS effective_roas,
      'sheet' AS source_tier
    FROM `your-gcp-project-id.raw_ads.external_ads_raw` e
    LEFT JOIN `your-gcp-project-id.core.dim_branch` b
      ON b.branch_id = e.branch_id
    GROUP BY e.date, e.branch_id, b.branch_name, e.channel_key
  )
  SELECT * FROM api_campaign
  UNION ALL
  SELECT * FROM external_sheet_campaign;

  CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_dashboard_branch_channel_daily` AS
  SELECT
    report_date,
    branch_id,
    ANY_VALUE(branch_name) AS branch_name,
    channel_key,
    currency_code,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    SUM(spend_native) AS spend_native,
    SUM(conversions) AS conversions,
    SUM(conversion_value_native) AS conversion_value_native,
    SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions), 0)) AS ctr,
    SAFE_DIVIDE(SUM(spend_native), NULLIF(SUM(clicks), 0)) AS cpc,
    SAFE_DIVIDE(SUM(conversion_value_native), NULLIF(SUM(spend_native), 0)) AS roas
  FROM `your-gcp-project-id.mart.v_dashboard_campaign_daily`
  GROUP BY report_date, branch_id, channel_key, currency_code;

  CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_business_branch_daily` AS
  SELECT
    f.order_date AS report_date,
    f.branch_id,
    ANY_VALUE(b.branch_name) AS branch_name,
    f.currency AS currency_code,
    COUNT(DISTINCT f.order_id) AS orders,
    SUM(IFNULL(f.quantity, 0)) AS quantity,
    SUM(IFNULL(f.gross_amount, 0)) AS gross_revenue_native,
    SUM(IFNULL(f.discount_amount, 0)) AS discount_amount_native,
    SUM(IFNULL(f.net_amount, 0)) AS net_revenue_native
  FROM `your-gcp-project-id.core.fact_order_line` f
  LEFT JOIN `your-gcp-project-id.core.dim_branch` b
    ON b.branch_id = f.branch_id
  GROUP BY f.order_date, f.branch_id, f.currency;

  CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_web_branch_daily` AS
  SELECT
    f.event_date AS report_date,
    f.branch_id,
    ANY_VALUE(b.branch_name) AS branch_name,
    SUM(IFNULL(f.users, 0)) AS users,
    SUM(IFNULL(f.sessions, 0)) AS sessions,
    SUM(IFNULL(f.event_count, 0)) AS event_count
  FROM `your-gcp-project-id.core.fact_web_event_daily` f
  LEFT JOIN `your-gcp-project-id.core.dim_branch` b
    ON b.branch_id = f.branch_id
  GROUP BY f.event_date, f.branch_id;

  CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_survey_branch_daily` AS
  SELECT
    f.response_date AS report_date,
    f.branch_id,
    ANY_VALUE(b.branch_name) AS branch_name,
    COUNT(DISTINCT f.response_id) AS response_count,
    AVG(f.answer_score) AS avg_answer_score
  FROM `your-gcp-project-id.core.fact_survey_response` f
  LEFT JOIN `your-gcp-project-id.core.dim_branch` b
    ON b.branch_id = f.branch_id
  GROUP BY f.response_date, f.branch_id;

  CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_blended_branch_daily` AS
  WITH ad AS (
    SELECT
      report_date,
      branch_id,
      currency_code,
      SUM(impressions) AS ad_impressions,
      SUM(clicks) AS ad_clicks,
      SUM(spend_native) AS ad_spend_native,
      SUM(conversions) AS ad_conversions,
      SUM(conversion_value_native) AS ad_conversion_value_native
    FROM `your-gcp-project-id.mart.v_dashboard_campaign_daily`
    GROUP BY report_date, branch_id, currency_code
  ),
  biz AS (
    SELECT
      report_date,
      branch_id,
      currency_code,
      SUM(orders) AS orders,
      SUM(net_revenue_native) AS net_revenue_native
    FROM `your-gcp-project-id.mart.v_business_branch_daily`
    GROUP BY report_date, branch_id, currency_code
  ),
  web AS (
    SELECT
      report_date,
      branch_id,
      users,
      sessions,
      event_count
    FROM `your-gcp-project-id.mart.v_web_branch_daily`
  ),
  survey AS (
    SELECT
      report_date,
      branch_id,
      response_count,
      avg_answer_score
    FROM `your-gcp-project-id.mart.v_survey_branch_daily`
  ),
  keys AS (
    SELECT report_date, branch_id, currency_code FROM ad
    UNION DISTINCT
    SELECT report_date, branch_id, currency_code FROM biz
    UNION DISTINCT
    SELECT w.report_date, w.branch_id, b.currency AS currency_code
    FROM web w
    LEFT JOIN `your-gcp-project-id.core.dim_branch` b
      ON b.branch_id = w.branch_id
    UNION DISTINCT
    SELECT s.report_date, s.branch_id, b.currency AS currency_code
    FROM survey s
    LEFT JOIN `your-gcp-project-id.core.dim_branch` b
      ON b.branch_id = s.branch_id
  )
  SELECT
    k.report_date,
    k.branch_id,
    b.branch_name,
    k.currency_code,
    ad.ad_impressions,
    ad.ad_clicks,
    ad.ad_spend_native,
    ad.ad_conversions,
    ad.ad_conversion_value_native,
    biz.orders,
    biz.net_revenue_native,
    web.users,
    web.sessions,
    web.event_count,
    survey.response_count,
    survey.avg_answer_score
  FROM keys k
  LEFT JOIN `your-gcp-project-id.core.dim_branch` b
    ON b.branch_id = k.branch_id
  LEFT JOIN ad
    ON ad.report_date = k.report_date
   AND ad.branch_id = k.branch_id
   AND ad.currency_code = k.currency_code
  LEFT JOIN biz
    ON biz.report_date = k.report_date
   AND biz.branch_id = k.branch_id
   AND biz.currency_code = k.currency_code
  LEFT JOIN web
    ON web.report_date = k.report_date
   AND web.branch_id = k.branch_id
  LEFT JOIN survey
    ON survey.report_date = k.report_date
   AND survey.branch_id = k.branch_id;
END

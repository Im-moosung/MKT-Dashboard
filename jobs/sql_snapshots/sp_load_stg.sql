BEGIN
  -- Bootstrap STG tables in case they were expired/deleted.
  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.stg.ads_performance_daily` (
    channel_key STRING,
    account_id_norm STRING,
    campaign_id STRING,
    ad_group_id STRING,
    ad_group_name STRING,
    ad_id STRING,
    currency_code STRING,
    stat_date DATE,
    impressions INT64,
    clicks INT64,
    spend NUMERIC,
    conversion_count FLOAT64,
    conversion_value NUMERIC,
    source_table STRING,
    load_ts TIMESTAMP
  )
  PARTITION BY stat_date
  CLUSTER BY channel_key, account_id_norm, campaign_id, ad_id
  OPTIONS (require_partition_filter = TRUE);

  ALTER TABLE `your-gcp-project-id.stg.ads_performance_daily`
    ADD COLUMN IF NOT EXISTS currency_code STRING;
  ALTER TABLE `your-gcp-project-id.stg.ads_performance_daily`
    ADD COLUMN IF NOT EXISTS ad_group_name STRING;

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.stg.ads_action_daily` (
    channel_key STRING,
    account_id_norm STRING,
    campaign_id STRING,
    ad_group_id STRING,
    ad_id STRING,
    stat_date DATE,
    action_type STRING,
    action_count FLOAT64,
    action_value NUMERIC,
    source_table STRING,
    load_ts TIMESTAMP
  )
  PARTITION BY stat_date
  CLUSTER BY channel_key, account_id_norm, action_type
  OPTIONS (require_partition_filter = TRUE);

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.stg.ads_creative_snapshot` (
    channel_key STRING,
    account_id_norm STRING,
    ad_id STRING,
    creative_id STRING,
    creative_name STRING,
    body_text STRING,
    headline STRING,
    description_text STRING,
    call_to_action STRING,
    thumbnail_url STRING,
    content_hash STRING,
    valid_from_ts TIMESTAMP,
    load_ts TIMESTAMP
  )
  PARTITION BY DATE(valid_from_ts)
  CLUSTER BY channel_key, account_id_norm, ad_id, creative_id
  OPTIONS (require_partition_filter = TRUE);

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.stg.ads_creative_text` (
    channel_key STRING,
    account_id_norm STRING,
    ad_id STRING,
    creative_id STRING,
    text_type STRING,
    text_seq INT64,
    text_content STRING,
    language STRING,
    valid_from_ts TIMESTAMP,
    load_ts TIMESTAMP
  )
  PARTITION BY DATE(valid_from_ts)
  CLUSTER BY channel_key, account_id_norm, creative_id, text_type
  OPTIONS (require_partition_filter = TRUE);

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.stg.ads_creative_asset` (
    channel_key STRING,
    account_id_norm STRING,
    ad_id STRING,
    creative_id STRING,
    asset_type STRING,
    asset_seq INT64,
    asset_url STRING,
    thumbnail_url STRING,
    image_hash STRING,
    video_id STRING,
    width INT64,
    height INT64,
    duration_sec INT64,
    valid_from_ts TIMESTAMP,
    load_ts TIMESTAMP
  )
  PARTITION BY DATE(valid_from_ts)
  CLUSTER BY channel_key, account_id_norm, creative_id, asset_type
  OPTIONS (require_partition_filter = TRUE);

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.stg.web_event_daily` (
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
    load_ts TIMESTAMP
  )
  PARTITION BY event_date
  CLUSTER BY property_id, source, medium, campaign
  OPTIONS (require_partition_filter = TRUE);

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.stg.order_line` (
    order_source STRING,
    source_system STRING,
    order_id STRING,
    order_line_id STRING,
    order_ts TIMESTAMP,
    order_date DATE,
    customer_email_hash STRING,
    customer_phone_hash STRING,
    product_id STRING,
    venue_name STRING,
    quantity INT64,
    gross_amount NUMERIC,
    discount_amount NUMERIC,
    net_amount NUMERIC,
    currency STRING,
    payment_status STRING,
    load_ts TIMESTAMP
  )
  PARTITION BY order_date
  CLUSTER BY order_source, order_id, order_line_id
  OPTIONS (require_partition_filter = TRUE);

  ALTER TABLE `your-gcp-project-id.stg.order_line`
    ADD COLUMN IF NOT EXISTS source_system STRING;
  ALTER TABLE `your-gcp-project-id.stg.order_line`
    ADD COLUMN IF NOT EXISTS venue_name STRING;

  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.stg.survey_response` (
    response_date DATE,
    response_ts TIMESTAMP,
    survey_source STRING,
    response_id STRING,
    customer_email_hash STRING,
    customer_phone_hash STRING,
    survey_id STRING,
    question_id STRING,
    answer_type STRING,
    answer_text STRING,
    answer_score FLOAT64,
    load_ts TIMESTAMP
  )
  PARTITION BY response_date
  CLUSTER BY survey_source, survey_id, response_id
  OPTIONS (require_partition_filter = TRUE);
  -- 1) Ads performance (Meta/Google/TikTok/Naver -> stg.ads_performance_daily)
  MERGE `your-gcp-project-id.stg.ads_performance_daily` t
  USING (
    WITH unioned AS (
      SELECT
        'META' AS channel_key,
        REGEXP_REPLACE(account_id, r'^act_', '') AS account_id_norm,
        campaign_id,
        ad_group_id,
        ad_group_name,
        ad_id,
        CAST(NULL AS STRING) AS currency_code,
        stat_date,
        impressions,
        clicks,
        spend,
        CAST(NULL AS FLOAT64) AS conversion_count,
        CAST(NULL AS NUMERIC) AS conversion_value,
        'raw_ads.meta_ads_performance_raw' AS source_table,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.meta_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date

      UNION ALL

      SELECT
        'GOOGLE_ADS' AS channel_key,
        customer_id AS account_id_norm,
        campaign_id,
        ad_group_id,
        ad_group_name,
        ad_id,
        CAST(NULL AS STRING) AS currency_code,
        stat_date,
        impressions,
        clicks,
        SAFE_DIVIDE(CAST(cost_micros AS NUMERIC), 1000000) AS spend,
        conversions AS conversion_count,
        conversions_value AS conversion_value,
        'raw_ads.google_ads_performance_raw' AS source_table,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.google_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date

      UNION ALL

      SELECT
        'TIKTOK_ADS' AS channel_key,
        advertiser_id AS account_id_norm,
        campaign_id,
        ad_group_id,
        CAST(NULL AS STRING) AS ad_group_name,
        ad_id,
        CAST(NULL AS STRING) AS currency_code,
        stat_date,
        impressions,
        clicks,
        spend,
        conversions AS conversion_count,
        conversions_value AS conversion_value,
        'raw_ads.tiktok_ads_performance_raw' AS source_table,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.tiktok_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date

      UNION ALL

      SELECT
        'NAVER_ADS' AS channel_key,
        account_id AS account_id_norm,
        campaign_id,
        ad_group_id,
        ad_group_name,
        ad_id,
        CAST(NULL AS STRING) AS currency_code,
        stat_date,
        impressions,
        clicks,
        SAFE_CAST(spend AS NUMERIC) AS spend,
        CAST(NULL AS FLOAT64) AS conversion_count,
        CAST(NULL AS NUMERIC) AS conversion_value,
        'raw_ads.naver_ads_performance_raw' AS source_table,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.naver_ads_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
    ),
    dedup AS (
      SELECT *
      FROM unioned
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY channel_key, account_id_norm, campaign_id, ad_group_id, IFNULL(ad_group_name, ''), ad_id, currency_code, stat_date
        ORDER BY load_ts DESC
      ) = 1
    )
    SELECT * FROM dedup
  ) s
  ON t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.campaign_id = s.campaign_id
 AND t.ad_group_id = s.ad_group_id
 AND IFNULL(t.ad_group_name, '') = IFNULL(s.ad_group_name, '')
 AND t.ad_id = s.ad_id
 AND IFNULL(t.currency_code, '') = IFNULL(s.currency_code, '')
 AND t.stat_date = s.stat_date
 AND t.stat_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    ad_group_name = COALESCE(s.ad_group_name, t.ad_group_name),
    currency_code = COALESCE(s.currency_code, t.currency_code),
    impressions = s.impressions,
    clicks = s.clicks,
    spend = s.spend,
    conversion_count = s.conversion_count,
    conversion_value = s.conversion_value,
    source_table = s.source_table,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    channel_key, account_id_norm, campaign_id, ad_group_id, ad_group_name, ad_id, currency_code, stat_date,
    impressions, clicks, spend, conversion_count, conversion_value, source_table, load_ts
  ) VALUES (
    s.channel_key, s.account_id_norm, s.campaign_id, s.ad_group_id, s.ad_group_name, s.ad_id, s.currency_code, s.stat_date,
    s.impressions, s.clicks, s.spend, s.conversion_count, s.conversion_value, s.source_table, s.load_ts
  );

  -- 2) Unified action long table (Meta + Google campaign-level) -> stg.ads_action_daily
  MERGE `your-gcp-project-id.stg.ads_action_daily` t
  USING (
    WITH meta_acts AS (
      SELECT
        'META' AS channel_key,
        REGEXP_REPLACE(account_id, r'^act_', '') AS account_id_norm,
        campaign_id,
        ad_group_id,
        ad_id,
        stat_date,
        JSON_VALUE(a, '$.action_type') AS action_type_raw,
        SAFE_CAST(JSON_VALUE(a, '$.value') AS FLOAT64) AS action_count,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.meta_ads_performance_raw`,
      UNNEST(IFNULL(JSON_QUERY_ARRAY(actions_json), CAST([] AS ARRAY<JSON>))) a
      WHERE stat_date BETWEEN p_start_date AND p_end_date
    ),
    meta_vals AS (
      SELECT
        REGEXP_REPLACE(account_id, r'^act_', '') AS account_id_norm,
        campaign_id,
        ad_group_id,
        ad_id,
        stat_date,
        JSON_VALUE(v, '$.action_type') AS action_type_raw,
        SAFE_CAST(JSON_VALUE(v, '$.value') AS NUMERIC) AS action_value
      FROM `your-gcp-project-id.raw_ads.meta_ads_performance_raw`,
      UNNEST(IFNULL(JSON_QUERY_ARRAY(action_values_json), CAST([] AS ARRAY<JSON>))) v
      WHERE stat_date BETWEEN p_start_date AND p_end_date
    ),
    meta_joined AS (
      SELECT
        m.channel_key,
        m.account_id_norm,
        m.campaign_id,
        m.ad_group_id,
        m.ad_id,
        m.stat_date,
        m.action_type_raw,
        m.action_count,
        v.action_value,
        'raw_ads.meta_ads_performance_raw' AS source_table,
        m.load_ts
      FROM meta_acts m
      LEFT JOIN meta_vals v
        ON m.account_id_norm = v.account_id_norm
       AND m.campaign_id = v.campaign_id
       AND m.ad_group_id = v.ad_group_id
       AND m.ad_id = v.ad_id
       AND m.stat_date = v.stat_date
       AND m.action_type_raw = v.action_type_raw
      WHERE m.action_type_raw IS NOT NULL
        AND m.action_type_raw != ''
        AND m.action_count > 0
    ),
    google_actions AS (
      SELECT
        'GOOGLE_ADS' AS channel_key,
        CAST(customer_id AS STRING) AS account_id_norm,
        CAST(campaign_id AS STRING) AS campaign_id,
        CAST(NULL AS STRING) AS ad_group_id,
        CAST(NULL AS STRING) AS ad_id,
        stat_date,
        CAST(action_type_raw AS STRING) AS action_type_raw,
        SAFE_CAST(action_count AS FLOAT64) AS action_count,
        SAFE_CAST(action_value AS NUMERIC) AS action_value,
        'raw_ads.google_ads_action_raw' AS source_table,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.google_ads_action_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
        AND action_type_raw IS NOT NULL
        AND action_type_raw != ''
        AND SAFE_CAST(action_count AS FLOAT64) > 0
    ),
    unioned AS (
      SELECT * FROM meta_joined
      UNION ALL
      SELECT * FROM google_actions
    ),
    mapped AS (
      SELECT
        u.channel_key,
        u.account_id_norm,
        u.campaign_id,
        u.ad_group_id,
        u.ad_id,
        u.stat_date,
        COALESCE(NULLIF(m.action_type_std, ''), u.action_type_raw) AS action_type,
        u.action_count,
        u.action_value,
        u.source_table,
        u.load_ts
      FROM unioned u
      JOIN `your-gcp-project-id.governance.action_type_map` m
        ON m.channel_key = u.channel_key
       AND m.action_type_raw = u.action_type_raw
      WHERE m.is_enabled = TRUE
    ),
    aggregated AS (
      SELECT
        channel_key,
        account_id_norm,
        campaign_id,
        ad_group_id,
        ad_id,
        stat_date,
        action_type,
        SUM(action_count) AS action_count,
        SUM(COALESCE(action_value, 0)) AS action_value,
        ARRAY_AGG(source_table ORDER BY load_ts DESC LIMIT 1)[OFFSET(0)] AS source_table,
        MAX(load_ts) AS load_ts
      FROM mapped
      GROUP BY channel_key, account_id_norm, campaign_id, ad_group_id, ad_id, stat_date, action_type
    )
    SELECT * FROM aggregated
  ) s
  ON t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.campaign_id = s.campaign_id
 AND IFNULL(t.ad_group_id, '') = IFNULL(s.ad_group_id, '')
 AND IFNULL(t.ad_id, '') = IFNULL(s.ad_id, '')
 AND t.stat_date = s.stat_date
 AND t.action_type = s.action_type
 AND t.stat_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    action_count = s.action_count,
    action_value = s.action_value,
    source_table = s.source_table,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    channel_key, account_id_norm, campaign_id, ad_group_id, ad_id, stat_date,
    action_type, action_count, action_value, source_table, load_ts
  ) VALUES (
    s.channel_key, s.account_id_norm, s.campaign_id, s.ad_group_id, s.ad_id, s.stat_date,
    s.action_type, s.action_count, s.action_value, s.source_table, s.load_ts
  );

  -- 3) Creative snapshot -> stg.ads_creative_snapshot
  MERGE `your-gcp-project-id.stg.ads_creative_snapshot` t
  USING (
    WITH unioned AS (
      SELECT
        'META' AS channel_key,
        account_id AS account_id_norm,
        ad_id,
        creative_id,
        creative_name,
        body_text,
        headline,
        description_text,
        call_to_action,
        thumbnail_url,
        TO_HEX(SHA256(CONCAT(
          IFNULL(creative_name, ''), '|',
          IFNULL(body_text, ''), '|',
          IFNULL(headline, ''), '|',
          IFNULL(description_text, ''), '|',
          IFNULL(call_to_action, ''), '|',
          IFNULL(thumbnail_url, '')
        ))) AS content_hash,
        TIMESTAMP(collected_date) AS valid_from_ts,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.meta_ads_creative_raw`
      WHERE collected_date BETWEEN p_start_date AND p_end_date

      UNION ALL

      SELECT
        'GOOGLE_ADS' AS channel_key,
        customer_id AS account_id_norm,
        ad_id,
        creative_id,
        creative_name,
        description_1 AS body_text,
        headline_1 AS headline,
        description_2 AS description_text,
        call_to_action,
        NULL AS thumbnail_url,
        TO_HEX(SHA256(CONCAT(
          IFNULL(creative_name, ''), '|',
          IFNULL(headline_1, ''), '|',
          IFNULL(headline_2, ''), '|',
          IFNULL(headline_3, ''), '|',
          IFNULL(description_1, ''), '|',
          IFNULL(description_2, ''), '|',
          IFNULL(call_to_action, '')
        ))) AS content_hash,
        TIMESTAMP(collected_date) AS valid_from_ts,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.google_ads_creative_raw`
      WHERE collected_date BETWEEN p_start_date AND p_end_date

      UNION ALL

      SELECT
        'TIKTOK_ADS' AS channel_key,
        advertiser_id AS account_id_norm,
        ad_id,
        creative_id,
        creative_name,
        body_text,
        NULL AS headline,
        NULL AS description_text,
        call_to_action,
        thumbnail_url,
        TO_HEX(SHA256(CONCAT(
          IFNULL(creative_name, ''), '|',
          IFNULL(body_text, ''), '|',
          IFNULL(call_to_action, ''), '|',
          IFNULL(thumbnail_url, ''), '|',
          IFNULL(video_url, '')
        ))) AS content_hash,
        TIMESTAMP(collected_date) AS valid_from_ts,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.tiktok_ads_creative_raw`
      WHERE collected_date BETWEEN p_start_date AND p_end_date

      UNION ALL

      SELECT
        'NAVER_ADS' AS channel_key,
        account_id AS account_id_norm,
        ad_id,
        creative_id,
        creative_name,
        body_text,
        headline,
        CAST(NULL AS STRING) AS description_text,
        CAST(NULL AS STRING) AS call_to_action,
        thumbnail_url,
        TO_HEX(SHA256(CONCAT(
          IFNULL(creative_name, ''), '|',
          IFNULL(body_text, ''), '|',
          IFNULL(headline, ''), '|',
          IFNULL(thumbnail_url, '')
        ))) AS content_hash,
        TIMESTAMP(collected_date) AS valid_from_ts,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.naver_ads_creative_raw`
      WHERE collected_date BETWEEN p_start_date AND p_end_date
    ),
    dedup AS (
      SELECT *
      FROM unioned
      WHERE creative_id IS NOT NULL AND creative_id != '' AND ad_id IS NOT NULL AND ad_id != ''
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY channel_key, account_id_norm, ad_id, creative_id, valid_from_ts
        ORDER BY load_ts DESC
      ) = 1
    )
    SELECT * FROM dedup
  ) s
  ON t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.ad_id = s.ad_id
 AND t.creative_id = s.creative_id
 AND t.valid_from_ts = s.valid_from_ts
 AND t.valid_from_ts >= TIMESTAMP(p_start_date) AND t.valid_from_ts < TIMESTAMP(DATE_ADD(p_end_date, INTERVAL 1 DAY))
  WHEN MATCHED THEN UPDATE SET
    creative_name = s.creative_name,
    body_text = s.body_text,
    headline = s.headline,
    description_text = s.description_text,
    call_to_action = s.call_to_action,
    thumbnail_url = s.thumbnail_url,
    content_hash = s.content_hash,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    channel_key, account_id_norm, ad_id, creative_id, creative_name, body_text, headline,
    description_text, call_to_action, thumbnail_url, content_hash, valid_from_ts, load_ts
  ) VALUES (
    s.channel_key, s.account_id_norm, s.ad_id, s.creative_id, s.creative_name, s.body_text, s.headline,
    s.description_text, s.call_to_action, s.thumbnail_url, s.content_hash, s.valid_from_ts, s.load_ts
  );

  -- 4) Creative text -> stg.ads_creative_text (disabled: assets-only creative policy)
  MERGE `your-gcp-project-id.stg.ads_creative_text` t
  USING (
    SELECT
      CAST(NULL AS STRING) AS channel_key,
      CAST(NULL AS STRING) AS account_id_norm,
      CAST(NULL AS STRING) AS ad_id,
      CAST(NULL AS STRING) AS creative_id,
      CAST(NULL AS STRING) AS text_type,
      CAST(NULL AS INT64) AS text_seq,
      CAST(NULL AS STRING) AS text_content,
      CAST(NULL AS STRING) AS language,
      CAST(NULL AS TIMESTAMP) AS valid_from_ts,
      CAST(NULL AS TIMESTAMP) AS load_ts
    FROM (SELECT 1) AS _
    WHERE FALSE
  ) s
  ON FALSE
  WHEN NOT MATCHED THEN INSERT (
    channel_key, account_id_norm, ad_id, creative_id, text_type, text_seq,
    text_content, language, valid_from_ts, load_ts
  ) VALUES (
    s.channel_key, s.account_id_norm, s.ad_id, s.creative_id, s.text_type, s.text_seq,
    s.text_content, s.language, s.valid_from_ts, s.load_ts
  );

  -- 5) Creative asset -> stg.ads_creative_asset
  MERGE `your-gcp-project-id.stg.ads_creative_asset` t
  USING (
    WITH meta_assets_json AS (
      SELECT
        'META' AS channel_key,
        m.account_id AS account_id_norm,
        m.ad_id,
        m.creative_id,
        UPPER(COALESCE(NULLIF(JSON_VALUE(a, '$.asset_type'), ''), 'IMAGE')) AS asset_type,
        off + 1 AS asset_seq,
        COALESCE(JSON_VALUE(a, '$.asset_url'), JSON_VALUE(a, '$.url')) AS asset_url,
        COALESCE(JSON_VALUE(a, '$.thumbnail_url'), m.thumbnail_url) AS thumbnail_url,
        JSON_VALUE(a, '$.image_hash') AS image_hash,
        JSON_VALUE(a, '$.video_id') AS video_id,
        SAFE_CAST(JSON_VALUE(a, '$.width') AS INT64) AS width,
        SAFE_CAST(JSON_VALUE(a, '$.height') AS INT64) AS height,
        SAFE_CAST(JSON_VALUE(a, '$.duration') AS INT64) AS duration_sec,
        TIMESTAMP(m.collected_date) AS valid_from_ts,
        COALESCE(m.source_extract_ts, m.ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.meta_ads_creative_raw` m,
      UNNEST(IFNULL(JSON_QUERY_ARRAY(m.assets_json), CAST([] AS ARRAY<JSON>))) a WITH OFFSET off
      WHERE m.collected_date BETWEEN p_start_date AND p_end_date
    ),
    meta_assets_fallback AS (
      SELECT
        'META' AS channel_key,
        account_id AS account_id_norm,
        ad_id,
        creative_id,
        'IMAGE' AS asset_type,
        1 AS asset_seq,
        permanent_image_url AS asset_url,
        thumbnail_url,
        image_hash,
        NULL AS video_id,
        NULL AS width,
        NULL AS height,
        NULL AS duration_sec,
        TIMESTAMP(collected_date) AS valid_from_ts,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.meta_ads_creative_raw`
      WHERE collected_date BETWEEN p_start_date AND p_end_date
      UNION ALL
      SELECT
        'META',
        account_id,
        ad_id,
        creative_id,
        'VIDEO',
        2,
        CAST(NULL AS STRING),
        thumbnail_url,
        NULL,
        video_id,
        NULL,
        NULL,
        NULL,
        TIMESTAMP(collected_date),
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP())
      FROM `your-gcp-project-id.raw_ads.meta_ads_creative_raw`
      WHERE collected_date BETWEEN p_start_date AND p_end_date
    ),
    google_assets AS (
      SELECT
        'GOOGLE_ADS' AS channel_key,
        customer_id AS account_id_norm,
        ad_id,
        creative_id,
        'IMAGE' AS asset_type,
        off + 1 AS asset_seq,
        img AS asset_url,
        CAST(NULL AS STRING) AS thumbnail_url,
        CAST(NULL AS STRING) AS image_hash,
        CAST(NULL AS STRING) AS video_id,
        NULL AS width,
        NULL AS height,
        NULL AS duration_sec,
        TIMESTAMP(collected_date) AS valid_from_ts,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.google_ads_creative_raw`,
      UNNEST(IFNULL(image_urls, CAST([] AS ARRAY<STRING>))) img WITH OFFSET off
      WHERE collected_date BETWEEN p_start_date AND p_end_date
      UNION ALL
      SELECT
        'GOOGLE_ADS',
        customer_id,
        ad_id,
        creative_id,
        'VIDEO',
        off + 1,
        CAST(NULL AS STRING),
        CAST(NULL AS STRING),
        CAST(NULL AS STRING),
        vid,
        NULL,
        NULL,
        NULL,
        TIMESTAMP(collected_date),
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP())
      FROM `your-gcp-project-id.raw_ads.google_ads_creative_raw`,
      UNNEST(IFNULL(youtube_video_ids, CAST([] AS ARRAY<STRING>))) vid WITH OFFSET off
      WHERE collected_date BETWEEN p_start_date AND p_end_date
    ),
    tiktok_assets AS (
      SELECT
        'TIKTOK_ADS' AS channel_key,
        advertiser_id AS account_id_norm,
        ad_id,
        creative_id,
        'IMAGE' AS asset_type,
        1 AS asset_seq,
        image_url AS asset_url,
        thumbnail_url,
        CAST(NULL AS STRING) AS image_hash,
        CAST(NULL AS STRING) AS video_id,
        NULL AS width,
        NULL AS height,
        NULL AS duration_sec,
        TIMESTAMP(collected_date) AS valid_from_ts,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.tiktok_ads_creative_raw`
      WHERE collected_date BETWEEN p_start_date AND p_end_date
      UNION ALL
      SELECT
        'TIKTOK_ADS',
        advertiser_id,
        ad_id,
        creative_id,
        'VIDEO',
        2,
        video_url,
        thumbnail_url,
        CAST(NULL AS STRING),
        video_id,
        NULL,
        NULL,
        NULL,
        TIMESTAMP(collected_date),
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP())
      FROM `your-gcp-project-id.raw_ads.tiktok_ads_creative_raw`
      WHERE collected_date BETWEEN p_start_date AND p_end_date
    ),
    unioned AS (
      SELECT * FROM meta_assets_json
      UNION ALL SELECT * FROM meta_assets_fallback
      UNION ALL SELECT * FROM google_assets
      UNION ALL SELECT * FROM tiktok_assets
    ),
    filtered AS (
      SELECT *
      FROM unioned
      WHERE creative_id IS NOT NULL
        AND creative_id != ''
        AND ad_id IS NOT NULL
        AND ad_id != ''
        AND (
          (asset_url IS NOT NULL AND TRIM(asset_url) != '')
          OR (video_id IS NOT NULL AND TRIM(video_id) != '')
          OR (thumbnail_url IS NOT NULL AND TRIM(thumbnail_url) != '')
          OR (image_hash IS NOT NULL AND TRIM(image_hash) != '')
        )
    ),
    dedup AS (
      SELECT *
      FROM filtered
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY channel_key, account_id_norm, ad_id, creative_id, asset_type, asset_seq, valid_from_ts
        ORDER BY load_ts DESC
      ) = 1
    )
    SELECT * FROM dedup
  ) s
  ON t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.ad_id = s.ad_id
 AND t.creative_id = s.creative_id
 AND t.asset_type = s.asset_type
 AND t.asset_seq = s.asset_seq
 AND t.valid_from_ts = s.valid_from_ts
 AND t.valid_from_ts >= TIMESTAMP(p_start_date) AND t.valid_from_ts < TIMESTAMP(DATE_ADD(p_end_date, INTERVAL 1 DAY))
  WHEN MATCHED THEN UPDATE SET
    asset_url = s.asset_url,
    thumbnail_url = s.thumbnail_url,
    image_hash = s.image_hash,
    video_id = s.video_id,
    width = s.width,
    height = s.height,
    duration_sec = s.duration_sec,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    channel_key, account_id_norm, ad_id, creative_id, asset_type, asset_seq,
    asset_url, thumbnail_url, image_hash, video_id, width, height, duration_sec, valid_from_ts, load_ts
  ) VALUES (
    s.channel_key, s.account_id_norm, s.ad_id, s.creative_id, s.asset_type, s.asset_seq,
    s.asset_url, s.thumbnail_url, s.image_hash, s.video_id, s.width, s.height, s.duration_sec, s.valid_from_ts, s.load_ts
  );

  -- 6) GA4 daily aggregation -> stg.web_event_daily
  MERGE `your-gcp-project-id.stg.web_event_daily` t
  USING (
    SELECT
      event_date,
      property_id,
      source,
      medium,
      campaign,
      event_name,
      COUNT(DISTINCT user_pseudo_id) AS users,
      COUNT(DISTINCT session_id) AS sessions,
      COUNT(*) AS event_count,
      CAST(NULL AS NUMERIC) AS event_value,
      MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP())) AS load_ts
    FROM `your-gcp-project-id.raw_web.ga4_events_raw`
    WHERE event_date BETWEEN p_start_date AND p_end_date
    GROUP BY event_date, property_id, source, medium, campaign, event_name
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
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    event_date, property_id, source, medium, campaign, event_name, users, sessions, event_count, event_value, load_ts
  ) VALUES (
    s.event_date, s.property_id, s.source, s.medium, s.campaign, s.event_name, s.users, s.sessions, s.event_count, s.event_value, s.load_ts
  );

  -- 7) Orders -> stg.order_line
  MERGE `your-gcp-project-id.stg.order_line` t
  USING (
    WITH unioned AS (
      SELECT
        'SALES' AS order_source,
        source_system,
        order_id,
        order_line_id,
        order_ts,
        order_date,
        IF(customer_email IS NULL OR TRIM(customer_email) = '', NULL, TO_HEX(SHA256(LOWER(TRIM(customer_email))))) AS customer_email_hash,
        IF(customer_phone IS NULL OR TRIM(customer_phone) = '', NULL, TO_HEX(SHA256(REGEXP_REPLACE(customer_phone, r'[^0-9+]', '')))) AS customer_phone_hash,
        product_id,
        CAST(NULL AS STRING) AS venue_name,
        quantity,
        gross_amount,
        discount_amount,
        net_amount,
        currency,
        payment_status,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_commerce.sales_orders_raw`
      WHERE order_date BETWEEN p_start_date AND p_end_date

      UNION ALL

      SELECT
        'FEVER',
        CAST(NULL AS STRING) AS source_system,
        fever_order_id AS order_id,
        ticket_id AS order_line_id,
        order_ts,
        order_date,
        IF(customer_email IS NULL OR TRIM(customer_email) = '', NULL, TO_HEX(SHA256(LOWER(TRIM(customer_email))))) AS customer_email_hash,
        NULL AS customer_phone_hash,
        event_id AS product_id,
        venue_name,
        quantity,
        gross_amount,
        discount_amount,
        net_amount,
        currency,
        payment_status,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_commerce.fever_ticket_orders_raw`
      WHERE order_date BETWEEN p_start_date AND p_end_date
    ),
    dedup AS (
      SELECT *
      FROM unioned
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY order_source, order_id, order_line_id
        ORDER BY load_ts DESC
      ) = 1
    )
    SELECT * FROM dedup
  ) s
  ON t.order_source = s.order_source
 AND t.order_id = s.order_id
 AND t.order_line_id = s.order_line_id
 AND t.order_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    order_ts = s.order_ts,
    order_date = s.order_date,
    source_system = s.source_system,
    customer_email_hash = s.customer_email_hash,
    customer_phone_hash = s.customer_phone_hash,
    product_id = s.product_id,
    venue_name = s.venue_name,
    quantity = s.quantity,
    gross_amount = s.gross_amount,
    discount_amount = s.discount_amount,
    net_amount = s.net_amount,
    currency = s.currency,
    payment_status = s.payment_status,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    order_source, source_system, order_id, order_line_id, order_ts, order_date, customer_email_hash, customer_phone_hash,
    product_id, venue_name, quantity, gross_amount, discount_amount, net_amount, currency, payment_status, load_ts
  ) VALUES (
    s.order_source, s.source_system, s.order_id, s.order_line_id, s.order_ts, s.order_date, s.customer_email_hash, s.customer_phone_hash,
    s.product_id, s.venue_name, s.quantity, s.gross_amount, s.discount_amount, s.net_amount, s.currency, s.payment_status, s.load_ts
  );

  -- 8) Survey -> stg.survey_response
  MERGE `your-gcp-project-id.stg.survey_response` t
  USING (
    SELECT
      response_date,
      response_ts,
      survey_source,
      response_id,
      IF(customer_email IS NULL OR TRIM(customer_email) = '', NULL, TO_HEX(SHA256(LOWER(TRIM(customer_email))))) AS customer_email_hash,
      IF(customer_phone IS NULL OR TRIM(customer_phone) = '', NULL, TO_HEX(SHA256(REGEXP_REPLACE(customer_phone, r'[^0-9+]', '')))) AS customer_phone_hash,
      survey_id,
      question_id,
      answer_type,
      answer_text,
      answer_score,
      COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
    FROM `your-gcp-project-id.raw_feedback.survey_responses_raw`
    WHERE response_date BETWEEN p_start_date AND p_end_date
  ) s
  ON t.survey_source = s.survey_source
 AND t.response_id = s.response_id
 AND t.question_id = s.question_id
 AND t.response_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    response_date = s.response_date,
    response_ts = s.response_ts,
    customer_email_hash = s.customer_email_hash,
    customer_phone_hash = s.customer_phone_hash,
    survey_id = s.survey_id,
    answer_type = s.answer_type,
    answer_text = s.answer_text,
    answer_score = s.answer_score,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    response_date, response_ts, survey_source, response_id, customer_email_hash, customer_phone_hash,
    survey_id, question_id, answer_type, answer_text, answer_score, load_ts
  ) VALUES (
    s.response_date, s.response_ts, s.survey_source, s.response_id, s.customer_email_hash, s.customer_phone_hash,
    s.survey_id, s.question_id, s.answer_type, s.answer_text, s.answer_score, s.load_ts
  );
END

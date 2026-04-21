BEGIN
  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.stg.ads_campaign_breakdown_daily` (
    stat_date DATE,
    channel_key STRING,
    account_id_norm STRING,
    campaign_id STRING,
    campaign_name STRING,
    breakdown_key STRING,
    breakdown_value STRING,
    impressions INT64,
    clicks INT64,
    spend NUMERIC,
    conversion_count FLOAT64,
    conversion_value NUMERIC,
    attribution_setting STRING,
    source_table STRING,
    load_ts TIMESTAMP
  )
  PARTITION BY stat_date
  CLUSTER BY channel_key, account_id_norm, campaign_id, breakdown_key
  OPTIONS (require_partition_filter = TRUE);

  DELETE FROM `your-gcp-project-id.stg.ads_campaign_breakdown_daily`
  WHERE stat_date < DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);

  MERGE `your-gcp-project-id.stg.ads_campaign_breakdown_daily` t
  USING (
    WITH meta_src AS (
      SELECT
        'META' AS channel_key,
        REGEXP_REPLACE(account_id, r'^act_', '') AS account_id_norm,
        COALESCE(campaign_id, '') AS campaign_id,
        ANY_VALUE(campaign_name) AS campaign_name,
        stat_date,
        breakdown_key,
        COALESCE(NULLIF(TRIM(breakdown_value), ''), 'Unknown') AS breakdown_value,
        SUM(IFNULL(impressions, 0)) AS impressions,
        SUM(IFNULL(clicks, 0)) AS clicks,
        SUM(IFNULL(spend, 0)) AS spend,
        CAST(NULL AS FLOAT64) AS conversion_count,
        CAST(NULL AS NUMERIC) AS conversion_value,
        ANY_VALUE(attribution_setting) AS attribution_setting,
        'raw_ads.meta_ads_campaign_breakdown_raw' AS source_table,
        MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP())) AS load_ts
      FROM `your-gcp-project-id.raw_ads.meta_ads_campaign_breakdown_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
        AND breakdown_key IN ('age', 'gender', 'country', 'region')
        AND campaign_id IS NOT NULL
        AND TRIM(campaign_id) != ''
        AND breakdown_value IS NOT NULL
        AND TRIM(breakdown_value) != ''
      GROUP BY channel_key, account_id_norm, campaign_id, stat_date, breakdown_key, breakdown_value
    ),
    google_src AS (
      SELECT
        'GOOGLE_ADS' AS channel_key,
        customer_id AS account_id_norm,
        COALESCE(campaign_id, '') AS campaign_id,
        ANY_VALUE(campaign_name) AS campaign_name,
        stat_date,
        CASE
          WHEN breakdown_key = 'age_range' THEN 'age'
          ELSE breakdown_key
        END AS breakdown_key,
        CASE
          WHEN breakdown_key = 'age_range' THEN
            CASE breakdown_value
              WHEN 'AGE_RANGE_18_24' THEN '18-24'
              WHEN 'AGE_RANGE_25_34' THEN '25-34'
              WHEN 'AGE_RANGE_35_44' THEN '35-44'
              WHEN 'AGE_RANGE_45_54' THEN '45-54'
              WHEN 'AGE_RANGE_55_64' THEN '55-64'
              WHEN 'AGE_RANGE_65_UP' THEN '65+'
              WHEN 'AGE_RANGE_UNDETERMINED' THEN 'Unknown'
              ELSE 'Unknown'
            END
          ELSE COALESCE(NULLIF(TRIM(breakdown_value), ''), 'Unknown')
        END AS breakdown_value,
        SUM(IFNULL(impressions, 0)) AS impressions,
        SUM(IFNULL(clicks, 0)) AS clicks,
        CAST(SAFE_DIVIDE(SUM(IFNULL(cost_micros, 0)), 1000000) AS NUMERIC) AS spend,
        SUM(IFNULL(conversions, 0)) AS conversion_count,
        SUM(IFNULL(conversions_value, 0)) AS conversion_value,
        CAST(NULL AS STRING) AS attribution_setting,
        'raw_ads.google_ads_campaign_breakdown_raw' AS source_table,
        MAX(COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP())) AS load_ts
      FROM `your-gcp-project-id.raw_ads.google_ads_campaign_breakdown_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
        AND breakdown_key IN ('age_range', 'gender', 'geo_target_country', 'geo_target_region')
        AND campaign_id IS NOT NULL
        AND TRIM(campaign_id) != ''
        AND breakdown_value IS NOT NULL
        AND TRIM(breakdown_value) != ''
      GROUP BY channel_key, account_id_norm, campaign_id, stat_date, breakdown_key, breakdown_value
    ),
    src AS (
      SELECT * FROM meta_src
      UNION ALL
      SELECT * FROM google_src
    )
    SELECT *
    FROM src
  ) s
  ON t.stat_date = s.stat_date
 AND t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.campaign_id = s.campaign_id
 AND t.breakdown_key = s.breakdown_key
 AND t.breakdown_value = s.breakdown_value
  WHEN MATCHED THEN UPDATE SET
    campaign_name = s.campaign_name,
    impressions = s.impressions,
    clicks = s.clicks,
    spend = s.spend,
    conversion_count = s.conversion_count,
    conversion_value = s.conversion_value,
    attribution_setting = s.attribution_setting,
    source_table = s.source_table,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    stat_date,
    channel_key,
    account_id_norm,
    campaign_id,
    campaign_name,
    breakdown_key,
    breakdown_value,
    impressions,
    clicks,
    spend,
    conversion_count,
    conversion_value,
    attribution_setting,
    source_table,
    load_ts
  ) VALUES (
    s.stat_date,
    s.channel_key,
    s.account_id_norm,
    s.campaign_id,
    s.campaign_name,
    s.breakdown_key,
    s.breakdown_value,
    s.impressions,
    s.clicks,
    s.spend,
    s.conversion_count,
    s.conversion_value,
    s.attribution_setting,
    s.source_table,
    s.load_ts
  );
END

BEGIN
  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.core.fact_marketing_campaign_breakdown_daily` (
    stat_date DATE,
    branch_id STRING,
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
    load_ts TIMESTAMP
  )
  PARTITION BY stat_date
  CLUSTER BY branch_id, channel_key, campaign_id, breakdown_key
  OPTIONS (require_partition_filter = TRUE);

  DELETE FROM `your-gcp-project-id.core.fact_marketing_campaign_breakdown_daily`
  WHERE stat_date < DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);

  MERGE `your-gcp-project-id.core.fact_marketing_campaign_breakdown_daily` t
  USING (
    WITH src AS (
      SELECT
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
        s.load_ts,
        m.branch_id,
        m.effective_start_date,
        m.updated_at
      FROM `your-gcp-project-id.stg.ads_campaign_breakdown_daily` s
      LEFT JOIN `your-gcp-project-id.governance.account_branch_map` m
        ON m.channel_key = s.channel_key
       AND m.account_id_norm = s.account_id_norm
       AND s.stat_date BETWEEN m.effective_start_date AND COALESCE(m.effective_end_date, DATE '9999-12-31')
       AND m.is_active = TRUE
      WHERE s.stat_date BETWEEN p_start_date AND p_end_date
    ),
    dedup AS (
      SELECT
        stat_date,
        COALESCE(branch_id, 'UNKNOWN') AS branch_id,
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
        load_ts
      FROM src
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY stat_date, channel_key, account_id_norm, campaign_id, breakdown_key, breakdown_value
        ORDER BY effective_start_date DESC, updated_at DESC, load_ts DESC
      ) = 1
    )
    SELECT * FROM dedup
  ) s
  ON t.stat_date = s.stat_date
 AND t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND t.campaign_id = s.campaign_id
 AND t.breakdown_key = s.breakdown_key
 AND t.breakdown_value = s.breakdown_value
  WHEN MATCHED THEN UPDATE SET
    branch_id = s.branch_id,
    campaign_name = s.campaign_name,
    impressions = s.impressions,
    clicks = s.clicks,
    spend = s.spend,
    conversion_count = s.conversion_count,
    conversion_value = s.conversion_value,
    attribution_setting = s.attribution_setting,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
    stat_date,
    branch_id,
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
    load_ts
  ) VALUES (
    s.stat_date,
    s.branch_id,
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
    s.load_ts
  );

  CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_campaign_breakdown_recent` AS
  WITH recent AS (
    SELECT
      f.stat_date AS report_date,
      f.branch_id,
      b.branch_name,
      f.channel_key,
      f.campaign_id,
      f.campaign_name,
      f.breakdown_key,
      f.breakdown_value,
      CASE
        WHEN f.breakdown_key IN ('geo_target_country', 'geo_target_region')
          THEN COALESCE(g.display_name, 'Unknown')
        ELSE COALESCE(f.breakdown_value, 'Unknown')
      END AS breakdown_value_name,
      CASE
        WHEN f.breakdown_key IN ('geo_target_country', 'geo_target_region')
          THEN COALESCE(g.display_name_ko, '미확인')
        ELSE COALESCE(f.breakdown_value, 'Unknown')
      END AS breakdown_value_name_ko,
      f.impressions,
      f.clicks,
      f.spend AS spend_native,
      f.conversion_count AS conversions,
      f.conversion_value AS conversion_value_native,
      SAFE_DIVIDE(f.clicks, NULLIF(f.impressions, 0)) AS ctr,
      SAFE_DIVIDE(f.spend, NULLIF(f.clicks, 0)) AS cpc
    FROM `your-gcp-project-id.core.fact_marketing_campaign_breakdown_daily` f
    LEFT JOIN `your-gcp-project-id.core.dim_branch` b
      ON b.branch_id = f.branch_id
    LEFT JOIN `your-gcp-project-id.governance.geo_target_map` g
      ON g.geo_target_constant_id = f.breakdown_value
     AND f.breakdown_key IN ('geo_target_country', 'geo_target_region')
    WHERE f.stat_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  )
  SELECT *
  FROM recent;
END

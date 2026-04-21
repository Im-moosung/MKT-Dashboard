BEGIN
  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.core.fact_marketing_asset_daily` (
    stat_date DATE,
    channel_key STRING,
    account_id_norm STRING,
    campaign_id STRING,
    campaign_channel_type STRING,
    ad_group_id STRING,
    ad_id STRING,
    asset_group_id STRING,
    asset_id STRING,
    field_type STRING,
    performance_label STRING,
    is_pmax BOOL,
    impressions INT64,
    clicks INT64,
    spend NUMERIC,
    conversion_count FLOAT64,
    conversion_value NUMERIC,
    source_view STRING,
    load_ts TIMESTAMP,
    branch_id STRING
  )
  PARTITION BY stat_date
  CLUSTER BY branch_id, channel_key, campaign_id, asset_id
  OPTIONS (require_partition_filter = TRUE);

  DELETE FROM `your-gcp-project-id.core.fact_marketing_asset_daily`
  WHERE stat_date BETWEEN p_start_date AND p_end_date
    AND channel_key = 'GOOGLE_ADS';

  MERGE `your-gcp-project-id.core.fact_marketing_asset_daily` t
  USING (
    SELECT
      s.stat_date,
      s.channel_key,
      s.account_id_norm,
      s.campaign_id,
      s.campaign_channel_type,
      s.ad_group_id,
      s.ad_id,
      s.asset_group_id,
      s.asset_id,
      s.field_type,
      s.performance_label,
      s.is_pmax,
      s.impressions,
      s.clicks,
      s.spend,
      s.conversion_count,
      s.conversion_value,
      s.source_view,
      s.load_ts,
      COALESCE(m.branch_id, 'UNKNOWN') AS branch_id
    FROM `your-gcp-project-id.stg.ads_asset_performance_daily` s
    LEFT JOIN `your-gcp-project-id.governance.account_branch_map` m
      ON m.channel_key = s.channel_key
     AND m.account_id_norm = s.account_id_norm
     AND s.stat_date BETWEEN m.effective_start_date AND COALESCE(m.effective_end_date, DATE '9999-12-31')
     AND m.is_active = TRUE
    WHERE s.stat_date BETWEEN p_start_date AND p_end_date
  ) s
  ON t.stat_date = s.stat_date
 AND t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND IFNULL(t.campaign_id, '') = IFNULL(s.campaign_id, '')
 AND IFNULL(t.ad_group_id, '') = IFNULL(s.ad_group_id, '')
 AND IFNULL(t.ad_id, '') = IFNULL(s.ad_id, '')
 AND IFNULL(t.asset_group_id, '') = IFNULL(s.asset_group_id, '')
 AND t.asset_id = s.asset_id
 AND t.field_type = s.field_type
 AND IFNULL(t.source_view, '') = IFNULL(s.source_view, '')
 AND t.stat_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    performance_label = s.performance_label,
    is_pmax = s.is_pmax,
    campaign_channel_type = s.campaign_channel_type,
    impressions = s.impressions,
    clicks = s.clicks,
    spend = s.spend,
    conversion_count = s.conversion_count,
    conversion_value = s.conversion_value,
    load_ts = s.load_ts,
    branch_id = s.branch_id
  WHEN NOT MATCHED THEN INSERT (
    stat_date,
    channel_key,
    account_id_norm,
    campaign_id,
    campaign_channel_type,
    ad_group_id,
    ad_id,
    asset_group_id,
    asset_id,
    field_type,
    performance_label,
    is_pmax,
    impressions,
    clicks,
    spend,
    conversion_count,
    conversion_value,
    source_view,
    load_ts,
    branch_id
  ) VALUES (
    s.stat_date,
    s.channel_key,
    s.account_id_norm,
    s.campaign_id,
    s.campaign_channel_type,
    s.ad_group_id,
    s.ad_id,
    s.asset_group_id,
    s.asset_id,
    s.field_type,
    s.performance_label,
    s.is_pmax,
    s.impressions,
    s.clicks,
    s.spend,
    s.conversion_count,
    s.conversion_value,
    s.source_view,
    s.load_ts,
    s.branch_id
  );
END

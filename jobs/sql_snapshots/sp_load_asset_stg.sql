BEGIN
  CREATE TABLE IF NOT EXISTS `your-gcp-project-id.stg.ads_asset_performance_daily` (
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
    stat_date DATE,
    impressions INT64,
    clicks INT64,
    spend NUMERIC,
    conversion_count FLOAT64,
    conversion_value NUMERIC,
    is_pmax BOOL,
    source_view STRING,
    load_ts TIMESTAMP
  )
  PARTITION BY stat_date
  CLUSTER BY channel_key, account_id_norm, campaign_id, asset_id
  OPTIONS (require_partition_filter = TRUE);

  DELETE FROM `your-gcp-project-id.stg.ads_asset_performance_daily`
  WHERE stat_date BETWEEN p_start_date AND p_end_date
    AND channel_key = 'GOOGLE_ADS';

  MERGE `your-gcp-project-id.stg.ads_asset_performance_daily` t
  USING (
    WITH raw_src AS (
      SELECT
        'GOOGLE_ADS' AS channel_key,
        customer_id AS account_id_norm,
        campaign_id,
        UPPER(COALESCE(campaign_channel_type, JSON_VALUE(source_payload, '$.campaign.advertising_channel_type'))) AS campaign_channel_type,
        ad_group_id,
        ad_id,
        asset_group_id,
        asset_id,
        field_type,
        performance_label,
        stat_date,
        impressions,
        clicks,
        SAFE_DIVIDE(CAST(cost_micros AS NUMERIC), 1000000) AS spend,
        conversions AS conversion_count,
        conversions_value AS conversion_value,
        is_pmax,
        source_view,
        COALESCE(source_extract_ts, ingestion_ts, CURRENT_TIMESTAMP()) AS load_ts
      FROM `your-gcp-project-id.raw_ads.google_ads_asset_performance_raw`
      WHERE stat_date BETWEEN p_start_date AND p_end_date
        AND asset_id IS NOT NULL
        AND asset_id != ''
    ),
    src AS (
      SELECT *
      FROM raw_src
      WHERE (
          (is_pmax = TRUE AND UPPER(field_type) IN ('MARKETING_IMAGE', 'SQUARE_MARKETING_IMAGE', 'PORTRAIT_MARKETING_IMAGE', 'YOUTUBE_VIDEO'))
          OR (
            is_pmax = FALSE
            AND campaign_channel_type = 'SEARCH'
            AND UPPER(field_type) IN ('HEADLINE', 'DESCRIPTION')
          )
          OR (
            is_pmax = FALSE
            AND campaign_channel_type IS NOT NULL
            AND campaign_channel_type != 'SEARCH'
            AND UPPER(field_type) IN ('MARKETING_IMAGE', 'SQUARE_MARKETING_IMAGE', 'PORTRAIT_MARKETING_IMAGE', 'YOUTUBE_VIDEO')
          )
        )
    ),
    dedup AS (
      SELECT *
      FROM src
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY
          channel_key,
          account_id_norm,
          IFNULL(campaign_id, ''),
          IFNULL(ad_group_id, ''),
          IFNULL(ad_id, ''),
          IFNULL(asset_group_id, ''),
          asset_id,
          field_type,
          stat_date,
          IFNULL(source_view, '')
        ORDER BY load_ts DESC
      ) = 1
    )
    SELECT * FROM dedup
  ) s
  ON t.channel_key = s.channel_key
 AND t.account_id_norm = s.account_id_norm
 AND IFNULL(t.campaign_id, '') = IFNULL(s.campaign_id, '')
 AND IFNULL(t.ad_group_id, '') = IFNULL(s.ad_group_id, '')
 AND IFNULL(t.ad_id, '') = IFNULL(s.ad_id, '')
 AND IFNULL(t.asset_group_id, '') = IFNULL(s.asset_group_id, '')
 AND t.asset_id = s.asset_id
 AND t.field_type = s.field_type
 AND IFNULL(t.source_view, '') = IFNULL(s.source_view, '')
 AND t.stat_date = s.stat_date
 AND t.stat_date BETWEEN p_start_date AND p_end_date
  WHEN MATCHED THEN UPDATE SET
    performance_label = s.performance_label,
    impressions = s.impressions,
    clicks = s.clicks,
    spend = s.spend,
    conversion_count = s.conversion_count,
    conversion_value = s.conversion_value,
    is_pmax = s.is_pmax,
    campaign_channel_type = s.campaign_channel_type,
    load_ts = s.load_ts
  WHEN NOT MATCHED THEN INSERT (
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
    stat_date,
    impressions,
    clicks,
    spend,
    conversion_count,
    conversion_value,
    is_pmax,
    source_view,
    load_ts
  ) VALUES (
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
    s.stat_date,
    s.impressions,
    s.clicks,
    s.spend,
    s.conversion_count,
    s.conversion_value,
    s.is_pmax,
    s.source_view,
    s.load_ts
  );
END

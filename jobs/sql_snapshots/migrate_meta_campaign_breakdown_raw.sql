-- One-time migration: rename canonical Meta campaign breakdown raw table.
-- Existing legacy table: raw_ads.meta_ads_adset_breakdown_raw
-- New canonical table: raw_ads.meta_ads_campaign_breakdown_raw

CREATE TABLE IF NOT EXISTS `your-gcp-project-id.raw_ads.meta_ads_campaign_breakdown_raw` (
  ingestion_id STRING,
  ingestion_ts TIMESTAMP,
  source_extract_ts TIMESTAMP,
  account_id STRING,
  account_name STRING,
  campaign_id STRING,
  campaign_name STRING,
  ad_group_id STRING,
  ad_group_name STRING,
  stat_date DATE,
  breakdown_key STRING,
  breakdown_value STRING,
  age STRING,
  gender STRING,
  country STRING,
  region STRING,
  publisher_platform STRING,
  platform_position STRING,
  attribution_setting STRING,
  impressions INT64,
  clicks INT64,
  link_clicks INT64,
  spend NUMERIC,
  actions_json JSON,
  action_values_json JSON,
  conversions_json JSON,
  conversion_values_json JSON,
  source_payload JSON
)
PARTITION BY stat_date
CLUSTER BY account_id, campaign_id, breakdown_key
OPTIONS (
  require_partition_filter = TRUE,
  description = 'Meta Ads campaign-level breakdown raw performance'
);

INSERT INTO `your-gcp-project-id.raw_ads.meta_ads_campaign_breakdown_raw`
SELECT *
FROM `your-gcp-project-id.raw_ads.meta_ads_adset_breakdown_raw`
WHERE stat_date BETWEEN DATE '2000-01-01' AND DATE '2100-01-01'
  AND NOT EXISTS (
    SELECT 1
    FROM `your-gcp-project-id.raw_ads.meta_ads_campaign_breakdown_raw` t
    WHERE t.ingestion_id = `your-gcp-project-id.raw_ads.meta_ads_adset_breakdown_raw`.ingestion_id
      AND t.account_id = `your-gcp-project-id.raw_ads.meta_ads_adset_breakdown_raw`.account_id
      AND t.campaign_id = `your-gcp-project-id.raw_ads.meta_ads_adset_breakdown_raw`.campaign_id
      AND t.stat_date = `your-gcp-project-id.raw_ads.meta_ads_adset_breakdown_raw`.stat_date
      AND t.breakdown_key = `your-gcp-project-id.raw_ads.meta_ads_adset_breakdown_raw`.breakdown_key
      AND t.breakdown_value = `your-gcp-project-id.raw_ads.meta_ads_adset_breakdown_raw`.breakdown_value
  );

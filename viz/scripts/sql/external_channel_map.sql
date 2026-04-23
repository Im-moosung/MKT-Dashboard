CREATE TABLE IF NOT EXISTS `mimetic-gravity-442013-u4.governance.external_channel_map` (
  raw_code STRING NOT NULL,
  channel_key STRING NOT NULL,
  is_active BOOL NOT NULL,
  notes STRING,
  updated_at TIMESTAMP
)
CLUSTER BY channel_key;

MERGE `mimetic-gravity-442013-u4.governance.external_channel_map` T
USING (
  SELECT raw_code, channel_key, TRUE AS is_active FROM UNNEST([
    STRUCT('1_Meta' AS raw_code, 'META' AS channel_key),
    ('META', 'META'),
    ('2_Google_Search', 'GOOGLE_ADS'),
    ('GOOGLE_SEARCH', 'GOOGLE_ADS'),
    ('3_Google_Display', 'GOOGLE_ADS'),
    ('22_Google_Demand_Gen', 'GOOGLE_DEMAND_GEN'),
    ('7_TikTok', 'TIKTOK_ADS'),
    ('TIKTOK', 'TIKTOK_ADS'),
    ('4_Youtube', 'YOUTUBE'),
    ('YOUTUBE', 'YOUTUBE'),
    ('10_Coupons', 'COUPON'),
    ('14_Affiliate', 'AFFILIATE'),
    ('15_Email', 'EMAIL'),
    ('102_Ambassadors', 'INFLUENCER'),
    ('58_Marketing_Fee', 'OTHER'),
    ('12_Organic_SEO', 'ORGANIC_SEO'),
    ('114_OTA', 'OTA')
  ])
) S
ON T.raw_code = S.raw_code
WHEN MATCHED THEN UPDATE SET channel_key = S.channel_key, is_active = S.is_active, updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (raw_code, channel_key, is_active, updated_at) VALUES (S.raw_code, S.channel_key, S.is_active, CURRENT_TIMESTAMP());

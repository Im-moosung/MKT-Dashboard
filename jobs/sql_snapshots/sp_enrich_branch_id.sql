BEGIN
  CREATE TEMP TABLE tmp_naver_rule_match AS
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
  WHERE rule_rank = 1;

  UPDATE `your-gcp-project-id.core.fact_marketing_daily` t
  SET branch_id = s.branch_id
  FROM (
    SELECT
      f.stat_date,
      f.channel_key,
      f.account_id_norm,
      f.campaign_id,
      f.ad_group_id,
      f.ad_id,
      CASE
        WHEN f.channel_key = 'NAVER_ADS' THEN COALESCE(n.branch_id, 'UNKNOWN')
        ELSE COALESCE(m.branch_id, 'UNKNOWN')
      END AS branch_id
    FROM `your-gcp-project-id.core.fact_marketing_daily` f
    LEFT JOIN `your-gcp-project-id.governance.account_branch_map` m
      ON m.channel_key = f.channel_key
     AND m.account_id_norm = f.account_id_norm
     AND f.stat_date BETWEEN m.effective_start_date AND COALESCE(m.effective_end_date, DATE '9999-12-31')
     AND m.is_active = TRUE
    LEFT JOIN tmp_naver_rule_match n
      ON f.channel_key = 'NAVER_ADS'
     AND n.account_id_norm = f.account_id_norm
     AND n.campaign_id = f.campaign_id
     AND IFNULL(n.ad_group_id, '') = IFNULL(f.ad_group_id, '')
     AND n.stat_date = f.stat_date
    WHERE f.stat_date BETWEEN p_start_date AND p_end_date
  ) s
  WHERE t.stat_date = s.stat_date
    AND t.channel_key = s.channel_key
    AND t.account_id_norm = s.account_id_norm
    AND t.campaign_id = s.campaign_id
    AND t.ad_group_id = s.ad_group_id
    AND t.ad_id = s.ad_id
    AND t.stat_date BETWEEN p_start_date AND p_end_date
    AND IFNULL(t.branch_id, '') != s.branch_id;

  UPDATE `your-gcp-project-id.core.fact_marketing_action_daily` t
  SET branch_id = s.branch_id
  FROM (
    SELECT
      f.stat_date,
      f.channel_key,
      f.account_id_norm,
      f.campaign_id,
      f.ad_group_id,
      f.ad_id,
      f.action_type,
      COALESCE(m.branch_id, 'UNKNOWN') AS branch_id
    FROM `your-gcp-project-id.core.fact_marketing_action_daily` f
    LEFT JOIN `your-gcp-project-id.governance.account_branch_map` m
      ON m.channel_key = f.channel_key
     AND m.account_id_norm = f.account_id_norm
     AND f.stat_date BETWEEN m.effective_start_date AND COALESCE(m.effective_end_date, DATE '9999-12-31')
     AND m.is_active = TRUE
    WHERE f.stat_date BETWEEN p_start_date AND p_end_date
  ) s
  WHERE t.stat_date = s.stat_date
    AND t.channel_key = s.channel_key
    AND t.account_id_norm = s.account_id_norm
    AND t.campaign_id = s.campaign_id
    AND t.ad_group_id = s.ad_group_id
    AND t.ad_id = s.ad_id
    AND t.action_type = s.action_type
    AND t.stat_date BETWEEN p_start_date AND p_end_date
    AND IFNULL(t.branch_id, '') != s.branch_id;

  UPDATE `your-gcp-project-id.core.fact_marketing_campaign_breakdown_daily` t
  SET branch_id = s.branch_id
  FROM (
    SELECT
      f.stat_date,
      f.channel_key,
      f.account_id_norm,
      f.campaign_id,
      f.breakdown_key,
      f.breakdown_value,
      COALESCE(m.branch_id, 'UNKNOWN') AS branch_id
    FROM `your-gcp-project-id.core.fact_marketing_campaign_breakdown_daily` f
    LEFT JOIN `your-gcp-project-id.governance.account_branch_map` m
      ON m.channel_key = f.channel_key
     AND m.account_id_norm = f.account_id_norm
     AND f.stat_date BETWEEN m.effective_start_date AND COALESCE(m.effective_end_date, DATE '9999-12-31')
     AND m.is_active = TRUE
    WHERE f.stat_date BETWEEN p_start_date AND p_end_date
  ) s
  WHERE t.stat_date = s.stat_date
    AND t.channel_key = s.channel_key
    AND t.account_id_norm = s.account_id_norm
    AND t.campaign_id = s.campaign_id
    AND t.breakdown_key = s.breakdown_key
    AND t.breakdown_value = s.breakdown_value
    AND t.stat_date BETWEEN p_start_date AND p_end_date
    AND IFNULL(t.branch_id, '') != s.branch_id;

  UPDATE `your-gcp-project-id.core.fact_marketing_asset_daily` t
  SET branch_id = s.branch_id
  FROM (
    SELECT
      f.stat_date,
      f.channel_key,
      f.account_id_norm,
      f.campaign_id,
      f.ad_group_id,
      f.ad_id,
      f.asset_group_id,
      f.asset_id,
      f.field_type,
      f.source_view,
      COALESCE(m.branch_id, 'UNKNOWN') AS branch_id
    FROM `your-gcp-project-id.core.fact_marketing_asset_daily` f
    LEFT JOIN `your-gcp-project-id.governance.account_branch_map` m
      ON m.channel_key = f.channel_key
     AND m.account_id_norm = f.account_id_norm
     AND f.stat_date BETWEEN m.effective_start_date AND COALESCE(m.effective_end_date, DATE '9999-12-31')
     AND m.is_active = TRUE
    WHERE f.stat_date BETWEEN p_start_date AND p_end_date
  ) s
  WHERE t.stat_date = s.stat_date
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
    AND IFNULL(t.branch_id, '') != s.branch_id;
END

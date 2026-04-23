MERGE `mimetic-gravity-442013-u4.core.dim_branch` T
USING (
  SELECT 'AMNY' AS branch_id, 'New York' AS branch_name, 'US' AS country_code, 'New York' AS city_name, 'America/New_York' AS timezone, 'USD' AS currency, 'ARTE_MUSEUM' AS branch_group, TRUE AS is_active
  UNION ALL SELECT 'DSTX', 'reSOUND New York', 'US', 'New York', 'America/New_York', 'USD', 'RESOUND', TRUE
) S
ON T.branch_id = S.branch_id
WHEN NOT MATCHED THEN
  INSERT (branch_id, branch_name, country_code, city_name, timezone, currency, branch_group, is_active, load_ts)
  VALUES (S.branch_id, S.branch_name, S.country_code, S.city_name, S.timezone, S.currency, S.branch_group, S.is_active, CURRENT_TIMESTAMP());

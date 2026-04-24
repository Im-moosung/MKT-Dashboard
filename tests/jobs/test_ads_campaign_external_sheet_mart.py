from pathlib import Path


SQL_PATH = Path("jobs/sql_snapshots/sp_load_core.sql")


def test_dashboard_campaign_view_unions_external_sheet_ads():
    sql = SQL_PATH.read_text()
    view_start = sql.index("CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_dashboard_campaign_daily`")
    next_view = sql.index("CREATE OR REPLACE VIEW", view_start + 1)
    view_sql = sql[view_start:next_view]

    assert "raw_ads.external_ads_raw" in view_sql
    assert "UNION ALL" in view_sql
    assert "source_tier" in view_sql
    assert "'api_real'" in view_sql
    assert "'sheet'" in view_sql


def test_ads_campaign_cube_exposes_source_tier_dimension():
    cube_sql = Path("viz/cube/schema/AdsCampaign.yml").read_text()

    assert "sourceTier" in cube_sql
    assert "source_tier" in cube_sql


def test_dashboard_campaign_view_does_not_join_partitioned_ad_fact_without_needed_metric():
    sql = SQL_PATH.read_text()
    view_start = sql.index("CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_dashboard_campaign_daily`")
    next_view = sql.index("CREATE OR REPLACE VIEW", view_start + 1)
    view_sql = sql[view_start:next_view]

    assert "core.fact_marketing_daily" not in view_sql


def test_dashboard_campaign_view_does_not_depend_on_naver_contract_view():
    sql = SQL_PATH.read_text()
    view_start = sql.index("CREATE OR REPLACE VIEW `your-gcp-project-id.mart.v_dashboard_campaign_daily`")
    next_view = sql.index("CREATE OR REPLACE VIEW", view_start + 1)
    view_sql = sql[view_start:next_view]

    assert "mart.v_naver_adgroup_daily" not in view_sql

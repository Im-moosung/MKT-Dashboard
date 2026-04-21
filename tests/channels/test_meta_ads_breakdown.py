from New_Data_flow.channels.meta_ads.adapter import (
    META_CAMPAIGN_BREAKDOWN_QUERY_SPECS,
    _build_campaign_breakdown_row,
)


def test_meta_breakdown_specs_include_requested_dimensions():
    flattened = []
    for spec in META_CAMPAIGN_BREAKDOWN_QUERY_SPECS:
        flattened.extend(spec["output_keys"])
    assert "age" in flattened
    assert "gender" in flattened
    assert "country" in flattened
    assert "region" in flattened
    assert "publisher_platform" not in flattened
    assert "platform_position" not in flattened


def test_build_campaign_breakdown_row_happy_path():
    insight = {
        "account_name": "Test Account",
        "campaign_id": "cmp_1",
        "campaign_name": "Campaign",
        "date_start": "2026-02-19",
        "age": "25-34",
        "gender": "female",
        "country": "US",
        "region": "Nevada",
        "attribution_setting": "1d_click",
        "impressions": "100",
        "clicks": "10",
        "inline_link_clicks": "6",
        "spend": "12.34",
        "actions": [{"action_type": "purchase", "value": "1"}],
        "action_values": [{"action_type": "purchase", "value": "99.9"}],
        "conversions": [{"action_type": "purchase", "value": "1"}],
        "conversion_values": [{"action_type": "purchase", "value": "99.9"}],
    }
    row = _build_campaign_breakdown_row(
        insight=insight,
        breakdown_key="age",
        account_norm="1234567890123456",
        source_extract_ts="2026-02-20T00:00:00+00:00",
        run_ingestion_id="test-ingestion-id",
    )

    assert row is not None
    assert row["breakdown_key"] == "age"
    assert row["breakdown_value"] == "25-34"
    assert row["account_id"] == "1234567890123456"
    assert row["ad_group_id"] == "cmp_1"
    assert row["ad_group_name"] == "Campaign"
    assert row["impressions"] == 100
    assert row["clicks"] == 10
    assert row["link_clicks"] == 6


def test_build_campaign_breakdown_row_returns_none_when_value_missing():
    insight = {"date_start": "2026-02-19", "age": ""}
    row = _build_campaign_breakdown_row(
        insight=insight,
        breakdown_key="age",
        account_norm="1234567890123456",
        source_extract_ts="2026-02-20T00:00:00+00:00",
        run_ingestion_id="test-ingestion-id",
    )
    assert row is None

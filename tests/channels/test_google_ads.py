import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from New_Data_flow.channels.base import IngestContext
from New_Data_flow.common.settings import Settings, AppSettings
from New_Data_flow.channels.google_ads.adapter import GoogleAdsIngestor


@pytest.fixture
def mock_context():
    return IngestContext(
        start_date=date(2026, 2, 12),
        end_date=date(2026, 2, 12),
            settings=Settings(
                app=AppSettings(
                    project_id="test-project",
                    location="us-central1",
                    log_level="INFO",
                ),
                raw_tables={},
                providers={
                    "google_ads": {
                        "account_ids": ["1234567890"],
                        "bq_credentials_path": None,
                    }
                }
            ),
        secret_ref="mock-secret",
        account_id_norm=None,
        replace_range=False,
        dry_run=False,
        api_test_only=True,
        api_sample_size=1,
    )


@patch("New_Data_flow.channels.google_ads.adapter.GoogleAdsClient.load_from_dict")
@patch("New_Data_flow.channels.google_ads.adapter.access_secret_dict")
@patch("New_Data_flow.channels.google_ads.adapter._search_google_ads_with_retry")
def test_google_ads_adapter_smoke(mock_search, mock_access_secret, mock_client_load, mock_context):
    mock_access_secret.return_value = {
        "GOOGLE_CLIENT_ID": "mock_client_id",
        "GOOGLE_CLIENT_SECRET": "mock_client_secret",
        "GOOGLE_REFRESH_TOKEN": "mock_refresh_token",
        "GOOGLE_DEVELOPER_TOKEN": "mock_developer_token",
        "GOOGLE_LOGIN_CUSTOMER_ID": "1234567890",
    }
    
    mock_client_load.return_value = MagicMock()
    
    # Mock row returned by the search generator for performance query
    class MockMetric:
        impressions = 100
        clicks = 10
        cost_micros = 15000000
        conversions = 5
        conversions_value = 50.0

    class MockSegment:
        date = "2026-02-12"
        geo_target_region = "geoTargetConstants/21167"

    class MockAd:
        id = "ad_123"
        name = "Test Ad"
        type_ = "RESPONSIVE_SEARCH_AD"

    class MockAdGroupAd:
        ad = MockAd()

    class MockAgeRange:
        type = "AGE_RANGE_25_34"

    class MockGender:
        type = "FEMALE"

    class MockParentalStatus:
        type = "NOT_A_PARENT"

    class MockIncomeRange:
        type = "INCOME_RANGE_50_60"

    class MockAdGroupCriterion:
        age_range = MockAgeRange()
        gender = MockGender()
        parental_status = MockParentalStatus()
        income_range = MockIncomeRange()

    class MockUserLocationView:
        country_criterion_id = 2840

    class MockRow:
        customer = MagicMock(descriptive_name="Test Customer")
        campaign = MagicMock(id="cmp_1", name="Test Campaign", advertising_channel_type="SEARCH")
        ad_group = MagicMock(id="ag_1", name="Test Ad Group")
        ad_group_ad = MockAdGroupAd()
        segments = MockSegment()
        metrics = MockMetric()
        ad_group_criterion = MockAdGroupCriterion()
        user_location_view = MockUserLocationView()
        
    mock_search.side_effect = [
        [MockRow()],  # performance
        [MockRow()],  # action
        [],           # conversion_action dim
        [MockRow()],  # creative
        [],           # search text asset
        [],           # non-search image/video asset
        [],           # pmax asset
        [MockRow()],  # age_range
        [MockRow()],  # gender
        [MockRow()],  # geo_target_country
        [MockRow()],  # geo_target_region
    ]
    
    ingestor = GoogleAdsIngestor()
    result = ingestor.run(mock_context)
    
    assert result.status == "API_OK"
    assert result.channel == "google_ads"
    assert "accounts=1" in result.message
    assert "perf_rows=1" in result.message
    assert "creative_rows=1" in result.message
    assert "asset_perf_rows=0" in result.message
    assert "campaign_breakdown_rows=4" in result.message
    
    # perf, action, conversion_action dim, creative, 2x non-pmax asset perf, pmax asset perf, 4 campaign breakdown queries
    assert mock_search.call_count == 11
    action_query = mock_search.call_args_list[1][0][2]
    assert "FROM campaign" in action_query
    assert "segments.conversion_action" in action_query
    conversion_action_dim_query = mock_search.call_args_list[2][0][2]
    assert "FROM conversion_action" in conversion_action_dim_query
    creative_query = mock_search.call_args_list[3][0][2]
    assert "campaign.id" in creative_query
    assert "ad_group.id" in creative_query
    assert "ad_group_ad.status" in creative_query
    assert "segments.date" in creative_query
    search_text_asset_query = mock_search.call_args_list[4][0][2]
    assert "FROM ad_group_ad_asset_view" in search_text_asset_query
    assert "campaign.advertising_channel_type = SEARCH" in search_text_asset_query
    assert "field_type IN (HEADLINE, DESCRIPTION)" in search_text_asset_query
    non_search_media_asset_query = mock_search.call_args_list[5][0][2]
    assert "FROM ad_group_ad_asset_view" in non_search_media_asset_query
    assert "campaign.advertising_channel_type IN (DEMAND_GEN, DISPLAY, VIDEO)" in non_search_media_asset_query
    assert "field_type IN (MARKETING_IMAGE, SQUARE_MARKETING_IMAGE, PORTRAIT_MARKETING_IMAGE, YOUTUBE_VIDEO)" in non_search_media_asset_query
    pmax_asset_query = mock_search.call_args_list[6][0][2]
    assert "FROM asset_group_asset" in pmax_asset_query
    assert "campaign.advertising_channel_type = PERFORMANCE_MAX" in pmax_asset_query
    age_range_query = mock_search.call_args_list[7][0][2]
    assert "FROM age_range_view" in age_range_query
    gender_query = mock_search.call_args_list[8][0][2]
    assert "FROM gender_view" in gender_query
    country_query = mock_search.call_args_list[9][0][2]
    assert "user_location_view.country_criterion_id" in country_query
    region_query = mock_search.call_args_list[10][0][2]
    assert "segments.geo_target_region" in region_query
    assert "user_location_view.country_criterion_id" in region_query

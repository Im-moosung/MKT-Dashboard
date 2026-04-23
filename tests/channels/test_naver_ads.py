import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from channels.base import IngestContext
from common.settings import Settings, AppSettings
from channels.naver_ads.ingestor import NaverAdsIngestor


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
                "naver_ads": {
                    "account_ids": ["cust_1234"],
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


@pytest.fixture
def mock_load_context():
    return IngestContext(
        start_date=date(2026, 2, 12),
        end_date=date(2026, 2, 12),
        settings=Settings(
            app=AppSettings(
                project_id="test-project",
                location="us-central1",
                log_level="INFO",
            ),
            raw_tables={
                "naver_ads": {
                    "performance": "raw_ads.naver_ads_performance_raw",
                    "creative": "raw_ads.naver_ads_creative_raw",
                }
            },
            providers={
                "naver_ads": {
                    "account_ids": ["cust_1234"],
                    "bq_credentials_path": None,
                }
            },
        ),
        secret_ref="mock-secret",
        account_id_norm=None,
        replace_range=True,
        dry_run=False,
        api_test_only=False,
        api_sample_size=1,
    )


def _mock_naver_api_side_effect(method, endpoint, api_key, secret_key, customer_id, params=None, json=None):
    if "/campaigns" in endpoint:
        return [{"campaignId": "cmp_001", "campaignName": "부산 봄 캠페인"}]
    if "/adgroups" in endpoint:
        return [
            {
                "adgroupId": "ag_001",
                "adgroupName": "부산 그룹",
                "campaignId": "cmp_001",
            }
        ]
    if "/stats" in endpoint:
        return {
            "data": [
                {
                    "campaign": {"name": "부산 봄 캠페인"},
                    "date": "2026-02-12",
                    "impressions": "200",
                    "clicks": "20",
                    "cost": "5000",
                    "ctr": "0.1",
                    "avgCpc": "250",
                    "adgroupId": "ag_001",
                    "adgroupName": "부산 그룹",
                }
            ]
        }
    if "/ads" in endpoint:
        return [
            {
                "adId": "ad_001",
                "campaignId": "cmp_001",
                "adgroupId": "ag_001",
                "adgroupName": "부산 그룹",
                "adName": "스프링 소재",
                "adType": "TEXT_AD",
                "headline": "봄 신상 도착!",
                "description": "한정 특가 구매하기",
                "image": {"url": "https://example.com/img.jpg"},
            }
        ]
    return {}


@patch("channels.naver_ads.ingestor.access_secret_dict")
@patch("channels.naver_ads.ingestor._call_naver_api")
def test_naver_ads_adapter_smoke(mock_call_api, mock_access_secret, mock_context):
    mock_access_secret.return_value = {
        "NAVER_API_KEY": "mock_api_key",
        "NAVER_SECRET_KEY": "mock_secret_key",
        "NAVER_CUSTOMER_ID": "cust_1234",
    }
    mock_call_api.side_effect = _mock_naver_api_side_effect

    ingestor = NaverAdsIngestor()
    result = ingestor.run(mock_context)

    assert result.status == "API_OK"
    assert result.channel == "naver_ads"
    assert "accounts=1" in result.message
    assert "perf_rows=1" in result.message
    assert "creative_rows=1" in result.message


@patch("channels.naver_ads.ingestor._build_bq_client_with_fallback")
@patch("channels.naver_ads.ingestor.load_idempotent_json")
@patch("channels.naver_ads.ingestor.access_secret_dict")
@patch("channels.naver_ads.ingestor._call_naver_api")
def test_naver_ads_load_includes_ad_group_name(
    mock_call_api,
    mock_access_secret,
    mock_load,
    mock_bq_client,
    mock_load_context,
):
    mock_access_secret.return_value = {
        "NAVER_API_KEY": "mock_api_key",
        "NAVER_SECRET_KEY": "mock_secret_key",
        "NAVER_CUSTOMER_ID": "cust_1234",
    }
    mock_call_api.side_effect = _mock_naver_api_side_effect
    mock_bq_client.return_value = MagicMock()
    mock_load.side_effect = [1, 1]

    ingestor = NaverAdsIngestor()
    result = ingestor.run(mock_load_context)

    assert result.status == "LOADED"
    assert result.channel == "naver_ads"
    assert mock_load.call_count == 2

    perf_call = mock_load.call_args_list[0]
    perf_rows = perf_call.kwargs["rows"]
    assert len(perf_rows) == 1
    assert perf_rows[0]["campaign_name"] == "부산 봄 캠페인"
    assert perf_rows[0]["ad_group_id"] == "ag_001"
    assert perf_rows[0]["ad_group_name"] == "부산 그룹"

    creative_call = mock_load.call_args_list[1]
    creative_rows = creative_call.kwargs["rows"]
    assert len(creative_rows) == 1
    assert creative_rows[0]["ad_group_id"] == "ag_001"

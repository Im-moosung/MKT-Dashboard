import pytest
from unittest.mock import patch
from datetime import date

from channels.base import IngestContext
from common.settings import Settings, AppSettings
from channels.tiktok_ads.ingestor import TikTokAdsIngestor


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
                "tiktok_ads": {
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


@patch("channels.tiktok_ads.ingestor.access_secret_dict")
@patch("channels.tiktok_ads.ingestor._call_tiktok_api")
def test_tiktok_ads_adapter_smoke(mock_call_api, mock_access_secret, mock_context):
    mock_access_secret.return_value = {
        "TIKTOK_ACCESS_TOKEN": "mock_access_token",
    }
    
    def mock_api_side_effect(method, url, headers, params=None, json=None):
        if url.endswith("/report/integrated/get/"):
            return {
                "page_info": {"page": 1, "total_page": 1},
                "list": [
                    {
                        "dimensions": {"ad_id": "ad_123", "stat_time_day": "2026-02-12"},
                        "metrics": {
                            "campaign_id": "cmp_1",
                            "campaign_name": "Test Campaign",
                            "adgroup_id": "ag_1",
                            "adgroup_name": "Test Ad Group",
                            "ad_name": "Test Ad",
                            "impressions": "100",
                            "clicks": "10",
                            "spend": "15.5",
                            "conversion": "5",
                        }
                    }
                ]
            }
        elif url.endswith("/ad/get/"):
            return {
                "list": [
                    {
                        "ad_id": "ad_123",
                        "campaign_id": "cmp_1",
                        "adgroup_id": "ag_1",
                        "ad_name": "Test Ad",
                        "ad_format": "SINGLE_VIDEO",
                        "ad_text": "Buy now!",
                        "video_id": "vid_xyz"
                    }
                ]
            }
            
        return {}

    mock_call_api.side_effect = mock_api_side_effect
    
    ingestor = TikTokAdsIngestor()
    result = ingestor.run(mock_context)
    
    assert result.status == "API_OK"
    assert result.channel == "tiktok_ads"
    assert "accounts=1" in result.message
    assert "perf_rows=1" in result.message
    assert "creative_rows=1" in result.message

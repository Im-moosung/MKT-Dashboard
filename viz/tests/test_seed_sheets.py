import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import seed_sheets


def test_normalize_channel_code_variants():
    assert seed_sheets.normalize_channel_code("1_Meta") == "META"
    assert seed_sheets.normalize_channel_code("META") == "META"
    assert seed_sheets.normalize_channel_code("2_Google_Search") == "GOOGLE_ADS"
    assert seed_sheets.normalize_channel_code("GOOGLE_SEARCH") == "GOOGLE_ADS"
    assert seed_sheets.normalize_channel_code("7_TikTok") == "TIKTOK_ADS"
    assert seed_sheets.normalize_channel_code("4_Youtube") == "YOUTUBE"
    assert seed_sheets.normalize_channel_code("14_Affiliate") == "AFFILIATE"
    assert seed_sheets.normalize_channel_code("15_Email") == "EMAIL"
    assert seed_sheets.normalize_channel_code("102_Ambassadors") == "INFLUENCER"
    assert seed_sheets.normalize_channel_code("12_Organic_SEO") == "ORGANIC_SEO"
    assert seed_sheets.normalize_channel_code("114_OTA") == "OTA"
    assert seed_sheets.normalize_channel_code("unknown_xyz") == "OTHER"


def test_parse_currency_amount():
    assert seed_sheets.parse_currency("$91,952.10") == 91952.10
    assert seed_sheets.parse_currency("1,495") == 1495.0
    assert seed_sheets.parse_currency("") is None
    assert seed_sheets.parse_currency("$0.00") == 0.0

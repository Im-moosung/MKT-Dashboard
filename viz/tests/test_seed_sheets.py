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


def test_guard_empty_truncate_refuses_overwrite_on_empty_rows():
    import pytest

    with pytest.raises(SystemExit) as exc:
        seed_sheets.guard_empty_truncate(rows=[], overwrite=True)
    # Non-zero exit so cron/orchestration detect the failure.
    assert exc.value.code != 0


def test_guard_empty_truncate_allows_non_empty_overwrite():
    seed_sheets.guard_empty_truncate(rows=[{"date": "2026-04-24"}], overwrite=True)


def test_guard_empty_truncate_allows_empty_append():
    # Append with zero rows is a no-op on existing data and must not raise.
    seed_sheets.guard_empty_truncate(rows=[], overwrite=False)


def test_main_refuses_empty_truncate_without_touching_bigquery(monkeypatch):
    import pytest

    monkeypatch.setattr(seed_sheets, "build_rows", lambda _branch: [])

    def _fail_import(*_a, **_kw):
        raise AssertionError("bigquery client must not be constructed when truncate is refused")

    # Shield the BQ import path: if main() proceeds past the guard, it will fail here.
    monkeypatch.setitem(
        __import__("sys").modules,
        "google.cloud",
        type("Stub", (), {"bigquery": type("BQ", (), {"Client": _fail_import})})(),
    )

    with pytest.raises(SystemExit) as exc:
        seed_sheets.main(["--overwrite", "--branches", "AMNY"])
    assert exc.value.code != 0

from channels.base import ChannelIngestor
from channels.meta_ads.ingestor import MetaAdsIngestor
from channels.google_ads.ingestor import GoogleAdsIngestor
from channels.tiktok_ads.ingestor import TikTokAdsIngestor
from channels.naver_ads.ingestor import NaverAdsIngestor


def build_registry() -> dict[str, ChannelIngestor]:
    return {
        "meta_ads": MetaAdsIngestor(),
        "google_ads": GoogleAdsIngestor(),
        "tiktok_ads": TikTokAdsIngestor(),
        "naver_ads": NaverAdsIngestor(),
    }


def resolve_ingestors(channel: str) -> list[ChannelIngestor]:
    registry = build_registry()
    if channel == "all":
        return list(registry.values())
    if channel not in registry:
        raise ValueError(f"unsupported channel: {channel}. available={', '.join(registry.keys())}")
    return [registry[channel]]


def warehouse_capable_channel_keys() -> set[str]:
    """Channel keys whose ingestors declare supports_warehouse=True."""
    return {
        getattr(ing, "channel_key", "")
        for ing in build_registry().values()
        if getattr(ing, "supports_warehouse", False) and getattr(ing, "channel_key", "")
    }


def resolve_ingestor_by_provider(provider_key: str) -> ChannelIngestor:
    normalized = (provider_key or "").strip().lower()
    provider_map = {
        "meta": "meta_ads",
        "meta_ads": "meta_ads",
        "google": "google_ads",
        "google_ads": "google_ads",
        "tiktok": "tiktok_ads",
        "tiktok_ads": "tiktok_ads",
        "naver": "naver_ads",
        "naver_ads": "naver_ads",
    }
    registry_key = provider_map.get(normalized)
    if not registry_key:
        raise ValueError(f"unsupported provider_key: {provider_key}")
    registry = build_registry()
    return registry[registry_key]

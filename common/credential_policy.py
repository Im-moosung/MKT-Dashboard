from __future__ import annotations

import os


def allow_env_fallback(provider_cfg: dict | None) -> bool:
    cfg = provider_cfg or {}
    value = cfg.get("allow_env_fallback")
    if value is None:
        return True
    return bool(value)


def resolve_credential_value(
    *,
    secret_data: dict,
    env_key: str,
    env_fallback_enabled: bool,
) -> str:
    value = secret_data.get(env_key)
    if value is not None and str(value).strip() != "":
        return str(value).strip()
    if env_fallback_enabled:
        return str(os.getenv(env_key, "")).strip()
    return ""

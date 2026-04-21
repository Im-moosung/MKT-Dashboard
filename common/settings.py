import os
from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class AppSettings:
    project_id: str
    location: str
    log_level: str
    env: str = "dev"


@dataclass(frozen=True)
class Settings:
    app: AppSettings
    raw_tables: dict
    providers: dict


def _resolve_config_path(value: str | None, project_root: Path) -> str | None:
    if value is None:
        return None

    raw = os.path.expandvars(os.path.expanduser(str(value).strip()))
    if not raw:
        return None

    path = Path(raw)
    if not path.is_absolute():
        path = project_root / path
    return str(path.resolve())


def _normalize_provider_config(
    provider_key: str,
    provider_cfg: dict,
    project_root: Path,
) -> dict:
    normalized = dict(provider_cfg or {})
    env_prefix = f"NEW_DATA_FLOW_{provider_key.upper()}"

    env_file_override = os.getenv(f"{env_prefix}_ENV_FILE")
    if env_file_override:
        normalized["env_file"] = env_file_override

    bq_credentials_override = (
        os.getenv(f"{env_prefix}_BQ_CREDENTIALS_PATH")
        or os.getenv("NEW_DATA_FLOW_BQ_CREDENTIALS_PATH")
    )
    if bq_credentials_override:
        normalized["bq_credentials_path"] = bq_credentials_override

    for key in ("env_file", "bq_credentials_path"):
        if key in normalized:
            normalized[key] = _resolve_config_path(normalized.get(key), project_root)

    return normalized


def load_settings(env: str, config_dir: Path) -> Settings:
    config_path = config_dir / f"{env}.toml"
    if not config_path.exists():
        raise FileNotFoundError(f"settings file not found: {config_path}")

    with config_path.open("rb") as fp:
        data = tomllib.load(fp)

    app = data.get("app", {})
    raw_tables = data.get("raw_tables", {})
    providers = data.get("providers", {})
    project_root = config_dir.parent
    project_id = app.get("project_id")
    if not project_id:
        raise ValueError("project_id is required in config TOML [app] section")

    # Backward compatibility for root-level provider config blocks.
    if "meta_ads" in data and "meta_ads" not in providers:
        providers["meta_ads"] = data.get("meta_ads", {})

    normalized_providers = {
        key: _normalize_provider_config(key, value, project_root)
        if isinstance(value, dict)
        else value
        for key, value in providers.items()
    }

    return Settings(
        app=AppSettings(
            project_id=str(project_id),
            location=app.get("location", "us-central1"),
            log_level=app.get("log_level", "INFO"),
            env=env,
        ),
        raw_tables=raw_tables,
        providers=normalized_providers,
    )

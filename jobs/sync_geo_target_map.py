from __future__ import annotations

import argparse
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import pycountry
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.cloud import bigquery

from channels.google_ads.ingestor import _search_google_ads_with_retry
from common.bigquery_loader import build_bigquery_client
from common.logger import setup_logger
from common.gcp_secret_manager import access_secret_dict
from common.settings import load_settings
from common.source_config import list_source_configs


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _normalize_account_id(account_id: str) -> str:
    return (account_id or "").replace("-", "").strip()


def _chunked(values: list[str], size: int) -> Iterable[list[str]]:
    for idx in range(0, len(values), size):
        yield values[idx : idx + size]


def _country_name_from_code(country_code: str | None) -> str | None:
    if not country_code:
        return None
    code = str(country_code).upper().strip()
    if len(code) != 2:
        return None
    found = pycountry.countries.get(alpha_2=code)
    if found:
        return str(found.name)
    return None


def _build_display_name(target_name: str | None, country_name: str | None, target_type: str | None, geo_id: str) -> str:
    if geo_id == "others":
        return "Others"
    name = (target_name or "").strip()
    country = (country_name or "").strip()
    ttype = (target_type or "").strip().upper()
    if ttype == "COUNTRY":
        return country or name or "Unknown"
    if name and country and country.lower() not in name.lower():
        return f"{name}, {country}"
    return name or country or "Unknown"


COUNTRY_NAME_KO_MAP = {
    "United States": "미국",
    "Canada": "캐나다",
    "Mexico": "멕시코",
    "South Korea": "대한민국",
    "Korea, Republic of": "대한민국",
    "Japan": "일본",
    "China": "중국",
    "United Arab Emirates": "아랍에미리트",
    "Singapore": "싱가포르",
    "Hong Kong": "홍콩",
    "Taiwan": "대만",
}


def _to_country_name_ko(country_name: str | None) -> str | None:
    if not country_name:
        return None
    return COUNTRY_NAME_KO_MAP.get(country_name, country_name)


def _build_display_name_ko(target_name: str | None, country_name: str | None, target_type: str | None, geo_id: str) -> str:
    if geo_id == "others":
        return "기타"
    name = (target_name or "").strip()
    country_ko = (_to_country_name_ko(country_name) or "").strip()
    ttype = (target_type or "").strip().upper()
    if ttype == "COUNTRY":
        return country_ko or name or "미확인"
    if name and country_ko and country_ko not in name:
        return f"{name}, {country_ko}"
    return name or country_ko or "미확인"


def _build_google_client(
    *,
    project_id: str,
    provider_cfg: dict,
    source_cfg,
) -> GoogleAdsClient:
    creds_path = provider_cfg.get("bq_credentials_path")
    env_file = provider_cfg.get("env_file")
    if env_file and Path(env_file).exists():
        load_dotenv(env_file, override=False)

    secret_data: dict = {}
    if source_cfg.secret_ref:
        secret_data = access_secret_dict(
            project_id=project_id,
            secret_ref=source_cfg.secret_ref,
            version=source_cfg.secret_version or "latest",
            credentials_path=creds_path,
        )

    client_id = str(secret_data.get("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID", ""))
    client_secret = str(secret_data.get("GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET", ""))
    refresh_token = str(secret_data.get("GOOGLE_REFRESH_TOKEN") or os.getenv("GOOGLE_REFRESH_TOKEN", ""))
    developer_token = str(secret_data.get("GOOGLE_DEVELOPER_TOKEN") or os.getenv("GOOGLE_DEVELOPER_TOKEN", ""))
    login_customer_id = str(secret_data.get("GOOGLE_LOGIN_CUSTOMER_ID") or os.getenv("GOOGLE_LOGIN_CUSTOMER_ID", ""))

    if not client_id or not client_secret or not refresh_token or not developer_token:
        raise ValueError("Google Ads credentials are missing")

    credentials_dict = {
        "developer_token": developer_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "use_proto_plus": True,
    }
    login_norm = login_customer_id.replace("-", "").replace(" ", "")
    if login_norm.isdigit() and len(login_norm) == 10:
        credentials_dict["login_customer_id"] = login_norm

    return GoogleAdsClient.load_from_dict(credentials_dict)


def _ensure_geo_target_map_table(client: bigquery.Client, project_id: str) -> None:
    query = f"""
    CREATE TABLE IF NOT EXISTS `{project_id}.governance.geo_target_map` (
      geo_target_constant_id STRING,
      target_type STRING,
      country_code STRING,
      country_name STRING,
      target_name STRING,
      canonical_name STRING,
      display_name STRING,
      display_name_ko STRING,
      source STRING,
      is_active BOOL,
      updated_at TIMESTAMP
    )
    CLUSTER BY geo_target_constant_id, target_type, country_code
    """
    client.query(query).result()


def _fetch_geo_target_ids(
    client: bigquery.Client,
    raw_table_ref: str,
    start_date: date,
    end_date: date,
) -> list[str]:
    query = f"""
    SELECT DISTINCT breakdown_value AS geo_target_constant_id
    FROM `{raw_table_ref}`
    WHERE stat_date BETWEEN @start_date AND @end_date
      AND breakdown_key IN ('geo_target_country', 'geo_target_region')
      AND breakdown_value IS NOT NULL
      AND TRIM(breakdown_value) != ''
    ORDER BY geo_target_constant_id
    """
    job = client.query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "DATE", start_date.isoformat()),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date.isoformat()),
            ]
        ),
    )
    return [str(row["geo_target_constant_id"]) for row in job.result()]


def _fetch_geo_target_metadata(
    *,
    google_client: GoogleAdsClient,
    customer_id: str,
    geo_ids: list[str],
) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for ids_chunk in _chunked(geo_ids, 200):
        quoted = ", ".join([f"'{geo_id}'" for geo_id in ids_chunk])
        query = f"""
            SELECT
              geo_target_constant.resource_name,
              geo_target_constant.name,
              geo_target_constant.canonical_name,
              geo_target_constant.country_code,
              geo_target_constant.target_type
            FROM geo_target_constant
            WHERE geo_target_constant.resource_name IN ({quoted})
        """
        rows = _search_google_ads_with_retry(google_client, customer_id, query)
        for row in rows:
            geo = getattr(row, "geo_target_constant", None)
            if not geo:
                continue
            resource_name = str(getattr(geo, "resource_name", "") or "")
            if not resource_name:
                continue
            target_type_obj = getattr(geo, "target_type", None)
            target_type = str(getattr(target_type_obj, "name", "") or target_type_obj or "")
            country_code = str(getattr(geo, "country_code", "") or "").upper()
            country_name = _country_name_from_code(country_code)
            target_name = str(getattr(geo, "name", "") or "")
            canonical_name = str(getattr(geo, "canonical_name", "") or "")
            result[resource_name] = {
                "geo_target_constant_id": resource_name,
                "target_type": target_type or "UNKNOWN",
                "country_code": country_code or None,
                "country_name": country_name or None,
                "target_name": target_name or None,
                "canonical_name": canonical_name or None,
                "display_name": _build_display_name(target_name, country_name, target_type, resource_name),
                "display_name_ko": _build_display_name_ko(target_name, country_name, target_type, resource_name),
                "source": "google_ads_api",
                "is_active": True,
                "updated_at": _utc_now_iso(),
            }
    return result


def _build_rows(
    geo_ids: list[str],
    metadata: dict[str, dict],
) -> list[dict]:
    rows: list[dict] = []
    for geo_id in geo_ids:
        if geo_id in metadata:
            rows.append(metadata[geo_id])
            continue
        if geo_id == "others":
            rows.append(
                {
                    "geo_target_constant_id": "others",
                    "target_type": "BUCKET",
                    "country_code": None,
                    "country_name": None,
                    "target_name": "Others",
                    "canonical_name": "Others",
                    "display_name": "Others",
                    "display_name_ko": "기타",
                    "source": "rule_bucket",
                    "is_active": True,
                    "updated_at": _utc_now_iso(),
                }
            )
            continue
        rows.append(
            {
                "geo_target_constant_id": geo_id,
                "target_type": "UNKNOWN",
                "country_code": None,
                "country_name": None,
                "target_name": "Unknown",
                "canonical_name": "Unknown",
                "display_name": "Unknown",
                "display_name_ko": "미확인",
                "source": "fallback_unknown",
                "is_active": True,
                "updated_at": _utc_now_iso(),
            }
        )
    return rows


def _upsert_geo_target_map(client: bigquery.Client, project_id: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    target_table = f"{project_id}.governance.geo_target_map"
    table = client.get_table(target_table)
    temp_table = f"{project_id}.governance._tmp_geo_target_map_{uuid.uuid4().hex[:8]}"
    load_job = client.load_table_from_json(
        rows,
        temp_table,
        job_config=bigquery.LoadJobConfig(
            schema=table.schema,
            write_disposition="WRITE_TRUNCATE",
        ),
    )
    load_job.result()
    merge_sql = f"""
    MERGE `{target_table}` t
    USING `{temp_table}` s
      ON t.geo_target_constant_id = s.geo_target_constant_id
    WHEN MATCHED THEN UPDATE SET
      target_type = s.target_type,
      country_code = s.country_code,
      country_name = s.country_name,
      target_name = s.target_name,
      canonical_name = s.canonical_name,
      display_name = s.display_name,
      display_name_ko = s.display_name_ko,
      source = s.source,
      is_active = s.is_active,
      updated_at = s.updated_at
    WHEN NOT MATCHED THEN INSERT (
      geo_target_constant_id,
      target_type,
      country_code,
      country_name,
      target_name,
      canonical_name,
      display_name,
      display_name_ko,
      source,
      is_active,
      updated_at
    ) VALUES (
      s.geo_target_constant_id,
      s.target_type,
      s.country_code,
      s.country_name,
      s.target_name,
      s.canonical_name,
      s.display_name,
      s.display_name_ko,
      s.source,
      s.is_active,
      s.updated_at
    )
    """
    try:
        merge_job = client.query(merge_sql)
        merge_job.result()
        return len(rows)
    finally:
        client.delete_table(temp_table, not_found_ok=True)


def _pick_google_source_config(client: bigquery.Client, project_id: str, table_ref: str, source_id: str | None):
    cfgs = list_source_configs(
        client=client,
        project_id=project_id,
        table_ref=table_ref,
        source_id=source_id,
        status=None,
        tier=None,
    )
    for cfg in cfgs:
        provider_key = (cfg.provider_key or "").strip().lower()
        if provider_key != "google_ads":
            continue
        if _normalize_account_id(cfg.account_id_norm or ""):
            return cfg
    raise ValueError("No usable google_ads source config found with account_id_norm")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync governance.geo_target_map from Google Ads geo_target_constant")
    parser.add_argument("--env", choices=["dev", "prod"], default="prod")
    parser.add_argument("--source-config-table", default="ops.ingest_source_config")
    parser.add_argument("--source-id", help="Optional source_id for Google Ads credentials/account")
    parser.add_argument("--raw-table", default="raw_ads.google_ads_campaign_breakdown_raw")
    parser.add_argument("--start-date", type=_parse_date, default=date(2000, 1, 1))
    parser.add_argument("--end-date", type=_parse_date, default=date(2100, 1, 1))
    parser.add_argument("--dry-run", action="store_true")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(env=args.env, config_dir=root / "config")
    logger = setup_logger("new_data_flow.sync_geo_target_map", settings.app.log_level)

    provider_cfg = (settings.providers or {}).get("google_ads", {})
    creds_path = provider_cfg.get("bq_credentials_path")
    bq_client = build_bigquery_client(
        project_id=settings.app.project_id,
        credentials_path=creds_path,
        location=settings.app.location,
    )

    _ensure_geo_target_map_table(bq_client, settings.app.project_id)
    source_cfg = _pick_google_source_config(
        client=bq_client,
        project_id=settings.app.project_id,
        table_ref=args.source_config_table,
        source_id=args.source_id,
    )
    account_norm = _normalize_account_id(source_cfg.account_id_norm or "")
    if not account_norm:
        raise ValueError("Google Ads source config has empty account_id_norm")

    raw_table_ref = (
        args.raw_table
        if args.raw_table.count(".") == 2
        else f"{settings.app.project_id}.{args.raw_table}"
    )
    geo_ids = _fetch_geo_target_ids(
        client=bq_client,
        raw_table_ref=raw_table_ref,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    if not geo_ids:
        print("sync skipped | no geo ids found")
        return 0

    custom_ids = [gid for gid in geo_ids if not gid.startswith("geoTargetConstants/")]
    api_ids = [gid for gid in geo_ids if gid.startswith("geoTargetConstants/")]

    google_client = _build_google_client(
        project_id=settings.app.project_id,
        provider_cfg=provider_cfg,
        source_cfg=source_cfg,
    )
    metadata = _fetch_geo_target_metadata(
        google_client=google_client,
        customer_id=account_norm,
        geo_ids=api_ids,
    )
    rows = _build_rows(geo_ids=api_ids + custom_ids, metadata=metadata)

    if args.dry_run:
        print(
            "dry_run ok | "
            f"total_ids={len(geo_ids)} api_ids={len(api_ids)} custom_ids={len(custom_ids)} mapped={len(metadata)}"
        )
        return 0

    upserted = _upsert_geo_target_map(bq_client, settings.app.project_id, rows)
    logger.info(
        "geo_target_map sync done | rows=%s ids=%s mapped=%s unknown=%s",
        upserted,
        len(geo_ids),
        len(metadata),
        len(geo_ids) - len(metadata),
    )
    print(
        "sync done | "
        f"rows={upserted} ids={len(geo_ids)} mapped={len(metadata)} unknown_or_bucket={len(geo_ids) - len(metadata)}"
    )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

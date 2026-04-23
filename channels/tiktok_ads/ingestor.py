from __future__ import annotations

import json
import time
import uuid
import requests
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from channels.base import IngestContext, IngestResult
from common.bigquery_loader import append_json_rows, build_bigquery_client, load_idempotent_json
from common.credential_policy import allow_env_fallback, resolve_credential_value
from common.logger import setup_logger
from common.gcp_secret_manager import access_secret_dict


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_account_id(account_id: str) -> str:
    return str(account_id).strip()


def _to_plain_json(value):
    """Convert objects to JSON primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_plain_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_plain_json(v) for v in value]
    return str(value)


def _build_bq_client_with_fallback(
    project_id: str,
    credentials_path: str | None,
    location: str,
    logger,
):
    """Fallback from explicit service key to ADC."""
    client = build_bigquery_client(project_id=project_id, credentials_path=credentials_path, location=location)
    try:
        client.query("SELECT 1").result()
        return client
    except Exception as exc:  # noqa: BLE001
        if not credentials_path:
            raise
        logger.warning("configured BigQuery credentials preflight failed; retrying with ADC: %s", exc)
        adc_client = build_bigquery_client(project_id=project_id, credentials_path=None, location=location)
        adc_client.query("SELECT 1").result()
        return adc_client


def _is_retryable_tiktok_exception(exc: BaseException) -> bool:
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return status in (429, 500, 502, 503, 504)
    if isinstance(exc, requests.exceptions.RequestException):
        return isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout))
    return False


@retry(
    retry=retry_if_exception(_is_retryable_tiktok_exception),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _call_tiktok_api(method: str, url: str, headers: dict, params: dict = None, json: dict = None) -> dict:
    resp = requests.request(method, url, headers=headers, params=params, json=json, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        msg = data.get("message", "Unknown TikTok API error")
        if data.get("code") == 40105:
            obj = requests.exceptions.HTTPError(f"TikTok Rate Limit: {msg}", response=resp)
            resp.status_code = 429
            raise obj
        raise ValueError(f"TikTok API Error: code={data.get('code')} msg={msg}")
    return data.get("data", {})


class TikTokAdsIngestor:
    name = "tiktok_ads"
    channel_key = "TIKTOK_ADS"
    supports_warehouse = True

    def run(self, ctx: IngestContext) -> IngestResult:
        logger = setup_logger("new_data_flow.tiktok_ads", ctx.settings.app.log_level)
        provider_cfg = (ctx.settings.providers or {}).get("tiktok_ads", {})
        env_fallback_enabled = allow_env_fallback(provider_cfg)
        bq_creds = provider_cfg.get("bq_credentials_path")

        env_file = provider_cfg.get("env_file")
        if env_file and Path(env_file).exists():
            load_dotenv(env_file, override=False)

        secret_data: dict = {}
        if ctx.secret_ref:
            secret_data = access_secret_dict(
                project_id=ctx.settings.app.project_id,
                secret_ref=ctx.secret_ref,
                version=ctx.secret_version or "latest",
                credentials_path=bq_creds,
            )

        access_token = resolve_credential_value(
            secret_data=secret_data,
            env_key="TIKTOK_ACCESS_TOKEN",
            env_fallback_enabled=env_fallback_enabled,
        )

        account_ids: list[str] = []
        if ctx.account_id_norm:
            account_ids = [ctx.account_id_norm]
        else:
            account_ids = provider_cfg.get("account_ids", []) or []

        if not access_token:
            if env_fallback_enabled:
                raise ValueError("TikTok Ads API credential missing (TIKTOK_ACCESS_TOKEN)")
            raise ValueError("TikTok Ads API credential missing in Secret Manager and env fallback is disabled")
        if not account_ids:
            raise ValueError("No TikTok Ads account configured")

        headers = {
            "Access-Token": access_token,
            "Content-Type": "application/json"
        }

        all_perf_rows: list[dict] = []
        all_creative_rows: list[dict] = []
        checked_accounts: list[str] = []
        account_failures = 0

        start_s = ctx.start_date.strftime("%Y-%m-%d")
        end_s = ctx.end_date.strftime("%Y-%m-%d")
        source_extract_ts = _utc_now_iso()
        run_ingestion_id = str(uuid.uuid4())

        for raw_account_id in account_ids:
            account_norm = _normalize_account_id(str(raw_account_id))

            report_url = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"
            params = {
                "advertiser_id": account_norm,
                "report_type": "BASIC",
                "data_level": "AUCTION_AD",
                "dimensions": '["stat_time_day", "ad_id"]',
                "start_date": start_s,
                "end_date": end_s,
                "metrics": '["campaign_id","campaign_name","adgroup_id","adgroup_name","ad_name","spend","impressions","clicks","conversion","cost_per_conversion"]',
                "page_size": 1000,
                "page": 1,
            }

            if ctx.api_test_only:
                params["page_size"] = ctx.api_sample_size

            insights_rows = []
            try:
                while True:
                    data = _call_tiktok_api("GET", report_url, headers=headers, params=params)
                    page_info = data.get("page_info", {})
                    items = data.get("list", [])
                    insights_rows.extend(items)

                    if ctx.api_test_only or page_info.get("page", 1) >= page_info.get("total_page", 1):
                        break
                    params["page"] += 1

                logger.info("tiktok ads performance fetched | account=%s rows=%s", account_norm, len(insights_rows))
            except Exception as exc:
                logger.error("tiktok ads fetch failed | account=%s err=%s", account_norm, exc)
                account_failures += 1
                continue
            checked_accounts.append(account_norm)

            ad_ids = set()
            for insight in insights_rows:
                metrics = insight.get("metrics", {})
                dimensions = insight.get("dimensions", {})
                
                ad_id = str(dimensions.get("ad_id", ""))
                if ad_id:
                    ad_ids.add(ad_id)

                perf_row = {
                    "ingestion_id": run_ingestion_id,
                    "ingestion_ts": _utc_now_iso(),
                    "source_extract_ts": source_extract_ts,
                    "advertiser_id": account_norm,
                    "campaign_id": str(metrics.get("campaign_id", "")),
                    "ad_group_id": str(metrics.get("adgroup_id", "")),
                    "ad_id": ad_id,
                    "stat_date": str(dimensions.get("stat_time_day", ""))[:10],
                    "impressions": int(float(metrics.get("impressions", 0))),
                    "clicks": int(float(metrics.get("clicks", 0))),
                    "spend": str(metrics.get("spend", "")),
                    "conversions": int(float(metrics.get("conversion", 0))),
                    "conversions_value": float(metrics.get("value", 0) or 0),
                    "source_payload": _to_plain_json(insight),
                }
                all_perf_rows.append(perf_row)

            creative_targets = list(ad_ids)[: ctx.max_ads] if hasattr(ctx, 'max_ads') else list(ad_ids)
            if ctx.api_test_only:
                creative_targets = creative_targets[:ctx.api_sample_size]
            
            ad_url = "https://business-api.tiktok.com/open_api/v1.3/ad/get/"
            ad_params = {
                "advertiser_id": account_norm,
                "filtering": json.dumps({"ad_ids": creative_targets}) if creative_targets else "{}",
            }

            try:
                ad_data = _call_tiktok_api("GET", ad_url, headers=headers, params=ad_params) if creative_targets else {}
                creative_rows = ad_data.get("list", [])
                logger.info("tiktok ads creative fetched | account=%s rows=%s", account_norm, len(creative_rows))
            except Exception as exc:
                logger.warning("tiktok ads creative fetch failed | account=%s err=%s", account_norm, exc)
                creative_rows = []

            for row in creative_rows:
                ad_id = str(row.get("ad_id", ""))
                creative_row = {
                    "ingestion_id": run_ingestion_id,
                    "ingestion_ts": _utc_now_iso(),
                    "source_extract_ts": source_extract_ts,
                    "collected_date": end_s,
                    "advertiser_id": account_norm,
                    "campaign_id": str(row.get("campaign_id", "")),
                    "ad_group_id": str(row.get("adgroup_id", "")),
                    "ad_id": ad_id,
                    "creative_id": ad_id,
                    "creative_name": str(row.get("ad_name", "")),
                    "status": str(row.get("operation_status", "")),
                    "body_text": "",
                    "call_to_action": "",
                    "landing_page_url": str(row.get("landing_page_url", "")),
                    "image_url": str(row.get("image_url", "")),
                    "video_id": str(row.get("video_id", "")),
                    "video_url": str(row.get("video_url", "")),
                    "thumbnail_url": str(row.get("image_url", "")),
                    "texts_json": [],
                    "assets_json": None,
                    "source_payload": _to_plain_json(row),
                }
                all_creative_rows.append(creative_row)

            sleep_seconds = float(provider_cfg.get("api_sleep_seconds", 0.2))
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        if not checked_accounts and account_failures > 0:
            raise ValueError(f"TikTok Ads ingest failed for all accounts (failed_accounts={account_failures})")

        if ctx.api_test_only or ctx.dry_run:
            return IngestResult(
                channel=self.name,
                status="API_OK",
                message=(
                    f"accounts={len(checked_accounts)}, perf_rows={len(all_perf_rows)}, "
                    f"creative_rows={len(all_creative_rows)}, mode={'API_TEST' if ctx.api_test_only else 'DRY_RUN'}"
                ),
            )

        raw_tiktok = (ctx.settings.raw_tables or {}).get("tiktok_ads", {})
        perf_table = raw_tiktok.get("performance", "raw_ads.tiktok_ads_performance_raw")
        creative_table = raw_tiktok.get("creative", "raw_ads.tiktok_ads_creative_raw")

        perf_table_ref = f"{ctx.settings.app.project_id}.{perf_table}"
        creative_table_ref = f"{ctx.settings.app.project_id}.{creative_table}"

        bq_client = _build_bq_client_with_fallback(
            project_id=ctx.settings.app.project_id,
            credentials_path=bq_creds,
            location=ctx.settings.app.location,
            logger=logger,
        )

        if ctx.replace_range:
            perf_loaded = load_idempotent_json(
                client=bq_client,
                table_ref=perf_table_ref,
                date_column="stat_date",
                start_date=start_s,
                end_date=end_s,
                account_ids=checked_accounts,
                account_id_column="advertiser_id",
                rows=all_perf_rows,
            )
            creative_loaded = load_idempotent_json(
                client=bq_client,
                table_ref=creative_table_ref,
                date_column="collected_date",
                start_date=start_s,
                end_date=end_s,
                account_ids=checked_accounts,
                account_id_column="advertiser_id",
                rows=all_creative_rows,
            )
        else:
            perf_loaded = append_json_rows(bq_client, perf_table_ref, all_perf_rows)
            creative_loaded = append_json_rows(bq_client, creative_table_ref, all_creative_rows)

        return IngestResult(
            channel=self.name,
            status="LOADED",
            message=(
                f"accounts={len(checked_accounts)}, perf_loaded={perf_loaded}, "
                f"creative_loaded={creative_loaded}, replace_range={ctx.replace_range}"
            ),
        )

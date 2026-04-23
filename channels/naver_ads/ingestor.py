from __future__ import annotations

import base64
import hashlib
import hmac
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

API_BASE = "https://api.searchad.naver.com"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_account_id(account_id: str) -> str:
    return str(account_id).strip()


def _to_plain_json(value):
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
    client = build_bigquery_client(project_id=project_id, credentials_path=credentials_path, location=location)
    try:
        client.query("SELECT 1").result()
        return client
    except Exception as exc:  # noqa: BLE001
        if not credentials_path:
            raise
        logger.warning("BQ credentials preflight failed; retrying with ADC: %s", exc)
        adc_client = build_bigquery_client(project_id=project_id, credentials_path=None, location=location)
        adc_client.query("SELECT 1").result()
        return adc_client


def _make_naver_signature(timestamp: str, method: str, uri: str, secret_key: str) -> str:
    """Naver Ads API 서명 생성 (HMAC-SHA256)."""
    message = f"{timestamp}.{method}.{uri}"
    hashed = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    return base64.b64encode(hashed.digest()).decode("utf-8")


def _naver_headers(timestamp: str, api_key: str, customer_id: str, signature: str) -> dict:
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": customer_id,
        "X-Signature": signature,
    }


def _is_retryable_naver_exception(exc: BaseException) -> bool:
    """429/5xx + 네트워크 장애만 재시도. 401/403/400 등 클라이언트 에러는 재시도하지 않음."""
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return status in (429, 500, 502, 503, 504)
    if isinstance(exc, requests.exceptions.RequestException):
        # ConnectionError, Timeout 등 네트워크 일시 장애만 재시도
        return isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout))
    return False


@retry(
    retry=retry_if_exception(_is_retryable_naver_exception),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _call_naver_api(method: str, endpoint: str, api_key: str, secret_key: str, customer_id: str, params: dict = None, json: dict = None) -> dict | list:
    timestamp = str(int(time.time() * 1000))
    uri = endpoint.split("naver.com")[-1]
    signature = _make_naver_signature(timestamp, method, uri, secret_key)
    headers = _naver_headers(timestamp, api_key, customer_id, signature)
    
    base_url = f"{API_BASE}{uri}"
    resp = requests.request(method, base_url, headers=headers, params=params, json=json, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _pick_first(record: dict, *keys: str) -> str | None:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _sanitize_naver_credential(value: str) -> str:
    return str(value or "").strip().replace('"', "").replace("'", "")


class NaverAdsIngestor:
    name = "naver_ads"
    channel_key = "NAVER_ADS"
    supports_warehouse = True

    def run(self, ctx: IngestContext) -> IngestResult:
        logger = setup_logger("new_data_flow.naver_ads", ctx.settings.app.log_level)
        provider_cfg = (ctx.settings.providers or {}).get("naver_ads", {})
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

        api_key = resolve_credential_value(
            secret_data=secret_data,
            env_key="NAVER_API_KEY",
            env_fallback_enabled=env_fallback_enabled,
        )
        secret_key = resolve_credential_value(
            secret_data=secret_data,
            env_key="NAVER_SECRET_KEY",
            env_fallback_enabled=env_fallback_enabled,
        )
        customer_id = resolve_credential_value(
            secret_data=secret_data,
            env_key="NAVER_CUSTOMER_ID",
            env_fallback_enabled=env_fallback_enabled,
        )
        api_key = _sanitize_naver_credential(api_key)
        secret_key = _sanitize_naver_credential(secret_key)
        customer_id = _sanitize_naver_credential(customer_id)

        account_ids: list[str] = []
        if ctx.account_id_norm:
            account_ids = [ctx.account_id_norm]
        else:
            account_ids = provider_cfg.get("account_ids", []) or []
        if not account_ids and customer_id:
            account_ids = [customer_id]

        if not api_key or not secret_key or not customer_id:
            if env_fallback_enabled:
                raise ValueError("Naver Ads API credentials missing (NAVER_API_KEY, NAVER_SECRET_KEY, NAVER_CUSTOMER_ID)")
            raise ValueError("Naver Ads API credentials missing in Secret Manager and env fallback is disabled")
        if not account_ids:
            raise ValueError("No Naver Ads account configured")

        all_perf_rows: list[dict] = []
        all_creative_rows: list[dict] = []
        checked_accounts: list[str] = []
        account_failures = 0

        start_s = ctx.start_date.strftime("%Y-%m-%d")
        end_s = ctx.end_date.strftime("%Y-%m-%d")
        source_extract_ts = _utc_now_iso()
        run_ingestion_id = str(uuid.uuid4())

        campaign_name_by_id: dict[str, str] = {}
        adgroup_meta_by_id: dict[str, dict[str, str]] = {}

        # Naver API는 customer-level 이므로, account_ids는 실질적으로 customer 레이블.
        # branch 구분은 V1에서 ad_group_name 규칙으로 수행한다.
        try:
            campaigns_raw = _call_naver_api(
                "GET",
                "/ncc/campaigns",
                api_key=api_key,
                secret_key=secret_key,
                customer_id=customer_id,
            )
            campaigns = campaigns_raw if isinstance(campaigns_raw, list) else campaigns_raw.get("data", [])
            for campaign in campaigns:
                campaign_id = _pick_first(campaign, "nccCampaignId", "campaignId", "id")
                campaign_name = _pick_first(campaign, "name", "campaignName")
                if campaign_id:
                    campaign_name_by_id[campaign_id] = campaign_name or ""
            logger.info("naver ads campaigns fetched | customer=%s count=%s", customer_id, len(campaigns))
        except Exception as exc:
            logger.error("naver ads campaign fetch failed | customer=%s err=%s", customer_id, exc)
            account_failures += 1
            campaigns = []

        if campaigns:
            checked_accounts.append(customer_id)

        campaign_ids = [
            campaign_id
            for campaign_id in (
                _pick_first(campaign, "nccCampaignId", "campaignId", "id") for campaign in campaigns
            )
            if campaign_id
        ]

        try:
            adgroups_raw = _call_naver_api(
                "GET",
                "/ncc/adgroups",
                api_key=api_key,
                secret_key=secret_key,
                customer_id=customer_id,
            )
            adgroups = adgroups_raw if isinstance(adgroups_raw, list) else adgroups_raw.get("data", [])
            for adgroup in adgroups:
                adgroup_id = _pick_first(adgroup, "nccAdgroupId", "adgroupId", "id")
                campaign_id = _pick_first(adgroup, "nccCampaignId", "campaignId")
                adgroup_name = _pick_first(adgroup, "name", "adgroupName")
                if adgroup_id:
                    adgroup_meta_by_id[adgroup_id] = {
                        "campaign_id": campaign_id or "",
                        "ad_group_name": adgroup_name or "",
                    }
            logger.info("naver ads adgroups fetched | customer=%s count=%s", customer_id, len(adgroups))
        except Exception as exc:
            logger.warning("naver ads adgroup fetch failed | customer=%s err=%s", customer_id, exc)
            adgroups = []

        adgroup_ids = sorted(adgroup_meta_by_id.keys())

        # 2. 광고그룹 성과 조회
        stats_endpoint = "/stats"
        target_adgroup_ids = adgroup_ids[:ctx.api_sample_size] if ctx.api_test_only else adgroup_ids
        if not target_adgroup_ids and campaign_ids:
            logger.warning("naver ads adgroup ids not found; falling back to campaign-level stats")
            target_adgroup_ids = campaign_ids[:ctx.api_sample_size] if ctx.api_test_only else campaign_ids

        if target_adgroup_ids:
            try:
                stats_params = {
                    "ids": target_adgroup_ids,
                    "fields": json.dumps(["clkCnt", "impCnt", "salesAmt"]),
                    "timeRange": json.dumps({"since": start_s, "until": end_s}),
                    "breakdown": "none",
                    "timeIncrement": "all",
                }
                stats_raw = _call_naver_api(
                    "GET",
                    stats_endpoint,
                    api_key=api_key,
                    secret_key=secret_key,
                    customer_id=customer_id,
                    params=stats_params,
                )
                stats_items = stats_raw if isinstance(stats_raw, list) else stats_raw.get("data", [])
                logger.info("naver ads stats fetched | entity_count=%s rows=%s", len(target_adgroup_ids), len(stats_items))
            except Exception as exc:
                logger.error("naver ads stats fetch failed | entity_count=%s err=%s", len(target_adgroup_ids), exc)
                stats_items = []
        else:
            stats_items = []

        for stat in stats_items:
                ad_group_id = _pick_first(stat, "adgroupId", "nccAdgroupId", "id")
                adgroup_meta = adgroup_meta_by_id.get(ad_group_id or "", {})
                campaign_id = _pick_first(stat, "campaignId", "nccCampaignId") or adgroup_meta.get("campaign_id") or ""
                campaign_name = campaign_name_by_id.get(campaign_id, "")
                ad_group_name = _pick_first(stat, "adgroupName") or adgroup_meta.get("ad_group_name") or None
                perf_row = {
                    "ingestion_id": run_ingestion_id,
                    "ingestion_ts": _utc_now_iso(),
                    "source_extract_ts": source_extract_ts,
                    "account_id": customer_id,
                    "campaign_id": campaign_id or None,
                    "campaign_name": campaign_name or None,
                    "ad_group_id": ad_group_id or None,
                    "ad_group_name": ad_group_name,
                    "ad_id": None,
                    "ad_name": None,
                    "stat_date": str(stat.get("date", end_s)),
                    "impressions": int(float(stat.get("impressions", stat.get("impCnt", 0)))),
                    "clicks": int(float(stat.get("clicks", stat.get("clkCnt", 0)))),
                    "spend": str(stat.get("cost", stat.get("salesAmt", ""))),
                    "ctr": stat.get("ctr"),
                    "avg_cpc": stat.get("avgCpc"),
                    "source_payload": _to_plain_json(stat),
                }
                all_perf_rows.append(perf_row)

        # 3. 소재(크리에이티브) 조회 - 키워드/콘텐츠 광고 기준 ads 조회
        ads: list[dict] = []
        creative_target_adgroups = target_adgroup_ids[:ctx.api_sample_size] if ctx.api_test_only else target_adgroup_ids
        for adgroup_id in creative_target_adgroups:
            try:
                ads_raw = _call_naver_api(
                    "GET",
                    "/ncc/ads",
                    api_key=api_key,
                    secret_key=secret_key,
                    customer_id=customer_id,
                    params={"nccAdgroupId": adgroup_id},
                )
                ad_rows = ads_raw if isinstance(ads_raw, list) else ads_raw.get("data", [])
                ads.extend(ad_rows)
            except Exception as exc:
                logger.warning("naver ads creative fetch failed | customer=%s adgroup=%s err=%s", customer_id, adgroup_id, exc)
        if ctx.api_test_only:
            ads = ads[:ctx.api_sample_size]
        logger.info("naver ads creative fetched | customer=%s rows=%s", customer_id, len(ads))

        for ad in ads:
            ad_group_id = _pick_first(ad, "adgroupId", "nccAdgroupId")
            adgroup_meta = adgroup_meta_by_id.get(ad_group_id or "", {})
            creative_row = {
                "ingestion_id": run_ingestion_id,
                "ingestion_ts": _utc_now_iso(),
                "source_extract_ts": source_extract_ts,
                "collected_date": end_s,
                "account_id": customer_id,
                "campaign_id": _pick_first(ad, "campaignId", "nccCampaignId") or adgroup_meta.get("campaign_id", ""),
                "ad_group_id": ad_group_id or "",
                "ad_id": _pick_first(ad, "adId", "nccAdId") or "",
                "creative_id": _pick_first(ad, "adId", "nccAdId") or "",
                "creative_name": _pick_first(ad, "adName", "name") or "",
                "ad_type": _pick_first(ad, "adType", "type") or "",
                # Assets-only policy: creative text fields are intentionally not collected.
                "headline": _pick_first(ad, "headline", "title") or "",
                "body_text": _pick_first(ad, "description", "descriptionLine") or "",
                "thumbnail_url": str((ad.get("image") or {}).get("url", "")),
                "source_payload": _to_plain_json(ad),
            }
            all_creative_rows.append(creative_row)

        if not checked_accounts and account_failures > 0:
            raise ValueError(f"Naver Ads ingest failed for all accounts (failed_accounts={account_failures})")

        if ctx.api_test_only or ctx.dry_run:
            return IngestResult(
                channel=self.name,
                status="API_OK",
                message=(
                    f"accounts={len(checked_accounts)}, perf_rows={len(all_perf_rows)}, "
                    f"creative_rows={len(all_creative_rows)}, mode={'API_TEST' if ctx.api_test_only else 'DRY_RUN'}"
                ),
            )

        raw_naver = (ctx.settings.raw_tables or {}).get("naver_ads", {})
        perf_table = raw_naver.get("performance", "raw_ads.naver_ads_performance_raw")
        creative_table = raw_naver.get("creative", "raw_ads.naver_ads_creative_raw")

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
                rows=all_perf_rows,
            )
            creative_loaded = load_idempotent_json(
                client=bq_client,
                table_ref=creative_table_ref,
                date_column="collected_date",
                start_date=start_s,
                end_date=end_s,
                account_ids=checked_accounts,
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

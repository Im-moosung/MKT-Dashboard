from __future__ import annotations

import time
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.api_core.exceptions import RetryError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from channels.base import IngestContext, IngestResult
from common.bigquery_loader import (
    append_json_rows,
    build_bigquery_client,
    delete_rows_before,
    load_idempotent_json,
)
from common.credential_policy import allow_env_fallback, resolve_credential_value
from common.logger import setup_logger
from common.gcp_secret_manager import access_secret_dict


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_account_id(account_id: str) -> str:
    if not account_id:
        return ""
    return account_id.replace("-", "")


def _to_plain_json(value):
    """Convert objects to JSON primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_plain_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_plain_json(v) for v in value]
    if hasattr(value, "_pb"):
        from google.protobuf.json_format import MessageToDict
        return MessageToDict(value._pb, preserving_proto_field_name=True)
    return str(value)


def _enum_name(value) -> str | None:
    if value is None:
        return None
    name = getattr(value, "name", None)
    if isinstance(name, str) and name:
        return name
    text = str(value)
    if text:
        return text
    return None


def _extract_text_asset(asset_obj) -> str:
    """Handle both proto-plus text shapes used in Google Ads assets."""
    if asset_obj is None:
        return ""

    direct_text = getattr(asset_obj, "text", None)
    if direct_text:
        return str(direct_text)

    nested_asset = getattr(asset_obj, "asset", None)
    if nested_asset:
        text_asset = getattr(nested_asset, "text_asset", None)
        nested_text = getattr(text_asset, "text", None) if text_asset else None
        if nested_text:
            return str(nested_text)

    return ""


def _extract_asset_id(asset_resource_name: str | None) -> str | None:
    if not asset_resource_name:
        return None
    # Example: customers/1234567890/assets/987654321
    parts = str(asset_resource_name).split("/")
    if len(parts) >= 2 and parts[-2] == "assets":
        return parts[-1]
    return str(asset_resource_name)


def _normalize_geo_target_constant(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("geoTargetConstants/"):
        return text
    if text.isdigit():
        return f"geoTargetConstants/{text}"
    return text


def _normalize_action_type_raw(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    normalized = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in text)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    normalized = normalized.strip("_")
    return normalized or None


ALLOWED_REGION_COUNTRY_IDS = {
    "geoTargetConstants/2840",  # United States
    "geoTargetConstants/2124",  # Canada
    "geoTargetConstants/2484",  # Mexico
}


def _extract_region_or_others(row) -> str | None:
    country = _normalize_geo_target_constant(
        getattr(getattr(row, "user_location_view", None), "country_criterion_id", None)
    )
    if country not in ALLOWED_REGION_COUNTRY_IDS:
        return "others"
    region = _normalize_geo_target_constant(getattr(getattr(row, "segments", None), "geo_target_region", None))
    return region or "others"


def _to_bq_numeric(value, scale: int = 6) -> str | None:
    """Return BigQuery NUMERIC-safe decimal string."""
    if value is None:
        return None
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    quant = Decimal("1").scaleb(-scale)
    return format(dec.quantize(quant, rounding=ROUND_HALF_UP), "f")


def _build_google_campaign_breakdown_rows(
    *,
    google_client,
    account_norm: str,
    start_s: str,
    end_s: str,
    source_extract_ts: str,
    run_ingestion_id: str,
    api_test_only: bool,
    api_sample_size: int,
    logger,
) -> list[dict]:
    """Collect campaign-level Google Ads breakdown rows for selected dimensions."""
    specs = [
        {
            "breakdown_key": "age_range",
            "field_name": "age_range",
            "source_view": "age_range_view",
            "query": """
                SELECT
                    campaign.id,
                    campaign.name,
                    segments.date,
                    ad_group_criterion.age_range.type,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM age_range_view
                WHERE segments.date BETWEEN '{start_s}' AND '{end_s}'
                  AND metrics.impressions > 0
            """,
            "value_extractor": lambda row: _enum_name(
                getattr(getattr(getattr(row, "ad_group_criterion", None), "age_range", None), "type", None)
            ),
        },
        {
            "breakdown_key": "gender",
            "field_name": "gender",
            "source_view": "gender_view",
            "query": """
                SELECT
                    campaign.id,
                    campaign.name,
                    segments.date,
                    ad_group_criterion.gender.type,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM gender_view
                WHERE segments.date BETWEEN '{start_s}' AND '{end_s}'
                  AND metrics.impressions > 0
            """,
            "value_extractor": lambda row: _enum_name(
                getattr(getattr(getattr(row, "ad_group_criterion", None), "gender", None), "type", None)
            ),
        },
        {
            "breakdown_key": "geo_target_country",
            "field_name": "geo_target_country",
            "source_view": "user_location_view",
            "query": """
                SELECT
                    campaign.id,
                    campaign.name,
                    segments.date,
                    user_location_view.country_criterion_id,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM user_location_view
                WHERE segments.date BETWEEN '{start_s}' AND '{end_s}'
                  AND metrics.impressions > 0
                  AND user_location_view.country_criterion_id > 0
            """,
            "value_extractor": lambda row: _normalize_geo_target_constant(
                getattr(getattr(row, "user_location_view", None), "country_criterion_id", None)
            ),
        },
        {
            "breakdown_key": "geo_target_region",
            "field_name": "geo_target_region",
            "source_view": "user_location_view",
            "query": """
                SELECT
                    campaign.id,
                    campaign.name,
                    segments.date,
                    segments.geo_target_region,
                    user_location_view.country_criterion_id,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM user_location_view
                WHERE segments.date BETWEEN '{start_s}' AND '{end_s}'
                  AND metrics.impressions > 0
            """,
            "value_extractor": _extract_region_or_others,
        },
    ]

    rows: list[dict] = []
    for spec in specs:
        query = spec["query"].format(start_s=start_s, end_s=end_s)
        if api_test_only:
            query += f" LIMIT {api_sample_size}"
        try:
            fetched = _search_google_ads_with_retry(google_client, account_norm, query)
            logger.info(
                "google ads campaign breakdown fetched | account=%s key=%s rows=%s",
                account_norm,
                spec["breakdown_key"],
                len(fetched),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "google ads campaign breakdown fetch failed | account=%s key=%s err=%s",
                account_norm,
                spec["breakdown_key"],
                exc,
            )
            fetched = []

        for row in fetched:
            campaign = getattr(row, "campaign", None)
            segments = getattr(row, "segments", None)
            metrics = getattr(row, "metrics", None)

            campaign_id = str(getattr(campaign, "id", "")) if campaign else ""
            if not campaign_id:
                continue
            breakdown_value = spec["value_extractor"](row)
            if not breakdown_value:
                continue

            stat_date = getattr(segments, "date", "") or end_s
            cost_micros = int(getattr(metrics, "cost_micros", 0) or 0) if metrics else 0

            breakdown_row = {
                "ingestion_id": run_ingestion_id,
                "ingestion_ts": _utc_now_iso(),
                "source_extract_ts": source_extract_ts,
                "customer_id": account_norm,
                "campaign_id": campaign_id,
                "campaign_name": str(getattr(campaign, "name", "")) if campaign else None,
                "stat_date": stat_date,
                "breakdown_key": spec["breakdown_key"],
                "breakdown_value": breakdown_value,
                "age_range": None,
                "gender": None,
                "parental_status": None,
                "income_range": None,
                "geo_target_country": None,
                "geo_target_region": None,
                "geo_target_city": None,
                "impressions": int(getattr(metrics, "impressions", 0) or 0) if metrics else 0,
                "clicks": int(getattr(metrics, "clicks", 0) or 0) if metrics else 0,
                "cost_micros": cost_micros,
                "conversions": float(getattr(metrics, "conversions", 0) or 0) if metrics else 0.0,
                "conversions_value": float(getattr(metrics, "conversions_value", 0) or 0) if metrics else 0.0,
                "source_view": spec["source_view"],
                "source_payload": _to_plain_json(row),
            }
            breakdown_row[spec["field_name"]] = breakdown_value
            rows.append(breakdown_row)

    # Guard against duplicate grain from API response artifacts.
    agg: dict[tuple[str, str, str, str, str], dict] = {}
    for row in rows:
        key = (
            row["customer_id"],
            row["campaign_id"],
            row["stat_date"],
            row["breakdown_key"],
            row["breakdown_value"],
        )
        if key not in agg:
            agg[key] = dict(row)
            continue
        cur = agg[key]
        cur["impressions"] = int(cur["impressions"] or 0) + int(row["impressions"] or 0)
        cur["clicks"] = int(cur["clicks"] or 0) + int(row["clicks"] or 0)
        cur["cost_micros"] = int(cur["cost_micros"] or 0) + int(row["cost_micros"] or 0)
        cur["conversions"] = float(cur["conversions"] or 0.0) + float(row["conversions"] or 0.0)
        cur["conversions_value"] = float(cur["conversions_value"] or 0.0) + float(row["conversions_value"] or 0.0)
        cur["source_extract_ts"] = max(str(cur["source_extract_ts"]), str(row["source_extract_ts"]))
        cur["ingestion_ts"] = max(str(cur["ingestion_ts"]), str(row["ingestion_ts"]))

    normalized_rows: list[dict] = []
    for row in agg.values():
        row["conversions_value"] = _to_bq_numeric(row.get("conversions_value"), scale=6)
        normalized_rows.append(row)

    return normalized_rows


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


def _is_retryable_google_exception(exc: BaseException) -> bool:
    if isinstance(exc, RetryError):
        return True
    if isinstance(exc, GoogleAdsException):
        first_error = exc.failure.errors[0] if exc.failure.errors else None
        if first_error:
            # Check for RateLimitError, InternalError, QuotaError
            reason = str(getattr(first_error.error_code, "reason", ""))
            error_type = type(first_error.error_code).__name__
            if "RateLimitError" in error_type or "InternalError" in error_type or "QuotaError" in error_type:
                return True
    return isinstance(exc, (TimeoutError, ConnectionError))


@retry(
    retry=retry_if_exception(_is_retryable_google_exception),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _search_google_ads_with_retry(client, customer_id: str, query: str):
    ga_service = client.get_service("GoogleAdsService")
    search_request = client.get_type("SearchGoogleAdsStreamRequest")
    search_request.customer_id = customer_id
    search_request.query = query
    response = ga_service.search_stream(search_request)
    
    rows = []
    for batch in response:
        for row in batch.results:
            rows.append(row)
    return rows


class GoogleAdsIngestor:
    name = "google_ads"
    channel_key = "GOOGLE_ADS"
    supports_warehouse = True

    def run(self, ctx: IngestContext) -> IngestResult:
        logger = setup_logger("new_data_flow.google_ads", ctx.settings.app.log_level)
        provider_cfg = (ctx.settings.providers or {}).get("google_ads", {})
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

        client_id = resolve_credential_value(
            secret_data=secret_data,
            env_key="GOOGLE_CLIENT_ID",
            env_fallback_enabled=env_fallback_enabled,
        )
        client_secret = resolve_credential_value(
            secret_data=secret_data,
            env_key="GOOGLE_CLIENT_SECRET",
            env_fallback_enabled=env_fallback_enabled,
        )
        refresh_token = resolve_credential_value(
            secret_data=secret_data,
            env_key="GOOGLE_REFRESH_TOKEN",
            env_fallback_enabled=env_fallback_enabled,
        )
        developer_token = resolve_credential_value(
            secret_data=secret_data,
            env_key="GOOGLE_DEVELOPER_TOKEN",
            env_fallback_enabled=env_fallback_enabled,
        )
        login_customer_id = resolve_credential_value(
            secret_data=secret_data,
            env_key="GOOGLE_LOGIN_CUSTOMER_ID",
            env_fallback_enabled=env_fallback_enabled,
        )

        account_ids: list[str] = []
        if ctx.account_id_norm:
            account_ids = [ctx.account_id_norm]
        else:
            account_ids = provider_cfg.get("account_ids", []) or []

        if not client_id or not client_secret or not refresh_token or not developer_token:
            if env_fallback_enabled:
                raise ValueError("Google Ads API credentials missing")
            raise ValueError("Google Ads API credentials missing in Secret Manager and env fallback is disabled")
        if not account_ids:
            raise ValueError("No Google Ads account configured")

        credentials_dict = {
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "use_proto_plus": True
        }
        if login_customer_id:
            login_customer_id_norm = login_customer_id.replace("-", "").replace(" ", "")
            if login_customer_id_norm.isdigit() and len(login_customer_id_norm) == 10:
                credentials_dict["login_customer_id"] = login_customer_id_norm
            else:
                logger.warning(
                    "GOOGLE_LOGIN_CUSTOMER_ID value is not a 10-digit number (input: %r). "
                    "login_customer_id must be a 10-digit MCC account ID. Proceeding without login_customer_id.",
                    login_customer_id,
                )

        try:
            google_client = GoogleAdsClient.load_from_dict(credentials_dict)
        except Exception as exc:
            raise ValueError(f"Failed to initialize Google Ads client: {exc}")

        all_perf_rows: list[dict] = []
        all_creative_rows: list[dict] = []
        all_action_rows: list[dict] = []
        all_conversion_action_dim_rows: list[dict] = []
        all_asset_perf_rows: list[dict] = []
        all_campaign_breakdown_rows: list[dict] = []
        checked_accounts: list[str] = []
        account_failures = 0

        start_s = ctx.start_date.strftime("%Y-%m-%d")
        end_s = ctx.end_date.strftime("%Y-%m-%d")
        source_extract_ts = _utc_now_iso()
        run_ingestion_id = str(uuid.uuid4())

        for raw_account_id in account_ids:
            account_norm = _normalize_account_id(str(raw_account_id))
            
            query = f"""
                SELECT
                    customer.id,
                    customer.descriptive_name,
                    campaign.id,
                    campaign.name,
                    campaign.advertising_channel_type,
                    ad_group.id,
                    ad_group.name,
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.ad.type,
                    segments.date,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM ad_group_ad
                WHERE segments.date BETWEEN '{start_s}' AND '{end_s}'
                  AND metrics.impressions > 0
            """
            
            if ctx.api_test_only:
                query += f" LIMIT {ctx.api_sample_size}"

            try:
                insights_rows = _search_google_ads_with_retry(google_client, account_norm, query)
                checked_accounts.append(account_norm)
                logger.info("google ads performance fetched | account=%s rows=%s", account_norm, len(insights_rows))
            except Exception as exc:
                account_failures += 1
                logger.error("google ads fetch failed | account=%s err=%s", account_norm, exc)
                continue

            for row in insights_rows:
                campaign = getattr(row, "campaign", None)
                ad_group = getattr(row, "ad_group", None)
                ad_group_ad = getattr(row, "ad_group_ad", None)
                ad = getattr(ad_group_ad, "ad", None) if ad_group_ad else None
                segments = getattr(row, "segments", None)
                metrics = getattr(row, "metrics", None)

                cost_micros = getattr(metrics, "cost_micros", 0) if metrics else 0

                perf_row = {
                    "ingestion_id": run_ingestion_id,
                    "ingestion_ts": _utc_now_iso(),
                    "source_extract_ts": source_extract_ts,
                    "customer_id": account_norm,
                    "campaign_id": str(getattr(campaign, "id", "")) if campaign else None,
                    "campaign_name": str(getattr(campaign, "name", "")) if campaign else None,
                    "ad_group_id": str(getattr(ad_group, "id", "")) if ad_group else None,
                    "ad_group_name": str(getattr(ad_group, "name", "")) if ad_group else None,
                    "ad_id": str(getattr(ad, "id", "")) if ad else None,
                    "ad_name": str(getattr(ad, "name", "")) if ad else None,
                    "stat_date": getattr(segments, "date", ""),
                    "impressions": int(getattr(metrics, "impressions", 0) or 0) if metrics else None,
                    "clicks": int(getattr(metrics, "clicks", 0) or 0) if metrics else None,
                    "cost_micros": int(cost_micros or 0),
                    "conversions": float(getattr(metrics, "conversions", 0) or 0) if metrics else None,
                    "conversions_value": float(getattr(metrics, "conversions_value", 0) or 0) if metrics else None,
                    "source_payload": _to_plain_json(row),
                }
                all_perf_rows.append(perf_row)

            action_query = f"""
                SELECT
                    customer.id,
                    campaign.id,
                    campaign.name,
                    segments.date,
                    segments.conversion_action,
                    segments.conversion_action_name,
                    segments.conversion_action_category,
                    metrics.all_conversions,
                    metrics.all_conversions_value
                FROM campaign
                WHERE segments.date BETWEEN '{start_s}' AND '{end_s}'
                  AND metrics.all_conversions > 0
            """
            if ctx.api_test_only:
                action_query += f" LIMIT {ctx.api_sample_size}"

            try:
                action_rows = _search_google_ads_with_retry(google_client, account_norm, action_query)
                logger.info("google ads action fetched | account=%s rows=%s", account_norm, len(action_rows))
            except Exception as exc:
                logger.warning("google ads action fetch failed | account=%s err=%s", account_norm, exc)
                action_rows = []

            for row in action_rows:
                campaign_ac = getattr(row, "campaign", None)
                segments_ac = getattr(row, "segments", None)
                metrics_ac = getattr(row, "metrics", None)

                action_category = _enum_name(getattr(segments_ac, "conversion_action_category", None))
                action_name = str(getattr(segments_ac, "conversion_action_name", "") or "")
                action_type_raw = _normalize_action_type_raw(action_category) or _normalize_action_type_raw(action_name)
                if not action_type_raw:
                    continue

                action_count = float(getattr(metrics_ac, "all_conversions", 0) or 0) if metrics_ac else 0.0
                if action_count <= 0:
                    continue

                action_row = {
                    "ingestion_id": run_ingestion_id,
                    "ingestion_ts": _utc_now_iso(),
                    "source_extract_ts": source_extract_ts,
                    "customer_id": account_norm,
                    "campaign_id": str(getattr(campaign_ac, "id", "")) if campaign_ac else None,
                    "campaign_name": str(getattr(campaign_ac, "name", "")) if campaign_ac else None,
                    "ad_group_id": None,
                    "ad_group_name": None,
                    "ad_id": None,
                    "ad_name": None,
                    "stat_date": getattr(segments_ac, "date", "") or end_s,
                    "conversion_action_resource_name": str(getattr(segments_ac, "conversion_action", "") or ""),
                    "conversion_action_id": _extract_asset_id(str(getattr(segments_ac, "conversion_action", "") or "")),
                    "conversion_action_name": action_name or None,
                    "conversion_action_category": action_category or None,
                    "action_type_raw": action_type_raw,
                    "action_count": action_count,
                    "action_value": _to_bq_numeric(
                        float(getattr(metrics_ac, "all_conversions_value", 0) or 0) if metrics_ac else 0.0,
                        scale=6,
                    ),
                    "source_payload": _to_plain_json(row),
                }
                all_action_rows.append(action_row)

            conversion_action_dim_query = """
                SELECT
                    conversion_action.resource_name,
                    conversion_action.id,
                    conversion_action.name,
                    conversion_action.category,
                    conversion_action.type,
                    conversion_action.status,
                    conversion_action.primary_for_goal,
                    conversion_action.include_in_conversions_metric
                FROM conversion_action
                WHERE conversion_action.status != REMOVED
            """
            if ctx.api_test_only:
                conversion_action_dim_query += f" LIMIT {ctx.api_sample_size}"
            try:
                conversion_action_dim_rows = _search_google_ads_with_retry(
                    google_client,
                    account_norm,
                    conversion_action_dim_query,
                )
                logger.info(
                    "google ads conversion_action dim fetched | account=%s rows=%s",
                    account_norm,
                    len(conversion_action_dim_rows),
                )
            except Exception as exc:
                logger.warning("google ads conversion_action dim fetch failed | account=%s err=%s", account_norm, exc)
                conversion_action_dim_rows = []

            seen_dim_ids: set[str] = set()
            for row in conversion_action_dim_rows:
                ca = getattr(row, "conversion_action", None)
                if not ca:
                    continue
                resource_name = str(getattr(ca, "resource_name", "") or "")
                conversion_action_id = str(getattr(ca, "id", "") or "")
                dedup_key = resource_name or conversion_action_id
                if not dedup_key or dedup_key in seen_dim_ids:
                    continue
                seen_dim_ids.add(dedup_key)

                all_conversion_action_dim_rows.append(
                    {
                        "ingestion_id": run_ingestion_id,
                        "ingestion_ts": _utc_now_iso(),
                        "source_extract_ts": source_extract_ts,
                        "collected_date": end_s,
                        "customer_id": account_norm,
                        "conversion_action_resource_name": resource_name or None,
                        "conversion_action_id": conversion_action_id or _extract_asset_id(resource_name),
                        "conversion_action_name": str(getattr(ca, "name", "") or "") or None,
                        "conversion_action_category": _enum_name(getattr(ca, "category", None)),
                        "conversion_action_type": _enum_name(getattr(ca, "type_", None)),
                        "conversion_action_status": _enum_name(getattr(ca, "status", None)),
                        "primary_for_goal": bool(getattr(ca, "primary_for_goal", False)),
                        "include_in_conversions_metric": bool(
                            getattr(ca, "include_in_conversions_metric", False)
                        ),
                        "source_payload": _to_plain_json(row),
                    }
                )

            creative_query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    ad_group.id,
                    ad_group.name,
                    ad_group_ad.status,
                    ad_group_ad.ad_strength,
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.ad.type,
                    ad_group_ad.ad.final_urls,
                    ad_group_ad.ad.image_ad.image_url,
                    ad_group_ad.ad.video_ad.video.asset,
                    segments.date
                FROM ad_group_ad
                WHERE segments.date BETWEEN '{start_s}' AND '{end_s}'
                  AND metrics.impressions > 0
            """
            
            if ctx.api_test_only:
                creative_query += f" LIMIT {ctx.api_sample_size}"

            try:
                creative_rows = _search_google_ads_with_retry(google_client, account_norm, creative_query)
                logger.info("google ads creative fetched | account=%s rows=%s", account_norm, len(creative_rows))
            except Exception as exc:
                logger.warning("google ads creative fetch failed | account=%s err=%s", account_norm, exc)
                creative_rows = []

            for row in creative_rows:
                ad_group_ad = getattr(row, "ad_group_ad", None)
                ad = getattr(ad_group_ad, "ad", None) if ad_group_ad else None
                campaign_cr = getattr(row, "campaign", None)
                ad_group_cr = getattr(row, "ad_group", None)
                segments_cr = getattr(row, "segments", None)
                if not ad:
                    continue

                ad_id = str(getattr(ad, "id", ""))
                ad_type = _enum_name(getattr(ad, "type_", None))

                final_urls = list(getattr(ad, "final_urls", []) or [])
                image_urls = []
                image_ad = getattr(ad, "image_ad", None)
                image_url = getattr(image_ad, "image_url", None) if image_ad else None
                if image_url:
                    image_urls.append(str(image_url))
                youtube_video_ids = []
                video_ad = getattr(ad, "video_ad", None)
                video_obj = getattr(video_ad, "video", None) if video_ad else None
                video_asset_resource = getattr(video_obj, "asset", None) if video_obj else None
                if video_asset_resource:
                    video_asset_id = _extract_asset_id(str(video_asset_resource))
                    youtube_video_ids.append(str(video_asset_id or video_asset_resource))

                creative_row = {
                    "ingestion_id": run_ingestion_id,
                    "ingestion_ts": _utc_now_iso(),
                    "source_extract_ts": source_extract_ts,
                    "collected_date": getattr(segments_cr, "date", None) or end_s,
                    "customer_id": account_norm,
                    "campaign_id": str(getattr(campaign_cr, "id", "")) if campaign_cr else None,
                    "ad_group_id": str(getattr(ad_group_cr, "id", "")) if ad_group_cr else None,
                    "ad_id": ad_id,
                    "creative_id": ad_id,
                    "creative_name": str(getattr(ad, "name", "")),
                    "ad_type": ad_type,
                    "ad_strength": _enum_name(getattr(ad_group_ad, "ad_strength", None)) if ad_group_ad else None,
                    "status": _enum_name(getattr(ad_group_ad, "status", None)) if ad_group_ad else None,
                    # Assets-only policy: creative text fields are intentionally not collected.
                    "headline_1": None,
                    "headline_2": None,
                    "headline_3": None,
                    "description_1": None,
                    "description_2": None,
                    "business_name": None,
                    "call_to_action": None,
                    "final_urls": [str(u) for u in final_urls] if final_urls else [],
                    "image_urls": image_urls,
                    "youtube_video_ids": youtube_video_ids,
                    "source_payload": _to_plain_json(row),
                }
                all_creative_rows.append(creative_row)

            def _append_non_pmax_asset_perf_rows(rows: list) -> None:
                for row in rows:
                    campaign_as = getattr(row, "campaign", None)
                    ad_group_as = getattr(row, "ad_group", None)
                    ad_group_ad_as = getattr(row, "ad_group_ad", None)
                    ad_as = getattr(ad_group_ad_as, "ad", None) if ad_group_ad_as else None
                    view_as = getattr(row, "ad_group_ad_asset_view", None)
                    metrics_as = getattr(row, "metrics", None)
                    segments_as = getattr(row, "segments", None)

                    asset_resource_name = str(getattr(view_as, "asset", "")) if view_as else ""
                    asset_id = _extract_asset_id(asset_resource_name)
                    cost_micros = int(getattr(metrics_as, "cost_micros", 0) or 0) if metrics_as else 0

                    asset_perf_row = {
                        "ingestion_id": run_ingestion_id,
                        "ingestion_ts": _utc_now_iso(),
                        "source_extract_ts": source_extract_ts,
                        "stat_date": getattr(segments_as, "date", "") or end_s,
                        "customer_id": account_norm,
                        "campaign_id": str(getattr(campaign_as, "id", "")) if campaign_as else None,
                        "campaign_channel_type": _enum_name(getattr(campaign_as, "advertising_channel_type", None))
                        if campaign_as
                        else None,
                        "asset_group_id": None,
                        "ad_group_id": str(getattr(ad_group_as, "id", "")) if ad_group_as else None,
                        "ad_id": str(getattr(ad_as, "id", "")) if ad_as else None,
                        "asset_id": asset_id,
                        "asset_resource_name": asset_resource_name or None,
                        "field_type": _enum_name(getattr(view_as, "field_type", None)) if view_as else None,
                        "performance_label": _enum_name(getattr(view_as, "performance_label", None)) if view_as else None,
                        "is_pmax": False,
                        "impressions": int(getattr(metrics_as, "impressions", 0) or 0) if metrics_as else 0,
                        "clicks": int(getattr(metrics_as, "clicks", 0) or 0) if metrics_as else 0,
                        "cost_micros": cost_micros,
                        "conversions": float(getattr(metrics_as, "conversions", 0) or 0) if metrics_as else 0.0,
                        "conversions_value": float(getattr(metrics_as, "conversions_value", 0) or 0) if metrics_as else 0.0,
                        "source_view": "ad_group_ad_asset_view",
                        "source_payload": _to_plain_json(row),
                    }
                    if asset_perf_row["asset_id"]:
                        all_asset_perf_rows.append(asset_perf_row)

            # Non-PMax SEARCH asset performance: text only
            asset_query_search_text = f"""
                SELECT
                    campaign.id,
                    campaign.advertising_channel_type,
                    ad_group.id,
                    ad_group_ad.ad.id,
                    ad_group_ad_asset_view.asset,
                    ad_group_ad_asset_view.field_type,
                    ad_group_ad_asset_view.performance_label,
                    segments.date,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM ad_group_ad_asset_view
                WHERE segments.date BETWEEN '{start_s}' AND '{end_s}'
                  AND campaign.advertising_channel_type = SEARCH
                  AND ad_group_ad_asset_view.field_type IN (HEADLINE, DESCRIPTION)
                  AND metrics.impressions > 0
            """
            if ctx.api_test_only:
                asset_query_search_text += f" LIMIT {ctx.api_sample_size}"

            try:
                search_text_asset_rows = _search_google_ads_with_retry(google_client, account_norm, asset_query_search_text)
                logger.info(
                    "google ads asset performance fetched (search text) | account=%s rows=%s",
                    account_norm,
                    len(search_text_asset_rows),
                )
            except Exception as exc:
                logger.warning(
                    "google ads search text asset performance fetch failed | account=%s err=%s",
                    account_norm,
                    exc,
                )
                search_text_asset_rows = []
            _append_non_pmax_asset_perf_rows(search_text_asset_rows)

            # Non-PMax non-search asset performance: image/video only
            asset_query_non_search_media = f"""
                SELECT
                    campaign.id,
                    campaign.advertising_channel_type,
                    ad_group.id,
                    ad_group_ad.ad.id,
                    ad_group_ad_asset_view.asset,
                    ad_group_ad_asset_view.field_type,
                    ad_group_ad_asset_view.performance_label,
                    segments.date,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM ad_group_ad_asset_view
                WHERE segments.date BETWEEN '{start_s}' AND '{end_s}'
                  AND campaign.advertising_channel_type IN (DEMAND_GEN, DISPLAY, VIDEO)
                  AND ad_group_ad_asset_view.field_type IN (MARKETING_IMAGE, SQUARE_MARKETING_IMAGE, PORTRAIT_MARKETING_IMAGE, YOUTUBE_VIDEO)
                  AND metrics.impressions > 0
            """
            if ctx.api_test_only:
                asset_query_non_search_media += f" LIMIT {ctx.api_sample_size}"

            try:
                non_search_media_asset_rows = _search_google_ads_with_retry(
                    google_client,
                    account_norm,
                    asset_query_non_search_media,
                )
                logger.info(
                    "google ads asset performance fetched (non-search image/video) | account=%s rows=%s",
                    account_norm,
                    len(non_search_media_asset_rows),
                )
            except Exception as exc:
                logger.warning(
                    "google ads non-search image/video asset performance fetch failed | account=%s err=%s",
                    account_norm,
                    exc,
                )
                non_search_media_asset_rows = []
            _append_non_pmax_asset_perf_rows(non_search_media_asset_rows)

            # PMax asset performance: IMAGE / VIDEO only
            asset_query_pmax = f"""
                SELECT
                    campaign.id,
                    campaign.advertising_channel_type,
                    asset_group.id,
                    asset_group_asset.asset,
                    asset_group_asset.field_type,
                    segments.date,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM asset_group_asset
                WHERE segments.date BETWEEN '{start_s}' AND '{end_s}'
                  AND campaign.advertising_channel_type = PERFORMANCE_MAX
                  AND asset_group_asset.field_type IN (MARKETING_IMAGE, SQUARE_MARKETING_IMAGE, PORTRAIT_MARKETING_IMAGE, YOUTUBE_VIDEO)
                  AND metrics.impressions > 0
            """
            if ctx.api_test_only:
                asset_query_pmax += f" LIMIT {ctx.api_sample_size}"

            try:
                pmax_asset_rows = _search_google_ads_with_retry(google_client, account_norm, asset_query_pmax)
                logger.info(
                    "google ads asset performance fetched (pmax image/video) | account=%s rows=%s",
                    account_norm,
                    len(pmax_asset_rows),
                )
            except Exception as exc:
                logger.warning("google ads pmax asset performance fetch failed | account=%s err=%s", account_norm, exc)
                pmax_asset_rows = []

            for row in pmax_asset_rows:
                campaign_px = getattr(row, "campaign", None)
                asset_group_px = getattr(row, "asset_group", None)
                asset_group_asset_px = getattr(row, "asset_group_asset", None)
                metrics_px = getattr(row, "metrics", None)
                segments_px = getattr(row, "segments", None)

                asset_resource_name = str(getattr(asset_group_asset_px, "asset", "")) if asset_group_asset_px else ""
                asset_id = _extract_asset_id(asset_resource_name)
                cost_micros = int(getattr(metrics_px, "cost_micros", 0) or 0) if metrics_px else 0

                pmax_asset_perf_row = {
                    "ingestion_id": run_ingestion_id,
                    "ingestion_ts": _utc_now_iso(),
                    "source_extract_ts": source_extract_ts,
                    "stat_date": getattr(segments_px, "date", "") or end_s,
                    "customer_id": account_norm,
                    "campaign_id": str(getattr(campaign_px, "id", "")) if campaign_px else None,
                    "campaign_channel_type": _enum_name(getattr(campaign_px, "advertising_channel_type", None))
                    if campaign_px
                    else None,
                    "asset_group_id": str(getattr(asset_group_px, "id", "")) if asset_group_px else None,
                    "ad_group_id": None,
                    "ad_id": None,
                    "asset_id": asset_id,
                    "asset_resource_name": asset_resource_name or None,
                    "field_type": _enum_name(getattr(asset_group_asset_px, "field_type", None)) if asset_group_asset_px else None,
                    "performance_label": None,
                    "is_pmax": True,
                    "impressions": int(getattr(metrics_px, "impressions", 0) or 0) if metrics_px else 0,
                    "clicks": int(getattr(metrics_px, "clicks", 0) or 0) if metrics_px else 0,
                    "cost_micros": cost_micros,
                    "conversions": float(getattr(metrics_px, "conversions", 0) or 0) if metrics_px else 0.0,
                    "conversions_value": float(getattr(metrics_px, "conversions_value", 0) or 0) if metrics_px else 0.0,
                    "source_view": "asset_group_asset",
                    "source_payload": _to_plain_json(row),
                }
                if pmax_asset_perf_row["asset_id"]:
                    all_asset_perf_rows.append(pmax_asset_perf_row)

            campaign_breakdown_rows = _build_google_campaign_breakdown_rows(
                google_client=google_client,
                account_norm=account_norm,
                start_s=start_s,
                end_s=end_s,
                source_extract_ts=source_extract_ts,
                run_ingestion_id=run_ingestion_id,
                api_test_only=ctx.api_test_only,
                api_sample_size=max(1, ctx.api_sample_size),
                logger=logger,
            )
            all_campaign_breakdown_rows.extend(campaign_breakdown_rows)

            
            sleep_seconds = float(provider_cfg.get("api_sleep_seconds", 0.2))
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        if not checked_accounts and account_failures > 0:
            raise ValueError(f"Google Ads ingest failed for all accounts (failed_accounts={account_failures})")

        if ctx.api_test_only or ctx.dry_run:
            return IngestResult(
                channel=self.name,
                status="API_OK",
                message=(
                    f"accounts={len(checked_accounts)}, perf_rows={len(all_perf_rows)}, "
                    f"creative_rows={len(all_creative_rows)}, asset_perf_rows={len(all_asset_perf_rows)}, "
                    f"campaign_breakdown_rows={len(all_campaign_breakdown_rows)}, "
                    f"mode={'API_TEST' if ctx.api_test_only else 'DRY_RUN'}"
                ),
            )

        raw_meta = (ctx.settings.raw_tables or {}).get("google_ads", {})
        perf_table = raw_meta.get("performance", "raw_ads.google_ads_performance_raw")
        creative_table = raw_meta.get("creative", "raw_ads.google_ads_creative_raw")
        asset_perf_table = raw_meta.get("asset_performance", "raw_ads.google_ads_asset_performance_raw")
        campaign_breakdown_table = raw_meta.get("campaign_breakdown", "raw_ads.google_ads_campaign_breakdown_raw")
        action_table = raw_meta.get("action", "raw_ads.google_ads_action_raw")
        conversion_action_dim_table = raw_meta.get(
            "conversion_action_dim",
            "raw_ads.google_ads_conversion_action_dim_raw",
        )

        perf_table_ref = f"{ctx.settings.app.project_id}.{perf_table}"
        creative_table_ref = f"{ctx.settings.app.project_id}.{creative_table}"
        asset_perf_table_ref = f"{ctx.settings.app.project_id}.{asset_perf_table}"
        campaign_breakdown_table_ref = f"{ctx.settings.app.project_id}.{campaign_breakdown_table}"
        action_table_ref = f"{ctx.settings.app.project_id}.{action_table}"
        conversion_action_dim_table_ref = f"{ctx.settings.app.project_id}.{conversion_action_dim_table}"

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
                account_id_column="customer_id",
                rows=all_perf_rows,
            )
            creative_loaded = load_idempotent_json(
                client=bq_client,
                table_ref=creative_table_ref,
                date_column="collected_date",
                start_date=start_s,
                end_date=end_s,
                account_ids=checked_accounts,
                account_id_column="customer_id",
                rows=all_creative_rows,
            )
            asset_perf_loaded = load_idempotent_json(
                client=bq_client,
                table_ref=asset_perf_table_ref,
                date_column="stat_date",
                start_date=start_s,
                end_date=end_s,
                account_ids=checked_accounts,
                account_id_column="customer_id",
                rows=all_asset_perf_rows,
            )
            campaign_breakdown_loaded = load_idempotent_json(
                client=bq_client,
                table_ref=campaign_breakdown_table_ref,
                date_column="stat_date",
                start_date=start_s,
                end_date=end_s,
                account_ids=checked_accounts,
                account_id_column="customer_id",
                rows=all_campaign_breakdown_rows,
            )
            action_loaded = load_idempotent_json(
                client=bq_client,
                table_ref=action_table_ref,
                date_column="stat_date",
                start_date=start_s,
                end_date=end_s,
                account_ids=checked_accounts,
                account_id_column="customer_id",
                rows=all_action_rows,
            )
            conversion_action_dim_loaded = load_idempotent_json(
                client=bq_client,
                table_ref=conversion_action_dim_table_ref,
                date_column="collected_date",
                start_date=start_s,
                end_date=end_s,
                account_ids=checked_accounts,
                account_id_column="customer_id",
                rows=all_conversion_action_dim_rows,
            )
        else:
            perf_loaded = append_json_rows(bq_client, perf_table_ref, all_perf_rows)
            creative_loaded = append_json_rows(bq_client, creative_table_ref, all_creative_rows)
            asset_perf_loaded = append_json_rows(bq_client, asset_perf_table_ref, all_asset_perf_rows)
            campaign_breakdown_loaded = append_json_rows(bq_client, campaign_breakdown_table_ref, all_campaign_breakdown_rows)
            action_loaded = append_json_rows(bq_client, action_table_ref, all_action_rows)
            conversion_action_dim_loaded = append_json_rows(
                bq_client,
                conversion_action_dim_table_ref,
                all_conversion_action_dim_rows,
            )

        if all_campaign_breakdown_rows:
            delete_rows_before(
                client=bq_client,
                table_ref=campaign_breakdown_table_ref,
                date_column="stat_date",
                cutoff_date=date.today() - timedelta(days=30),
            )

        return IngestResult(
            channel=self.name,
            status="LOADED",
                message=(
                    f"accounts={len(checked_accounts)}, perf_loaded={perf_loaded}, "
                    f"creative_loaded={creative_loaded}, asset_perf_loaded={asset_perf_loaded}, "
                    f"campaign_breakdown_loaded={campaign_breakdown_loaded}, "
                    f"action_loaded={action_loaded}, conversion_action_dim_loaded={conversion_action_dim_loaded}, "
                    f"replace_range={ctx.replace_range}"
                ),
        )

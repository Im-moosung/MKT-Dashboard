from __future__ import annotations

import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError
from requests.exceptions import RequestException

from New_Data_flow.channels.base import IngestContext, IngestResult
from New_Data_flow.common.bigquery_loader import (
    append_json_rows,
    build_bigquery_client,
    delete_rows_before,
    load_idempotent_json,
)
from New_Data_flow.common.credential_policy import allow_env_fallback, resolve_credential_value
from New_Data_flow.common.logger import setup_logger
from New_Data_flow.common.secret_manager import access_secret_dict
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


META_CAMPAIGN_BREAKDOWN_QUERY_SPECS = (
    {
        "request_breakdowns": ["age"],
        "output_keys": ["age"],
    },
    {
        "request_breakdowns": ["gender"],
        "output_keys": ["gender"],
    },
    {
        "request_breakdowns": ["country"],
        "output_keys": ["country"],
    },
    {
        "request_breakdowns": ["region"],
        "output_keys": ["region"],
    },
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_account_id(account_id: str) -> str:
    if not account_id:
        return ""
    return account_id[4:] if account_id.startswith("act_") else account_id


def _to_api_account_id(account_id: str) -> str:
    if not account_id:
        return ""
    return account_id if account_id.startswith("act_") else f"act_{account_id}"


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _to_numeric(value):
    if value is None or value == "":
        return None
    try:
        return str(value)
    except Exception:
        return None


def _to_plain_json(value):
    """Convert Facebook SDK objects into JSON-serializable primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_plain_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_plain_json(v) for v in value]

    if hasattr(value, "export_all_data"):
        try:
            return _to_plain_json(value.export_all_data())
        except Exception:
            pass

    if hasattr(value, "items"):
        try:
            return {str(k): _to_plain_json(v) for k, v in value.items()}
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        try:
            return {
                str(k): _to_plain_json(v)
                for k, v in vars(value).items()
                if not str(k).startswith("_")
            }
        except Exception:
            pass

    return str(value)


def _build_bq_client_with_fallback(
    project_id: str,
    credentials_path: str | None,
    location: str,
    logger,
):
    """Use configured service key first, then fall back to ADC if query job creation fails."""
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


def _extract_texts(creative: dict) -> list[dict]:
    texts: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add_text(text_type: str, raw_value) -> None:
        if raw_value is None:
            return
        value = str(raw_value).strip()
        if not value:
            return
        key = (text_type, value)
        if key in seen:
            return
        seen.add(key)
        texts.append({
            "text_type": text_type,
            "text_content": value,
            "language": "",
        })

    add_text("BODY", creative.get("body"))

    spec = creative.get("object_story_spec", {}) or {}
    link_data = spec.get("link_data", {}) if isinstance(spec, dict) else {}
    if isinstance(link_data, dict):
        add_text("BODY", link_data.get("message"))
        add_text("HEADLINE", link_data.get("name"))
        add_text("DESCRIPTION", link_data.get("description"))
        cta = link_data.get("call_to_action", {})
        if isinstance(cta, dict):
            add_text("CTA", cta.get("type"))

    video_data = spec.get("video_data", {}) if isinstance(spec, dict) else {}
    if isinstance(video_data, dict):
        add_text("BODY", video_data.get("message"))
        add_text("HEADLINE", video_data.get("title"))

    asset_spec = creative.get("asset_feed_spec", {}) or {}
    if isinstance(asset_spec, dict):
        for body in asset_spec.get("bodies", []) or []:
            if isinstance(body, dict):
                add_text("BODY", body.get("text"))
        for title in asset_spec.get("titles", []) or []:
            if isinstance(title, dict):
                add_text("HEADLINE", title.get("text"))
        for desc in asset_spec.get("descriptions", []) or []:
            if isinstance(desc, dict):
                add_text("DESCRIPTION", desc.get("text"))
        for cta in asset_spec.get("call_to_action_types", []) or []:
            add_text("CTA", cta)

    return texts


def _extract_assets(creative: dict) -> list[dict]:
    assets: list[dict] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    def add_asset(asset_type: str, asset_url: str = "", thumbnail_url: str = "", image_hash: str = "", video_id: str = "") -> None:
        key = (asset_type, asset_url or "", thumbnail_url or "", image_hash or "", video_id or "")
        if key in seen:
            return
        seen.add(key)
        assets.append(
            {
                "asset_type": asset_type,
                "asset_url": asset_url or "",
                "thumbnail_url": thumbnail_url or "",
                "image_hash": image_hash or "",
                "video_id": video_id or "",
            }
        )

    thumbnail_url = creative.get("thumbnail_url", "") or ""
    image_hash = creative.get("image_hash", "") or ""
    if thumbnail_url or image_hash:
        add_asset("IMAGE", thumbnail_url, thumbnail_url, image_hash, "")

    spec = creative.get("object_story_spec", {}) or {}
    if isinstance(spec, dict):
        link_data = spec.get("link_data", {})
        if isinstance(link_data, dict):
            add_asset("IMAGE", link_data.get("picture", "") or "", thumbnail_url, link_data.get("image_hash", "") or "", "")
            for child in link_data.get("child_attachments", []) or []:
                if not isinstance(child, dict):
                    continue
                if child.get("video_id"):
                    add_asset("VIDEO", child.get("picture", "") or "", child.get("picture", "") or "", "", child.get("video_id", "") or "")
                else:
                    add_asset("IMAGE", child.get("picture", "") or "", child.get("picture", "") or "", child.get("image_hash", "") or "", "")

        video_data = spec.get("video_data", {})
        if isinstance(video_data, dict):
            add_asset(
                "VIDEO",
                video_data.get("image_url", "") or "",
                thumbnail_url,
                video_data.get("image_hash", "") or "",
                video_data.get("video_id", "") or "",
            )

    asset_spec = creative.get("asset_feed_spec", {}) or {}
    if isinstance(asset_spec, dict):
        for image in asset_spec.get("images", []) or []:
            if isinstance(image, dict):
                add_asset("IMAGE", image.get("url", "") or "", thumbnail_url, image.get("hash", "") or "", "")
        for video in asset_spec.get("videos", []) or []:
            if isinstance(video, dict):
                add_asset("VIDEO", "", thumbnail_url, "", video.get("video_id", "") or "")

    return assets


def _build_campaign_breakdown_row(
    *,
    insight: dict,
    breakdown_key: str,
    account_norm: str,
    source_extract_ts: str,
    run_ingestion_id: str,
) -> dict | None:
    breakdown_raw = insight.get(breakdown_key)
    if breakdown_raw is None or str(breakdown_raw).strip() == "":
        return None

    return {
        "ingestion_id": run_ingestion_id,
        "ingestion_ts": _utc_now_iso(),
        "source_extract_ts": source_extract_ts,
        "account_id": account_norm,
        "account_name": insight.get("account_name"),
        "campaign_id": insight.get("campaign_id"),
        "campaign_name": insight.get("campaign_name"),
        # V1 breakdown grain is campaign-level. Keep ad_group fields populated for
        # backward-compatible raw schemas that still expect them.
        "ad_group_id": insight.get("campaign_id"),
        "ad_group_name": insight.get("campaign_name"),
        "stat_date": insight.get("date_start"),
        "breakdown_key": breakdown_key,
        "breakdown_value": str(breakdown_raw),
        "age": insight.get("age"),
        "gender": insight.get("gender"),
        "country": insight.get("country"),
        "region": insight.get("region"),
        "attribution_setting": insight.get("attribution_setting"),
        "impressions": _to_int(insight.get("impressions")),
        "clicks": _to_int(insight.get("clicks")),
        "link_clicks": _to_int(insight.get("inline_link_clicks")),
        "spend": _to_numeric(insight.get("spend")),
        "actions_json": _to_plain_json(insight.get("actions")),
        "action_values_json": _to_plain_json(insight.get("action_values")),
        "conversions_json": _to_plain_json(insight.get("conversions")),
        "conversion_values_json": _to_plain_json(insight.get("conversion_values")),
        "source_payload": _to_plain_json(insight),
    }


def _is_retryable_meta_exception(exc: BaseException) -> bool:
    if isinstance(exc, FacebookRequestError):
        if bool(exc.api_transient_error()):
            return True
        status = int(exc.http_status() or 0)
        return status in (429, 500, 502, 503, 504)
    return isinstance(exc, (TimeoutError, RequestException))


@retry(
    retry=retry_if_exception(_is_retryable_meta_exception),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _fetch_ad_creative(ad_id: str) -> dict:
    ad = Ad(ad_id)
    creatives = ad.get_ad_creatives(
        fields=[
            "id",
            "name",
            "object_type",
            "status",
            "thumbnail_url",
            "image_hash",
            "object_story_spec",
            "body",
            "asset_feed_spec",
        ]
    )
    if len(creatives) == 0:
        return {}
    return dict(creatives[0])


@retry(
    retry=retry_if_exception(_is_retryable_meta_exception),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _get_insights_with_retry(account, fields, params, max_rows=None) -> list[dict]:
    cursor = account.get_insights(fields=fields, params=params)
    rows = []
    for item in cursor:
        rows.append(_to_plain_json(dict(item)))
        if max_rows is not None and len(rows) >= max_rows:
            break
    return rows


class MetaAdsIngestor:
    name = "meta_ads"

    def run(self, ctx: IngestContext) -> IngestResult:
        logger = setup_logger("new_data_flow.meta_ads", ctx.settings.app.log_level)
        provider_cfg = (ctx.settings.providers or {}).get("meta_ads", {})
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

        app_id = resolve_credential_value(
            secret_data=secret_data,
            env_key="FB_APP_ID",
            env_fallback_enabled=env_fallback_enabled,
        )
        app_secret = resolve_credential_value(
            secret_data=secret_data,
            env_key="FB_APP_SECRET",
            env_fallback_enabled=env_fallback_enabled,
        )
        access_token = resolve_credential_value(
            secret_data=secret_data,
            env_key="FB_ACCESS_TOKEN",
            env_fallback_enabled=env_fallback_enabled,
        )
        env_account = resolve_credential_value(
            secret_data=secret_data,
            env_key="FB_AD_ACCOUNT_ID",
            env_fallback_enabled=env_fallback_enabled,
        )

        account_ids: list[str] = []
        if ctx.account_id_norm:
            account_ids = [ctx.account_id_norm]
        else:
            account_ids = provider_cfg.get("account_ids", []) or []
        if not account_ids and env_account:
            account_ids = [env_account]

        if not app_id or not app_secret or not access_token:
            if env_fallback_enabled:
                raise ValueError("Meta Ads API credential missing (FB_APP_ID/FB_APP_SECRET/FB_ACCESS_TOKEN)")
            raise ValueError(
                "Meta Ads API credential missing in Secret Manager and env fallback is disabled "
                "(FB_APP_ID/FB_APP_SECRET/FB_ACCESS_TOKEN)"
            )
        if not account_ids:
            if env_fallback_enabled:
                raise ValueError("No Meta Ads account configured (providers.meta_ads.account_ids or FB_AD_ACCOUNT_ID)")
            raise ValueError(
                "No Meta Ads account configured (providers.meta_ads.account_ids); env fallback is disabled"
            )

        FacebookAdsApi.init(app_id, app_secret, access_token)

        all_perf_rows: list[dict] = []
        all_creative_rows: list[dict] = []
        all_campaign_breakdown_rows: list[dict] = []
        checked_accounts: list[str] = []
        account_failures = 0

        start_s = ctx.start_date.isoformat()
        end_s = ctx.end_date.isoformat()
        source_extract_ts = _utc_now_iso()
        run_ingestion_id = str(uuid.uuid4())

        for raw_account_id in account_ids:
            account_api_id = _to_api_account_id(str(raw_account_id))
            account_norm = _normalize_account_id(account_api_id)
            account = AdAccount(account_api_id)

            insights_fields = [
                "account_id",
                "account_name",
                "campaign_id",
                "campaign_name",
                "adset_id",
                "adset_name",
                "ad_id",
                "ad_name",
                "date_start",
                "impressions",
                "clicks",
                "inline_link_clicks",
                "spend",
                "actions",
                "action_values",
                "conversions",
                "conversion_values",
                "attribution_setting",
            ]
            insights_params = {
                "time_range": {"since": start_s, "until": end_s},
                "level": "ad",
                "time_increment": 1,
                "filtering": [{"field": "impressions", "operator": "GREATER_THAN", "value": 0}],
                "use_unified_attribution_setting": True,
            }

            max_rows = ctx.api_sample_size if ctx.api_test_only else None
            try:
                # Minimal API health check (1 call)
                info = account.api_get(fields=["id", "name"])
                logger.info("meta account check ok | account=%s name=%s", info.get("id"), info.get("name"))
                insights_rows = _get_insights_with_retry(
                    account,
                    fields=insights_fields,
                    params=insights_params,
                    max_rows=max_rows,
                )
                checked_accounts.append(account_norm)
                logger.info("meta insights fetched | account=%s rows=%s", account_norm, len(insights_rows))
            except Exception as exc:  # noqa: BLE001
                account_failures += 1
                logger.error("meta account fetch failed | account=%s err=%s", account_norm, exc)
                continue

            for insight in insights_rows:
                perf_row = {
                    "ingestion_id": run_ingestion_id,
                    "ingestion_ts": _utc_now_iso(),
                    "source_extract_ts": source_extract_ts,
                    "account_id": account_norm,
                    "account_name": insight.get("account_name"),
                    "campaign_id": insight.get("campaign_id"),
                    "campaign_name": insight.get("campaign_name"),
                    "campaign_type": None,
                    "ad_group_id": insight.get("adset_id"),
                    "ad_group_name": insight.get("adset_name"),
                    "ad_id": insight.get("ad_id"),
                    "ad_name": insight.get("ad_name"),
                    "stat_date": insight.get("date_start"),
                    "attribution_setting": insight.get("attribution_setting"),
                    "impressions": _to_int(insight.get("impressions")),
                    "clicks": _to_int(insight.get("clicks")),
                    "link_clicks": _to_int(insight.get("inline_link_clicks")),
                    "spend": _to_numeric(insight.get("spend")),
                    "actions_json": _to_plain_json(insight.get("actions")),
                    "action_values_json": _to_plain_json(insight.get("action_values")),
                    "conversions_json": _to_plain_json(insight.get("conversions")),
                    "conversion_values_json": _to_plain_json(insight.get("conversion_values")),
                    "source_payload": _to_plain_json(insight),
                }
                all_perf_rows.append(perf_row)

            campaign_breakdown_fields = [
                "account_id",
                "account_name",
                "campaign_id",
                "campaign_name",
                "date_start",
                "impressions",
                "clicks",
                "inline_link_clicks",
                "spend",
                "actions",
                "action_values",
                "conversions",
                "conversion_values",
                "attribution_setting",
            ]
            campaign_breakdown_base_params = {
                "time_range": {"since": start_s, "until": end_s},
                "level": "campaign",
                "time_increment": 1,
                "filtering": [{"field": "impressions", "operator": "GREATER_THAN", "value": 0}],
                "use_unified_attribution_setting": True,
            }
            for spec in META_CAMPAIGN_BREAKDOWN_QUERY_SPECS:
                params = dict(campaign_breakdown_base_params)
                params["breakdowns"] = spec["request_breakdowns"]
                try:
                    campaign_rows = _get_insights_with_retry(
                        account,
                        fields=campaign_breakdown_fields,
                        params=params,
                        max_rows=max_rows,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "meta campaign breakdown fetch failed | account=%s request_breakdowns=%s err=%s",
                        account_norm,
                        ",".join(spec["request_breakdowns"]),
                        exc,
                    )
                    continue
                emitted_rows = 0
                for insight in campaign_rows:
                    for breakdown_key in spec["output_keys"]:
                        breakdown_row = _build_campaign_breakdown_row(
                            insight=insight,
                            breakdown_key=breakdown_key,
                            account_norm=account_norm,
                            source_extract_ts=source_extract_ts,
                            run_ingestion_id=run_ingestion_id,
                        )
                        if breakdown_row is None:
                            continue
                        all_campaign_breakdown_rows.append(breakdown_row)
                        emitted_rows += 1
                logger.info(
                    "meta campaign breakdown fetched | account=%s request_breakdowns=%s source_rows=%s emitted_rows=%s",
                    account_norm,
                    ",".join(spec["request_breakdowns"]),
                    len(campaign_rows),
                    emitted_rows,
                )

            creative_targets = insights_rows[: min(len(insights_rows), ctx.max_ads)]
            sleep_seconds = float(provider_cfg.get("api_sleep_seconds", 0.2))

            for insight in creative_targets:
                ad_id = str(insight.get("ad_id") or "")
                if not ad_id:
                    continue

                creative_raw: dict = {}
                try:
                    creative_raw = _to_plain_json(_fetch_ad_creative(ad_id))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("creative fetch failed | account=%s ad_id=%s err=%s", account_norm, ad_id, exc)

                assets = _extract_assets(creative_raw) if creative_raw else []
                # Assets-only policy: creative text fields are intentionally not collected.
                headline = ""
                description = ""
                call_to_action = ""
                body_text = ""

                creative_row = {
                    "ingestion_id": run_ingestion_id,
                    "ingestion_ts": _utc_now_iso(),
                    "source_extract_ts": source_extract_ts,
                    "collected_date": end_s,
                    "account_id": account_norm,
                    "campaign_id": insight.get("campaign_id"),
                    "ad_group_id": insight.get("adset_id"),
                    "ad_id": ad_id,
                    "creative_id": creative_raw.get("id", "") if creative_raw else "",
                    "creative_name": creative_raw.get("name", "") if creative_raw else "",
                    "ad_type": "",
                    "object_type": creative_raw.get("object_type", "") if creative_raw else "",
                    "status": creative_raw.get("status", "") if creative_raw else "",
                    "body_text": body_text,
                    "headline": headline,
                    "description_text": description,
                    "call_to_action": call_to_action,
                    "language": "",
                    "thumbnail_url": creative_raw.get("thumbnail_url", "") if creative_raw else "",
                    "permanent_image_url": "",
                    "image_hash": creative_raw.get("image_hash", "") if creative_raw else "",
                    "video_id": "",
                    "object_story_spec_json": _to_plain_json(creative_raw.get("object_story_spec")) if creative_raw else None,
                    "asset_feed_spec_json": _to_plain_json(creative_raw.get("asset_feed_spec")) if creative_raw else None,
                    "texts_json": [],
                    "assets_json": assets,
                    "source_payload": {
                        "insight": _to_plain_json(insight),
                        "creative": _to_plain_json(creative_raw),
                    },
                }
                all_creative_rows.append(creative_row)

                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)

        if not checked_accounts and account_failures > 0:
            raise ValueError(f"Meta Ads ingest failed for all accounts (failed_accounts={account_failures})")

        if ctx.api_test_only or ctx.dry_run:
            return IngestResult(
                channel=self.name,
                status="API_OK",
                message=(
                    f"accounts={len(checked_accounts)}, perf_rows={len(all_perf_rows)}, "
                    f"creative_rows={len(all_creative_rows)}, campaign_breakdown_rows={len(all_campaign_breakdown_rows)}, "
                    f"mode={'API_TEST' if ctx.api_test_only else 'DRY_RUN'}"
                ),
            )

        raw_meta = (ctx.settings.raw_tables or {}).get("meta_ads", {})
        perf_table = raw_meta.get("performance", "raw_ads.meta_ads_performance_raw")
        creative_table = raw_meta.get("creative", "raw_ads.meta_ads_creative_raw")
        campaign_breakdown_table = raw_meta.get(
            "campaign_breakdown",
            "raw_ads.meta_ads_campaign_breakdown_raw",
        )

        perf_table_ref = f"{ctx.settings.app.project_id}.{perf_table}"
        creative_table_ref = f"{ctx.settings.app.project_id}.{creative_table}"
        campaign_breakdown_table_ref = f"{ctx.settings.app.project_id}.{campaign_breakdown_table}"

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
            campaign_breakdown_loaded = load_idempotent_json(
                client=bq_client,
                table_ref=campaign_breakdown_table_ref,
                date_column="stat_date",
                start_date=start_s,
                end_date=end_s,
                account_ids=checked_accounts,
                rows=all_campaign_breakdown_rows,
            )
        else:
            perf_loaded = append_json_rows(bq_client, perf_table_ref, all_perf_rows)
            creative_loaded = append_json_rows(bq_client, creative_table_ref, all_creative_rows)
            campaign_breakdown_loaded = append_json_rows(
                bq_client,
                campaign_breakdown_table_ref,
                all_campaign_breakdown_rows,
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
                f"creative_loaded={creative_loaded}, campaign_breakdown_loaded={campaign_breakdown_loaded}, "
                f"replace_range={ctx.replace_range}"
            ),
        )

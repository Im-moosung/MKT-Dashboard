from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Sequence

from channels.base import IngestContext
from channels.registry import (
    resolve_ingestor_by_provider,
    resolve_ingestors,
    warehouse_capable_channel_keys,
)
from common.bigquery_loader import (
    build_bigquery_client,
    call_date_range_procedure,
    get_latest_successful_warehouse_run,
)
from common.date_range import compute_date_range
from common.logger import setup_logger
from common.settings import load_settings
from common.source_config import list_source_configs


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Raw ingestion orchestrator")
    parser.add_argument("--env", choices=["dev", "prod"], default="dev")
    parser.add_argument("--channel", default="meta_ads", help="meta_ads | all")
    parser.add_argument("--use-source-config", action="store_true", help="Load active sources from source config table")
    parser.add_argument("--source-config-table", default="ops.ingest_source_config", help="Dataset.table or Project.Dataset.table")
    parser.add_argument("--source-id", help="Run a single source_id from source config table")
    parser.add_argument("--source-status", default="ACTIVE", help="Source status filter (default: ACTIVE)")
    parser.add_argument("--tier", help="Optional source tier filter: PROD | TEST | EXPERIMENT")
    parser.add_argument(
        "--refresh-mode",
        choices=["daily", "weekly", "monthly", "custom"],
        default="daily",
    )
    parser.add_argument("--start-date", type=parse_date)
    parser.add_argument("--end-date", type=parse_date)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--api-test-only", action="store_true", help="Call source API minimally and skip BigQuery load")
    parser.add_argument("--api-sample-size", type=int, default=1, help="Sample row count for API smoke test")
    parser.add_argument("--max-ads", type=int, default=500, help="Max ad rows for creative detail fetch")
    parser.add_argument("--no-replace-range", action="store_true", help="Do not delete same date range before append")
    parser.add_argument("--run-warehouse", action="store_true", help="Run warehouse procedure after raw ingest")
    parser.add_argument(
        "--force-warehouse-rerun",
        action="store_true",
        help="Force warehouse procedure even if same date range already succeeded recently",
    )
    parser.add_argument("--warehouse-procedure", default="ops.sp_load_all", help="Dataset.routine or Project.Dataset.routine")
    parser.add_argument("--warehouse-credentials-path", help="Optional service account JSON path for warehouse call")
    parser.add_argument(
        "--skip-geo-sync",
        action="store_true",
        help="Skip post-warehouse geo_target_map sync",
    )
    parser.add_argument(
        "--geo-sync-source-id",
        help="Optional source_id for post-warehouse geo_target_map sync",
    )
    parser.add_argument(
        "--skip-dq-checks",
        action="store_true",
        help="Skip post-warehouse DQ checks",
    )
    return parser


def resolve_procedure_ref(project_id: str, procedure: str) -> str:
    if procedure.count(".") == 1:
        return f"{project_id}.{procedure}"
    if procedure.count(".") == 2:
        return procedure
    raise ValueError("warehouse-procedure must be Dataset.routine or Project.Dataset.routine")


def resolve_table_ref(project_id: str, table_ref: str) -> str:
    if table_ref.count(".") == 1:
        return f"{project_id}.{table_ref}"
    if table_ref.count(".") == 2:
        return table_ref
    raise ValueError("source-config-table must be Dataset.table or Project.Dataset.table")


def resolve_bq_credentials_path(providers: dict) -> str | None:
    for provider_cfg in (providers or {}).values():
        if isinstance(provider_cfg, dict):
            path = provider_cfg.get("bq_credentials_path")
            if path:
                return str(path)
    return None


def classify_exception(exc: Exception) -> str:
    text = str(exc).lower()
    if "access denied" in text or "forbidden" in text or "permission" in text:
        return "PERMISSION"
    if "update/merge must match at most one source row" in text:
        return "MERGE_DUPLICATE_MATCH"
    if "cannot query over table" in text and "partition" in text:
        return "PARTITION_FILTER"
    if "too many requests" in text or "429" in text or "rate limit" in text:
        return "RATE_LIMIT"
    if "timeout" in text or "deadline" in text:
        return "TIMEOUT"
    return "UNKNOWN"


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    settings = load_settings(env=args.env, config_dir=root / "config")
    logger = setup_logger("new_data_flow", settings.app.log_level)

    window = compute_date_range(
        refresh_mode=args.refresh_mode,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    logger.info(
        "start raw ingest | env=%s channel=%s mode=%s range=%s~%s dry_run=%s api_test_only=%s",
        args.env,
        args.channel,
        args.refresh_mode,
        window.start_date,
        window.end_date,
        args.dry_run,
        args.api_test_only,
    )

    failures = 0
    processed_units = 0
    successful_units = 0
    auto_run_warehouse = False
    use_source_config = args.use_source_config or bool(args.source_id)
    successful_google_source_ids: set[str] = set()
    ran_google_ads_channel = False

    if use_source_config:
        creds_path = args.warehouse_credentials_path or resolve_bq_credentials_path(settings.providers or {})
        bq_client = build_bigquery_client(
            project_id=settings.app.project_id,
            credentials_path=creds_path,
            location=settings.app.location,
        )
        source_table_ref = resolve_table_ref(settings.app.project_id, args.source_config_table)
        try:
            source_configs = list_source_configs(
                client=bq_client,
                project_id=settings.app.project_id,
                table_ref=source_table_ref,
                source_id=args.source_id,
                status=args.source_status,
                tier=args.tier,
            )
        except Exception as exc:  # noqa: BLE001
            if not creds_path:
                raise
            logger.warning(
                "source config query failed with credentials_path, retrying with ADC | category=%s err=%s",
                classify_exception(exc),
                exc,
            )
            bq_client = build_bigquery_client(
                project_id=settings.app.project_id,
                credentials_path=None,
                location=settings.app.location,
            )
            source_configs = list_source_configs(
                client=bq_client,
                project_id=settings.app.project_id,
                table_ref=source_table_ref,
                source_id=args.source_id,
                status=args.source_status,
                tier=args.tier,
            )
        if not source_configs:
            logger.warning("no source configs found | table=%s source_id=%s status=%s tier=%s", source_table_ref, args.source_id, args.source_status, args.tier)
            return 0

        for source_cfg in source_configs:
            processed_units += 1
            try:
                ingestor = resolve_ingestor_by_provider(source_cfg.provider_key)
            except Exception as exc:  # noqa: BLE001
                failures += 1
                logger.exception(
                    "source_id=%s provider=%s failed to resolve | category=%s err=%s",
                    source_cfg.source_id,
                    source_cfg.provider_key,
                    classify_exception(exc),
                    exc,
                )
                continue

            ctx = IngestContext(
                settings=settings,
                start_date=window.start_date,
                end_date=window.end_date,
                dry_run=args.dry_run,
                api_test_only=args.api_test_only,
                api_sample_size=max(1, args.api_sample_size),
                max_ads=max(1, args.max_ads),
                replace_range=not args.no_replace_range,
                source_id=source_cfg.source_id,
                branch_id=source_cfg.branch_id,
                channel_key=source_cfg.channel_key,
                provider_key=source_cfg.provider_key,
                account_id_norm=source_cfg.account_id_norm,
                secret_ref=source_cfg.secret_ref,
                secret_version=source_cfg.secret_version,
                tier=source_cfg.tier,
            )
            try:
                result = ingestor.run(ctx)
                logger.info(
                    "source_id=%s channel=%s status=%s msg=%s",
                    source_cfg.source_id,
                    result.channel,
                    result.status,
                    result.message,
                )
                successful_units += 1
                if source_cfg.run_warehouse_after_ingest:
                    channel_key_norm = (source_cfg.channel_key or "").strip().upper()
                    warehouse_channels = warehouse_capable_channel_keys()
                    if channel_key_norm in warehouse_channels:
                        auto_run_warehouse = True
                    else:
                        logger.warning(
                            "source_id=%s auto warehouse suppressed | channel_key=%s supported=%s",
                            source_cfg.source_id,
                            channel_key_norm or "UNKNOWN",
                            ",".join(sorted(warehouse_channels)),
                        )
                if (source_cfg.channel_key or "").strip().upper() == "GOOGLE_ADS":
                    successful_google_source_ids.add(source_cfg.source_id)
            except Exception as exc:  # noqa: BLE001
                failures += 1
                logger.exception(
                    "source_id=%s channel=%s failed | category=%s err=%s",
                    source_cfg.source_id,
                    ingestor.name,
                    classify_exception(exc),
                    exc,
                )
    else:
        ingestors = resolve_ingestors(args.channel)
        for ingestor in ingestors:
            processed_units += 1
            ctx = IngestContext(
                settings=settings,
                start_date=window.start_date,
                end_date=window.end_date,
                dry_run=args.dry_run,
                api_test_only=args.api_test_only,
                api_sample_size=max(1, args.api_sample_size),
                max_ads=max(1, args.max_ads),
                replace_range=not args.no_replace_range,
            )
            try:
                result = ingestor.run(ctx)
                logger.info("channel=%s status=%s msg=%s", result.channel, result.status, result.message)
                successful_units += 1
                if ingestor.name == "google_ads":
                    ran_google_ads_channel = True
            except Exception as exc:  # noqa: BLE001
                failures += 1
                logger.exception(
                    "channel=%s failed | category=%s err=%s",
                    ingestor.name,
                    classify_exception(exc),
                    exc,
                )

    if failures:
        logger.error(
            "finished with failures=%s processed=%s successful=%s",
            failures,
            processed_units,
            successful_units,
        )
        return 1

    should_run_warehouse = args.run_warehouse or auto_run_warehouse
    if should_run_warehouse:
        if args.dry_run or args.api_test_only:
            logger.warning("skip warehouse call (dry_run/api_test_only enabled)")
        else:
            procedure_ref = resolve_procedure_ref(settings.app.project_id, args.warehouse_procedure)
            creds_path = args.warehouse_credentials_path or resolve_bq_credentials_path(settings.providers or {})

            def _run_procedure(client, mode: str) -> None:
                logger.info(
                    "warehouse call attempt | mode=%s procedure=%s range=%s~%s",
                    mode,
                    procedure_ref,
                    window.start_date,
                    window.end_date,
                )
                call_date_range_procedure(
                    client=client,
                    procedure_ref=procedure_ref,
                    start_date=window.start_date.isoformat(),
                    end_date=window.end_date.isoformat(),
                )
            fallback_used = False
            primary_client = build_bigquery_client(
                project_id=settings.app.project_id,
                credentials_path=creds_path,
                location=settings.app.location,
            )
            try:
                if not args.force_warehouse_rerun:
                    latest_success = get_latest_successful_warehouse_run(
                        client=primary_client,
                        run_log_table_ref=f"{settings.app.project_id}.ops.etl_run_log",
                        start_date=window.start_date.isoformat(),
                        end_date=window.end_date.isoformat(),
                    )
                    if latest_success:
                        logger.info(
                            "skip warehouse call (already succeeded) | run_id=%s started_at=%s range=%s~%s",
                            latest_success.run_id,
                            latest_success.started_at,
                            window.start_date,
                            window.end_date,
                        )
                        logger.info("warehouse call finished | procedure=%s fallback_used=%s", procedure_ref, fallback_used)
                        logger.info("finished successfully | processed=%s successful=%s", processed_units, successful_units)
                        return 0
                _run_procedure(primary_client, mode="credentials_path" if creds_path else "adc")
            except Exception as exc:
                if not creds_path:
                    raise
                fallback_used = True
                logger.warning(
                    "warehouse procedure failed with credentials_path, retrying with ADC | category=%s err=%s",
                    classify_exception(exc),
                    exc,
                )
                adc_client = build_bigquery_client(
                    project_id=settings.app.project_id,
                    credentials_path=None,
                    location=settings.app.location,
                )
                try:
                    if not args.force_warehouse_rerun:
                        latest_success = get_latest_successful_warehouse_run(
                            client=adc_client,
                            run_log_table_ref=f"{settings.app.project_id}.ops.etl_run_log",
                            start_date=window.start_date.isoformat(),
                            end_date=window.end_date.isoformat(),
                        )
                        if latest_success:
                            logger.info(
                                "skip warehouse call after fallback check (already succeeded) | run_id=%s started_at=%s range=%s~%s",
                                latest_success.run_id,
                                latest_success.started_at,
                                window.start_date,
                                window.end_date,
                            )
                            logger.info("warehouse call finished | procedure=%s fallback_used=%s", procedure_ref, fallback_used)
                            logger.info("finished successfully | processed=%s successful=%s", processed_units, successful_units)
                            return 0
                    _run_procedure(adc_client, mode="adc_fallback")
                except Exception as adc_exc:  # noqa: BLE001
                    logger.error(
                        "warehouse procedure failed after ADC fallback | category=%s err=%s",
                        classify_exception(adc_exc),
                        adc_exc,
                    )
                    raise

            logger.info("warehouse call finished | procedure=%s fallback_used=%s", procedure_ref, fallback_used)

            if args.skip_geo_sync:
                logger.info("post-warehouse geo sync skipped by flag")
            else:
                geo_sync_candidates: list[str | None] = []
                if args.geo_sync_source_id:
                    geo_sync_candidates = [args.geo_sync_source_id]
                elif successful_google_source_ids:
                    geo_sync_candidates = sorted(successful_google_source_ids)
                elif ran_google_ads_channel or args.channel in {"google_ads", "all"}:
                    # Non source-config mode fallback: sync script auto-picks a usable Google source.
                    geo_sync_candidates = [None]

                if not geo_sync_candidates:
                    logger.info("post-warehouse geo sync skipped (no google source detected)")
                else:
                    from jobs.sync_geo_target_map import run as run_geo_sync

                    for source_id in geo_sync_candidates:
                        geo_argv = [
                            "--env",
                            args.env,
                            "--source-config-table",
                            args.source_config_table,
                            "--start-date",
                            window.start_date.isoformat(),
                            "--end-date",
                            window.end_date.isoformat(),
                        ]
                        if source_id:
                            geo_argv.extend(["--source-id", source_id])

                        try:
                            rc = run_geo_sync(geo_argv)
                            if rc != 0:
                                logger.warning(
                                    "post-warehouse geo sync returned non-zero | source_id=%s rc=%s",
                                    source_id or "auto",
                                    rc,
                                )
                            else:
                                logger.info("post-warehouse geo sync done | source_id=%s", source_id or "auto")
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "post-warehouse geo sync failed (non-blocking) | source_id=%s category=%s err=%s",
                                source_id or "auto",
                                classify_exception(exc),
                                exc,
                            )

            if args.skip_dq_checks:
                logger.info("post-warehouse DQ checks skipped by flag")
            else:
                from jobs.run_dq_checks import run as run_dq_checks

                dq_argv = [
                    "--env",
                    args.env,
                    "--start-date",
                    window.start_date.isoformat(),
                    "--end-date",
                    window.end_date.isoformat(),
                ]
                try:
                    dq_rc = run_dq_checks(dq_argv)
                    if dq_rc != 0:
                        logger.warning("post-warehouse DQ checks returned alert | rc=%s", dq_rc)
                    else:
                        logger.info("post-warehouse DQ checks done")
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "post-warehouse DQ checks failed (non-blocking) | category=%s err=%s",
                        classify_exception(exc),
                        exc,
                    )

    logger.info("finished successfully | processed=%s successful=%s", processed_units, successful_units)
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

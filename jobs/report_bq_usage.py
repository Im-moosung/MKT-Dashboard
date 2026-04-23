from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Sequence

from google.cloud import bigquery

from common.bigquery_loader import build_bigquery_client
from common.settings import load_settings


FREE_QUERY_TIER_BYTES = 1 * 1024 * 1024 * 1024 * 1024  # 1 TiB / month


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _region_info_schema(region: str) -> str:
    normalized = region.strip().lower()
    if normalized == "us":
        return "region-us"
    return f"region-{normalized}"


def _query_root_usage(
    client: bigquery.Client,
    region: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    info_schema = _region_info_schema(region)
    sql = f"""
    SELECT
      @region AS region,
      user_email,
      COUNT(*) AS root_jobs,
      SUM(total_bytes_billed) AS billed_bytes,
      ROUND(SUM(total_bytes_billed) / POW(1024, 3), 6) AS billed_gib
    FROM `{info_schema}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
    WHERE creation_time >= TIMESTAMP(@start_date)
      AND creation_time < TIMESTAMP(DATE_ADD(@end_date, INTERVAL 1 DAY))
      AND job_type = 'QUERY'
      AND state = 'DONE'
      AND parent_job_id IS NULL
    GROUP BY user_email
    ORDER BY billed_bytes DESC
    """
    config = bigquery.QueryJobConfig(
        labels={"pipeline": "new_data_flow", "step": "usage_report"},
        query_parameters=[
            bigquery.ScalarQueryParameter("region", "STRING", region),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date.isoformat()),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date.isoformat()),
        ],
    )
    rows = client.query(sql, job_config=config).result()
    return [dict(row) for row in rows]


def _query_root_workload_mix(
    client: bigquery.Client,
    region: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    info_schema = _region_info_schema(region)
    sql = f"""
    SELECT
      CASE
        WHEN query LIKE 'CALL `%ops.sp_load_all`%' THEN 'warehouse_call_sp_load_all'
        WHEN query LIKE 'CALL `%ops.sp_load_%' THEN 'warehouse_other_proc_calls'
        WHEN REGEXP_CONTAINS(query, r'BEGIN\\s+TRANSACTION;\\s*DELETE\\s+FROM `.*\\.raw_ads\\.') THEN 'raw_idempotent_load_script'
        WHEN statement_type = 'SELECT' THEN 'ad_hoc_select'
        WHEN statement_type = 'SCRIPT' THEN 'other_script'
        ELSE COALESCE(statement_type, 'UNKNOWN')
      END AS workload,
      COUNT(*) AS root_jobs,
      SUM(total_bytes_billed) AS billed_bytes,
      ROUND(SUM(total_bytes_billed) / POW(1024, 3), 6) AS billed_gib
    FROM `{info_schema}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
    WHERE creation_time >= TIMESTAMP(@start_date)
      AND creation_time < TIMESTAMP(DATE_ADD(@end_date, INTERVAL 1 DAY))
      AND job_type = 'QUERY'
      AND state = 'DONE'
      AND parent_job_id IS NULL
    GROUP BY workload
    ORDER BY billed_bytes DESC
    """
    config = bigquery.QueryJobConfig(
        labels={"pipeline": "new_data_flow", "step": "usage_report_mix"},
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date.isoformat()),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date.isoformat()),
        ],
    )
    rows = client.query(sql, job_config=config).result()
    return [dict(row) for row in rows]


def _print_table(title: str, rows: list[dict], columns: list[str]) -> None:
    print(f"\n[{title}]")
    if not rows:
        print("(no rows)")
        return
    widths: dict[str, int] = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            widths[col] = max(widths[col], len(str(row.get(col, ""))))
    header = " | ".join([col.ljust(widths[col]) for col in columns])
    print(header)
    print("-+-".join(["-" * widths[col] for col in columns]))
    for row in rows:
        print(" | ".join([str(row.get(col, "")).ljust(widths[col]) for col in columns]))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report BigQuery usage (root job 기준)")
    parser.add_argument("--env", choices=["dev", "prod"], default="prod")
    parser.add_argument("--start-date", type=_parse_date, help="YYYY-MM-DD (default: month start)")
    parser.add_argument("--end-date", type=_parse_date, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--include-us-region", action="store_true", help="Include US multi-region usage")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(env=args.env, config_dir=root / "config")

    today = date.today()
    start_date = args.start_date or _month_start(today)
    end_date = args.end_date or today
    if end_date < start_date:
        raise ValueError("end-date must be greater than or equal to start-date")

    regions = [settings.app.location]
    if args.include_us_region and "us" not in {r.lower() for r in regions}:
        regions.append("US")
    elif args.include_us_region and "us" in {r.lower() for r in regions} and settings.app.location.lower() != "us":
        regions.append("US")
    elif args.include_us_region and settings.app.location.lower() == "us":
        pass

    merged_total = 0
    for region in regions:
        client = build_bigquery_client(
            project_id=settings.app.project_id,
            location=region,
        )
        usage_rows = _query_root_usage(client=client, region=region, start_date=start_date, end_date=end_date)
        mix_rows = _query_root_workload_mix(client=client, region=region, start_date=start_date, end_date=end_date)

        region_total = int(sum(int(row.get("billed_bytes") or 0) for row in usage_rows))
        merged_total += region_total

        _print_table(
            title=f"{region} root usage by user ({start_date}~{end_date})",
            rows=usage_rows,
            columns=["region", "user_email", "root_jobs", "billed_bytes", "billed_gib"],
        )
        _print_table(
            title=f"{region} root workload mix ({start_date}~{end_date})",
            rows=mix_rows[:10],
            columns=["workload", "root_jobs", "billed_bytes", "billed_gib"],
        )

    ratio = (merged_total / FREE_QUERY_TIER_BYTES) * 100
    print(
        "\n[summary]\n"
        f"project_id={settings.app.project_id}\n"
        f"period={start_date}~{end_date}\n"
        f"root_billed_bytes_total={merged_total}\n"
        f"free_tier_percent_of_1TiB={ratio:.4f}%"
    )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Sequence

from google.cloud import bigquery

from common.bigquery_loader import build_bigquery_client
from common.settings import load_settings


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _unknown_geo_name_check(
    client: bigquery.Client,
    project_id: str,
    start_date: date,
    end_date: date,
) -> tuple[int, int]:
    sql = f"""
    SELECT
      COUNT(*) AS total_rows,
      COUNTIF(breakdown_value_name = 'Unknown') AS unknown_rows
    FROM `{project_id}.mart.v_campaign_breakdown_recent`
    WHERE report_date BETWEEN @start_date AND @end_date
      AND breakdown_key IN ('geo_target_country', 'geo_target_region')
    """
    cfg = bigquery.QueryJobConfig(
        labels={"pipeline": "new_data_flow", "step": "dq_unknown_geo_name"},
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date.isoformat()),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date.isoformat()),
        ],
    )
    row = list(client.query(sql, job_config=cfg).result())[0]
    return int(row["total_rows"] or 0), int(row["unknown_rows"] or 0)


def _insert_dq_result(
    client: bigquery.Client,
    project_id: str,
    *,
    check_date: date,
    check_name: str,
    severity: str,
    status: str,
    failed_rows: int,
    check_sql: str,
    details: dict,
) -> None:
    sql = f"""
    INSERT INTO `{project_id}.ops.dq_check_result` (
      check_ts,
      check_date,
      table_name,
      check_name,
      severity,
      status,
      failed_rows,
      check_sql,
      details
    )
    VALUES (
      CURRENT_TIMESTAMP(),
      @check_date,
      @table_name,
      @check_name,
      @severity,
      @status,
      @failed_rows,
      @check_sql,
      PARSE_JSON(@details_json)
    )
    """
    cfg = bigquery.QueryJobConfig(
        labels={"pipeline": "new_data_flow", "step": "dq_insert_result"},
        query_parameters=[
            bigquery.ScalarQueryParameter("check_date", "DATE", check_date.isoformat()),
            bigquery.ScalarQueryParameter("table_name", "STRING", "mart.v_campaign_breakdown_recent"),
            bigquery.ScalarQueryParameter("check_name", "STRING", check_name),
            bigquery.ScalarQueryParameter("severity", "STRING", severity),
            bigquery.ScalarQueryParameter("status", "STRING", status),
            bigquery.ScalarQueryParameter("failed_rows", "INT64", failed_rows),
            bigquery.ScalarQueryParameter("check_sql", "STRING", check_sql),
            bigquery.ScalarQueryParameter("details_json", "STRING", json.dumps(details, ensure_ascii=False)),
        ],
    )
    client.query(sql, job_config=cfg).result()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run post-warehouse DQ checks")
    parser.add_argument("--env", choices=["dev", "prod"], default="prod")
    parser.add_argument("--start-date", type=_parse_date, required=True)
    parser.add_argument("--end-date", type=_parse_date, required=True)
    parser.add_argument(
        "--fail-on-alert",
        action="store_true",
        help="Return non-zero when DQ status is FAIL",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.end_date < args.start_date:
        raise ValueError("end-date must be greater than or equal to start-date")

    root = Path(__file__).resolve().parents[1]
    settings = load_settings(env=args.env, config_dir=root / "config")
    client = build_bigquery_client(
        project_id=settings.app.project_id,
        location=settings.app.location,
    )

    total_rows, unknown_rows = _unknown_geo_name_check(
        client=client,
        project_id=settings.app.project_id,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    status = "FAIL" if unknown_rows > 0 else "PASS"
    severity = "WARN" if unknown_rows > 0 else "INFO"
    ratio = float(unknown_rows / total_rows) if total_rows > 0 else 0.0
    check_sql = (
        "COUNTIF(breakdown_value_name = 'Unknown') "
        "FROM mart.v_campaign_breakdown_recent "
        "WHERE breakdown_key IN ('geo_target_country','geo_target_region')"
    )
    details = {
        "start_date": args.start_date.isoformat(),
        "end_date": args.end_date.isoformat(),
        "total_geo_rows": total_rows,
        "unknown_rows": unknown_rows,
        "unknown_ratio": ratio,
    }

    _insert_dq_result(
        client=client,
        project_id=settings.app.project_id,
        check_date=args.end_date,
        check_name="geo_breakdown_value_name_unknown",
        severity=severity,
        status=status,
        failed_rows=unknown_rows,
        check_sql=check_sql,
        details=details,
    )

    print(
        "dq check done | "
        f"check=geo_breakdown_value_name_unknown status={status} "
        f"unknown_rows={unknown_rows} total_geo_rows={total_rows}"
    )
    if status == "FAIL" and args.fail_on_alert:
        return 2
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

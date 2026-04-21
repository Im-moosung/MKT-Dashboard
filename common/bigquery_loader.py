from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from google.cloud import bigquery
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


DEFAULT_BQ_LOCATION = "us-central1"


@dataclass(frozen=True)
class WarehouseRunLog:
    run_id: str
    started_at: str
    ended_at: str | None


def build_bigquery_client(
    project_id: str,
    credentials_path: str | None = None,
    location: str = DEFAULT_BQ_LOCATION,
) -> bigquery.Client:
    """Build BigQuery client from explicit credentials or ADC."""
    if credentials_path:
        path = Path(credentials_path)
        if path.exists():
            creds = service_account.Credentials.from_service_account_file(str(path))
            return bigquery.Client(project=project_id, credentials=creds, location=location)
    return bigquery.Client(project=project_id, location=location)


def load_idempotent_json(
    client: bigquery.Client,
    table_ref: str,
    date_column: str,
    start_date: str,
    end_date: str,
    account_ids: list[str],
    rows: Iterable[dict],
    account_id_column: str = "account_id",
) -> int:
    """Atomically delete specific accounts in a date range and append new rows (P0 Data Loss Risk Fix)."""
    payload = list(rows)
    normalized_account_ids = sorted({str(v).strip() for v in (account_ids or []) if str(v).strip()})

    if not normalized_account_ids:
        raise ValueError("account_ids is required for idempotent load")

    if not payload:
        # If no payload, we do absolutely nothing.
        # This prevents accidental deletion of existing data when API temporarily returns 0 rows.
        return 0

    # 1. Retrieve the exact target schema
    table = client.get_table(table_ref)

    # 2. Save data to a temporary schema-matched table
    temp_table_id = f"{table_ref}_tmp_{uuid.uuid4().hex[:8]}"
    job_config = bigquery.LoadJobConfig(
        schema=table.schema,
        write_disposition="WRITE_TRUNCATE",
        labels={"pipeline": "new_data_flow", "step": "idempotent_load_temp"},
    )
    load_job = client.load_table_from_json(payload, temp_table_id, job_config=job_config)
    load_job.result()  # Wait for load to finish

    # 3. Perform DELETE and INSERT within a single transaction
    query = f"""
    BEGIN TRANSACTION;
    DELETE FROM `{table_ref}`
    WHERE {date_column} BETWEEN @start_date AND @end_date
      AND `{account_id_column}` IN UNNEST(@account_ids);

    INSERT INTO `{table_ref}`
    SELECT * FROM `{temp_table_id}`;
    COMMIT TRANSACTION;
    """
    query_config = bigquery.QueryJobConfig(
        labels={"pipeline": "new_data_flow", "step": "idempotent_merge"},
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            bigquery.ArrayQueryParameter("account_ids", "STRING", normalized_account_ids),
        ]
    )
    
    try:
        client.query(query, job_config=query_config).result()
    finally:
        # Cleanup failure should not mask the main load result.
        try:
            client.delete_table(temp_table_id, not_found_ok=True)
        except Exception as cleanup_exc:  # noqa: BLE001
            logger.warning("temp table cleanup failed | table=%s err=%s", temp_table_id, cleanup_exc)

    return len(payload)

def append_json_rows(
    client: bigquery.Client,
    table_ref: str,
    rows: Iterable[dict],
) -> int:
    """Append rows to BigQuery using JSON ingestion."""
    payload = list(rows)
    if not payload:
        return 0

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    job = client.load_table_from_json(payload, table_ref, job_config=job_config)
    job.result()
    return len(payload)


def delete_rows_before(
    client: bigquery.Client,
    table_ref: str,
    date_column: str,
    cutoff_date: date,
) -> None:
    """Delete partitions older than cutoff_date for rolling-retention tables."""
    query = f"""
    DELETE FROM `{table_ref}`
    WHERE {date_column} < @cutoff_date
    """
    job_config = bigquery.QueryJobConfig(
        labels={"pipeline": "new_data_flow", "step": "delete_old_partitions"},
        query_parameters=[
            bigquery.ScalarQueryParameter("cutoff_date", "DATE", cutoff_date.isoformat()),
        ],
    )
    client.query(query, job_config=job_config).result()


def call_date_range_procedure(
    client: bigquery.Client,
    procedure_ref: str,
    start_date: str,
    end_date: str,
) -> None:
    """Call BigQuery stored procedure with DATE parameters."""
    query = f"CALL `{procedure_ref}`(@start_date, @end_date)"
    job_config = bigquery.QueryJobConfig(
        labels={"pipeline": "new_data_flow", "step": "warehouse_call"},
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )
    client.query(query, job_config=job_config).result()


def get_latest_successful_warehouse_run(
    client: bigquery.Client,
    run_log_table_ref: str,
    start_date: str,
    end_date: str,
    lookback_days: int = 30,
) -> WarehouseRunLog | None:
    """Return latest SUCCESS run matching same date range, if exists."""
    query = f"""
    SELECT
      run_id,
      CAST(started_at AS STRING) AS started_at,
      CAST(ended_at AS STRING) AS ended_at
    FROM `{run_log_table_ref}`
    WHERE started_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @lookback_days DAY)
      AND pipeline_name = 'warehouse_v2'
      AND source_name = 'all'
      AND status = 'SUCCESS'
      AND JSON_VALUE(metadata, '$.start_date') = @start_date
      AND JSON_VALUE(metadata, '$.end_date') = @end_date
    ORDER BY started_at DESC
    LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        labels={"pipeline": "new_data_flow", "step": "warehouse_rerun_guard"},
        query_parameters=[
            bigquery.ScalarQueryParameter("lookback_days", "INT64", lookback_days),
            bigquery.ScalarQueryParameter("start_date", "STRING", start_date),
            bigquery.ScalarQueryParameter("end_date", "STRING", end_date),
        ],
    )
    rows = list(client.query(query, job_config=job_config).result())
    if not rows:
        return None
    row = rows[0]
    return WarehouseRunLog(
        run_id=str(row["run_id"]),
        started_at=str(row["started_at"]),
        ended_at=str(row["ended_at"]) if row["ended_at"] else None,
    )

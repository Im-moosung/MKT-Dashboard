from __future__ import annotations

from dataclasses import dataclass

from google.cloud import bigquery


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    branch_id: str
    channel_key: str
    provider_key: str
    credential_mode: str | None
    account_id_norm: str | None
    secret_ref: str | None
    secret_version: str | None
    status: str | None
    tier: str | None
    refresh_mode: str | None
    lookback_days: int | None
    api_sleep_seconds: float | None
    run_warehouse_after_ingest: bool | None
    priority: int | None


def resolve_table_ref(project_id: str, table_ref: str) -> str:
    if table_ref.count(".") == 1:
        return f"{project_id}.{table_ref}"
    if table_ref.count(".") == 2:
        return table_ref
    raise ValueError("source-config-table must be Dataset.table or Project.Dataset.table")


def _split_table_ref(full_ref: str) -> tuple[str, str, str]:
    parts = full_ref.split(".")
    if len(parts) != 3:
        raise ValueError(f"invalid table_ref: {full_ref}")
    return parts[0], parts[1], parts[2]


def _table_has_column(
    client: bigquery.Client,
    project_id: str,
    dataset: str,
    table: str,
    column_name: str,
) -> bool:
    query = f"""
    SELECT 1
    FROM `{project_id}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
    WHERE table_name = @table_name
      AND column_name = @column_name
    LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("table_name", "STRING", table),
            bigquery.ScalarQueryParameter("column_name", "STRING", column_name),
        ]
    )
    return any(client.query(query, job_config=job_config).result())


def list_source_configs(
    client: bigquery.Client,
    project_id: str,
    table_ref: str,
    source_id: str | None = None,
    status: str | None = "ACTIVE",
    tier: str | None = None,
) -> list[SourceConfig]:
    full_ref = resolve_table_ref(project_id=project_id, table_ref=table_ref)
    resolved_project, dataset, table = _split_table_ref(full_ref)
    has_credential_mode = _table_has_column(
        client=client,
        project_id=resolved_project,
        dataset=dataset,
        table=table,
        column_name="credential_mode",
    )
    where_clauses = ["1=1"]
    params: list[bigquery.ScalarQueryParameter] = []

    if source_id:
        where_clauses.append("source_id = @source_id")
        params.append(bigquery.ScalarQueryParameter("source_id", "STRING", source_id))
    if status:
        where_clauses.append("status = @status")
        params.append(bigquery.ScalarQueryParameter("status", "STRING", status))
    if tier:
        where_clauses.append("tier = @tier")
        params.append(bigquery.ScalarQueryParameter("tier", "STRING", tier))

    credential_mode_sql = "credential_mode"
    if not has_credential_mode:
        credential_mode_sql = "'ENV'"

    query = f"""
    SELECT
      source_id,
      branch_id,
      channel_key,
      provider_key,
      {credential_mode_sql} AS credential_mode,
      account_id_norm,
      secret_ref,
      secret_version,
      status,
      tier,
      refresh_mode,
      lookback_days,
      api_sleep_seconds,
      run_warehouse_after_ingest,
      priority
    FROM `{full_ref}`
    WHERE {" AND ".join(where_clauses)}
    ORDER BY priority ASC, source_id ASC
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(query, job_config=job_config).result()

    result: list[SourceConfig] = []
    for row in rows:
        result.append(
            SourceConfig(
                source_id=row["source_id"],
                branch_id=row["branch_id"],
                channel_key=row["channel_key"],
                provider_key=row["provider_key"],
                credential_mode=row["credential_mode"],
                account_id_norm=row["account_id_norm"],
                secret_ref=row["secret_ref"],
                secret_version=row["secret_version"],
                status=row["status"],
                tier=row["tier"],
                refresh_mode=row["refresh_mode"],
                lookback_days=row["lookback_days"],
                api_sleep_seconds=row["api_sleep_seconds"],
                run_warehouse_after_ingest=row["run_warehouse_after_ingest"],
                priority=row["priority"],
            )
        )
    return result

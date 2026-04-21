from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from dotenv import dotenv_values
from google.api_core.exceptions import AlreadyExists
from google.api_core.exceptions import PermissionDenied

from New_Data_flow.common.bigquery_loader import build_bigquery_client
from New_Data_flow.common.secret_manager import build_secret_manager_client

REQUIRED_KEYS_BY_PROVIDER: dict[str, set[str]] = {
    "meta_ads": {"FB_APP_ID", "FB_APP_SECRET", "FB_ACCESS_TOKEN"},
    "google_ads": {"GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "GOOGLE_DEVELOPER_TOKEN"},
    "tiktok_ads": {"TIKTOK_ACCESS_TOKEN"},
    "naver_ads": {"NAVER_API_KEY", "NAVER_SECRET_KEY", "NAVER_CUSTOMER_ID"},
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap channel credentials into Secret Manager and source config")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", default="us-central1", help="BigQuery job location")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--secret-id", required=True, help="Secret name only (without projects/.../secrets/)")
    parser.add_argument("--env-file", required=True, help="Path to local .env file")
    parser.add_argument("--source-config-table", default="ops.ingest_source_config")
    parser.add_argument("--credentials-path", help="Optional service account json path for BQ/SecretManager")
    parser.add_argument(
        "--status-on-success",
        choices=["KEEP", "ACTIVE", "PENDING_SETUP", "PAUSED"],
        default="KEEP",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def resolve_table_ref(project_id: str, table_ref: str) -> str:
    if table_ref.count(".") == 1:
        return f"{project_id}.{table_ref}"
    if table_ref.count(".") == 2:
        return table_ref
    raise ValueError("source-config-table must be Dataset.table or Project.Dataset.table")


def load_source_row(client, table_ref: str, source_id: str) -> dict:
    query = f"""
    SELECT source_id, provider_key, status, account_id_norm, secret_ref, secret_version
    FROM `{table_ref}`
    WHERE source_id = @source_id
    LIMIT 1
    """
    from google.cloud import bigquery  # local import to keep module import light

    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("source_id", "STRING", source_id)]
    )
    rows = list(client.query(query, job_config=config).result())
    if not rows:
        raise ValueError(f"source_id not found: {source_id}")
    return dict(rows[0])


def parse_env_file(path: Path) -> dict[str, str]:
    raw = dotenv_values(path)
    parsed: dict[str, str] = {}
    for k, v in raw.items():
        if not k:
            continue
        if v is None:
            continue
        vv = str(v).strip()
        if vv:
            parsed[str(k).strip()] = vv
    return parsed


def validate_required_keys(provider_key: str, data: dict[str, str]) -> None:
    required = REQUIRED_KEYS_BY_PROVIDER.get(provider_key, set())
    missing = sorted([k for k in required if not data.get(k)])
    if missing:
        raise ValueError(f"missing required keys for {provider_key}: {', '.join(missing)}")


def ensure_secret(sm_client, project_id: str, secret_id: str) -> str:
    parent = f"projects/{project_id}"
    secret_path = f"{parent}/secrets/{secret_id}"
    try:
        sm_client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
    except AlreadyExists:
        pass
    return secret_path


def add_secret_version(sm_client, secret_path: str, payload: dict[str, str]) -> str:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    resp = sm_client.add_secret_version(request={"parent": secret_path, "payload": {"data": body}})
    return resp.name


def update_source_secret_ref(client, table_ref: str, source_id: str, secret_id: str, status_on_success: str) -> int:
    from google.cloud import bigquery

    set_status_sql = ""
    if status_on_success != "KEEP":
        set_status_sql = ", status = @status_on_success"

    query = f"""
    UPDATE `{table_ref}`
    SET
      secret_ref = @secret_ref,
      secret_version = 'latest'
      {set_status_sql},
      updated_at = CURRENT_TIMESTAMP()
    WHERE source_id = @source_id
    """
    params = [
        bigquery.ScalarQueryParameter("secret_ref", "STRING", secret_id),
        bigquery.ScalarQueryParameter("source_id", "STRING", source_id),
    ]
    if status_on_success != "KEEP":
        params.append(bigquery.ScalarQueryParameter("status_on_success", "STRING", status_on_success))

    job = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params))
    job.result()
    return int(job.num_dml_affected_rows or 0)


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    env_path = Path(args.env_file)
    if not env_path.exists():
        raise FileNotFoundError(f"env file not found: {env_path}")

    bq_client = build_bigquery_client(
        project_id=args.project_id,
        credentials_path=args.credentials_path,
        location=args.location,
    )
    source_table_ref = resolve_table_ref(args.project_id, args.source_config_table)
    source_row = load_source_row(bq_client, source_table_ref, args.source_id)
    provider_key = str(source_row["provider_key"])

    payload = parse_env_file(env_path)
    validate_required_keys(provider_key=provider_key, data=payload)

    if args.dry_run:
        print(
            f"dry_run ok | source_id={args.source_id} provider={provider_key} "
            f"keys={len(payload)} target_secret={args.secret_id}"
        )
        return 0

    sm_client = build_secret_manager_client(credentials_path=args.credentials_path)
    try:
        secret_path = ensure_secret(sm_client, project_id=args.project_id, secret_id=args.secret_id)
        version_name = add_secret_version(sm_client, secret_path=secret_path, payload=payload)
    except PermissionDenied as exc:
        text = str(exc)
        if "SERVICE_DISABLED" in text or "secretmanager.googleapis.com" in text:
            print(
                "secret manager is disabled for this project. "
                "enable secretmanager.googleapis.com first, then re-run."
            )
            return 2
        raise
    affected = update_source_secret_ref(
        client=bq_client,
        table_ref=source_table_ref,
        source_id=args.source_id,
        secret_id=args.secret_id,
        status_on_success=args.status_on_success,
    )

    print(
        "bootstrap done | "
        f"source_id={args.source_id} provider={provider_key} secret={secret_path} version={version_name} "
        f"rows_updated={affected}"
    )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

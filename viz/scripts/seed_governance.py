"""Apply governance + dim_branch patches to BigQuery (idempotent MERGE)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent / "sql"


def sql_file_paths() -> list[Path]:
    return sorted(SQL_DIR.glob("*.sql"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", default=os.getenv("BQ_PROJECT_ID", "mimetic-gravity-442013-u4"))
    parser.add_argument("--credentials-path", default=os.getenv("BQ_CREDENTIALS_PATH"))
    args = parser.parse_args(argv)

    from google.cloud import bigquery
    from google.oauth2 import service_account

    creds = None
    if args.credentials_path and Path(args.credentials_path).exists():
        creds = service_account.Credentials.from_service_account_file(args.credentials_path)
    client = bigquery.Client(project=args.project_id, credentials=creds, location="us-central1")

    for path in sql_file_paths():
        print(f"[seed-governance] executing {path.name}")
        sql = path.read_text()
        # Split on ';' for multi-statement files; skip empty segments.
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        for i, stmt in enumerate(statements, 1):
            print(f"[seed-governance]   stmt {i}/{len(statements)}")
            client.query(stmt).result()
    print("[seed-governance] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Seed test data for Sales/Survey into BigQuery raw tables (POC-only).

WARNING: Uses WRITE_TRUNCATE on raw_commerce.sales_orders_raw and
raw_feedback.survey_responses_raw. Do NOT run on production ingest paths.
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

BRANCH_IDS = ["AMLV", "AMBS", "AMDB", "AMGN", "AMJJ", "AMYS", "AKJJ"]
START = date(2026, 4, 1)
DAYS = 12


def gen_sales() -> list[dict]:
    rows = []
    for d_offset in range(DAYS):
        d = START + timedelta(days=d_offset)
        for branch in BRANCH_IDS:
            n = random.randint(10, 50)
            for i in range(n):
                order_id = f"POC_{branch}_{d.isoformat()}_{i:03d}"
                qty = random.randint(1, 4)
                gross = round(random.uniform(15, 120) * qty, 2)
                discount = round(gross * random.uniform(0, 0.15), 2)
                net = round(gross - discount, 2)
                rows.append({
                    "ingestion_id": f"POC-SEED-{order_id}",
                    "ingestion_ts": datetime.now(timezone.utc).isoformat(),
                    "source_extract_ts": datetime.now(timezone.utc).isoformat(),
                    "source_system": "POC_SEED",
                    "order_id": order_id,
                    "order_line_id": f"{order_id}-1",
                    "order_ts": datetime.combine(d, datetime.min.time()).isoformat(),
                    "order_date": d.isoformat(),
                    "customer_id": f"CUST_{random.randint(1000, 9999)}",
                    "customer_email": None,
                    "customer_phone": None,
                    "product_id": f"TICKET_{branch}",
                    "product_name": "일반권",
                    "quantity": qty,
                    "gross_amount": gross,
                    "discount_amount": discount,
                    "net_amount": net,
                    "currency": "USD" if branch in ("AMLV",) else "KRW",
                    "payment_status": "PAID",
                    "source_payload": None,
                })
    return rows


def gen_surveys() -> list[dict]:
    rows = []
    for d_offset in range(DAYS):
        d = START + timedelta(days=d_offset)
        for branch in BRANCH_IDS:
            n = random.randint(3, 8)
            for i in range(n):
                response_id = f"POC_SURV_{branch}_{d.isoformat()}_{i:03d}"
                score = random.randint(6, 10)
                rows.append({
                    "ingestion_id": f"POC-SEED-{response_id}",
                    "ingestion_ts": datetime.now(timezone.utc).isoformat(),
                    "source_extract_ts": datetime.now(timezone.utc).isoformat(),
                    "survey_source": "POC_SEED",
                    "response_id": response_id,
                    "response_ts": datetime.combine(d, datetime.min.time()).isoformat(),
                    "response_date": d.isoformat(),
                    "customer_email": None,
                    "customer_phone": None,
                    "survey_id": "NPS_2026_04",
                    "survey_name": "Post-visit NPS",
                    "question_id": "q_nps",
                    "question_text": "추천 의향",
                    "answer_type": "score",
                    "answer_text": str(score),
                    "answer_score": float(score),
                    "source_payload": None,
                })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", default=os.getenv("BQ_PROJECT_ID", "mimetic-gravity-442013-u4"))
    parser.add_argument("--credentials-path", default=os.getenv("BQ_CREDENTIALS_PATH"))
    parser.add_argument("--sales-table", default="raw_commerce.sales_orders_raw")
    parser.add_argument("--survey-table", default="raw_feedback.survey_responses_raw")
    args = parser.parse_args(argv)

    from google.cloud import bigquery
    from google.oauth2 import service_account

    creds = None
    if args.credentials_path and Path(args.credentials_path).exists():
        creds = service_account.Credentials.from_service_account_file(args.credentials_path)
    client = bigquery.Client(project=args.project_id, credentials=creds, location="us-central1")

    sales = gen_sales()
    surveys = gen_surveys()
    print(f"[seed-test-data] sales={len(sales)} surveys={len(surveys)}")

    for table, rows in [(args.sales_table, sales), (args.survey_table, surveys)]:
        ref = f"{args.project_id}.{table}"
        job = client.load_table_from_json(
            rows,
            ref,
            job_config=bigquery.LoadJobConfig(
                write_disposition="WRITE_TRUNCATE",
                labels={"pipeline": "mkt_viz", "step": "seed_test_data"},
            ),
        )
        job.result()
        print(f"[seed-test-data] loaded {len(rows)} rows into {ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

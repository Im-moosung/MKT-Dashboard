"""Snapshot AMNY/DSTX Google Sheets → BigQuery raw_ads.external_ads_raw.

Idempotent: WRITE_TRUNCATE on each run. Designed for cron use.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests

SHEET_ID = "1WsATorbjts3CgjXKkNYW8iVs3ZKrnOkzcK4gHOIru50"

BRANCH_GIDS = {
    "AMNY": {
        "spend": 1792827791,
        "impressions": 980029740,
        "clicks": 643195110,
        "cr": 2093655192,
    },
    "DSTX": {
        "spend": 2095643634,
        "impressions": 1248817661,
        "clicks": 323203861,
        "cr": 584816983,
    },
}

# Channel code → canonical channel_key mapping
# Covers prefixed (1_Meta) and flat (META) variants.
CHANNEL_MAP = {
    "1_meta": "META",
    "meta": "META",
    "2_google_search": "GOOGLE_ADS",
    "google_search": "GOOGLE_ADS",
    "3_google_display": "GOOGLE_ADS",
    "22_google_demand_gen": "GOOGLE_DEMAND_GEN",
    "7_tiktok": "TIKTOK_ADS",
    "tiktok": "TIKTOK_ADS",
    "4_youtube": "YOUTUBE",
    "youtube": "YOUTUBE",
    "10_coupons": "COUPON",
    "14_affiliate": "AFFILIATE",
    "15_email": "EMAIL",
    "102_ambassadors": "INFLUENCER",
    "58_marketing_fee": "OTHER",
    "12_organic_seo": "ORGANIC_SEO",
    "114_ota": "OTA",
}


def normalize_channel_code(raw: str) -> str:
    key = (raw or "").strip().lower()
    return CHANNEL_MAP.get(key, "OTHER")


_currency_re = re.compile(r"[,$%]")


def parse_currency(value: str) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    s = _currency_re.sub("", s)
    try:
        return float(s)
    except ValueError:
        return None


def fetch_sheet_csv(gid: int) -> str:
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text


@dataclass
class MetricRow:
    date: str
    channel_code: str
    value: float | None


def parse_metric_sheet(csv_text: str, metric_cols: int = 3) -> Iterable[MetricRow]:
    """Read only the first `metric_cols` columns (DATE, CHANNEL, METRIC).

    Trailing pivot columns are ignored.
    """
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader, None)
    if not header or header[0].strip().upper() != "DATE":
        raise AssertionError(f"Unexpected header: {header}")
    for row in reader:
        if len(row) < metric_cols:
            continue
        raw_date = row[0].strip()
        channel = row[1].strip() if len(row) > 1 else ""
        value = parse_currency(row[2]) if len(row) > 2 else None
        if not raw_date or not channel:
            continue
        try:
            date = datetime.fromisoformat(raw_date.replace(" 0:00:00", "")).date().isoformat()
        except ValueError:
            continue
        yield MetricRow(date=date, channel_code=channel, value=value)


def parse_cr_sheet(csv_text: str) -> Iterable[tuple[str, str, float | None, float | None, float | None]]:
    """CR sheet schema: DATE, CD_MKT_CHANNEL, MXP_TRANSACTIONS, MXP_PLAN_VIEWS, CR."""
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader, None)
    if not header or header[0].strip().upper() != "DATE":
        raise AssertionError(f"Unexpected header: {header}")
    for row in reader:
        if len(row) < 5:
            continue
        date_raw, channel, tx, pv, cr = row[:5]
        try:
            date = datetime.fromisoformat(date_raw.strip().replace(" 0:00:00", "")).date().isoformat()
        except ValueError:
            continue
        if not channel.strip():
            continue
        yield date, channel.strip(), parse_currency(tx), parse_currency(pv), parse_currency(cr)


def build_rows(branch_id: str) -> list[dict]:
    """Join 4 metric sheets on (date, channel_code)."""
    gids = BRANCH_GIDS[branch_id]
    ingestion_ts = datetime.now(timezone.utc).isoformat()

    # Load each metric into keyed dicts
    spend = {(r.date, normalize_channel_code(r.channel_code)): r.value for r in parse_metric_sheet(fetch_sheet_csv(gids["spend"]))}
    impressions = {(r.date, normalize_channel_code(r.channel_code)): r.value for r in parse_metric_sheet(fetch_sheet_csv(gids["impressions"]))}
    clicks = {(r.date, normalize_channel_code(r.channel_code)): r.value for r in parse_metric_sheet(fetch_sheet_csv(gids["clicks"]))}

    cr_rows = list(parse_cr_sheet(fetch_sheet_csv(gids["cr"])))
    cr_by_key = {}
    for date, channel, tx, pv, cr in cr_rows:
        k = (date, normalize_channel_code(channel))
        cr_by_key[k] = (tx, pv, cr)

    keys = set(spend.keys()) | set(impressions.keys()) | set(clicks.keys()) | set(cr_by_key.keys())

    rows = []
    for (date, channel_key) in sorted(keys):
        tx, pv, cr = cr_by_key.get((date, channel_key), (None, None, None))
        rows.append({
            "date": date,
            "branch_id": branch_id,
            "channel_code": channel_key,
            "channel_key": channel_key,
            "spend_usd": spend.get((date, channel_key)),
            "impressions": impressions.get((date, channel_key)),
            "clicks": clicks.get((date, channel_key)),
            "transactions": tx,
            "plan_views": pv,
            "cr_pct": cr,
            "ingestion_ts": ingestion_ts,
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true", help="WRITE_TRUNCATE the raw table")
    parser.add_argument("--project-id", default=os.getenv("BQ_PROJECT_ID", "mimetic-gravity-442013-u4"))
    parser.add_argument("--credentials-path", default=os.getenv("BQ_CREDENTIALS_PATH"))
    parser.add_argument("--table", default="raw_ads.external_ads_raw")
    parser.add_argument("--branches", nargs="+", default=["AMNY", "DSTX"])
    args = parser.parse_args(argv)

    all_rows: list[dict] = []
    for b in args.branches:
        all_rows.extend(build_rows(b))

    print(f"[seed-sheets] branches={args.branches} rows={len(all_rows)}")

    from google.cloud import bigquery
    from google.oauth2 import service_account

    creds = None
    if args.credentials_path and Path(args.credentials_path).exists():
        creds = service_account.Credentials.from_service_account_file(args.credentials_path)
    client = bigquery.Client(project=args.project_id, credentials=creds, location="us-central1")

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE" if args.overwrite else "WRITE_APPEND",
        schema=[
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("branch_id", "STRING"),
            bigquery.SchemaField("channel_code", "STRING"),
            bigquery.SchemaField("channel_key", "STRING"),
            bigquery.SchemaField("spend_usd", "NUMERIC"),
            bigquery.SchemaField("impressions", "NUMERIC"),
            bigquery.SchemaField("clicks", "NUMERIC"),
            bigquery.SchemaField("transactions", "NUMERIC"),
            bigquery.SchemaField("plan_views", "NUMERIC"),
            bigquery.SchemaField("cr_pct", "FLOAT64"),
            bigquery.SchemaField("ingestion_ts", "TIMESTAMP"),
        ],
        labels={"pipeline": "mkt_viz", "step": "seed_sheets"},
    )
    table_ref = f"{args.project_id}.{args.table}"
    job = client.load_table_from_json(all_rows, table_ref, job_config=job_config)
    job.result()
    print(f"[seed-sheets] loaded {len(all_rows)} rows into {table_ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

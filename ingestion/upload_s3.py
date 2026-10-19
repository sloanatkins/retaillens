"""
S3 Upload
=========

Uploads the 9 Olist CSVs from the local data/raw folder to S3 with
date-partitioned paths, so each day's load is preserved separately.

S3 key format:
    {table_name}/ingestion_date={YYYY-MM-DD}/{filename}

Example:
    olist_orders/ingestion_date=2026-06-01/olist_orders_dataset.csv

The table name in the path is the clean version (olist_orders, not
olist_orders_dataset) so it matches what Snowflake and dbt expect.

Run with:
    python ingestion/upload_s3.py

Dependencies:
- boto3
- python-dotenv
- loguru
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────
BUCKET = os.getenv("S3_BUCKET", "retaillens-raw")
REGION = os.getenv("AWS_REGION", "us-east-1")
RAW_DATA_PATH = Path(__file__).parent.parent / "data" / "raw"

EXPECTED_FILES = [
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]

# Maps the raw filename to a clean table name used in the S3 path
TABLE_NAME_MAP = {
    "olist_customers_dataset.csv":              "olist_customers",
    "olist_geolocation_dataset.csv":            "olist_geolocation",
    "olist_order_items_dataset.csv":            "olist_order_items",
    "olist_order_payments_dataset.csv":         "olist_order_payments",
    "olist_order_reviews_dataset.csv":          "olist_order_reviews",
    "olist_orders_dataset.csv":                 "olist_orders",
    "olist_products_dataset.csv":               "olist_products",
    "olist_sellers_dataset.csv":                "olist_sellers",
    "product_category_name_translation.csv":    "product_category_translation",
}


# ── Helpers ───────────────────────────────────────────────────────────
def get_s3_key(filename: str, ingestion_date: str) -> str:
    """Build the date-partitioned S3 key for a given file."""
    table_name = TABLE_NAME_MAP[filename]
    return f"{table_name}/ingestion_date={ingestion_date}/{filename}"


# ── Main ──────────────────────────────────────────────────────────────
def upload_to_s3(ingestion_date: str = None) -> dict:
    """Upload all 9 CSVs to S3 and return a summary of what succeeded or failed."""
    if ingestion_date is None:
        ingestion_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    logger.info(f"Starting S3 upload — bucket: {BUCKET}, date: {ingestion_date}")

    s3 = boto3.client("s3", region_name=REGION)
    results = {"uploaded": [], "failed": [], "ingestion_date": ingestion_date}

    for filename in EXPECTED_FILES:
        local_path = RAW_DATA_PATH / filename
        s3_key = get_s3_key(filename, ingestion_date)

        if not local_path.exists():
            logger.error(f"Local file not found: {local_path}")
            results["failed"].append(filename)
            continue

        try:
            logger.info(f"Uploading {filename} -> s3://{BUCKET}/{s3_key}")
            s3.upload_file(
                str(local_path),
                BUCKET,
                s3_key,
                ExtraArgs={"ContentType": "text/csv"},
            )
            logger.info(f"Uploaded: {filename}")
            results["uploaded"].append(filename)

        except Exception as e:
            logger.error(f"Failed to upload {filename}: {e}")
            results["failed"].append(filename)

    uploaded = len(results["uploaded"])
    failed = len(results["failed"])
    logger.info(f"Upload complete — {uploaded}/{len(EXPECTED_FILES)} succeeded, {failed} failed")

    if failed > 0:
        raise RuntimeError(f"{failed} file(s) failed to upload: {results['failed']}")

    return results


if __name__ == "__main__":
    result = upload_to_s3()
    logger.info(f"Result: {result}")
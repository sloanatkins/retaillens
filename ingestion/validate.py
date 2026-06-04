import boto3
import pandas as pd
from io import StringIO
from pathlib import Path
from datetime import datetime, timezone
from loguru import logger
from dotenv import load_dotenv
import os

load_dotenv()

BUCKET = os.getenv("S3_BUCKET", "retaillens-raw")
REGION = os.getenv("AWS_REGION", "us-east-1")

VALIDATION_RULES = {
    "olist_orders": {
        "s3_prefix": "olist_orders",
        "filename": "olist_orders_dataset.csv",
        "min_rows": 90000,
        "not_null": ["order_id", "customer_id", "order_status"],
        "accepted_values": {
            "order_status": [
                "delivered", "shipped", "canceled", "unavailable",
                "invoiced", "processing", "created", "approved"
            ]
        },
    },
    "olist_order_items": {
        "s3_prefix": "olist_order_items",
        "filename": "olist_order_items_dataset.csv",
        "min_rows": 100000,
        "not_null": ["order_id", "product_id", "seller_id"],
        "non_negative": ["price", "freight_value"],
    },
    "olist_customers": {
        "s3_prefix": "olist_customers",
        "filename": "olist_customers_dataset.csv",
        "min_rows": 90000,
        "not_null": ["customer_id", "customer_unique_id"],
    },
    "olist_products": {
        "s3_prefix": "olist_products",
        "filename": "olist_products_dataset.csv",
        "min_rows": 30000,
        "not_null": ["product_id"],
    },
    "olist_sellers": {
        "s3_prefix": "olist_sellers",
        "filename": "olist_sellers_dataset.csv",
        "min_rows": 3000,
        "not_null": ["seller_id"],
    },
    "olist_order_payments": {
        "s3_prefix": "olist_order_payments",
        "filename": "olist_order_payments_dataset.csv",
        "min_rows": 100000,
        "not_null": ["order_id", "payment_type"],
        "non_negative": ["payment_value"],
    },
    "olist_order_reviews": {
        "s3_prefix": "olist_order_reviews",
        "filename": "olist_order_reviews_dataset.csv",
        "min_rows": 90000,
        "not_null": ["review_id", "order_id"],
    },
    "olist_geolocation": {
        "s3_prefix": "olist_geolocation",
        "filename": "olist_geolocation_dataset.csv",
        "min_rows": 500000,
        "not_null": ["geolocation_zip_code_prefix"],
    },
    "product_category_translation": {
        "s3_prefix": "product_category_translation",
        "filename": "product_category_name_translation.csv",
        "min_rows": 60,
        "not_null": ["product_category_name", "product_category_name_english"],
    },
}


def read_csv_from_s3(s3_client, bucket: str, key: str) -> pd.DataFrame:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read().decode("utf-8")
    return pd.read_csv(StringIO(content))


def get_latest_s3_key(s3_client, bucket: str, prefix: str, filename: str) -> str:
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    keys = []
    for page in pages:
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(filename):
                keys.append(obj["Key"])
    if not keys:
        raise FileNotFoundError(f"No files found in s3://{bucket}/{prefix}/")
    return sorted(keys)[-1]


def validate_table(s3_client, table_name: str, rules: dict) -> dict:
    result = {"table": table_name, "passed": [], "failed": [], "warnings": []}

    try:
        key = get_latest_s3_key(
            s3_client, BUCKET, rules["s3_prefix"], rules["filename"]
        )
        logger.info(f"Validating {table_name} from s3://{BUCKET}/{key}")
        df = read_csv_from_s3(s3_client, BUCKET, key)
    except Exception as e:
        result["failed"].append(f"Could not read file: {e}")
        return result

    # Row count check
    actual_rows = len(df)
    min_rows = rules.get("min_rows", 0)
    if actual_rows >= min_rows:
        result["passed"].append(f"row_count: {actual_rows} >= {min_rows}")
    else:
        result["failed"].append(f"row_count: {actual_rows} < {min_rows}")

    # Not null checks
    for col in rules.get("not_null", []):
        if col not in df.columns:
            result["failed"].append(f"not_null: column '{col}' missing")
            continue
        null_count = df[col].isnull().sum()
        if null_count == 0:
            result["passed"].append(f"not_null: {col}")
        else:
            result["failed"].append(f"not_null: {col} has {null_count} nulls")

    # Non-negative checks
    for col in rules.get("non_negative", []):
        if col not in df.columns:
            result["failed"].append(f"non_negative: column '{col}' missing")
            continue
        negative_count = (df[col] < 0).sum()
        if negative_count == 0:
            result["passed"].append(f"non_negative: {col}")
        else:
            result["failed"].append(f"non_negative: {col} has {negative_count} negative values")

    # Accepted values checks
    for col, accepted in rules.get("accepted_values", {}).items():
        if col not in df.columns:
            result["failed"].append(f"accepted_values: column '{col}' missing")
            continue
        unexpected = set(df[col].dropna().unique()) - set(accepted)
        if not unexpected:
            result["passed"].append(f"accepted_values: {col}")
        else:
            result["warnings"].append(f"accepted_values: {col} has unexpected values: {unexpected}")

    return result


def validate(ingestion_date: str = None) -> dict:
    if ingestion_date is None:
        ingestion_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    logger.info(f"Starting validation — date: {ingestion_date}")
    s3 = boto3.client("s3", region_name=REGION)

    all_results = []
    total_passed = 0
    total_failed = 0

    for table_name, rules in VALIDATION_RULES.items():
        result = validate_table(s3, table_name, rules)
        all_results.append(result)
        total_passed += len(result["passed"])
        total_failed += len(result["failed"])

        status = "PASS" if not result["failed"] else "FAIL"
        logger.info(f"{status} — {table_name}: {len(result['passed'])} passed, {len(result['failed'])} failed")

        for msg in result["failed"]:
            logger.error(f"  FAILED: {msg}")
        for msg in result["warnings"]:
            logger.warning(f"  WARNING: {msg}")

    logger.info(f"Validation complete — {total_passed} checks passed, {total_failed} checks failed")

    if total_failed > 0:
        raise RuntimeError(f"Validation failed with {total_failed} error(s)")

    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tables_validated": len(all_results),
        "total_passed": total_passed,
        "total_failed": total_failed,
    }


if __name__ == "__main__":
    result = validate()
    logger.info(f"Result: {result}")

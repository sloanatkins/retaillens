"""
Snowflake Load
==============

Copies the 9 Olist CSVs from S3 into the raw Snowflake tables using
COPY INTO. This is the end of the ingestion leg — after this, dbt takes over.

For each table:
1. Find the latest partition in S3 (date-partitioned paths)
2. Truncate the raw table
3. COPY INTO from the S3 stage

Everything lands as VARCHAR in the raw layer. Type casting happens in
dbt staging models, not here, so a bad value becomes null instead of
crashing the load.

Uses RSA key-pair auth for the same reason as the dashboard — the trial
account has MFA enforced account-wide, which blocks password auth.

Run with:
    python ingestion/load_snowflake.py

Dependencies:
- snowflake-connector-python
- boto3
- cryptography
- python-dotenv
- loguru
"""

import os
from datetime import datetime, timezone

import boto3
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────
BUCKET = os.getenv("S3_BUCKET", "retaillens-raw")
REGION = os.getenv("AWS_REGION", "us-east-1")

# All 9 tables — maps the Snowflake table name to its S3 prefix and filename
TABLES = [
    {"table": "OLIST_ORDERS",               "s3_prefix": "olist_orders",               "filename": "olist_orders_dataset.csv"},
    {"table": "OLIST_ORDER_ITEMS",          "s3_prefix": "olist_order_items",          "filename": "olist_order_items_dataset.csv"},
    {"table": "OLIST_CUSTOMERS",            "s3_prefix": "olist_customers",            "filename": "olist_customers_dataset.csv"},
    {"table": "OLIST_PRODUCTS",             "s3_prefix": "olist_products",             "filename": "olist_products_dataset.csv"},
    {"table": "OLIST_SELLERS",              "s3_prefix": "olist_sellers",              "filename": "olist_sellers_dataset.csv"},
    {"table": "OLIST_ORDER_PAYMENTS",       "s3_prefix": "olist_order_payments",       "filename": "olist_order_payments_dataset.csv"},
    {"table": "OLIST_ORDER_REVIEWS",        "s3_prefix": "olist_order_reviews",        "filename": "olist_order_reviews_dataset.csv"},
    {"table": "OLIST_GEOLOCATION",          "s3_prefix": "olist_geolocation",          "filename": "olist_geolocation_dataset.csv"},
    {"table": "PRODUCT_CATEGORY_TRANSLATION", "s3_prefix": "product_category_translation", "filename": "product_category_name_translation.csv"},
]


# ── Auth ──────────────────────────────────────────────────────────────
def load_private_key() -> bytes:
    """Load the RSA private key and return it as DER bytes for the connector."""
    with open(os.path.expanduser("~/.ssh/snowflake_key.pem"), "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_snowflake_config() -> dict:
    """Build the connector config dict. Called at load time so the key is read once."""
    return {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "private_key": load_private_key(),
        "database": os.getenv("SNOWFLAKE_DATABASE", "RETAILLENS_DB"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        "schema": "RAW",
    }


# ── S3 helpers ────────────────────────────────────────────────────────
def get_latest_s3_key(s3_client, prefix: str, filename: str) -> str:
    """
    Find the most recent partition for a table in S3.

    Partitions look like: olist_orders/ingestion_date=2026-06-01/olist_orders_dataset.csv
    Sorting lexicographically works because the date is ISO format.
    """
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=BUCKET, Prefix=prefix)
    keys = [
        obj["Key"]
        for page in pages
        for obj in page.get("Contents", [])
        if obj["Key"].endswith(filename)
    ]
    if not keys:
        raise FileNotFoundError(f"No files found at s3://{BUCKET}/{prefix}/")
    return sorted(keys)[-1]


# ── Snowflake helpers ─────────────────────────────────────────────────
def create_raw_tables(cursor):
    """Create the 9 raw tables if they don't exist yet. Everything is VARCHAR — dbt handles casting."""
    statements = [
        """CREATE TABLE IF NOT EXISTS RETAILLENS_DB.RAW.OLIST_ORDERS (
            order_id VARCHAR, customer_id VARCHAR, order_status VARCHAR,
            order_purchase_timestamp VARCHAR, order_approved_at VARCHAR,
            order_delivered_carrier_date VARCHAR, order_delivered_customer_date VARCHAR,
            order_estimated_delivery_date VARCHAR)""",
        """CREATE TABLE IF NOT EXISTS RETAILLENS_DB.RAW.OLIST_ORDER_ITEMS (
            order_id VARCHAR, order_item_id VARCHAR, product_id VARCHAR,
            seller_id VARCHAR, shipping_limit_date VARCHAR,
            price VARCHAR, freight_value VARCHAR)""",
        """CREATE TABLE IF NOT EXISTS RETAILLENS_DB.RAW.OLIST_CUSTOMERS (
            customer_id VARCHAR, customer_unique_id VARCHAR,
            customer_zip_code_prefix VARCHAR, customer_city VARCHAR,
            customer_state VARCHAR)""",
        """CREATE TABLE IF NOT EXISTS RETAILLENS_DB.RAW.OLIST_PRODUCTS (
            product_id VARCHAR, product_category_name VARCHAR,
            product_name_lenght VARCHAR, product_description_lenght VARCHAR,
            product_photos_qty VARCHAR, product_weight_g VARCHAR,
            product_length_cm VARCHAR, product_height_cm VARCHAR,
            product_width_cm VARCHAR)""",
        """CREATE TABLE IF NOT EXISTS RETAILLENS_DB.RAW.OLIST_SELLERS (
            seller_id VARCHAR, seller_zip_code_prefix VARCHAR,
            seller_city VARCHAR, seller_state VARCHAR)""",
        """CREATE TABLE IF NOT EXISTS RETAILLENS_DB.RAW.OLIST_ORDER_PAYMENTS (
            order_id VARCHAR, payment_sequential VARCHAR,
            payment_type VARCHAR, payment_installments VARCHAR,
            payment_value VARCHAR)""",
        """CREATE TABLE IF NOT EXISTS RETAILLENS_DB.RAW.OLIST_ORDER_REVIEWS (
            review_id VARCHAR, order_id VARCHAR, review_score VARCHAR,
            review_comment_title VARCHAR, review_comment_message VARCHAR,
            review_creation_date VARCHAR, review_answer_timestamp VARCHAR)""",
        """CREATE TABLE IF NOT EXISTS RETAILLENS_DB.RAW.OLIST_GEOLOCATION (
            geolocation_zip_code_prefix VARCHAR, geolocation_lat VARCHAR,
            geolocation_lng VARCHAR, geolocation_city VARCHAR,
            geolocation_state VARCHAR)""",
        """CREATE TABLE IF NOT EXISTS RETAILLENS_DB.RAW.PRODUCT_CATEGORY_TRANSLATION (
            product_category_name VARCHAR, product_category_name_english VARCHAR)""",
    ]
    for stmt in statements:
        cursor.execute(stmt)
    logger.info("All RAW tables ready")


def create_stage(cursor, stage_name: str):
    """Create (or replace) the external stage pointing at the S3 bucket."""
    cursor.execute(f"""
        CREATE OR REPLACE STAGE {stage_name}
        URL = 's3://{BUCKET}/'
        CREDENTIALS = (
            AWS_KEY_ID = '{os.getenv("AWS_ACCESS_KEY_ID")}'
            AWS_SECRET_KEY = '{os.getenv("AWS_SECRET_ACCESS_KEY")}'
        )
        FILE_FORMAT = (
            TYPE = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            SKIP_HEADER = 1
            NULL_IF = ('', 'NULL', 'null')
            EMPTY_FIELD_AS_NULL = TRUE
        );
    """)
    logger.info(f"Stage {stage_name} ready")


def load_table(cursor, table_name: str, s3_key: str, stage_name: str):
    """
    Truncate the raw table and COPY INTO from S3.

    ON_ERROR = CONTINUE means bad rows get skipped and logged instead of
    failing the whole load. The error count comes back in the COPY result.
    """
    cursor.execute(f"TRUNCATE TABLE IF EXISTS RETAILLENS_DB.RAW.{table_name};")
    cursor.execute(f"""
        COPY INTO RETAILLENS_DB.RAW.{table_name}
        FROM @{stage_name}/{s3_key}
        FILE_FORMAT = (
            TYPE = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            SKIP_HEADER = 1
            NULL_IF = ('', 'NULL', 'null')
            EMPTY_FIELD_AS_NULL = TRUE
        )
        ON_ERROR = 'CONTINUE';
    """)
    results = cursor.fetchall()
    rows_loaded = sum(r[3] for r in results) if results else 0
    errors = sum(r[4] for r in results) if results else 0
    logger.info(f"Loaded {table_name}: {rows_loaded} rows, {errors} errors")
    return rows_loaded, errors


# ── Main ──────────────────────────────────────────────────────────────
def load(ingestion_date: str = None) -> dict:
    """Load all 9 tables from S3 into Snowflake and return a summary."""
    if ingestion_date is None:
        ingestion_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    logger.info(f"Starting Snowflake load — date: {ingestion_date}")

    s3 = boto3.client("s3", region_name=REGION)
    conn = snowflake.connector.connect(**get_snowflake_config())
    cursor = conn.cursor()

    try:
        create_raw_tables(cursor)
        stage_name = "RETAILLENS_DB.RAW.RETAILLENS_S3_STAGE"
        create_stage(cursor, stage_name)

        results = {"loaded": [], "failed": [], "ingestion_date": ingestion_date}

        for table_def in TABLES:
            try:
                s3_key = get_latest_s3_key(s3, table_def["s3_prefix"], table_def["filename"])
                rows, errors = load_table(cursor, table_def["table"], s3_key, stage_name)
                results["loaded"].append({"table": table_def["table"], "rows": rows, "errors": errors})
            except Exception as e:
                logger.error(f"Failed to load {table_def['table']}: {e}")
                results["failed"].append(table_def["table"])

        conn.commit()
        logger.info(f"Load complete — {len(results['loaded'])} tables loaded, {len(results['failed'])} failed")

        if results["failed"]:
            raise RuntimeError(f"Failed tables: {results['failed']}")

        return results

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    result = load()
    logger.info(f"Result: {result}")
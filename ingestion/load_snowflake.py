import os
import boto3
import snowflake.connector
from pathlib import Path
from datetime import datetime, timezone
from loguru import logger
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization

load_dotenv()

BUCKET = os.getenv("S3_BUCKET", "retaillens-raw")
REGION = os.getenv("AWS_REGION", "us-east-1")

def load_private_key():
    with open(os.path.expanduser("~/.ssh/snowflake_key.pem"), "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

SNOWFLAKE_CONFIG = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "private_key": load_private_key(),
    "database": os.getenv("SNOWFLAKE_DATABASE", "RETAILLENS_DB"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    "schema": "RAW",
}

TABLES = [
    {
        "table": "OLIST_ORDERS",
        "s3_prefix": "olist_orders",
        "filename": "olist_orders_dataset.csv",
    },
    {
        "table": "OLIST_ORDER_ITEMS",
        "s3_prefix": "olist_order_items",
        "filename": "olist_order_items_dataset.csv",
    },
    {
        "table": "OLIST_CUSTOMERS",
        "s3_prefix": "olist_customers",
        "filename": "olist_customers_dataset.csv",
    },
    {
        "table": "OLIST_PRODUCTS",
        "s3_prefix": "olist_products",
        "filename": "olist_products_dataset.csv",
    },
    {
        "table": "OLIST_SELLERS",
        "s3_prefix": "olist_sellers",
        "filename": "olist_sellers_dataset.csv",
    },
    {
        "table": "OLIST_ORDER_PAYMENTS",
        "s3_prefix": "olist_order_payments",
        "filename": "olist_order_payments_dataset.csv",
    },
    {
        "table": "OLIST_ORDER_REVIEWS",
        "s3_prefix": "olist_order_reviews",
        "filename": "olist_order_reviews_dataset.csv",
    },
    {
        "table": "OLIST_GEOLOCATION",
        "s3_prefix": "olist_geolocation",
        "filename": "olist_geolocation_dataset.csv",
    },
    {
        "table": "PRODUCT_CATEGORY_TRANSLATION",
        "s3_prefix": "product_category_translation",
        "filename": "product_category_name_translation.csv",
    },
]


def get_latest_s3_key(s3_client, prefix: str, filename: str) -> str:
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=BUCKET, Prefix=prefix)
    keys = []
    for page in pages:
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(filename):
                keys.append(obj["Key"])
    if not keys:
        raise FileNotFoundError(f"No files found at s3://{BUCKET}/{prefix}/")
    return sorted(keys)[-1]


def create_stage(cursor, stage_name: str):
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
    logger.info(f"Stage {stage_name} created")


def load_table(cursor, table_name: str, s3_key: str, stage_name: str):
    cursor.execute(f"TRUNCATE TABLE IF EXISTS RETAILLENS_DB.RAW.{table_name};")
    copy_sql = f"""
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
    """
    cursor.execute(copy_sql)
    results = cursor.fetchall()
    rows_loaded = sum(r[3] for r in results) if results else 0
    errors = sum(r[4] for r in results) if results else 0
    logger.info(f"Loaded {table_name}: {rows_loaded} rows, {errors} errors")
    return rows_loaded, errors


def create_raw_tables(cursor):
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
    logger.info("All RAW tables created")


def load(ingestion_date: str = None) -> dict:
    if ingestion_date is None:
        ingestion_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    logger.info(f"Starting Snowflake load — date: {ingestion_date}")

    s3 = boto3.client("s3", region_name=REGION)
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cursor = conn.cursor()

    try:
        create_raw_tables(cursor)
        stage_name = "RETAILLENS_DB.RAW.RETAILLENS_S3_STAGE"
        create_stage(cursor, stage_name)

        results = {"loaded": [], "failed": [], "ingestion_date": ingestion_date}

        for table_def in TABLES:
            try:
                s3_key = get_latest_s3_key(
                    s3, table_def["s3_prefix"], table_def["filename"]
                )
                rows, errors = load_table(
                    cursor, table_def["table"], s3_key, stage_name
                )
                results["loaded"].append({
                    "table": table_def["table"],
                    "rows": rows,
                    "errors": errors,
                })
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

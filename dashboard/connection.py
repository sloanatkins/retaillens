"""
Snowflake Connection
====================

Handles connecting to Snowflake and running queries for the dashboard.

Uses RSA key-pair auth instead of a password because the Snowflake trial
account has MFA enforced account-wide, which blocks password auth for
service users. The private key lives at ~/.ssh/snowflake_key.pem.

Dependencies:
- snowflake-connector-python[pandas]
- cryptography
- python-dotenv
"""

import os

import pandas as pd
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

load_dotenv()


def load_private_key() -> bytes:
    """
    Read the RSA private key and return it as DER bytes for the connector.

    Snowflake's Python connector expects the key in DER format, not PEM,
    so we load it with cryptography and convert before passing it in.
    """
    key_path = os.path.expanduser("/Users/sloanatkins/.ssh/snowflake_key.pem")
    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_connection() -> snowflake.connector.SnowflakeConnection:
    """Open a new Snowflake connection using the service user and RSA key."""
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT", "aviqhrs-ms03292"),
        user=os.getenv("SNOWFLAKE_USER", "RETAILLENS_SVC"),
        private_key=load_private_key(),
        database=os.getenv("SNOWFLAKE_DATABASE", "RETAILLENS_DB"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        schema="RAW_MART",
    )


def run_query(sql: str) -> pd.DataFrame:
    """
    Run a SQL query and return the results as a DataFrame.

    Opens a new connection for each call. Fine for a dashboard this size
    since queries are infrequent and connection setup is fast.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        return cursor.fetch_pandas_all()
    finally:
        conn.close()
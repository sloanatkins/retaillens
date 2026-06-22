import os
import snowflake.connector
import pandas as pd
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

load_dotenv()

def load_private_key():
    with open(os.path.expanduser("/Users/sloanatkins/.ssh/snowflake_key.pem"), "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

def get_connection():
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
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        df = cursor.fetch_pandas_all()
        return df
    finally:
        conn.close()

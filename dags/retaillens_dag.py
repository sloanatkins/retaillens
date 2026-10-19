"""
RetailLens DAG
==============

Runs the full ELT pipeline once a day at 6 AM:
1. Download the Olist CSVs from Kaggle
2. Upload them to S3 (date-partitioned)
3. Validate the raw files before touching Snowflake
4. COPY INTO the raw Snowflake tables
5. dbt staging → intermediate → mart
6. dbt test (all 53 tests)

Each step is a BashOperator so the pipeline scripts run exactly the
same way locally and in Airflow — no special Airflow dependencies needed.

Dependencies:
- apache-airflow
- the ingestion scripts and dbt project in the repo root
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# ── Paths ─────────────────────────────────────────────────────────────
# PROJECT_DIR points one level up from the dags/ folder, which is the repo root
PROJECT_DIR = "/usr/local/airflow/dags/../"
DBT_DIR = f"{PROJECT_DIR}retaillens_dbt"

# ── Default args ──────────────────────────────────────────────────────
default_args = {
    "owner": "retaillens",
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
    "email_on_failure": False,
}

with DAG(
    dag_id="retaillens_dag",
    default_args=default_args,
    description="RetailLens ELT pipeline — ingest, validate, load, transform",
    schedule="0 6 * * *",  # daily at 6 AM
    start_date=datetime(2026, 6, 1),
    catchup=False,
    tags=["retaillens", "elt", "snowflake"],
) as dag:

    # ── Ingestion ──────────────────────────────────────────────────────
    download_raw = BashOperator(
        task_id="download_raw",
        bash_command=f"cd {PROJECT_DIR} && python ingestion/download.py",
    )

    upload_to_s3 = BashOperator(
        task_id="upload_to_s3",
        bash_command=f"cd {PROJECT_DIR} && python ingestion/upload_s3.py",
    )

    validate_data = BashOperator(
        task_id="validate_data",
        bash_command=f"cd {PROJECT_DIR} && python ingestion/validate.py",
    )

    load_to_snowflake = BashOperator(
        task_id="load_to_snowflake",
        bash_command=f"cd {PROJECT_DIR} && python ingestion/load_snowflake.py",
    )

    # ── dbt transforms ─────────────────────────────────────────────────
    # Run each layer separately so a failure in staging doesn't waste time
    # trying to build intermediate models on top of broken data
    dbt_staging = BashOperator(
        task_id="dbt_staging",
        bash_command=f"cd {DBT_DIR} && dbt run --select staging",
    )

    dbt_intermediate = BashOperator(
        task_id="dbt_intermediate",
        bash_command=f"cd {DBT_DIR} && dbt run --select intermediate",
    )

    dbt_mart = BashOperator(
        task_id="dbt_mart",
        bash_command=f"cd {DBT_DIR} && dbt run --select mart",
    )

    # Run all tests after every layer is built, not just the last one
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test",
    )

    # ── Pipeline order ─────────────────────────────────────────────────
    (
        download_raw
        >> upload_to_s3
        >> validate_data
        >> load_to_snowflake
        >> dbt_staging
        >> dbt_intermediate
        >> dbt_mart
        >> dbt_test
    )
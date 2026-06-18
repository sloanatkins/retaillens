from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/usr/local/airflow/dags/../"
DBT_DIR = f"{PROJECT_DIR}retaillens_dbt"

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
    schedule="0 6 * * *",
    start_date=datetime(2026, 6, 1),
    catchup=False,
    tags=["retaillens", "elt", "snowflake"],
) as dag:

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

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test",
    )

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

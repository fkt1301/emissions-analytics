from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import subprocess, sys

default_args = {
    "owner": "olivier",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="emissions_analytics_pipeline",
    default_args=default_args,
    description="Ingest OWID + Eurostat → BQ → dbt transformations",
    schedule_interval="0 6 * * *",   # daily at 6am
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["emissions-analytics", "dbt", "bigquery"],
) as dag:

    def ingest_owid():
        """Load OWID CO2 data into BigQuery raw dataset"""
        sys.path.insert(0, "/opt/airflow/ingestion")
        from owid_to_bq import run
        run()

    ingest = PythonOperator(
        task_id="ingest_owid_to_bq",
        python_callable=ingest_owid,
    )

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command="cd /opt/airflow/dbt && dbt deps",
    )

    dbt_run_staging = BashOperator(
        task_id="dbt_run_staging",
        #bash_command="cd /opt/airflow/dbt && dbt run --select staging",
        bash_command="cd /opt/airflow/dbt && dbt run --select staging --profiles-dir /opt/airflow/dbt",
    )

    dbt_run_marts = BashOperator(
        task_id="dbt_run_marts",
        # bash_command="cd /opt/airflow/dbt && dbt run --select intermediate+ marts",
        bash_command="cd /opt/airflow/dbt && dbt run --select intermediate+ marts --profiles-dir /opt/airflow/dbt",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        # bash_command="cd /opt/airflow/dbt && dbt test",
        bash_command="cd /opt/airflow/dbt && dbt test --profiles-dir /opt/airflow/dbt",
    )

    dbt_docs = BashOperator(
        task_id="dbt_generate_docs",
        bash_command="cd /opt/airflow/dbt && dbt docs generate",
    )

    # DAG dependency chain
    ingest >> dbt_deps >> dbt_run_staging >> dbt_run_marts >> dbt_test >> dbt_docs

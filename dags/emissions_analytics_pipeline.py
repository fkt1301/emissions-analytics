from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "olivier",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="emissions_analytics_pipeline",
    default_args=default_args,
    description="Ingest OWID CO2 + World Bank → BigQuery → dbt transformations",
    schedule_interval="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["emissions-analytics", "dbt", "bigquery"],
) as dag:

    def ingest_owid():
        import sys
        sys.path.insert(0, "/opt/airflow/ingestion")
        from owid_to_bq import run
        run()

    def ingest_worldbank():
        import sys
        sys.path.insert(0, "/opt/airflow/ingestion")
        from worldbank_to_bq import run
        run()

    ingest_owid_task = PythonOperator(
        task_id="ingest_owid_to_bq",
        python_callable=ingest_owid,
        retries=2,
        retry_delay=timedelta(minutes=5),
    )

    ingest_worldbank_task = PythonOperator(
        task_id="ingest_worldbank_to_bq",
        python_callable=ingest_worldbank,
        retries=5,                          # flaky API needs more retries
        retry_delay=timedelta(minutes=2),
    )

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command="cd /opt/airflow/dbt && dbt deps --profiles-dir /opt/airflow/dbt",
    )

    dbt_run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command="cd /opt/airflow/dbt && dbt run --select staging --profiles-dir /opt/airflow/dbt",
    )

    dbt_test_staging = BashOperator(
        task_id="dbt_test_staging",
        bash_command="cd /opt/airflow/dbt && dbt test --select staging --profiles-dir /opt/airflow/dbt",
    )

    dbt_run_intermediate = BashOperator(
        task_id="dbt_run_intermediate",
        bash_command="cd /opt/airflow/dbt && dbt run --select intermediate --profiles-dir /opt/airflow/dbt",
    )

    dbt_test_intermediate = BashOperator(
        task_id="dbt_test_intermediate",
        bash_command="cd /opt/airflow/dbt && dbt test --select intermediate --profiles-dir /opt/airflow/dbt",
    )

    dbt_run_marts = BashOperator(
        task_id="dbt_run_marts",
        bash_command="cd /opt/airflow/dbt && dbt run --select marts --profiles-dir /opt/airflow/dbt",
    )

    dbt_test_marts = BashOperator(
        task_id="dbt_test_marts",
        bash_command="cd /opt/airflow/dbt && dbt test --select marts --profiles-dir /opt/airflow/dbt",
    )

    dbt_docs = BashOperator(
        task_id="dbt_generate_docs",
        bash_command="cd /opt/airflow/dbt && dbt docs generate --profiles-dir /opt/airflow/dbt",
    )

    # both ingestions run in parallel, then dbt pipeline starts
    [ingest_owid_task, ingest_worldbank_task] >> dbt_deps >> dbt_run_staging >> dbt_test_staging >> dbt_run_intermediate >> dbt_test_intermediate >> dbt_run_marts >> dbt_test_marts >> dbt_docs

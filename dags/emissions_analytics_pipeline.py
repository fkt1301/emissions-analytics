from datetime import datetime, timedelta
from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "olivier",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# set dbt_target variable in Airflow UI (Admin → Variables)
# dev = dev_staging, dev_intermediate, dev_marts
# prod = staging, intermediate, marts
DBT_TARGET = Variable.get("dbt_target", default_var="prod")
DBT_BASE = f"cd /opt/airflow/dbt && dbt --target {DBT_TARGET} --profiles-dir /opt/airflow/dbt"

with DAG(
    dag_id="emissions_analytics_pipeline",
    default_args=default_args,
    description="Ingest OWID CO2 + World Bank → BigQuery → dbt transformations",
    schedule_interval="0 6 * * *",
    start_date=datetime(2026, 1, 1),
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
        retries=5,
        retry_delay=timedelta(minutes=2),
    )

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command="cd /opt/airflow/dbt && dbt deps --profiles-dir /opt/airflow/dbt",
    )

    dbt_run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=f"{DBT_BASE} run --select staging",
    )

    dbt_test_staging = BashOperator(
        task_id="dbt_test_staging",
        bash_command=f"{DBT_BASE} test --select staging",
    )

    dbt_run_intermediate = BashOperator(
        task_id="dbt_run_intermediate",
        bash_command=f"{DBT_BASE} run --select intermediate",
    )

    dbt_test_intermediate = BashOperator(
        task_id="dbt_test_intermediate",
        bash_command=f"{DBT_BASE} test --select intermediate",
    )

    dbt_run_marts = BashOperator(
        task_id="dbt_run_marts",
        bash_command=f"{DBT_BASE} run --select marts",
    )

    dbt_test_marts = BashOperator(
        task_id="dbt_test_marts",
        bash_command=f"{DBT_BASE} test --select marts",
    )

    dbt_docs = BashOperator(
        task_id="dbt_generate_docs",
        bash_command=f"{DBT_BASE} docs generate",
    )

    (
        [ingest_owid_task, ingest_worldbank_task]
        >> dbt_deps
        >> dbt_run_staging
        >> dbt_test_staging
        >> dbt_run_intermediate
        >> dbt_test_intermediate
        >> dbt_run_marts
        >> dbt_test_marts
        >> dbt_docs
    )

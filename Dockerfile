FROM apache/airflow:2.8.1-python3.11

USER root
RUN apt-get update && apt-get install -y git && apt-get clean

USER airflow

# Install uv
RUN pip install uv

# Copy dependency files first (Docker layer caching — only reinstalls if these change)
COPY pyproject.toml uv.lock ./

# Install from pyproject.toml, into the system env (not a virtualenv)
RUN uv pip install --system -r pyproject.toml

# Copy dbt project
COPY dbt/ /opt/airflow/dbt/

FROM apache/airflow:2.8.1-python3.11

# Copy uv binary directly from official image
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

# uv env vars recommended for Docker
ENV UV_NO_PROGRESS=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_SYSTEM_PYTHON=1

# Add venv to PATH so dbt and other tools are found automatically
ENV PATH="/opt/airflow/.venv/bin:$PATH"

USER root
RUN apt-get update && apt-get install -y git && apt-get clean

# Copy dependency files first (cached layer — only rebuilds if deps change)
COPY pyproject.toml uv.lock ./

# Install deps from lockfile into the airflow venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

USER airflow

# Copy dbt project
COPY --chown=airflow:root dbt/ /opt/airflow/dbt/

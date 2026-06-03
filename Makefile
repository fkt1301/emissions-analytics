.PHONY: help install up down restart build logs \
        dbt-run dbt-test dbt-freshness dbt-docs \
        dbt-run-prod dbt-test-prod \
        ingest-owid ingest-worldbank \
        ci clean

# load local env vars
ifneq (,$(wildcard .env.local))
    include .env.local
    export
endif

DBT_LOCAL = cd dbt && ../.venv/bin/dbt --profiles-dir .
DBT_DOCKER = docker compose exec airflow-scheduler bash -c "cd /opt/airflow/dbt && dbt --profiles-dir /opt/airflow/dbt"

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | \
		sed 's/:.*## /|/' | \
		awk -F'|' '{printf "%-20s %s\n", $$1, $$2}'

# ── Infrastructure ────────────────────────────────────────────────────────────

install: ## install python dependencies locally
	uv sync

up: ## start all docker services
	docker compose up -d

down: ## stop all docker services
	docker compose down

restart: ## restart all docker services
	docker compose down && docker compose up -d

build: ## rebuild and start all docker services
	docker compose up --build -d

logs: ## tail airflow logs
	docker compose logs -f airflow-scheduler

# ── Local dbt (Mac) ───────────────────────────────────────────────────────────

dbt-deps: ## install dbt packages locally
	$(DBT_LOCAL) deps

dbt-run: ## run all dbt models locally (dev)
	$(DBT_LOCAL) run

dbt-test: ## test all dbt models locally (dev)
	$(DBT_LOCAL) test

dbt-freshness: ## check source freshness locally
	$(DBT_LOCAL) source freshness

dbt-docs: ## generate and serve dbt docs locally
	$(DBT_LOCAL) docs generate && $(DBT_LOCAL) docs serve --port 8081

dbt-run-select: ## run specific model locally e.g. make dbt-run-select SELECT=staging
	$(DBT_LOCAL) run --select $(SELECT)

# ── Docker dbt ────────────────────────────────────────────────────────────────

docker-deps: ## install dbt packages in container
	$(DBT_DOCKER) deps

docker-run: ## run all dbt models in container (dev)
	$(DBT_DOCKER) run --target dev

docker-test: ## test all dbt models in container (dev)
	$(DBT_DOCKER) test --target dev

docker-run-prod: ## run all dbt models in container (prod) — use with caution
	$(DBT_DOCKER) run --target prod

docker-test-prod: ## test all dbt models in container (prod)
	$(DBT_DOCKER) test --target prod

# ── Ingestion ─────────────────────────────────────────────────────────────────

ingest-owid: ## run OWID ingestion in container
	docker compose exec airflow-scheduler bash -c "cd /opt/airflow && python ingestion/owid_to_bq.py"

ingest-worldbank: ## run World Bank ingestion in container
	docker compose exec airflow-scheduler bash -c "cd /opt/airflow && python ingestion/worldbank_to_bq.py"

ingest-all: ingest-owid ingest-worldbank ## run all ingestions in container

# ── Full pipeline ─────────────────────────────────────────────────────────────

pipeline-dev: ingest-all docker-deps docker-run docker-test ## run full pipeline in dev
pipeline-prod: ingest-all docker-deps docker-run-prod docker-test-prod ## run full pipeline in prod — use with caution

# ── CI ────────────────────────────────────────────────────────────────────────

ci: install dbt-deps dbt-run dbt-test ## run full CI checks locally before pushing

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean: ## remove dbt artifacts
	rm -rf dbt/target/ dbt/dbt_packages/

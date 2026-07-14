# Emissions Analytics

![dbt CI](https://github.com/fkt1301/emissions-analytics/actions/workflows/dbt_ci.yml/badge.svg)

A modern data engineering pipeline for global CO2 emissions analysis, built with Apache Airflow, dbt, and BigQuery on Google Cloud Platform.

## Architecture

```
OWID CO2 Dataset (CSV)          World Bank API
        │                               │
        ▼                               ▼
  Python Ingestion              Python Ingestion
  (owid_to_bq.py)            (worldbank_to_bq.py)
        │                       incremental load
        │                               │
        ▼                               ▼
BigQuery — raw.owid_co2_raw    raw.worldbank_indicators_raw
        │                               │
        └───────────┬───────────────────┘
                    ▼
             dbt staging
      stg_owid__co2 (view)
      stg_worldbank__indicators (view)
                    │
                    ▼
          dbt intermediate
      int_countries__profile (view)   ← joins both sources
      int_co2__by_source (view)
                    │
                    ▼
              dbt marts
      fct_co2_emissions (table)
      fct_emissions_trend (table)
      fct_country_ranking (table)
      dim_country (table)
```

## Business Questions Answered

- Which countries are the highest CO2 emitters and how has that changed since 1990?
- What is the year-over-year emissions trend per country?
- How dependent is each country on fossil fuels?
- Which countries have the highest emissions per capita?
- What is the gap between production-based and consumption-based emissions per country?
- Which countries have the highest renewable energy share?
- How does electricity access correlate with emissions levels?
- How does urbanization relate to energy consumption per capita?

## Stack

| Layer | Tool |
|---|---|
| Orchestration | Apache Airflow 2.8 |
| Transformation | dbt 1.11 (dbt-bigquery) |
| Warehouse | Google BigQuery |
| Ingestion | Python + Pandas |
| Dependency management | uv |
| Infrastructure | Docker Compose |
| CI | GitHub Actions |

## Data Sources

| Source | Dataset | Granularity | Load strategy |
|---|---|---|---|
| [Our World in Data](https://github.com/owid/co2-data) | CO2 & energy by country | Country / year | Full refresh |
| [World Bank API](https://data.worldbank.org) | Energy & development indicators | Country / year | Incremental |

## dbt Packages

Declared in `dbt/packages.yml` and pinned in `dbt/package-lock.yml`:

| Package | Version | Used for |
|---|---|---|
| [dbt-labs/dbt_utils](https://github.com/dbt-labs/dbt-utils) | `>=1.1.0, <2.0.0` | Surrogate keys, `accepted_range` data tests |
| [metaplane/dbt_expectations](https://github.com/metaplane/dbt-expectations) | `>=0.10.0, <1.0.0` | Extended data quality tests |

Run `make dbt-deps` (local) or `make docker-deps` (container) to install them before compiling or running models.

## Project Structure

```
emissions-analytics/
├── dags/
│   └── emissions_analytics_pipeline.py   # Airflow DAG
├── dbt/
│   ├── models/
│   │   ├── staging/                      # 1-to-1 with sources, light cleaning
│   │   ├── intermediate/                 # business logic, joins
│   │   └── marts/                        # analyst-ready tables
│   ├── macros/
│   │   └── generate_schema_name.sql      # dev_ prefix on non-prod schemas
│   ├── packages.yml                      # dbt package dependencies
│   ├── package-lock.yml                  # pinned package versions (generated)
│   ├── profiles.yml                      # dev/prod BigQuery connection targets
│   └── dbt_project.yml
├── ingestion/
│   ├── owid_to_bq.py                     # OWID full refresh ingestion
│   └── worldbank_to_bq.py                # World Bank incremental ingestion
├── .github/
│   └── workflows/
│       └── dbt_ci.yml                    # CI pipeline
├── Dockerfile
├── docker-compose.yml
├── Makefile                              # local + containerized dbt/pipeline shortcuts
└── pyproject.toml
```

## dbt Lineage

![dbt lineage](docs/lineage.png)

## DAG

The pipeline runs daily at 6am. Both ingestions run in parallel before dbt starts:

```
ingest_owid_to_bq ──┐
                    ├──► dbt_deps ──► dbt_run_staging ──► dbt_test_staging
ingest_worldbank ───┘                      ──► dbt_run_intermediate ──► dbt_test_intermediate
                                                   ──► dbt_run_marts ──► dbt_test_marts
                                                               ──► dbt_generate_docs
```

## Getting Started

### Prerequisites

- Docker Desktop
- Google Cloud project with BigQuery enabled
- GCP service account with BigQuery Admin role
- [uv](https://docs.astral.sh/uv/) (for local Python/dbt dependency management)

### Setup

1. Clone the repo:
```bash
git clone https://github.com/fkt1301/emissions-analytics.git
cd emissions-analytics
```

2. Copy the example env file and fill in your values:
```bash
cp .env.example .env
```

3. Place your GCP service account key at `keys/gcp-keyfile.json`

4. Create BigQuery datasets:
```bash
bq mk --dataset --location=EU YOUR_PROJECT_ID:raw
bq mk --dataset --location=EU YOUR_PROJECT_ID:staging
bq mk --dataset --location=EU YOUR_PROJECT_ID:intermediate
bq mk --dataset --location=EU YOUR_PROJECT_ID:marts
```

5. Start the stack:
```bash
make up
```
(equivalent to `docker compose up -d`; use `make build` the first time or after Dockerfile changes)

6. Open Airflow at `http://localhost:8080` (admin/admin), trigger the DAG manually.

### Local dbt development

Local dbt runs use the `dev` profile target (schemas prefixed `dev_`), so they're safe to run against the same GCP project as prod.

```bash
# install Python deps into .venv (created by uv)
make install

# also export GCP_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS,
# e.g. via a .env.local file (auto-loaded by the Makefile)

make dbt-deps     # install dbt packages (dbt_utils, dbt_expectations)
make dbt-run      # run all models against dev_* schemas
make dbt-test     # run all tests
make dbt-freshness  # check source freshness
make dbt-docs     # generate + serve docs locally on :8081
```

Run a specific layer with:
```bash
make dbt-run-select SELECT=staging
```

### Running dbt inside the container

Once the stack is up (`make up`), you can run dbt against the Airflow container's environment instead of locally:

```bash
make docker-deps
make docker-run     # dev target
make docker-test    # dev target
make docker-run-prod   # prod target — use with caution, writes to prod schemas
make docker-test-prod
```

### Ingestion + full pipeline shortcuts

```bash
make ingest-owid        # run OWID ingestion once, ad hoc
make ingest-worldbank   # run World Bank ingestion once, ad hoc
make ingest-all         # both

make pipeline-dev       # ingest-all → docker-deps → docker-run → docker-test
make pipeline-prod      # same, but against prod schemas — use with caution
```

Run `make help` to see all available targets.

## Contributing

Pre-commit hooks (Ruff, sqlfluff for BigQuery SQL, trailing-whitespace/YAML/JSON checks) are configured in `.pre-commit-config.yaml`. Install them once with:

```bash
uv run pre-commit install
```

Before pushing, `make ci` mirrors what the GitHub Actions workflow checks: installs deps, installs dbt packages, compiles, and runs all dbt tests.

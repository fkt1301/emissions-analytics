# Emissions Analytics

![dbt CI](https://github.com/YOUR_USERNAME/emissions-analytics/actions/workflows/dbt_ci.yml/badge.svg)

A modern data engineering pipeline for global CO2 emissions analysis, built with Apache Airflow, dbt, and BigQuery on Google Cloud Platform.

## Architecture

```
OWID CO2 Dataset (CSV)
        │
        ▼
  Python Ingestion
  (owid_to_bq.py)x
        │
        ▼
BigQuery — raw.owid_co2_raw
        │
        ▼
   dbt staging
   stg_owid__co2 (view)
        │
        ▼
  dbt intermediate
  ├── int_countries__profile (view)
  └── int_co2__by_source (view)
        │
        ▼
    dbt marts
  ├── fct_co2_emissions (table)
  ├── fct_emissions_trend (table)
  ├── fct_country_ranking (table)
  └── dim_country (table)
```

## Business Questions Answered

- Which countries are the highest CO2 emitters and how has that changed since 1990?
- What is the year-over-year emissions trend per country?
- How dependent is each country on fossil fuels?
- Which countries have the highest emissions per capita?
- What is the gap between production-based and consumption-based emissions per country?

## Stack

| Layer | Tool |
|---|---|
| Orchestration | Apache Airflow 2.8 |
| Transformation | dbt 1.11 |
| Warehouse | Google BigQuery |
| Ingestion | Python + Pandas |
| Dependency management | uv |
| Infrastructure | Docker Compose |
| CI | GitHub Actions |

## Project Structure

```
emissions-analytics/
├── dags/                        # Airflow DAGs
│   └── emissions_analytics_pipeline.py
├── dbt/                         # dbt project
│   ├── models/
│   │   ├── staging/             # 1-to-1 with sources, light cleaning
│   │   ├── intermediate/        # business logic, joins
│   │   └── marts/               # analyst-ready tables
│   ├── macros/
│   ├── profiles.yml
│   └── dbt_project.yml
├── ingestion/                   # raw data loaders
│   └── owid_to_bq.py
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml               # dependencies managed by uv
```

## dbt Lineage

![dbt lineage](docs/lineage.png)

## Getting Started

### Prerequisites

- Docker Desktop
- Google Cloud project with BigQuery enabled
- GCP service account with BigQuery Admin role

### Setup

1. Clone the repo:
```bash
git clone https://github.com/YOUR_USERNAME/emissions-analytics.git
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
docker compose up --build -d
```

6. Open Airflow at `http://localhost:8080` (admin/admin), trigger the DAG manually.

## DAG

The pipeline runs daily at 6am and executes the following steps:

```
ingest_owid_to_bq
      │
   dbt_deps
      │
 dbt_run_staging → dbt_test_staging
                          │
              dbt_run_intermediate → dbt_test_intermediate
                                              │
                                      dbt_run_marts → dbt_test_marts
                                                              │
                                                    dbt_generate_docs
```

## Data Source

[Our World in Data — CO2 and Greenhouse Gas Emissions](https://github.com/owid/co2-data)

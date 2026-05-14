import os
import requests
import pandas as pd
from google.cloud import bigquery

OWID_CO2_URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET_RAW = os.environ.get("BQ_DATASET_RAW", "raw")
TABLE_NAME = "owid_co2_raw"


def extract() -> pd.DataFrame:
    """Download OWID CO2 dataset from GitHub"""
    print(f"Downloading OWID CO2 data from {OWID_CO2_URL}")
    response = requests.get(OWID_CO2_URL, timeout=30)
    response.raise_for_status()

    from io import StringIO
    df = pd.read_csv(StringIO(response.text))
    print(f"Downloaded {len(df)} rows, {len(df.columns)} columns")
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Light cleaning before landing in raw — keep it minimal"""
    # drop rows with no iso_code (regional aggregates like 'World', 'Asia', etc.)
    df = df[df["iso_code"].notna()].copy()

    # add ingestion timestamp so we know when each load ran
    df["_ingested_at"] = pd.Timestamp.now(tz="UTC")

    print(f"After filtering regional aggregates: {len(df)} rows")
    return df


def load(df: pd.DataFrame) -> None:
    """Write to BigQuery raw dataset, replacing the table each run"""
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET_RAW}.{TABLE_NAME}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # full refresh
        autodetect=True,  # let BQ infer schema from the dataframe
    )

    print(f"Loading to {table_id}")
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # wait for job to complete

    table = client.get_table(table_id)
    print(f"Loaded {table.num_rows} rows to {table_id}")


def run():
    df = extract()
    df = transform(df)
    load(df)


if __name__ == "__main__":
    run()

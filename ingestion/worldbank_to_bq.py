import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from google.cloud import bigquery
from datetime import datetime

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET_RAW = os.environ.get("BQ_DATASET_RAW", "raw")
TABLE_NAME = "worldbank_indicators_raw"

INDICATORS = {
    "EG.FEC.RNEW.ZS": "renewable_energy_pct",
    "EG.ELC.RNEW.ZS": "renewable_electricity_pct",
    "EG.USE.PCAP.KG.OE": "energy_use_per_capita_kgoe",
    "EG.ELC.ACCS.ZS": "electricity_access_pct",
    "SP.URB.TOTL.IN.ZS": "urban_population_pct",
}

BASE_URL = "https://api.worldbank.org/v2/country/all/indicator"


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def get_latest_year_in_bq() -> int:
    """Get the earliest of the per-country max years to ensure no country is skipped"""
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET_RAW}.{TABLE_NAME}"

    try:
        client.get_table(table_id)
    except Exception:
        print("Table doesn't exist yet — will do full load from 1990")
        return 1989

    query = f"""
        select min(max_year) as safe_start_year
        from (
            select country_code, max(year) as max_year
            from `{table_id}`
            group by country_code
        )
    """
    result = client.query(query).result()
    row = next(iter(result))
    safe_start_year = row.safe_start_year or 1989
    print(f"Earliest per-country max year: {safe_start_year}")
    return safe_start_year


def fetch_indicator(
    session: requests.Session,
    indicator_code: str,
    column_name: str,
    date_range: str,
) -> pd.DataFrame:
    """Fetch all countries for one indicator for the given date range"""
    print(f"Fetching {indicator_code} ({column_name}) for {date_range}")
    rows = []
    page = 1

    while True:
        try:
            r = session.get(
                f"{BASE_URL}/{indicator_code}",
                params={
                    "format": "json",
                    "per_page": 500,
                    "page": page,
                    "date": date_range,
                },
                timeout=120,
            )
            r.raise_for_status()
        except requests.exceptions.RetryError as e:
            print(f"  all retries exhausted on page {page}: {e}")
            raise

        data = r.json()

        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            print(f"  no data on page {page}, stopping")
            break

        meta = data[0]
        records = data[1]

        for record in records:
            if record["value"] is not None and record["countryiso3code"]:
                rows.append({
                    "country_code": record["countryiso3code"],
                    "country_name": record["country"]["value"],
                    "year": int(record["date"]),
                    column_name: record["value"],
                })

        print(f"  page {page}/{meta['pages']} — {len(rows)} rows so far")
        time.sleep(1)

        if page >= meta["pages"]:
            break
        page += 1

    print(f"  done — {len(rows)} rows for {column_name}")
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["country_code", "country_name", "year", column_name]
    )


def extract(date_range: str) -> pd.DataFrame:
    """Fetch all indicators for the given date range"""
    session = make_session()
    dfs = []

    for indicator_code, column_name in INDICATORS.items():
        df = fetch_indicator(session, indicator_code, column_name, date_range)
        dfs.append(df)
        time.sleep(3)

    # merge all indicators on country_code + year
    merged = dfs[0]
    for df in dfs[1:]:
        if df.empty:
            continue
        cols = ["country_code", "year"] + [
            c for c in df.columns
            if c not in ["country_code", "country_name", "year"]
        ]
        merged = merged.merge(df[cols], on=["country_code", "year"], how="outer")

    return merged


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Light cleaning"""
    df = df[df["country_code"].str.len() == 3].copy()
    df["_ingested_at"] = pd.Timestamp.now(tz="UTC")
    print(f"Total rows after transform: {len(df)}")
    return df


def load(df: pd.DataFrame, is_first_load: bool) -> None:
    """Append new rows to BigQuery"""
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET_RAW}.{TABLE_NAME}"

    write_disposition = (
        bigquery.WriteDisposition.WRITE_TRUNCATE if is_first_load
        else bigquery.WriteDisposition.WRITE_APPEND
    )

    job_config = bigquery.LoadJobConfig(
        write_disposition=write_disposition,
        autodetect=True,
    )

    print(f"Loading to {table_id} ({'full' if is_first_load else 'incremental'})")
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

    table = client.get_table(table_id)
    print(f"Table now has {table.num_rows} rows")


def run():
    current_year = datetime.now().year
    latest_year = get_latest_year_in_bq()
    is_first_load = latest_year == 1989

    if latest_year >= current_year - 1:
        print(f"Data already up to date (latest year: {latest_year}), skipping")
        return

    date_range = f"{latest_year + 1}:{current_year}"
    print(f"Fetching incremental data for {date_range}")

    df = extract(date_range)
    if df.empty:
        print("No new data to load")
        return

    df = transform(df)
    load(df, is_first_load=is_first_load)


if __name__ == "__main__":
    run()

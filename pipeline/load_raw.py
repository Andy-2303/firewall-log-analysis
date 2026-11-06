"""Step 1: load log2.csv into Postgres as a raw table."""
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("load_raw")

DB_URL = "postgresql+psycopg2://fw_user:fw_pass@localhost:5432/firewall"
CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "log2.csv"


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def main() -> None:
    log.info("Reading %s", CSV_PATH)
    df = clean_columns(pd.read_csv(CSV_PATH))
    log.info("Read %d rows, columns: %s", len(df), list(df.columns))

    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))

    # replace = safe to re-run: same input gives same table
    df.to_sql("firewall_sessions", engine, schema="raw",
              if_exists="replace", index=False, chunksize=10_000)

    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM raw.firewall_sessions")).scalar()
    log.info("raw.firewall_sessions now has %d rows", n)
    assert n == len(df), "Row count mismatch after load"


if __name__ == "__main__":
    main()

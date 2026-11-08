"""Step 2: build the staging and analytics layers from the raw table, then run data quality checks."""
import logging
from pathlib import Path

from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("transform")

DB_URL = "postgresql+psycopg2://fw_user:fw_pass@localhost:5432/firewall"
SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
SQL_FILES = ["02_staging.sql", "03_analytics.sql"]
VALID_ACTIONS = {"allow", "deny", "drop", "reset-both"}


def run_sql_files(engine) -> None:
    for name in SQL_FILES:
        sql = (SQL_DIR / name).read_text(encoding="utf-8")
        log.info("Running %s", name)
        with engine.begin() as conn:  # one transaction per file: all or nothing
            conn.exec_driver_sql(sql)


def scalar(engine, query: str):
    with engine.connect() as conn:
        return conn.execute(text(query)).scalar()


def run_quality_checks(engine) -> None:
    raw_n = scalar(engine, "SELECT COUNT(*) FROM raw.firewall_sessions")
    stg_n = scalar(engine, "SELECT COUNT(*) FROM staging.firewall_sessions")
    assert raw_n == stg_n, f"Row count changed: raw={raw_n}, staging={stg_n}"
    log.info("CHECK ok: staging has the same %d rows as raw", stg_n)

    nulls = scalar(engine, "SELECT COUNT(*) FROM staging.firewall_sessions WHERE destination_port IS NULL OR action IS NULL")
    assert nulls == 0, f"{nulls} rows have a null destination_port or action"
    log.info("CHECK ok: no null destination_port or action")

    with engine.connect() as conn:
        actions = {r[0] for r in conn.execute(text("SELECT DISTINCT action FROM staging.firewall_sessions"))}
    assert actions <= VALID_ACTIONS, f"Unexpected actions: {actions - VALID_ACTIONS}"
    log.info("CHECK ok: all actions are valid: %s", sorted(actions))

    neg = scalar(engine, "SELECT COUNT(*) FROM staging.firewall_sessions WHERE bytes < 0 OR packets < 0")
    assert neg == 0, f"{neg} rows have negative bytes or packets"
    log.info("CHECK ok: no negative bytes or packets")

    for table in ("action_summary", "block_rate_by_port", "outlier_sessions"):
        n = scalar(engine, f"SELECT COUNT(*) FROM analytics.{table}")
        assert n > 0, f"analytics.{table} is empty"
        log.info("analytics.%s has %d rows", table, n)


def main() -> None:
    engine = create_engine(DB_URL)
    run_sql_files(engine)
    run_quality_checks(engine)
    log.info("Transform finished successfully")


if __name__ == "__main__":
    main()

"""Runs validated queries as the read-only database user."""
from decimal import Decimal

from sqlalchemy import create_engine, text

from safe_sql import validate_and_wrap

READONLY_URL = "postgresql+psycopg2://assistant_ro:assistant_pw@localhost:5432/firewall"
_engine = create_engine(READONLY_URL)


def _plain(value):
    """Make values JSON-friendly (Postgres numeric comes back as Decimal)."""
    return float(value) if isinstance(value, Decimal) else value


def run_query(sql: str) -> dict:
    """Validate, run, and return {'sql', 'columns', 'rows'}. Raises UnsafeSQLError if rejected."""
    safe_sql = validate_and_wrap(sql)
    with _engine.connect() as conn:
        result = conn.execute(text(safe_sql))
        columns = list(result.keys())
        rows = [{c: _plain(v) for c, v in zip(columns, row)} for row in result.fetchall()]
    return {"sql": safe_sql, "columns": columns, "rows": rows}

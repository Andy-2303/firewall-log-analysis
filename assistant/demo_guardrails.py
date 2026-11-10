"""Shows the two layers of protection: the SQL validator, and the read-only database user."""
from sqlalchemy import text

from db import _engine, run_query
from safe_sql import UnsafeSQLError


def show(title: str, func) -> None:
    try:
        result = func()
        print(f"[ALLOWED ] {title}")
        if isinstance(result, dict):
            for row in result["rows"][:3]:
                print("           ", row)
    except UnsafeSQLError as e:
        print(f"[BLOCKED by validator] {title}: {e}")
    except Exception as e:
        first_line = str(e).splitlines()[0]
        print(f"[BLOCKED by database ] {title}: {first_line}")


if __name__ == "__main__":
    print("--- Layer 1: SQL validator ---")
    show("top ports by sessions",
         lambda: run_query("SELECT service_name, sessions FROM analytics.block_rate_by_port ORDER BY sessions DESC LIMIT 3"))
    show("DELETE statement", lambda: run_query("DELETE FROM analytics.action_summary"))
    show("two statements", lambda: run_query("SELECT 1; DROP TABLE analytics.action_summary"))
    show("raw schema", lambda: run_query("SELECT * FROM raw.firewall_sessions"))

    print()
    print("--- Layer 2: read-only database user (validator bypassed on purpose) ---")
    def direct(sql):
        def _run():
            with _engine.connect() as conn:
                conn.execute(text(sql))
        return _run
    show("read raw table directly", direct("SELECT * FROM raw.firewall_sessions LIMIT 1"))
    show("write to analytics directly", direct("DELETE FROM analytics.action_summary"))
    show("create a table directly", direct("CREATE TABLE analytics.hacked (x int)"))

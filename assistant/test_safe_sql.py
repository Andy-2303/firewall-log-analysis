"""Run with:  python -m pytest assistant"""
import pytest

from safe_sql import UnsafeSQLError, validate_and_wrap


def test_plain_select_is_allowed_and_row_capped():
    out = validate_and_wrap("SELECT * FROM analytics.action_summary;")
    assert out.startswith("SELECT * FROM (")
    assert out.endswith("LIMIT 100")


def test_cte_is_allowed():
    sql = "WITH t AS (SELECT * FROM analytics.block_rate_by_port) SELECT * FROM t"
    assert "LIMIT" in validate_and_wrap(sql)


def test_keyword_inside_a_string_literal_is_allowed():
    sql = "SELECT * FROM analytics.block_rate_by_port WHERE service_name = 'Set'"
    assert "LIMIT" in validate_and_wrap(sql)


def test_like_pattern_is_allowed():
    sql = "SELECT * FROM analytics.block_rate_by_port WHERE service_name LIKE 'HTTP%'"
    assert "LIMIT" in validate_and_wrap(sql)


@pytest.mark.parametrize("bad_sql", [
    "",
    "   ",
    "DELETE FROM analytics.action_summary",
    "DROP TABLE analytics.action_summary",
    "UPDATE analytics.action_summary SET sessions = 0",
    "INSERT INTO analytics.action_summary VALUES (1)",
    "SELECT 1; DROP TABLE analytics.action_summary",
    "SELECT * FROM analytics.action_summary -- hidden comment",
    "SELECT * FROM raw.firewall_sessions",
    "SELECT * FROM staging.firewall_sessions",
    "SELECT * FROM pg_catalog.pg_tables",
    "SELECT pg_sleep(10)",
    "SELECT * INTO new_table FROM analytics.action_summary",
    "EXPLAIN SELECT 1",
    'SELECT * FROM "raw"."firewall_sessions"',
    "CREATE TABLE x AS SELECT 1",
])
def test_unsafe_queries_are_rejected(bad_sql):
    with pytest.raises(UnsafeSQLError):
        validate_and_wrap(bad_sql)

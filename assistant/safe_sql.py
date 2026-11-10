"""Guardrails for SQL written by an LLM. Only a single read-only SELECT on the analytics schema gets through."""
import re

MAX_ROWS = 100

FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke",
    "copy", "call", "do", "execute", "vacuum", "analyze", "merge", "set", "reset",
    "listen", "notify", "lock", "comment", "refresh", "reindex", "cluster", "into",
]


class UnsafeSQLError(ValueError):
    """Raised when a query is not allowed to run."""


def _strip_literals(sql: str) -> str:
    """Replace 'text literals' with '' so keywords inside strings are not flagged."""
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def validate_and_wrap(sql: str, max_rows: int = MAX_ROWS) -> str:
    """Return a safe version of the query (row-capped), or raise UnsafeSQLError."""
    if not sql or not sql.strip():
        raise UnsafeSQLError("Empty query")

    text = sql.strip().rstrip(";").strip()

    if "--" in text or "/*" in text:
        raise UnsafeSQLError("Comments are not allowed")
    if '"' in text:
        raise UnsafeSQLError("Quoted identifiers are not allowed")

    bare = _strip_literals(text)
    lowered = bare.lower()

    if ";" in bare:
        raise UnsafeSQLError("Only one statement is allowed")
    if not re.match(r"^(select|with)\b", lowered):
        raise UnsafeSQLError("Only SELECT queries are allowed")

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise UnsafeSQLError(f"Keyword not allowed: {keyword.upper()}")

    if re.search(r"\b(pg_\w*|information_schema|current_setting|set_config)\b", lowered):
        raise UnsafeSQLError("System catalogs and settings are not allowed")
    if re.search(r"\b(raw|staging|public)\s*\.", lowered):
        raise UnsafeSQLError("Only the analytics schema may be queried")

    # Cap the number of rows no matter what the query asks for
    return f"SELECT * FROM ({text}) AS limited_result LIMIT {int(max_rows)}"

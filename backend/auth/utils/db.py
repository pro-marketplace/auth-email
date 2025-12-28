"""Database utilities."""
import os
import psycopg2
from typing import Any


_schema_cache: str | None = None


def get_connection():
    """Get database connection."""
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise ValueError('DATABASE_URL not configured')
    return psycopg2.connect(dsn)


def get_schema() -> str:
    """Get schema prefix for tables. Returns 'schema.' or empty string."""
    global _schema_cache

    if _schema_cache is not None:
        return _schema_cache

    conn = get_connection()
    cur = conn.cursor()

    # Get project schema (starts with t_, not system schemas)
    cur.execute("""
        SELECT schema_name FROM information_schema.schemata
        WHERE schema_name LIKE 't_%'
        ORDER BY schema_name
        LIMIT 1
    """)

    result = cur.fetchone()
    cur.close()
    conn.close()

    if result:
        _schema_cache = f"{result[0]}."
    else:
        _schema_cache = ""

    return _schema_cache


def escape(value: Any) -> str:
    """Escape value for SQL (simple protocol)."""
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, (int, float)):
        return str(value)
    # String - escape quotes
    s = str(value).replace("'", "''")
    return f"'{s}'"

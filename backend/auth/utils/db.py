"""Database utilities."""
import os
import psycopg2
from typing import Any


def get_connection():
    """Get database connection."""
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise ValueError('DATABASE_URL not configured')
    return psycopg2.connect(dsn)


def get_schema() -> str:
    """Get schema prefix for tables. Returns 'schema.' or empty string."""
    schema = os.environ.get('DB_SCHEMA', '')
    return f"{schema}." if schema else ""


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

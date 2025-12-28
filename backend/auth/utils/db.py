"""Database utilities."""
import os
import psycopg2
from typing import Any


def get_connection():
    """Get database connection with proper schema search_path."""
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise ValueError('DATABASE_URL not configured')

    conn = psycopg2.connect(dsn)

    # Set search_path to project schema if provided
    schema = os.environ.get('DB_SCHEMA')
    if schema:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {schema}")
        cur.close()

    return conn


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

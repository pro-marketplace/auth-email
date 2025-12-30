"""Database utilities for Simple Query Protocol."""
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
    """Get schema prefix from env. Returns 'schema.' or empty string."""
    schema = os.environ.get('MAIN_DB_SCHEMA', '')
    return f"{schema}." if schema else ""


def escape(value: Any) -> str:
    """Escape value for SQL (simple protocol)."""
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, (int, float)):
        return str(value)
    # String - escape single quotes
    s = str(value).replace("'", "''")
    return f"'{s}'"


def query(sql: str) -> list:
    """Execute SELECT query and return all rows."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def query_one(sql: str):
    """Execute SELECT query and return first row or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def execute(sql: str) -> None:
    """Execute INSERT/UPDATE/DELETE query."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()


def execute_returning(sql: str):
    """Execute INSERT with RETURNING and return first value."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return result[0] if result else None

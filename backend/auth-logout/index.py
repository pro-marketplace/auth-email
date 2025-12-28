"""
Auth Email Extension - Logout

Revokes refresh token.
Для Yandex Cloud Functions: токен передаётся через X-Refresh-Token header или body.
"""
import json
import os
import hashlib
import psycopg2
from typing import Optional


def get_db_connection():
    """Get database connection."""
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise ValueError('DATABASE_URL not configured')
    return psycopg2.connect(dsn)


def get_cors_origin() -> str:
    return os.environ.get('CORS_ORIGIN', '*')


def make_headers() -> dict:
    origin = get_cors_origin()
    return {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Refresh-Token',
        'Access-Control-Allow-Credentials': 'true' if origin != '*' else 'false',
        'Content-Type': 'application/json'
    }


def get_refresh_token(event: dict) -> Optional[str]:
    """
    Extract refresh token from:
    1. X-Refresh-Token header
    2. Request body { refresh_token: "..." }
    """
    headers = event.get('headers', {})

    token = (
        headers.get('X-Refresh-Token') or
        headers.get('x-refresh-token') or
        headers.get('X-REFRESH-TOKEN')
    )

    if token:
        return token

    body_str = event.get('body', '{}')
    try:
        payload = json.loads(body_str)
        return payload.get('refresh_token')
    except json.JSONDecodeError:
        return None


def handler(event: dict, context) -> dict:
    """
    Logout user by revoking refresh token.

    Token can be passed via:
    - X-Refresh-Token header
    - POST body { "refresh_token": "..." }
    """
    method = event.get('httpMethod', 'GET').upper()

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': make_headers(), 'body': '', 'isBase64Encoded': False}

    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': make_headers(),
            'body': json.dumps({'error': 'Method not allowed'}),
            'isBase64Encoded': False
        }

    refresh_token = get_refresh_token(event)

    if refresh_token:
        # Revoke token in DB
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM refresh_tokens WHERE token_hash = %s", (token_hash,))

        conn.commit()
        cur.close()
        conn.close()

    return {
        'statusCode': 200,
        'headers': make_headers(),
        'body': json.dumps({'message': 'Logged out successfully'}),
        'isBase64Encoded': False
    }

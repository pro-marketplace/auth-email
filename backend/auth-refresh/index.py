"""
Auth Email Extension - Refresh Token

Обновление access token с помощью refresh token.
Для Yandex Cloud Functions: токен передаётся через X-Refresh-Token header или body.
"""
import json
import os
import jwt
import hashlib
import psycopg2
from datetime import datetime, timedelta
from typing import Optional


JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '15'))


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
    1. X-Refresh-Token header (preferred for Yandex Cloud Functions)
    2. Request body { refresh_token: "..." }
    """
    headers = event.get('headers', {})

    # Try header first (case-insensitive)
    token = (
        headers.get('X-Refresh-Token') or
        headers.get('x-refresh-token') or
        headers.get('X-REFRESH-TOKEN')
    )

    if token:
        return token

    # Try body
    body_str = event.get('body', '{}')
    try:
        payload = json.loads(body_str)
        return payload.get('refresh_token')
    except json.JSONDecodeError:
        return None


def create_access_token(user_id: int, email: str) -> str:
    """Create short-lived JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        'sub': str(user_id),
        'email': email,
        'type': 'access',
        'exp': expire,
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def handler(event: dict, context) -> dict:
    """
    Refresh access token using refresh token.

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

    if not JWT_SECRET:
        return {
            'statusCode': 500,
            'headers': make_headers(),
            'body': json.dumps({'error': 'JWT_SECRET not configured'}),
            'isBase64Encoded': False
        }

    # Get refresh token
    refresh_token = get_refresh_token(event)

    if not refresh_token:
        return {
            'statusCode': 401,
            'headers': make_headers(),
            'body': json.dumps({'error': 'Refresh token not provided'}),
            'isBase64Encoded': False
        }

    # Verify JWT
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {
            'statusCode': 401,
            'headers': make_headers(),
            'body': json.dumps({'error': 'Refresh token expired'}),
            'isBase64Encoded': False
        }
    except jwt.InvalidTokenError:
        return {
            'statusCode': 401,
            'headers': make_headers(),
            'body': json.dumps({'error': 'Invalid refresh token'}),
            'isBase64Encoded': False
        }

    if payload.get('type') != 'refresh':
        return {
            'statusCode': 401,
            'headers': make_headers(),
            'body': json.dumps({'error': 'Invalid token type'}),
            'isBase64Encoded': False
        }

    user_id = int(payload.get('sub'))

    # Check token hash in DB (revocation check)
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT rt.id, u.email, u.name
        FROM refresh_tokens rt
        JOIN users u ON u.id = rt.user_id
        WHERE rt.token_hash = %s AND rt.user_id = %s AND rt.expires_at > %s
    """, (token_hash, user_id, datetime.utcnow()))

    result = cur.fetchone()

    if not result:
        cur.close()
        conn.close()
        return {
            'statusCode': 401,
            'headers': make_headers(),
            'body': json.dumps({'error': 'Refresh token revoked or expired'}),
            'isBase64Encoded': False
        }

    _, user_email, user_name = result

    cur.close()
    conn.close()

    # Issue new access token
    access_token = create_access_token(user_id, user_email)

    return {
        'statusCode': 200,
        'headers': make_headers(),
        'body': json.dumps({
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            'user': {
                'id': user_id,
                'email': user_email,
                'name': user_name
            }
        }),
        'isBase64Encoded': False
    }

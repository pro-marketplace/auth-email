"""
Auth Email Extension - Refresh Token

Обновление access token с помощью refresh token из HttpOnly cookie.
Читает cookie через X-Cookie (proxy mapping).
"""
import json
import os
import jwt
import hashlib
import psycopg2
from datetime import datetime, timedelta
from typing import Optional
from http.cookies import SimpleCookie


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
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Credentials': 'true',
        'Content-Type': 'application/json'
    }


def get_refresh_token_from_cookie(event: dict) -> Optional[str]:
    """
    Extract refresh_token from X-Cookie header.
    Proxy maps Cookie -> X-Cookie.
    """
    headers = event.get('headers', {})

    # Proxy maps Cookie -> X-Cookie
    cookie_header = (
        headers.get('X-Cookie') or
        headers.get('x-cookie') or
        ''
    )

    if not cookie_header:
        return None

    cookie = SimpleCookie()
    cookie.load(cookie_header)

    if 'refresh_token' in cookie:
        return cookie['refresh_token'].value

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
    Refresh access token using refresh token from HttpOnly cookie.

    Security:
    - Validates refresh token signature
    - Checks token hash in DB (for revocation support)
    - Issues new short-lived access token
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

    # Get refresh token from cookie
    refresh_token = get_refresh_token_from_cookie(event)

    if not refresh_token:
        return {
            'statusCode': 401,
            'headers': make_headers(),
            'body': json.dumps({'error': 'Refresh token not found'}),
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

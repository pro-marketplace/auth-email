"""
Auth Email Extension - Logout

Revokes refresh token and clears HttpOnly cookie.
Reads cookie via X-Cookie, clears via X-Set-Cookie (proxy mapping).
"""
import json
import os
import hashlib
import psycopg2
from datetime import datetime
from typing import Optional
from http.cookies import SimpleCookie


def get_db_connection():
    """Get database connection."""
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise ValueError('DATABASE_URL not configured')
    return psycopg2.connect(dsn)


def get_cors_origin() -> str:
    return os.environ.get('CORS_ORIGIN', '*')


def get_cookie_domain() -> str:
    """Get cookie domain from env."""
    return os.environ.get('COOKIE_DOMAIN', '')


def get_refresh_token_from_cookie(event: dict) -> Optional[str]:
    """Extract refresh_token from X-Cookie header."""
    headers = event.get('headers', {})

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


def make_clear_cookie() -> str:
    """Create cookie string that clears refresh_token."""
    secure = os.environ.get('COOKIE_SECURE', 'true').lower() == 'true'
    same_site = os.environ.get('COOKIE_SAMESITE', 'Strict')
    domain = get_cookie_domain()

    cookie_parts = [
        'refresh_token=',
        'Expires=Thu, 01 Jan 1970 00:00:00 GMT',
        'HttpOnly',
        'Path=/',
        f'SameSite={same_site}'
    ]

    if secure:
        cookie_parts.append('Secure')
    if domain:
        cookie_parts.append(f'Domain={domain}')

    return '; '.join(cookie_parts)


def make_headers(set_cookie: Optional[str] = None) -> dict:
    origin = get_cors_origin()
    headers = {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Credentials': 'true',
        'Content-Type': 'application/json'
    }
    if set_cookie:
        # Use X-Set-Cookie - proxy will convert to Set-Cookie
        headers['X-Set-Cookie'] = set_cookie
    return headers


def handler(event: dict, context) -> dict:
    """
    Logout user by revoking refresh token and clearing cookie.
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

    # Get refresh token from cookie
    refresh_token = get_refresh_token_from_cookie(event)

    if refresh_token:
        # Revoke token in DB
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM refresh_tokens WHERE token_hash = %s", (token_hash,))

        conn.commit()
        cur.close()
        conn.close()

    # Clear cookie via X-Set-Cookie
    clear_cookie = make_clear_cookie()

    return {
        'statusCode': 200,
        'headers': make_headers(set_cookie=clear_cookie),
        'body': json.dumps({'message': 'Logged out successfully'}),
        'isBase64Encoded': False
    }

"""
Auth Email Extension - User Login
"""
import json
import os
import hashlib
import secrets
import psycopg2
from datetime import datetime, timedelta


def hash_password(password: str, salt: str) -> str:
    """Hash password with salt using SHA-256."""
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def generate_session_token() -> str:
    """Generate secure session token."""
    return secrets.token_urlsafe(32)


def get_db_connection():
    """Get database connection."""
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise ValueError('DATABASE_URL not configured')
    return psycopg2.connect(dsn)


HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json'
}

# Session lifetime in days
SESSION_LIFETIME_DAYS = int(os.environ.get('SESSION_LIFETIME_DAYS', '30'))


def handler(event: dict, context) -> dict:
    """
    Authenticate user with email and password.
    POST body: email, password
    Returns: session_token, user (id, email, name), expires_at
    """
    method = event.get('httpMethod', 'GET').upper()

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': HEADERS, 'body': '', 'isBase64Encoded': False}

    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': HEADERS,
            'body': json.dumps({'error': 'Method not allowed'}),
            'isBase64Encoded': False
        }

    body_str = event.get('body', '{}')
    payload = json.loads(body_str)

    email = str(payload.get('email', '')).lower().strip()
    password = str(payload.get('password', ''))

    if not email or not password:
        return {
            'statusCode': 400,
            'headers': HEADERS,
            'body': json.dumps({'error': 'Email и пароль обязательны'}),
            'isBase64Encoded': False
        }

    conn = get_db_connection()
    cur = conn.cursor()

    # Find user
    cur.execute("""
        SELECT id, email, name, password_hash, salt
        FROM users
        WHERE email = %s
    """, (email,))

    user = cur.fetchone()

    if not user:
        cur.close()
        conn.close()
        return {
            'statusCode': 401,
            'headers': HEADERS,
            'body': json.dumps({'error': 'Неверный email или пароль'}),
            'isBase64Encoded': False
        }

    user_id, user_email, user_name, stored_hash, salt = user

    # Verify password
    password_hash = hash_password(password, salt)

    if password_hash != stored_hash:
        cur.close()
        conn.close()
        return {
            'statusCode': 401,
            'headers': HEADERS,
            'body': json.dumps({'error': 'Неверный email или пароль'}),
            'isBase64Encoded': False
        }

    # Create session
    session_token = generate_session_token()
    expires_at = datetime.utcnow() + timedelta(days=SESSION_LIFETIME_DAYS)

    cur.execute("""
        INSERT INTO sessions (user_id, token, expires_at, created_at)
        VALUES (%s, %s, %s, %s)
    """, (user_id, session_token, expires_at, datetime.utcnow()))

    # Update last login
    cur.execute("""
        UPDATE users SET last_login_at = %s WHERE id = %s
    """, (datetime.utcnow(), user_id))

    conn.commit()
    cur.close()
    conn.close()

    return {
        'statusCode': 200,
        'headers': HEADERS,
        'body': json.dumps({
            'session_token': session_token,
            'expires_at': expires_at.isoformat() + 'Z',
            'user': {
                'id': user_id,
                'email': user_email,
                'name': user_name
            }
        }),
        'isBase64Encoded': False
    }

"""
Auth Email Extension - Password Reset
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

RESET_TOKEN_LIFETIME_HOURS = 24


def handler(event: dict, context) -> dict:
    """
    Password reset flow:
    1. POST with email only -> generates reset token, returns token (for demo) or sends email
    2. POST with token + new_password -> resets password
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
    token = str(payload.get('token', '')).strip()
    new_password = str(payload.get('new_password', ''))

    conn = get_db_connection()
    cur = conn.cursor()

    # Step 1: Request password reset (email provided, no token)
    if email and not token:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if not user:
            # Don't reveal if user exists
            cur.close()
            conn.close()
            return {
                'statusCode': 200,
                'headers': HEADERS,
                'body': json.dumps({
                    'message': 'Если пользователь существует, ссылка для сброса пароля будет отправлена'
                }),
                'isBase64Encoded': False
            }

        user_id = user[0]

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=RESET_TOKEN_LIFETIME_HOURS)

        # Delete old tokens for this user
        cur.execute("DELETE FROM password_reset_tokens WHERE user_id = %s", (user_id,))

        # Create new token
        cur.execute("""
            INSERT INTO password_reset_tokens (user_id, token, expires_at, created_at)
            VALUES (%s, %s, %s, %s)
        """, (user_id, reset_token, expires_at, datetime.utcnow()))

        conn.commit()
        cur.close()
        conn.close()

        # In production: send email with reset link
        # For demo: return token directly
        return {
            'statusCode': 200,
            'headers': HEADERS,
            'body': json.dumps({
                'message': 'Ссылка для сброса пароля отправлена на email',
                'reset_token': reset_token,  # Remove in production!
                'expires_in_hours': RESET_TOKEN_LIFETIME_HOURS
            }),
            'isBase64Encoded': False
        }

    # Step 2: Reset password (token + new_password provided)
    if token and new_password:
        if len(new_password) < 8:
            cur.close()
            conn.close()
            return {
                'statusCode': 400,
                'headers': HEADERS,
                'body': json.dumps({'error': 'Пароль должен содержать минимум 8 символов'}),
                'isBase64Encoded': False
            }

        # Find valid token
        cur.execute("""
            SELECT user_id FROM password_reset_tokens
            WHERE token = %s AND expires_at > %s
        """, (token, datetime.utcnow()))

        token_record = cur.fetchone()

        if not token_record:
            cur.close()
            conn.close()
            return {
                'statusCode': 400,
                'headers': HEADERS,
                'body': json.dumps({'error': 'Недействительный или истёкший токен'}),
                'isBase64Encoded': False
            }

        user_id = token_record[0]

        # Update password
        salt = secrets.token_hex(16)
        password_hash = hash_password(new_password, salt)

        cur.execute("""
            UPDATE users SET password_hash = %s, salt = %s, updated_at = %s
            WHERE id = %s
        """, (password_hash, salt, datetime.utcnow(), user_id))

        # Delete used token
        cur.execute("DELETE FROM password_reset_tokens WHERE token = %s", (token,))

        # Invalidate all sessions for this user
        cur.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))

        conn.commit()
        cur.close()
        conn.close()

        return {
            'statusCode': 200,
            'headers': HEADERS,
            'body': json.dumps({'message': 'Пароль успешно изменён'}),
            'isBase64Encoded': False
        }

    cur.close()
    conn.close()

    return {
        'statusCode': 400,
        'headers': HEADERS,
        'body': json.dumps({'error': 'Укажите email или token с new_password'}),
        'isBase64Encoded': False
    }

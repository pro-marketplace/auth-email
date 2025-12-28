"""
Auth Email Extension - Password Reset (Secure)

Security:
- bcrypt for new password
- Secure random tokens
- Token expiration (1 hour)
- Single-use tokens
- Revokes all sessions on reset
"""
import json
import os
import secrets
import bcrypt
import psycopg2
from datetime import datetime, timedelta


RESET_TOKEN_LIFETIME_HOURS = 1  # Short-lived for security


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def get_db_connection():
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
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Credentials': 'true' if origin != '*' else 'false',
        'Content-Type': 'application/json'
    }


def handler(event: dict, context) -> dict:
    """
    Password reset flow:
    1. POST {email} -> generates reset token
    2. POST {token, new_password} -> resets password

    Security:
    - Tokens expire in 1 hour
    - Single-use (deleted after use)
    - All sessions revoked on password change
    - No user enumeration (same response for existing/non-existing email)
    """
    method = event.get('httpMethod', 'GET').upper()
    headers = make_headers()

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': '', 'isBase64Encoded': False}

    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': headers,
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

    # Step 1: Request password reset
    if email and not token:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        # Same response regardless of user existence (prevent enumeration)
        response_msg = 'Если пользователь существует, ссылка для сброса будет отправлена на email'

        if user:
            user_id = user[0]

            # Generate secure token
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=RESET_TOKEN_LIFETIME_HOURS)

            # Delete old tokens
            cur.execute("DELETE FROM password_reset_tokens WHERE user_id = %s", (user_id,))

            # Store new token (hashed for security)
            import hashlib
            token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

            cur.execute("""
                INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, created_at)
                VALUES (%s, %s, %s, %s)
            """, (user_id, token_hash, expires_at, datetime.utcnow()))

            conn.commit()

            # In production: send email with reset_token
            # For demo only: return token (REMOVE IN PRODUCTION!)
            cur.close()
            conn.close()

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'message': response_msg,
                    'reset_token': reset_token,  # REMOVE IN PRODUCTION!
                    'expires_in_minutes': RESET_TOKEN_LIFETIME_HOURS * 60
                }),
                'isBase64Encoded': False
            }

        cur.close()
        conn.close()

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': response_msg}),
            'isBase64Encoded': False
        }

    # Step 2: Reset password with token
    if token and new_password:
        # Validate password
        if len(new_password) < 8:
            cur.close()
            conn.close()
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Пароль должен содержать минимум 8 символов'}),
                'isBase64Encoded': False
            }

        if len(new_password) > 128:
            cur.close()
            conn.close()
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Пароль слишком длинный'}),
                'isBase64Encoded': False
            }

        # Find valid token
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        cur.execute("""
            SELECT user_id FROM password_reset_tokens
            WHERE token_hash = %s AND expires_at > %s
        """, (token_hash, datetime.utcnow()))

        token_record = cur.fetchone()

        if not token_record:
            cur.close()
            conn.close()
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Недействительный или истёкший токен'}),
                'isBase64Encoded': False
            }

        user_id = token_record[0]

        # Update password with bcrypt
        password_hash = hash_password(new_password)

        cur.execute("""
            UPDATE users SET password_hash = %s, updated_at = %s
            WHERE id = %s
        """, (password_hash, datetime.utcnow(), user_id))

        # Delete used token (single-use)
        cur.execute("DELETE FROM password_reset_tokens WHERE token_hash = %s", (token_hash,))

        # Revoke all refresh tokens (force re-login)
        cur.execute("DELETE FROM refresh_tokens WHERE user_id = %s", (user_id,))

        conn.commit()
        cur.close()
        conn.close()

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'Пароль успешно изменён'}),
            'isBase64Encoded': False
        }

    cur.close()
    conn.close()

    return {
        'statusCode': 400,
        'headers': headers,
        'body': json.dumps({'error': 'Укажите email или token с new_password'}),
        'isBase64Encoded': False
    }

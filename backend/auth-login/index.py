"""
Auth Email Extension - User Login (Secure)

Security features:
- JWT access + refresh tokens
- HttpOnly cookie for refresh token (via X-Set-Cookie proxy mapping)
- Rate limiting via failed_login_attempts
- bcrypt password verification
"""
import json
import os
import jwt
import bcrypt
import hashlib
import psycopg2
from datetime import datetime, timedelta
from typing import Optional


# ============================================================================
# CONFIG
# ============================================================================

JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '15'))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get('REFRESH_TOKEN_EXPIRE_DAYS', '30'))
MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5'))
LOCKOUT_MINUTES = int(os.environ.get('LOCKOUT_MINUTES', '15'))


def get_db_connection():
    """Get database connection."""
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise ValueError('DATABASE_URL not configured')
    return psycopg2.connect(dsn)


def get_cors_origin() -> str:
    """Get allowed CORS origin from env."""
    return os.environ.get('CORS_ORIGIN', '*')


def get_cookie_domain() -> str:
    """Get cookie domain from env."""
    return os.environ.get('COOKIE_DOMAIN', '')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


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


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    """Create long-lived JWT refresh token."""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        'sub': str(user_id),
        'type': 'refresh',
        'exp': expire,
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expire


def make_refresh_cookie(token: str, expires: datetime) -> str:
    """Create HttpOnly cookie string for refresh token."""
    secure = os.environ.get('COOKIE_SECURE', 'true').lower() == 'true'
    same_site = os.environ.get('COOKIE_SAMESITE', 'Strict')
    domain = get_cookie_domain()

    cookie_parts = [
        f'refresh_token={token}',
        f'Expires={expires.strftime("%a, %d %b %Y %H:%M:%S GMT")}',
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
    """Create response headers."""
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


def check_rate_limit(cur, email: str) -> tuple[bool, Optional[int]]:
    """Check if user is rate limited. Returns (is_allowed, remaining_seconds)."""
    cur.execute("""
        SELECT failed_login_attempts, last_failed_login_at
        FROM users WHERE email = %s
    """, (email,))

    result = cur.fetchone()
    if not result:
        return True, None

    attempts, last_failed = result

    if attempts and attempts >= MAX_LOGIN_ATTEMPTS and last_failed:
        lockout_until = last_failed + timedelta(minutes=LOCKOUT_MINUTES)
        if datetime.utcnow() < lockout_until:
            remaining = int((lockout_until - datetime.utcnow()).total_seconds())
            return False, remaining

    return True, None


def increment_failed_attempts(cur, conn, email: str):
    """Increment failed login attempts counter."""
    cur.execute("""
        UPDATE users
        SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1,
            last_failed_login_at = %s
        WHERE email = %s
    """, (datetime.utcnow(), email))
    conn.commit()


def reset_failed_attempts(cur, conn, user_id: int):
    """Reset failed login attempts on successful login."""
    cur.execute("""
        UPDATE users
        SET failed_login_attempts = 0,
            last_failed_login_at = NULL,
            last_login_at = %s
        WHERE id = %s
    """, (datetime.utcnow(), user_id))
    conn.commit()


def handler(event: dict, context) -> dict:
    """
    Authenticate user and issue JWT tokens.

    Security:
    - Rate limiting (5 attempts, 15 min lockout)
    - bcrypt password verification
    - Short-lived access token (15 min)
    - Long-lived refresh token in HttpOnly cookie (30 days)
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

    body_str = event.get('body', '{}')
    payload = json.loads(body_str)

    email = str(payload.get('email', '')).lower().strip()
    password = str(payload.get('password', ''))

    if not email or not password:
        return {
            'statusCode': 400,
            'headers': make_headers(),
            'body': json.dumps({'error': 'Email и пароль обязательны'}),
            'isBase64Encoded': False
        }

    conn = get_db_connection()
    cur = conn.cursor()

    # Check rate limit
    is_allowed, remaining = check_rate_limit(cur, email)
    if not is_allowed:
        cur.close()
        conn.close()
        return {
            'statusCode': 429,
            'headers': make_headers(),
            'body': json.dumps({
                'error': f'Слишком много попыток. Повторите через {remaining // 60 + 1} мин.'
            }),
            'isBase64Encoded': False
        }

    # Find user
    cur.execute("""
        SELECT id, email, name, password_hash
        FROM users WHERE email = %s
    """, (email,))

    user = cur.fetchone()

    # Generic error to prevent user enumeration
    auth_error = {'error': 'Неверный email или пароль'}

    if not user:
        cur.close()
        conn.close()
        return {
            'statusCode': 401,
            'headers': make_headers(),
            'body': json.dumps(auth_error),
            'isBase64Encoded': False
        }

    user_id, user_email, user_name, stored_hash = user

    # Verify password
    if not verify_password(password, stored_hash):
        increment_failed_attempts(cur, conn, email)
        cur.close()
        conn.close()
        return {
            'statusCode': 401,
            'headers': make_headers(),
            'body': json.dumps(auth_error),
            'isBase64Encoded': False
        }

    # Success - reset failed attempts
    reset_failed_attempts(cur, conn, user_id)

    # Create tokens
    access_token = create_access_token(user_id, user_email)
    refresh_token, refresh_expires = create_refresh_token(user_id)

    # Store refresh token hash in DB for revocation support
    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    cur.execute("""
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at)
        VALUES (%s, %s, %s, %s)
    """, (user_id, refresh_hash, refresh_expires, datetime.utcnow()))

    conn.commit()
    cur.close()
    conn.close()

    # Set refresh token as HttpOnly cookie via X-Set-Cookie
    cookie = make_refresh_cookie(refresh_token, refresh_expires)

    return {
        'statusCode': 200,
        'headers': make_headers(set_cookie=cookie),
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

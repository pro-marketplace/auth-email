"""Login handler."""
import json
import os
from datetime import datetime, timedelta

from utils.db import get_connection, escape, get_schema
from utils.password import verify_password
from utils.jwt_utils import create_access_token, create_refresh_token, hash_token, ACCESS_TOKEN_EXPIRE_MINUTES
from utils.cookies import make_refresh_cookie
from utils.http import response, error


MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5'))
LOCKOUT_MINUTES = int(os.environ.get('LOCKOUT_MINUTES', '15'))


def check_rate_limit(cur, email: str, S: str) -> tuple[bool, int | None]:
    """Check if user is rate limited. Returns (is_allowed, remaining_seconds)."""
    cur.execute(f"""
        SELECT failed_login_attempts, last_failed_login_at
        FROM {S}users WHERE email = {escape(email)}
    """)

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


def increment_failed_attempts(cur, conn, email: str, S: str):
    """Increment failed login attempts counter."""
    now = datetime.utcnow().isoformat()
    cur.execute(f"""
        UPDATE {S}users
        SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1,
            last_failed_login_at = {escape(now)}
        WHERE email = {escape(email)}
    """)
    conn.commit()


def reset_failed_attempts(cur, conn, user_id: int, S: str):
    """Reset failed login attempts on successful login."""
    now = datetime.utcnow().isoformat()
    cur.execute(f"""
        UPDATE {S}users
        SET failed_login_attempts = 0,
            last_failed_login_at = NULL,
            last_login_at = {escape(now)}
        WHERE id = {escape(user_id)}
    """)
    conn.commit()


def handle(event: dict) -> dict:
    """Authenticate user and issue JWT tokens."""
    jwt_secret = os.environ.get('JWT_SECRET')
    if not jwt_secret:
        return error(500, 'JWT_SECRET not configured')

    body_str = event.get('body', '{}')
    payload = json.loads(body_str)

    email = str(payload.get('email', '')).lower().strip()
    password = str(payload.get('password', ''))

    if not email or not password:
        return error(400, 'Email и пароль обязательны')

    S = get_schema()
    conn = get_connection()
    cur = conn.cursor()

    # Check rate limit
    is_allowed, remaining = check_rate_limit(cur, email, S)
    if not is_allowed:
        cur.close()
        conn.close()
        return error(429, f'Слишком много попыток. Повторите через {remaining // 60 + 1} мин.')

    # Find user
    cur.execute(f"""
        SELECT id, email, name, password_hash
        FROM {S}users WHERE email = {escape(email)}
    """)

    user = cur.fetchone()
    auth_error_msg = 'Неверный email или пароль'

    if not user:
        cur.close()
        conn.close()
        return error(401, auth_error_msg)

    user_id, user_email, user_name, stored_hash = user

    if not verify_password(password, stored_hash):
        increment_failed_attempts(cur, conn, email, S)
        cur.close()
        conn.close()
        return error(401, auth_error_msg)

    # Success
    reset_failed_attempts(cur, conn, user_id, S)

    access_token = create_access_token(user_id, user_email)
    refresh_token, refresh_expires = create_refresh_token(user_id)

    # Store refresh token hash
    refresh_hash = hash_token(refresh_token)
    now = datetime.utcnow().isoformat()
    expires_at = refresh_expires.isoformat()

    cur.execute(f"""
        INSERT INTO {S}refresh_tokens (user_id, token_hash, expires_at, created_at)
        VALUES ({escape(user_id)}, {escape(refresh_hash)}, {escape(expires_at)}, {escape(now)})
    """)

    conn.commit()
    cur.close()
    conn.close()

    cookie = make_refresh_cookie(refresh_token, refresh_expires)

    return response(200, {
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        'user': {
            'id': user_id,
            'email': user_email,
            'name': user_name
        }
    }, set_cookie=cookie)

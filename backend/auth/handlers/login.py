"""Login handler."""
import json
import os
from datetime import datetime, timedelta

from utils.db import query_one, execute, escape, get_schema
from utils.password import verify_password
from utils.jwt_utils import create_access_token, create_refresh_token, hash_token, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from utils.email import is_email_enabled
from utils.http import response, error


MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5'))
LOCKOUT_MINUTES = int(os.environ.get('LOCKOUT_MINUTES', '15'))


def handle(event: dict, origin: str = '*') -> dict:
    """Authenticate user and issue JWT tokens."""
    jwt_secret = os.environ.get('JWT_SECRET')
    if not jwt_secret:
        return error(500, 'JWT_SECRET not configured', origin)

    body_str = event.get('body', '{}')
    payload = json.loads(body_str)

    email = str(payload.get('email', '')).lower().strip()
    password = str(payload.get('password', ''))

    if not email or not password:
        return error(400, 'Email и пароль обязательны', origin)

    S = get_schema()

    rate_check = query_one(f"""
        SELECT failed_login_attempts, last_failed_login_at
        FROM {S}users WHERE email = {escape(email)}
    """)

    if rate_check:
        attempts, last_failed = rate_check
        if attempts and attempts >= MAX_LOGIN_ATTEMPTS and last_failed:
            lockout_until = last_failed + timedelta(minutes=LOCKOUT_MINUTES)
            if datetime.utcnow() < lockout_until:
                remaining = int((lockout_until - datetime.utcnow()).total_seconds())
                return error(429, f'Слишком много попыток. Повторите через {remaining // 60 + 1} мин.', origin)

    user = query_one(f"""
        SELECT id, email, name, password_hash, email_verified
        FROM {S}users WHERE email = {escape(email)}
    """)

    auth_error_msg = 'Неверный email или пароль'

    if not user:
        return error(401, auth_error_msg, origin)

    user_id, user_email, user_name, stored_hash, email_verified = user

    if not verify_password(password, stored_hash):
        now = datetime.utcnow().isoformat()
        execute(f"""
            UPDATE {S}users
            SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1,
                last_failed_login_at = {escape(now)}
            WHERE email = {escape(email)}
        """)
        return error(401, auth_error_msg, origin)

    # Check email verification if SMTP is configured
    if is_email_enabled() and not email_verified:
        return error(403, 'Email не подтверждён. Проверьте почту.', origin)

    now = datetime.utcnow().isoformat()
    execute(f"""
        UPDATE {S}users
        SET failed_login_attempts = 0,
            last_failed_login_at = NULL,
            last_login_at = {escape(now)}
        WHERE id = {escape(user_id)}
    """)

    access_token = create_access_token(user_id, user_email)
    refresh_token, refresh_expires = create_refresh_token(user_id)

    refresh_hash = hash_token(refresh_token)
    expires_at = refresh_expires.isoformat()

    execute(f"""
        INSERT INTO {S}refresh_tokens (user_id, token_hash, expires_at, created_at)
        VALUES ({escape(user_id)}, {escape(refresh_hash)}, {escape(expires_at)}, {escape(now)})
    """)

    return response(200, {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        'refresh_expires_in': REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        'user': {
            'id': user_id,
            'email': user_email,
            'name': user_name,
            'email_verified': email_verified
        }
    }, origin)

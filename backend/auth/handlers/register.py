"""Registration handler."""
import json
import os
import secrets
from datetime import datetime, timedelta

from utils.db import query_one, execute_returning, execute, escape, get_schema
from utils.password import hash_password, validate_password, validate_email
from utils.jwt_utils import hash_token
from utils.email import is_email_enabled, send_verification_email
from utils.http import response, error


VERIFICATION_TOKEN_HOURS = 24


def handle(event: dict, origin: str = '*') -> dict:
    """Register new user with email and password."""
    body_str = event.get('body', '{}')
    payload = json.loads(body_str)

    email = str(payload.get('email', '')).lower().strip()
    password = str(payload.get('password', ''))
    name = str(payload.get('name', '')).strip()[:255]

    if not email or not validate_email(email):
        return error(400, 'Некорректный email', origin)

    is_valid, error_msg = validate_password(password)
    if not is_valid:
        return error(400, error_msg, origin)

    S = get_schema()

    existing = query_one(f"SELECT id FROM {S}users WHERE email = {escape(email)}")
    if existing:
        return error(409, 'Пользователь с таким email уже существует', origin)

    password_hash = hash_password(password)
    now = datetime.utcnow().isoformat()

    # Check if email verification is enabled
    require_verification = is_email_enabled() and os.environ.get('REQUIRE_EMAIL_VERIFICATION', '').lower() == 'true'

    user_id = execute_returning(f"""
        INSERT INTO {S}users (email, password_hash, name, email_verified, created_at, updated_at)
        VALUES ({escape(email)}, {escape(password_hash)}, {escape(name or None)}, {escape(not require_verification)}, {escape(now)}, {escape(now)})
        RETURNING id
    """)

    result = {
        'user_id': user_id,
        'message': 'Регистрация успешна',
        'email_verification_required': require_verification
    }

    # Send verification email if enabled
    if require_verification:
        verification_token = secrets.token_urlsafe(32)
        token_hash = hash_token(verification_token)
        expires_at = (datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_HOURS)).isoformat()

        execute(f"""
            INSERT INTO {S}email_verification_tokens (user_id, token_hash, expires_at, created_at)
            VALUES ({escape(user_id)}, {escape(token_hash)}, {escape(expires_at)}, {escape(now)})
        """)

        # Get AUTH_URL from request or env for email link
        auth_url = os.environ.get('AUTH_URL', '')
        if auth_url:
            send_verification_email(email, verification_token, auth_url)
            result['message'] = 'Регистрация успешна. Проверьте почту для подтверждения.'
        else:
            # Return token in response if AUTH_URL not configured (for testing)
            result['verification_token'] = verification_token
            result['message'] = 'Регистрация успешна. Подтвердите email.'

    return response(201, result, origin)

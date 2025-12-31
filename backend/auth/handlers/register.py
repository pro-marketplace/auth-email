"""Registration handler."""
import json
from datetime import datetime, timedelta

from utils.db import query_one, execute_returning, execute, escape, get_schema
from utils.password import hash_password, verify_password, validate_password, validate_email
from utils.email import is_email_enabled, generate_code, send_verification_code
from utils.http import response, error


VERIFICATION_CODE_HOURS = 24


def _send_verification_code(user_id: int, email: str, S: str) -> dict:
    """Generate and send verification code, return result dict."""
    now = datetime.utcnow().isoformat()
    code = generate_code()
    expires_at = (datetime.utcnow() + timedelta(hours=VERIFICATION_CODE_HOURS)).isoformat()

    # Delete old codes
    execute(f"DELETE FROM {S}email_verification_tokens WHERE user_id = {escape(user_id)}")

    # Store new code
    execute(f"""
        INSERT INTO {S}email_verification_tokens (user_id, token_hash, expires_at, created_at)
        VALUES ({escape(user_id)}, {escape(code)}, {escape(expires_at)}, {escape(now)})
    """)

    if send_verification_code(email, code):
        return {'message': 'Код подтверждения отправлен на email', 'sent': True}
    return {'message': 'Не удалось отправить код', 'sent': False}


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
    email_enabled = is_email_enabled()

    # Check if user exists
    existing = query_one(f"SELECT id, email_verified, password_hash FROM {S}users WHERE email = {escape(email)}")

    if existing:
        user_id, email_verified, stored_hash = existing

        # If email verified - user already exists
        if email_verified:
            return error(409, 'Пользователь с таким email уже существует', origin)

        # Email not verified - verify password before resending code
        if not verify_password(password, stored_hash):
            return error(409, 'Пользователь с таким email уже существует', origin)

        # Password correct - resend code
        if email_enabled:
            send_result = _send_verification_code(user_id, email, S)
            return response(200, {
                'user_id': user_id,
                'message': send_result['message'],
                'email_verification_required': True,
                'resent': True
            }, origin)
        else:
            # No SMTP - mark as verified and let them login
            now = datetime.utcnow().isoformat()
            execute(f"UPDATE {S}users SET email_verified = TRUE, updated_at = {escape(now)} WHERE id = {escape(user_id)}")
            return response(200, {
                'user_id': user_id,
                'message': 'Регистрация успешна',
                'email_verification_required': False
            }, origin)

    # Create new user
    password_hash = hash_password(password)
    now = datetime.utcnow().isoformat()

    user_id = execute_returning(f"""
        INSERT INTO {S}users (email, password_hash, name, email_verified, created_at, updated_at)
        VALUES ({escape(email)}, {escape(password_hash)}, {escape(name or None)}, {escape(not email_enabled)}, {escape(now)}, {escape(now)})
        RETURNING id
    """)

    result = {
        'user_id': user_id,
        'message': 'Регистрация успешна',
        'email_verification_required': email_enabled
    }

    # Send verification code if SMTP configured
    if email_enabled:
        send_result = _send_verification_code(user_id, email, S)
        result['message'] = send_result['message']

    return response(201, result, origin)

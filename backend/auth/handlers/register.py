"""Registration handler."""
import json
from datetime import datetime, timedelta

from utils.db import query_one, execute_returning, execute, escape, get_schema
from utils.password import hash_password, validate_password, validate_email
from utils.email import is_email_enabled, generate_code, send_verification_code
from utils.http import response, error


VERIFICATION_CODE_HOURS = 24


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

    # If SMTP configured -> require email verification
    email_enabled = is_email_enabled()

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
        code = generate_code()
        expires_at = (datetime.utcnow() + timedelta(hours=VERIFICATION_CODE_HOURS)).isoformat()

        # Store code (hashed for security? no, it's just 6 digits, store plain for simplicity)
        execute(f"""
            INSERT INTO {S}email_verification_tokens (user_id, token_hash, expires_at, created_at)
            VALUES ({escape(user_id)}, {escape(code)}, {escape(expires_at)}, {escape(now)})
        """)

        if send_verification_code(email, code):
            result['message'] = 'Код подтверждения отправлен на email'
        else:
            result['message'] = 'Регистрация успешна, но не удалось отправить код'

    return response(201, result, origin)

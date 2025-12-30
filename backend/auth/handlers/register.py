"""Registration handler."""
import json
from datetime import datetime

from ..utils.db import query_one, execute_returning, escape, get_schema
from ..utils.password import hash_password, validate_password, validate_email
from ..utils.http import response, error


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

    user_id = execute_returning(f"""
        INSERT INTO {S}users (email, password_hash, name, created_at, updated_at)
        VALUES ({escape(email)}, {escape(password_hash)}, {escape(name or None)}, {escape(now)}, {escape(now)})
        RETURNING id
    """)

    return response(201, {'user_id': user_id, 'message': 'Регистрация успешна'}, origin)

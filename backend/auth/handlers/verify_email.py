"""Email verification handler."""
import json
from datetime import datetime

from utils.db import query_one, execute, escape, get_schema
from utils.http import response, error


def handle(event: dict, origin: str = '*') -> dict:
    """Verify email with code. POST {email, code}."""
    body_str = event.get('body', '{}')
    payload = json.loads(body_str)

    email = str(payload.get('email', '')).lower().strip()
    code = str(payload.get('code', '')).strip()

    if not email or not code:
        return error(400, 'Email и код обязательны', origin)

    now = datetime.utcnow().isoformat()
    S = get_schema()

    # Find user by email
    user = query_one(f"SELECT id, email_verified FROM {S}users WHERE email = {escape(email)}")
    if not user:
        return error(404, 'Пользователь не найден', origin)

    user_id, already_verified = user

    if already_verified:
        return response(200, {'message': 'Email уже подтверждён'}, origin)

    # Find valid code
    token_record = query_one(f"""
        SELECT id FROM {S}email_verification_tokens
        WHERE user_id = {escape(user_id)}
          AND token_hash = {escape(code)}
          AND expires_at > {escape(now)}
    """)

    if not token_record:
        return error(400, 'Неверный или истёкший код', origin)

    # Mark email as verified
    execute(f"""
        UPDATE {S}users SET email_verified = TRUE, updated_at = {escape(now)}
        WHERE id = {escape(user_id)}
    """)

    # Delete used token
    execute(f"DELETE FROM {S}email_verification_tokens WHERE user_id = {escape(user_id)}")

    return response(200, {'message': 'Email подтверждён'}, origin)

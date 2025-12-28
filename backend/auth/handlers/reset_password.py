"""Password reset handler."""
import json
import secrets
from datetime import datetime, timedelta

from utils.db import query_one, execute, escape, get_schema
from utils.password import hash_password, validate_password
from utils.jwt_utils import hash_token
from utils.http import response, error


RESET_TOKEN_LIFETIME_HOURS = 1


def handle(event: dict) -> dict:
    """Password reset: POST {email} or POST {token, new_password}."""
    body_str = event.get('body', '{}')
    payload = json.loads(body_str)

    email = str(payload.get('email', '')).lower().strip()
    token = str(payload.get('token', '')).strip()
    new_password = str(payload.get('new_password', ''))

    S = get_schema()

    # Step 1: Request password reset
    if email and not token:
        user = query_one(f"SELECT id FROM {S}users WHERE email = {escape(email)}")
        response_msg = 'Если пользователь существует, ссылка для сброса будет отправлена на email'

        if user:
            user_id = user[0]
            reset_token = secrets.token_urlsafe(32)
            expires_at = (datetime.utcnow() + timedelta(hours=RESET_TOKEN_LIFETIME_HOURS)).isoformat()
            now = datetime.utcnow().isoformat()

            execute(f"DELETE FROM {S}password_reset_tokens WHERE user_id = {escape(user_id)}")

            token_hash = hash_token(reset_token)
            execute(f"""
                INSERT INTO {S}password_reset_tokens (user_id, token_hash, expires_at, created_at)
                VALUES ({escape(user_id)}, {escape(token_hash)}, {escape(expires_at)}, {escape(now)})
            """)

            return response(200, {
                'message': response_msg,
                'reset_token': reset_token,
                'expires_in_minutes': RESET_TOKEN_LIFETIME_HOURS * 60
            })

        return response(200, {'message': response_msg})

    # Step 2: Reset password with token
    if token and new_password:
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            return error(400, error_msg)

        token_hash = hash_token(token)
        now = datetime.utcnow().isoformat()

        token_record = query_one(f"""
            SELECT user_id FROM {S}password_reset_tokens
            WHERE token_hash = {escape(token_hash)} AND expires_at > {escape(now)}
        """)

        if not token_record:
            return error(400, 'Недействительный или истёкший токен')

        user_id = token_record[0]
        password_hash = hash_password(new_password)

        execute(f"""
            UPDATE {S}users SET password_hash = {escape(password_hash)}, updated_at = {escape(now)}
            WHERE id = {escape(user_id)}
        """)

        execute(f"DELETE FROM {S}password_reset_tokens WHERE token_hash = {escape(token_hash)}")
        execute(f"DELETE FROM {S}refresh_tokens WHERE user_id = {escape(user_id)}")

        return response(200, {'message': 'Пароль успешно изменён'})

    return error(400, 'Укажите email или token с new_password')

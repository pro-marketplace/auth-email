"""Password reset handler."""
import json
from datetime import datetime, timedelta

from utils.db import query_one, execute, escape, get_schema
from utils.password import hash_password, validate_password
from utils.email import is_email_enabled, generate_code, send_password_reset_code
from utils.http import response, error


RESET_CODE_LIFETIME_HOURS = 1


def handle(event: dict, origin: str = '*') -> dict:
    """
    Password reset flow:
    1. POST {email} - request reset, sends code to email
    2. POST {email, code, new_password} - set new password with code
    """
    body_str = event.get('body', '{}')
    payload = json.loads(body_str)

    email = str(payload.get('email', '')).lower().strip()
    code = str(payload.get('code', '')).strip()
    new_password = str(payload.get('new_password', ''))

    if not email:
        return error(400, 'Email обязателен', origin)

    S = get_schema()

    # Step 1: Request reset code
    if email and not code and not new_password:
        user = query_one(f"SELECT id FROM {S}users WHERE email = {escape(email)}")
        response_msg = 'Если пользователь существует, код сброса будет отправлен на email'

        if user:
            user_id = user[0]
            now = datetime.utcnow().isoformat()

            # Delete old tokens
            execute(f"DELETE FROM {S}password_reset_tokens WHERE user_id = {escape(user_id)}")

            # Generate and store new code
            reset_code = generate_code()
            expires_at = (datetime.utcnow() + timedelta(hours=RESET_CODE_LIFETIME_HOURS)).isoformat()

            execute(f"""
                INSERT INTO {S}password_reset_tokens (user_id, token_hash, expires_at, created_at)
                VALUES ({escape(user_id)}, {escape(reset_code)}, {escape(expires_at)}, {escape(now)})
            """)

            # Send code via email if SMTP configured
            if is_email_enabled():
                if send_password_reset_code(email, reset_code):
                    return response(200, {'message': response_msg}, origin)
                else:
                    return response(200, {'message': 'Не удалось отправить код'}, origin)
            else:
                # Return code in response for development
                return response(200, {
                    'message': response_msg,
                    'reset_code': reset_code,
                    'expires_in_minutes': RESET_CODE_LIFETIME_HOURS * 60
                }, origin)

        return response(200, {'message': response_msg}, origin)

    # Step 2: Reset password with code
    if email and code and new_password:
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            return error(400, error_msg, origin)

        now = datetime.utcnow().isoformat()

        # Find user
        user = query_one(f"SELECT id FROM {S}users WHERE email = {escape(email)}")
        if not user:
            return error(400, 'Неверный код', origin)

        user_id = user[0]

        # Verify code
        token_record = query_one(f"""
            SELECT id FROM {S}password_reset_tokens
            WHERE user_id = {escape(user_id)}
              AND token_hash = {escape(code)}
              AND expires_at > {escape(now)}
        """)

        if not token_record:
            return error(400, 'Неверный или истёкший код', origin)

        # Update password
        new_password_hash = hash_password(new_password)
        execute(f"""
            UPDATE {S}users SET password_hash = {escape(new_password_hash)}, updated_at = {escape(now)}
            WHERE id = {escape(user_id)}
        """)

        # Cleanup tokens
        execute(f"DELETE FROM {S}password_reset_tokens WHERE user_id = {escape(user_id)}")
        execute(f"DELETE FROM {S}refresh_tokens WHERE user_id = {escape(user_id)}")

        return response(200, {'message': 'Пароль успешно изменён'}, origin)

    return error(400, 'Укажите email для запроса кода или email + code + new_password для сброса', origin)

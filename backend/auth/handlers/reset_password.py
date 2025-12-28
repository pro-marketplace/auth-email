"""Password reset handler."""
import json
import secrets
from datetime import datetime, timedelta

from utils.db import get_connection, escape
from utils.password import hash_password, validate_password
from utils.jwt_utils import hash_token
from utils.http import response, error


RESET_TOKEN_LIFETIME_HOURS = 1


def handle(event: dict) -> dict:
    """
    Password reset flow:
    1. POST {email} -> generates reset token
    2. POST {token, new_password} -> resets password
    """
    body_str = event.get('body', '{}')
    payload = json.loads(body_str)

    email = str(payload.get('email', '')).lower().strip()
    token = str(payload.get('token', '')).strip()
    new_password = str(payload.get('new_password', ''))

    conn = get_connection()
    cur = conn.cursor()

    # Step 1: Request password reset
    if email and not token:
        cur.execute(f"SELECT id FROM users WHERE email = {escape(email)}")
        user = cur.fetchone()

        # Same response regardless of user existence (prevent enumeration)
        response_msg = 'Если пользователь существует, ссылка для сброса будет отправлена на email'

        if user:
            user_id = user[0]

            reset_token = secrets.token_urlsafe(32)
            expires_at = (datetime.utcnow() + timedelta(hours=RESET_TOKEN_LIFETIME_HOURS)).isoformat()
            now = datetime.utcnow().isoformat()

            cur.execute(f"DELETE FROM password_reset_tokens WHERE user_id = {escape(user_id)}")

            token_hash = hash_token(reset_token)
            cur.execute(f"""
                INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, created_at)
                VALUES ({escape(user_id)}, {escape(token_hash)}, {escape(expires_at)}, {escape(now)})
            """)

            conn.commit()
            cur.close()
            conn.close()

            # In production: send email with reset_token
            # For demo: return token (REMOVE IN PRODUCTION!)
            return response(200, {
                'message': response_msg,
                'reset_token': reset_token,  # REMOVE IN PRODUCTION!
                'expires_in_minutes': RESET_TOKEN_LIFETIME_HOURS * 60
            })

        cur.close()
        conn.close()
        return response(200, {'message': response_msg})

    # Step 2: Reset password with token
    if token and new_password:
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            cur.close()
            conn.close()
            return error(400, error_msg)

        token_hash = hash_token(token)
        now = datetime.utcnow().isoformat()

        cur.execute(f"""
            SELECT user_id FROM password_reset_tokens
            WHERE token_hash = {escape(token_hash)} AND expires_at > {escape(now)}
        """)

        token_record = cur.fetchone()
        if not token_record:
            cur.close()
            conn.close()
            return error(400, 'Недействительный или истёкший токен')

        user_id = token_record[0]
        password_hash = hash_password(new_password)

        cur.execute(f"""
            UPDATE users SET password_hash = {escape(password_hash)}, updated_at = {escape(now)}
            WHERE id = {escape(user_id)}
        """)

        # Delete used token (single-use)
        cur.execute(f"DELETE FROM password_reset_tokens WHERE token_hash = {escape(token_hash)}")

        # Revoke all refresh tokens (force re-login)
        cur.execute(f"DELETE FROM refresh_tokens WHERE user_id = {escape(user_id)}")

        conn.commit()
        cur.close()
        conn.close()

        return response(200, {'message': 'Пароль успешно изменён'})

    cur.close()
    conn.close()
    return error(400, 'Укажите email или token с new_password')

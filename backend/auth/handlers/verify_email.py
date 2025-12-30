"""Email verification handler."""
from datetime import datetime

from utils.db import query_one, execute, escape, get_schema
from utils.jwt_utils import hash_token
from utils.http import response, error


def handle(event: dict, origin: str = '*') -> dict:
    """Verify email with token from query string."""
    params = event.get('queryStringParameters', {}) or {}
    token = params.get('token', '')

    if not token:
        return error(400, 'Token required', origin)

    token_hash = hash_token(token)
    now = datetime.utcnow().isoformat()
    S = get_schema()

    # Find valid token
    token_record = query_one(f"""
        SELECT user_id FROM {S}email_verification_tokens
        WHERE token_hash = {escape(token_hash)} AND expires_at > {escape(now)}
    """)

    if not token_record:
        return error(400, 'Invalid or expired token', origin)

    user_id = token_record[0]

    # Mark email as verified
    execute(f"""
        UPDATE {S}users SET email_verified = TRUE, updated_at = {escape(now)}
        WHERE id = {escape(user_id)}
    """)

    # Delete used token
    execute(f"DELETE FROM {S}email_verification_tokens WHERE user_id = {escape(user_id)}")

    return response(200, {'message': 'Email verified successfully'}, origin)

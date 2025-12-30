"""Token refresh handler."""
import json
import os
from datetime import datetime

from utils.db import query_one, escape, get_schema
from utils.jwt_utils import create_access_token, decode_refresh_token, hash_token, ACCESS_TOKEN_EXPIRE_MINUTES
from utils.http import response, error


def handle(event: dict, origin: str = '*') -> dict:
    """Refresh access token using refresh token from request body."""
    jwt_secret = os.environ.get('JWT_SECRET')
    if not jwt_secret:
        return error(500, 'JWT_SECRET not configured', origin)

    body_str = event.get('body', '{}')
    payload = json.loads(body_str)
    refresh_token = payload.get('refresh_token', '')

    if not refresh_token:
        return error(401, 'Refresh token required', origin)

    decoded = decode_refresh_token(refresh_token)
    if not decoded:
        return error(401, 'Invalid or expired refresh token', origin)

    user_id = int(decoded.get('sub'))
    token_hash = hash_token(refresh_token)
    now = datetime.utcnow().isoformat()

    S = get_schema()

    result = query_one(f"""
        SELECT rt.id, u.email, u.name
        FROM {S}refresh_tokens rt
        JOIN {S}users u ON u.id = rt.user_id
        WHERE rt.token_hash = {escape(token_hash)}
          AND rt.user_id = {escape(user_id)}
          AND rt.expires_at > {escape(now)}
    """)

    if not result:
        return error(401, 'Refresh token revoked or expired', origin)

    _, user_email, user_name = result
    access_token = create_access_token(user_id, user_email)

    return response(200, {
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        'user': {
            'id': user_id,
            'email': user_email,
            'name': user_name
        }
    }, origin)

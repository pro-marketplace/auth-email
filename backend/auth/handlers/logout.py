"""Logout handler."""
import json

from utils.db import execute, escape, get_schema
from utils.jwt_utils import hash_token
from utils.http import response


def handle(event: dict, origin: str = '*') -> dict:
    """Logout user by revoking refresh token from request body."""
    body_str = event.get('body', '{}')
    payload = json.loads(body_str)
    refresh_token = payload.get('refresh_token', '')

    if refresh_token:
        token_hash = hash_token(refresh_token)
        S = get_schema()
        execute(f"DELETE FROM {S}refresh_tokens WHERE token_hash = {escape(token_hash)}")

    return response(200, {'message': 'Logged out successfully'}, origin)

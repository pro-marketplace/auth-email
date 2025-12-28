"""Logout handler."""
from utils.db import get_connection, escape, get_schema
from utils.jwt_utils import hash_token
from utils.cookies import get_refresh_token_from_cookie, make_clear_cookie
from utils.http import response


def handle(event: dict) -> dict:
    """Logout user by revoking refresh token and clearing cookie."""
    refresh_token = get_refresh_token_from_cookie(event)

    if refresh_token:
        token_hash = hash_token(refresh_token)
        S = get_schema()

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {S}refresh_tokens WHERE token_hash = {escape(token_hash)}")
        conn.commit()
        cur.close()
        conn.close()

    clear_cookie = make_clear_cookie()

    return response(200, {'message': 'Logged out successfully'}, set_cookie=clear_cookie)

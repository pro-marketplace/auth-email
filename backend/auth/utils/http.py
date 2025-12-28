"""HTTP response utilities."""
import os
import json
from typing import Optional


def get_cors_origin() -> str:
    """Get allowed CORS origin from env."""
    return os.environ.get('CORS_ORIGIN', '*')


def make_headers(set_cookie: Optional[str] = None) -> dict:
    """Create response headers with CORS."""
    origin = get_cors_origin()
    headers = {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Credentials': 'true',
        'Content-Type': 'application/json'
    }
    if set_cookie:
        # Use X-Set-Cookie - proxy will convert to Set-Cookie
        headers['X-Set-Cookie'] = set_cookie
    return headers


def response(status_code: int, body: dict, set_cookie: Optional[str] = None) -> dict:
    """Create HTTP response."""
    return {
        'statusCode': status_code,
        'headers': make_headers(set_cookie),
        'body': json.dumps(body),
        'isBase64Encoded': False
    }


def options_response() -> dict:
    """Create OPTIONS preflight response."""
    return {
        'statusCode': 200,
        'headers': make_headers(),
        'body': '',
        'isBase64Encoded': False
    }


def error(status_code: int, message: str) -> dict:
    """Create error response."""
    return response(status_code, {'error': message})

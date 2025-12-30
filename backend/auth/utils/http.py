"""HTTP response utilities."""
import os
import json
from typing import Optional


def get_origin_from_event(event: dict) -> str:
    """Get Origin header from request, fallback to CORS_ORIGIN env or '*'."""
    headers = event.get('headers', {})
    # Try Origin header (case-insensitive)
    origin = headers.get('Origin') or headers.get('origin') or ''
    if origin:
        return origin
    # Fallback to env or '*'
    return os.environ.get('CORS_ORIGIN', '*')


def make_headers(origin: str = '*', set_cookie: Optional[str] = None) -> dict:
    """Create response headers with CORS."""
    headers = {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Credentials': 'true',
        'Content-Type': 'application/json'
    }
    if set_cookie:
        headers['X-Set-Cookie'] = set_cookie
    return headers


def response(status_code: int, body: dict, origin: str = '*', set_cookie: Optional[str] = None) -> dict:
    """Create HTTP response."""
    return {
        'statusCode': status_code,
        'headers': make_headers(origin, set_cookie),
        'body': json.dumps(body),
        'isBase64Encoded': False
    }


def options_response(origin: str = '*') -> dict:
    """Create OPTIONS preflight response."""
    return {
        'statusCode': 200,
        'headers': make_headers(origin),
        'body': '',
        'isBase64Encoded': False
    }


def error(status_code: int, message: str, origin: str = '*') -> dict:
    """Create error response."""
    return response(status_code, {'error': message}, origin)

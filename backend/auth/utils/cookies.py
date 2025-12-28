"""Cookie utilities for HttpOnly refresh token."""
import os
from datetime import datetime
from typing import Optional
from http.cookies import SimpleCookie


def get_cookie_domain() -> str:
    """Get cookie domain from env."""
    return os.environ.get('COOKIE_DOMAIN', '')


def make_refresh_cookie(token: str, expires: datetime) -> str:
    """Create HttpOnly cookie string for refresh token."""
    secure = os.environ.get('COOKIE_SECURE', 'true').lower() == 'true'
    same_site = os.environ.get('COOKIE_SAMESITE', 'Strict')
    domain = get_cookie_domain()

    cookie_parts = [
        f'refresh_token={token}',
        f'Expires={expires.strftime("%a, %d %b %Y %H:%M:%S GMT")}',
        'HttpOnly',
        'Path=/',
        f'SameSite={same_site}'
    ]

    if secure:
        cookie_parts.append('Secure')
    if domain:
        cookie_parts.append(f'Domain={domain}')

    return '; '.join(cookie_parts)


def make_clear_cookie() -> str:
    """Create cookie string that clears refresh_token."""
    secure = os.environ.get('COOKIE_SECURE', 'true').lower() == 'true'
    same_site = os.environ.get('COOKIE_SAMESITE', 'Strict')
    domain = get_cookie_domain()

    cookie_parts = [
        'refresh_token=',
        'Expires=Thu, 01 Jan 1970 00:00:00 GMT',
        'HttpOnly',
        'Path=/',
        f'SameSite={same_site}'
    ]

    if secure:
        cookie_parts.append('Secure')
    if domain:
        cookie_parts.append(f'Domain={domain}')

    return '; '.join(cookie_parts)


def get_refresh_token_from_cookie(event: dict) -> Optional[str]:
    """Extract refresh_token from X-Cookie header (proxy mapping)."""
    headers = event.get('headers', {})

    cookie_header = (
        headers.get('X-Cookie') or
        headers.get('x-cookie') or
        ''
    )

    if not cookie_header:
        return None

    cookie = SimpleCookie()
    cookie.load(cookie_header)

    if 'refresh_token' in cookie:
        return cookie['refresh_token'].value

    return None

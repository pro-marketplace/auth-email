"""JWT token utilities."""
import os
import jwt
import hashlib
from datetime import datetime, timedelta


JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '15'))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get('REFRESH_TOKEN_EXPIRE_DAYS', '30'))


def create_access_token(user_id: int, email: str) -> str:
    """Create short-lived JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        'sub': str(user_id),
        'email': email,
        'type': 'access',
        'exp': expire,
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    """Create long-lived JWT refresh token."""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        'sub': str(user_id),
        'type': 'refresh',
        'exp': expire,
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expire


def decode_refresh_token(token: str) -> dict | None:
    """Decode and validate refresh token. Returns payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get('type') != 'refresh':
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def hash_token(token: str) -> str:
    """Hash token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()

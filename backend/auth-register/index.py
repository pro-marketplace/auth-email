"""
Auth Email Extension - User Registration (Secure)
"""
import json
import os
import re
import psycopg2
import bcrypt
from datetime import datetime


def hash_password(password: str) -> str:
    """Hash password using bcrypt with auto-generated salt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength."""
    if len(password) < 8:
        return False, "Пароль должен содержать минимум 8 символов"
    if len(password) > 128:
        return False, "Пароль слишком длинный"
    if not re.search(r'[A-Za-z]', password):
        return False, "Пароль должен содержать хотя бы одну букву"
    if not re.search(r'\d', password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    return True, ""


def get_db_connection():
    """Get database connection."""
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        raise ValueError('DATABASE_URL not configured')
    return psycopg2.connect(dsn)


def get_cors_origin() -> str:
    """Get allowed CORS origin from env."""
    return os.environ.get('CORS_ORIGIN', '*')


def make_headers() -> dict:
    """Create response headers with CORS."""
    origin = get_cors_origin()
    return {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Credentials': 'true' if origin != '*' else 'false',
        'Content-Type': 'application/json'
    }


def handler(event: dict, context) -> dict:
    """
    Register new user with email and password.

    Security:
    - bcrypt password hashing (cost factor 12)
    - Email normalization and validation
    - Password strength requirements
    """
    method = event.get('httpMethod', 'GET').upper()
    headers = make_headers()

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': '', 'isBase64Encoded': False}

    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({'error': 'Method not allowed'}),
            'isBase64Encoded': False
        }

    body_str = event.get('body', '{}')
    payload = json.loads(body_str)

    email = str(payload.get('email', '')).lower().strip()
    password = str(payload.get('password', ''))
    name = str(payload.get('name', '')).strip()[:255]  # Limit name length

    # Validate email
    if not email or not validate_email(email):
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Некорректный email'}),
            'isBase64Encoded': False
        }

    # Validate password
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': error_msg}),
            'isBase64Encoded': False
        }

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if user already exists
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    existing = cur.fetchone()

    if existing:
        cur.close()
        conn.close()
        return {
            'statusCode': 409,
            'headers': headers,
            'body': json.dumps({'error': 'Пользователь с таким email уже существует'}),
            'isBase64Encoded': False
        }

    # Create user with bcrypt hashed password
    password_hash = hash_password(password)

    cur.execute("""
        INSERT INTO users (email, password_hash, name, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (email, password_hash, name or None, datetime.utcnow(), datetime.utcnow()))

    user_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return {
        'statusCode': 201,
        'headers': headers,
        'body': json.dumps({
            'user_id': user_id,
            'message': 'Регистрация успешна'
        }),
        'isBase64Encoded': False
    }

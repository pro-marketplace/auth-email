"""Password utilities."""
import re
import bcrypt


def hash_password(password: str) -> str:
    """Hash password using bcrypt with cost factor 12."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength. Returns (is_valid, error_message)."""
    if len(password) < 8:
        return False, "Пароль должен содержать минимум 8 символов"
    if len(password) > 128:
        return False, "Пароль слишком длинный"
    if not re.search(r'[A-Za-z]', password):
        return False, "Пароль должен содержать хотя бы одну букву"
    if not re.search(r'\d', password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    return True, ""


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

"""
Auth Email Extension - Single Function Router

Routes:
  POST /auth/register       - Register new user
  POST /auth/login          - Login and get tokens
  POST /auth/refresh        - Refresh access token
  POST /auth/logout         - Logout and revoke tokens
  POST /auth/reset-password - Request/complete password reset
"""
from handlers import register, login, logout, refresh, reset_password
from utils.http import options_response, error


ROUTES = {
    'register': register.handle,
    'login': login.handle,
    'refresh': refresh.handle,
    'logout': logout.handle,
    'reset-password': reset_password.handle,
}


def handler(event: dict, context) -> dict:
    """Main router for auth endpoints."""
    method = event.get('httpMethod', 'GET').upper()

    if method == 'OPTIONS':
        return options_response()

    if method != 'POST':
        return error(405, 'Method not allowed')

    # Extract route from path: /auth/login -> login
    path = event.get('path', '')
    parts = [p for p in path.strip('/').split('/') if p]

    # Expected: ['auth', 'login'] or just ['login'] depending on deployment
    route = None
    if len(parts) >= 2 and parts[0] == 'auth':
        route = parts[1]
    elif len(parts) == 1:
        route = parts[0]

    if not route or route not in ROUTES:
        return error(404, f'Unknown route: {route}')

    return ROUTES[route](event)

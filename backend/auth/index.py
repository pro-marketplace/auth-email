"""
Auth Email Extension - Single Function Router

Routes (via ?action= query parameter):
  GET  /auth?action=health         - Check DB schema (required tables/columns)
  POST /auth?action=register       - Register new user
  POST /auth?action=login          - Login and get tokens
  POST /auth?action=refresh        - Refresh access token
  POST /auth?action=logout         - Logout and revoke tokens
  POST /auth?action=reset-password - Request/complete password reset
"""
from handlers import register, login, logout, refresh, reset_password, health
from utils.http import options_response, error


ROUTES = {
    'register': register.handle,
    'login': login.handle,
    'refresh': refresh.handle,
    'logout': logout.handle,
    'reset-password': reset_password.handle,
    'health': health.handle,
}


def handler(event: dict, context) -> dict:
    """Main router for auth endpoints."""
    method = event.get('httpMethod', 'GET').upper()

    if method == 'OPTIONS':
        return options_response()

    # Extract action from query parameters
    params = event.get('queryStringParameters') or {}
    action = params.get('action', '')

    # Health check allows GET
    if action == 'health' and method == 'GET':
        return ROUTES['health'](event)

    if method != 'POST':
        return error(405, 'Method not allowed')

    if not action or action not in ROUTES:
        return error(404, f'Unknown action: {action}. Use ?action=health|login|register|refresh|logout|reset-password')

    return ROUTES[action](event)

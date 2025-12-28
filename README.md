# Auth Email Extension (Secure)

Безопасная авторизация и регистрация по email + пароль с JWT токенами.

**1 функция** вместо 5 — экономит лимит пользователя.

## Безопасность

- **bcrypt** для хеширования паролей (cost factor 12)
- **JWT** access tokens (короткоживущие, 15 мин)
- **HttpOnly cookie** для refresh token (защита от XSS)
- **Rate limiting** при входе (5 попыток, затем блокировка 15 мин)
- **Токены сброса пароля** с коротким сроком жизни (1 час)
- **Отзыв сессий** при смене пароля
- **Защита от перебора email** (одинаковый ответ для существующих/несуществующих)

### Работа с Yandex Cloud Functions

Yandex Cloud Functions фильтрует заголовки `Authorization` и `Cookie`.
Прокси `functions.poehali.dev` выполняет маппинг:

| Направление | Маппинг |
|-------------|---------|
| Запрос к функции | `Cookie` → `X-Cookie` |
| Запрос к функции | `Authorization` → `X-Authorization` |
| Ответ функции | `X-Set-Cookie` → `Set-Cookie` |

**Frontend работает как обычно** — использует `credentials: 'include'` и стандартный `Authorization` header.

## Структура

```
backend/auth/
├── index.py              # Роутер
├── handlers/
│   ├── register.py       # Регистрация
│   ├── login.py          # Вход + JWT + Set-Cookie
│   ├── refresh.py        # Обновление access token
│   ├── logout.py         # Выход + очистка cookie
│   └── reset_password.py # Сброс пароля
├── utils/
│   ├── db.py             # Подключение к БД
│   ├── jwt_utils.py      # JWT токены
│   ├── password.py       # bcrypt, валидация
│   ├── cookies.py        # HttpOnly cookies
│   └── http.py           # CORS, responses
└── requirements.txt

frontend/
├── useAuth.ts            # React хук с auto-refresh
├── LoginForm.tsx
├── RegisterForm.tsx
└── ResetPasswordForm.tsx
```

## Установка

### 1. База данных

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(72) NOT NULL,
    name VARCHAR(255),
    failed_login_attempts INTEGER DEFAULT 0,
    last_failed_login_at TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_password_reset_tokens_hash ON password_reset_tokens(token_hash);
```

### 2. Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `JWT_SECRET` | **Обязательно!** Секретный ключ | `openssl rand -hex 32` |
| `CORS_ORIGIN` | Домен фронтенда | `https://example.com` |
| `COOKIE_DOMAIN` | Домен для cookie | `.example.com` |
| `COOKIE_SECURE` | HTTPS only | `true` |
| `COOKIE_SAMESITE` | SameSite policy | `Strict` |

### 3. Frontend

```tsx
import { useAuth } from "@/lib/useAuth";

const AUTH_BASE = func2url["auth"]; // одна функция

function App() {
  const auth = useAuth({
    apiUrls: {
      login: `${AUTH_BASE}/login`,
      register: `${AUTH_BASE}/register`,
      refresh: `${AUTH_BASE}/refresh`,
      logout: `${AUTH_BASE}/logout`,
      resetPassword: `${AUTH_BASE}/reset-password`,
    },
  });

  if (auth.isLoading) return <div>Loading...</div>;

  if (!auth.isAuthenticated) {
    return <LoginForm onLogin={auth.login} error={auth.error} />;
  }

  return (
    <div>
      <p>Welcome, {auth.user?.name}</p>
      <button onClick={auth.logout}>Logout</button>
    </div>
  );
}
```

## API

Все эндпоинты через одну функцию:

```
POST /auth/register        - Регистрация
POST /auth/login           - Вход
POST /auth/refresh         - Обновление токена
POST /auth/logout          - Выход
POST /auth/reset-password  - Сброс пароля
```

### POST /auth/register

```json
{ "email": "user@example.com", "password": "SecurePass123", "name": "Иван" }
// Response 201: { "user_id": 1, "message": "Регистрация успешна" }
```

### POST /auth/login

```json
{ "email": "user@example.com", "password": "SecurePass123" }
// Response 200 + Set-Cookie: refresh_token=...; HttpOnly
{
  "access_token": "eyJ...",
  "expires_in": 900,
  "user": { "id": 1, "email": "...", "name": "..." }
}
```

### POST /auth/refresh

```json
// credentials: 'include' (cookie автоматически)
// Response 200: { "access_token": "eyJ...", "expires_in": 900, "user": {...} }
```

### POST /auth/logout

```json
// credentials: 'include'
// Response 200 + Set-Cookie: refresh_token=; Expires=<past>
{ "message": "Logged out successfully" }
```

### POST /auth/reset-password

```json
// Step 1: { "email": "user@example.com" }
// Step 2: { "token": "...", "new_password": "NewPass123" }
```

## Требования к паролю

- 8-128 символов
- Минимум 1 буква
- Минимум 1 цифра

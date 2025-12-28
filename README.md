# Auth Email Extension (Secure)

Безопасная авторизация и регистрация по email + пароль с JWT токенами.

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
Прокси автоматически конвертирует заголовки.

## Структура

```
backend/
├── auth-register/       # Регистрация
├── auth-login/          # Вход + выдача JWT + Set-Cookie
├── auth-refresh/        # Обновление access token (читает cookie)
├── auth-logout/         # Выход + отзыв токена + очистка cookie
└── auth-reset-password/ # Сброс пароля

frontend/
├── useAuth.ts           # React хук с auto-refresh
├── LoginForm.tsx        # Форма входа
├── RegisterForm.tsx     # Форма регистрации
└── ResetPasswordForm.tsx
```

## Установка

### 1. База данных

```sql
-- Пользователи
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(72) NOT NULL,  -- bcrypt hash
    name VARCHAR(255),
    failed_login_attempts INTEGER DEFAULT 0,
    last_failed_login_at TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Refresh токены (для отзыва)
CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Токены сброса пароля
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_password_reset_tokens_hash ON password_reset_tokens(token_hash);
```

### 2. Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `JWT_SECRET` | **Обязательно!** Секретный ключ для JWT | `openssl rand -hex 32` |
| `CORS_ORIGIN` | Домен фронтенда | `https://example.com` |
| `COOKIE_DOMAIN` | Домен для cookie | `.example.com` |
| `COOKIE_SECURE` | HTTPS only cookies | `true` (production) |
| `COOKIE_SAMESITE` | Cookie SameSite policy | `Strict` или `Lax` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни access token | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Время жизни refresh token | `30` |
| `MAX_LOGIN_ATTEMPTS` | Лимит попыток входа | `5` |
| `LOCKOUT_MINUTES` | Время блокировки | `15` |

### 3. Frontend

```tsx
import { useAuth } from "@/lib/useAuth";
import { LoginForm } from "@/components/LoginForm";

function App() {
  const auth = useAuth({
    apiUrls: {
      login: func2url["auth-login"],
      register: func2url["auth-register"],
      refresh: func2url["auth-refresh"],
      logout: func2url["auth-logout"],
      resetPassword: func2url["auth-reset-password"],
    },
    onAuthChange: (user) => {
      console.log("Auth changed:", user);
    },
  });

  // Для API запросов
  const fetchData = async () => {
    const res = await fetch("/api/data", {
      headers: auth.getAuthHeader(),
    });
  };

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

## Token Flow

```
1. Login
   POST /auth-login {email, password}
   credentials: 'include'
   ↓
   Response: {access_token, expires_in, user}
   Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict

2. API Requests
   Header: Authorization: Bearer {access_token}

3. Token Refresh (auto, before expiry)
   POST /auth-refresh
   credentials: 'include' (отправляет HttpOnly cookie)
   ↓
   Response: {access_token, expires_in, user}

4. Logout
   POST /auth-logout
   credentials: 'include'
   ↓
   Deletes refresh_token from DB
   Set-Cookie: refresh_token=; Expires=<past>; HttpOnly
```

## API

### POST /auth-register

```json
// Request
{ "email": "user@example.com", "password": "SecurePass123", "name": "Иван" }

// Response 201
{ "user_id": 1, "message": "Регистрация успешна" }
```

### POST /auth-login

```json
// Request (credentials: 'include')
{ "email": "user@example.com", "password": "SecurePass123" }

// Response 200
// Set-Cookie: refresh_token=eyJ...; HttpOnly; Secure; Path=/; SameSite=Strict
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": { "id": 1, "email": "user@example.com", "name": "Иван" }
}
```

### POST /auth-refresh

```json
// Request (credentials: 'include' - отправляет HttpOnly cookie автоматически)
// Тело не требуется

// Response 200
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": { "id": 1, "email": "user@example.com", "name": "Иван" }
}
```

### POST /auth-logout

```json
// Request (credentials: 'include')
// Тело не требуется

// Response 200
// Set-Cookie: refresh_token=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly
{ "message": "Logged out successfully" }
```

### POST /auth-reset-password

```json
// Step 1: Request reset
{ "email": "user@example.com" }
// Response: { "message": "...", "reset_token": "..." }

// Step 2: Set new password
{ "token": "...", "new_password": "NewSecurePass123" }
// Response: { "message": "Пароль успешно изменён" }
```

## Требования к паролю

- Минимум 8 символов
- Максимум 128 символов
- Хотя бы одна буква
- Хотя бы одна цифра

## Чеклист

- [ ] `JWT_SECRET` установлен (32+ случайных байта)
- [ ] `CORS_ORIGIN` указывает на ваш домен (не `*` в production)
- [ ] `COOKIE_DOMAIN` настроен для вашего домена
- [ ] `COOKIE_SECURE=true` для HTTPS
- [ ] Миграция БД применена
- [ ] Backend функции задеплоены
- [ ] Тестовая регистрация/вход работает
- [ ] Token refresh работает автоматически
- [ ] Cookies корректно устанавливаются (проверить DevTools → Application → Cookies)

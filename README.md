# Auth Email Extension

Авторизация и регистрация по email + пароль с JWT токенами.

**1 функция** вместо 5 — экономит лимит пользователя.

## Безопасность

- **bcrypt** для хеширования паролей (cost factor 12)
- **JWT** access tokens (короткоживущие, 15 мин)
- **Refresh tokens** (30 дней) хранятся в localStorage
- **Rate limiting** при входе (5 попыток, затем блокировка 15 мин)
- **Токены сброса пароля** с коротким сроком жизни (1 час)
- **Отзыв сессий** при смене пароля
- **Защита от перебора email** (одинаковый ответ для существующих/несуществующих)

### XSS и localStorage

Refresh токены хранятся в `localStorage`. Это необходимо для работы расширения на кросс-доменных сайтах (браузеры блокируют third-party cookies).

**Риски:**
- XSS-атаки могут украсть токены из localStorage
- Вредоносные npm-пакеты в проекте могут получить доступ к токенам

**Рекомендации:**
1. Используйте строгий Content Security Policy (CSP)
2. Проверяйте все пользовательские данные перед выводом
3. Используйте надёжные npm-пакеты, регулярно обновляйте зависимости
4. Не храните чувствительные данные в токенах
5. Рассмотрите короткий срок жизни токенов для критичных приложений

```
Content-Security-Policy: default-src 'self'; script-src 'self'
```

## Структура

```
backend/auth/
├── index.py              # Роутер
├── handlers/
│   ├── register.py       # Регистрация
│   ├── login.py          # Вход + JWT
│   ├── refresh.py        # Обновление access token
│   ├── logout.py         # Выход
│   ├── reset_password.py # Сброс пароля
│   └── health.py         # Проверка схемы БД
└── utils/
    ├── db.py             # Подключение к БД
    ├── jwt_utils.py      # JWT токены
    ├── password.py       # bcrypt, валидация
    └── http.py           # CORS, responses

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

**Обязательные:**

| Переменная | Описание | Пример |
|------------|----------|--------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `MAIN_DB_SCHEMA` | Схема БД проекта | `t_p18279400_...` |
| `JWT_SECRET` | Секретный ключ для JWT | `openssl rand -hex 32` |

**Опциональные:**

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `CORS_ORIGIN` | Домен фронтенда | _(читается из Origin)_ |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни access token | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Время жизни refresh token | `30` |
| `MAX_LOGIN_ATTEMPTS` | Лимит попыток входа | `5` |
| `LOCKOUT_MINUTES` | Время блокировки | `15` |

### 3. Frontend

```tsx
import { useAuth } from "@/lib/useAuth";

const AUTH_URL = func2url["auth"]; // одна функция

function App() {
  const auth = useAuth({
    apiUrls: {
      login: `${AUTH_URL}?action=login`,
      register: `${AUTH_URL}?action=register`,
      refresh: `${AUTH_URL}?action=refresh`,
      logout: `${AUTH_URL}?action=logout`,
      resetPassword: `${AUTH_URL}?action=reset-password`,
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

## Проверки после деплоя

### 1. Проверить func2url.json

Убедитесь что в `func2url.json` появился ключ с URL функции:

```json
{
  "auth-email-auth": "https://functions.poehali.dev/xxx..."
}
```

### 2. Проверить схему БД

Вызовите health check endpoint:

```bash
curl "https://functions.poehali.dev/xxx...?action=health"
```

Ожидаемый ответ при успехе:
```json
{
  "status": "ok",
  "schema": "t_p18279400_...",
  "tables": ["users", "refresh_tokens", "password_reset_tokens"],
  "message": "All required tables and columns exist"
}
```

При ошибке — список недостающих таблиц/колонок.

## API

Все эндпоинты через одну функцию с query parameter `?action=`:

```
GET  /auth?action=health          - Проверка схемы БД
POST /auth?action=register        - Регистрация
POST /auth?action=login           - Вход
POST /auth?action=refresh         - Обновление токена
POST /auth?action=logout          - Выход
POST /auth?action=reset-password  - Сброс пароля
```

### GET /auth?action=health

```json
// Response 200 (success):
{
  "status": "ok",
  "schema": "t_p18279400_...",
  "tables": ["users", "refresh_tokens", "password_reset_tokens"],
  "message": "All required tables and columns exist"
}

// Response 500 (error):
{ "error": "Schema validation failed: Table 'users' not found..." }
```

### POST /auth?action=register

```json
// Обязательные: email, password
// Опциональные: name
{ "email": "user@example.com", "password": "SecurePass123", "name": "Иван" }

// Response 201:
{ "user_id": 1, "message": "Регистрация успешна" }
```

### POST /auth?action=login

```json
{ "email": "user@example.com", "password": "SecurePass123" }

// Response 200:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_expires_in": 2592000,
  "user": { "id": 1, "email": "...", "name": "..." }
}
```

### POST /auth?action=refresh

```json
// Request:
{ "refresh_token": "eyJ..." }

// Response 200:
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": { "id": 1, "email": "...", "name": "..." }
}
```

### POST /auth?action=logout

```json
// Request:
{ "refresh_token": "eyJ..." }

// Response 200:
{ "message": "Logged out successfully" }
```

### POST /auth?action=reset-password

```json
// Step 1 - запрос на сброс:
{ "email": "user@example.com" }
// Response: { "message": "Если пользователь существует...", "reset_token": "...", "expires_in_minutes": 60 }

// Step 2 - установка нового пароля:
{ "token": "...", "new_password": "NewPass123" }
// Response: { "message": "Пароль успешно изменён" }
```

## Требования к паролю

- 8-128 символов
- Минимум 1 буква
- Минимум 1 цифра

# Auth Email Extension

Авторизация по email + пароль с JWT токенами.

**1 функция** вместо 5 — экономит лимит.

---

## Для ассистента: перед интеграцией

**Спроси пользователя:**

> Хотите подтверждение email и восстановление пароля через почту?
>
> Для этого нужен Gmail с двухфакторной аутентификацией.
> Без этого: регистрация работает сразу, сброс пароля возвращает код в ответе.

**Если ДА → добавь переменные:**
```
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # App Password
```

**Если НЕТ → ничего не добавляй**, всё работает без email.

---

## Как это работает

| SMTP настроен? | Регистрация | Вход | Сброс пароля |
|----------------|-------------|------|--------------|
| Нет | Сразу активен | Работает | Код в ответе API |
| Да | Код на почту | После подтверждения | Код на почту |

---

## Установка

### 1. База данных

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(72) NOT NULL,
    name VARCHAR(255),
    email_verified BOOLEAN DEFAULT TRUE,
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

CREATE TABLE email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_password_reset_tokens_hash ON password_reset_tokens(token_hash);
CREATE INDEX idx_email_verification_tokens_hash ON email_verification_tokens(token_hash);
```

### 2. Переменные окружения

**Обязательные:**

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | PostgreSQL connection string |
| `MAIN_DB_SCHEMA` | Схема БД проекта |
| `JWT_SECRET` | Секретный ключ (`openssl rand -hex 32`) |

**Для email (опционально):**

| Переменная | Описание |
|------------|----------|
| `SMTP_USER` | Gmail адрес |
| `SMTP_PASSWORD` | Gmail App Password |

### 3. Настройка Gmail (если нужен email)

1. Включи 2FA: https://myaccount.google.com/security
2. Создай App Password: https://myaccount.google.com/apppasswords
3. Выбери "Другое", введи название, скопируй 16-символьный пароль

---

## После деплоя

**ВАЖНО:** Обнови `AUTH_URL` в коде на URL из `backend/func2url.json`:

```tsx
const AUTH_URL = "https://functions.poehali.dev/xxx"; // ← заменить
```

---

## API

```
POST /auth?action=register        - Регистрация
POST /auth?action=verify-email    - Подтверждение email (code)
POST /auth?action=login           - Вход
POST /auth?action=refresh         - Обновление токена
POST /auth?action=logout          - Выход
POST /auth?action=reset-password  - Сброс пароля
GET  /auth?action=health          - Проверка БД
```

### register

```json
// Request
{ "email": "user@example.com", "password": "Pass123", "name": "Имя" }

// Response (без SMTP)
{ "user_id": 1, "message": "Регистрация успешна", "email_verification_required": false }

// Response (с SMTP) - новый пользователь
{ "user_id": 1, "message": "Код подтверждения отправлен на email", "email_verification_required": true }

// Response (с SMTP) - email существует, но не подтверждён → переотправка кода
{ "user_id": 1, "message": "Код подтверждения отправлен на email", "email_verification_required": true, "resent": true }
```

### verify-email

```json
// Request
{ "email": "user@example.com", "code": "123456" }

// Response
{ "message": "Email подтверждён" }
```

### login

```json
// Request
{ "email": "user@example.com", "password": "Pass123" }

// Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 900,
  "user": { "id": 1, "email": "...", "name": "...", "email_verified": true }
}
```

### reset-password

```json
// Step 1: Запрос кода
{ "email": "user@example.com" }
// Response (без SMTP): { "message": "...", "reset_code": "123456" }
// Response (с SMTP): { "message": "Если пользователь существует, код будет отправлен" }

// Step 2: Новый пароль
{ "email": "user@example.com", "code": "123456", "new_password": "NewPass123" }
// Response: { "message": "Пароль успешно изменён" }
```

---

## Frontend

```tsx
const AUTH_URL = "https://functions.poehali.dev/xxx";

const auth = useAuth({
  apiUrls: {
    login: `${AUTH_URL}?action=login`,
    register: `${AUTH_URL}?action=register`,
    refresh: `${AUTH_URL}?action=refresh`,
    logout: `${AUTH_URL}?action=logout`,
    resetPassword: `${AUTH_URL}?action=reset-password`,
  },
});

// Для verify-email добавь состояние в форму регистрации
// Если email_verification_required === true, показывай поле ввода кода
```

---

## Безопасность

- bcrypt для паролей
- JWT access tokens (15 мин)
- Refresh tokens (30 дней) в localStorage
- Rate limiting (5 попыток, блокировка 15 мин)
- 6-значные коды для верификации

### XSS

Токены в localStorage — стандарт для кросс-доменных SPA.
Используйте CSP: `Content-Security-Policy: default-src 'self'`

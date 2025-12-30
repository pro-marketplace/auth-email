# Auth Email Extension

Авторизация и регистрация по email + пароль с JWT токенами.

**1 функция** вместо 5 — экономит лимит пользователя.

---

## Для ассистента: перед интеграцией

**ВАЖНО: Спроси пользователя:**

> Хотите включить подтверждение email и восстановление пароля через почту?
>
> Это потребует настройки Gmail:
> 1. Включить 2FA в Google аккаунте
> 2. Создать App Password (пароль приложения)
>
> Без этого: регистрация работает сразу, сброс пароля возвращает токен в ответе (для разработки).

**Если пользователь хочет email:**
1. Добавь переменные окружения: `SMTP_USER`, `SMTP_PASSWORD`, `AUTH_URL`, `PASSWORD_RESET_URL`, `REQUIRE_EMAIL_VERIFICATION=true`
2. Используй расширенную схему БД (с `email_verified` и `email_verification_tokens`)

**Если НЕ хочет:**
1. Не добавляй SMTP переменные
2. Можно использовать базовую схему БД (без `email_verified`)

---

## Безопасность

- **bcrypt** для хеширования паролей (cost factor 12)
- **JWT** access tokens (15 мин)
- **Refresh tokens** (30 дней) в localStorage
- **Rate limiting** (5 попыток, блокировка 15 мин)
- **Опционально:** подтверждение email через Gmail

### XSS и localStorage

Токены хранятся в `localStorage` — это стандарт для кросс-доменных SPA.

**Рекомендации:**
- Используйте CSP: `Content-Security-Policy: default-src 'self'`
- Проверяйте npm-пакеты

---

## Установка

### 1. База данных

```sql
-- Базовая таблица пользователей
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

-- Только если включено подтверждение email
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
| `SMTP_PASSWORD` | Gmail App Password (16 символов) |
| `AUTH_URL` | URL функции для ссылок в письмах |
| `PASSWORD_RESET_URL` | URL страницы сброса пароля на сайте |
| `REQUIRE_EMAIL_VERIFICATION` | `true` — требовать подтверждение |

**Прочие (опционально):**

| Переменная | По умолчанию |
|------------|--------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` |
| `MAX_LOGIN_ATTEMPTS` | `5` |
| `LOCKOUT_MINUTES` | `15` |

### 3. Настройка Gmail (если нужен email)

Gmail используется для отправки писем подтверждения и сброса пароля.

**Шаг 1: Включить двухфакторную аутентификацию**
1. Перейди на https://myaccount.google.com/security
2. Найди "Двухэтапная аутентификация" → Включить
3. Следуй инструкциям (понадобится телефон)

**Шаг 2: Создать пароль приложения**
1. Перейди на https://myaccount.google.com/apppasswords
2. Выбери "Приложение" → "Другое" → введи название (например "poehali-auth")
3. Нажми "Создать"
4. Скопируй 16-символьный пароль (показывается один раз!)

**Шаг 3: Добавить переменные окружения**
```
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # 16-символьный пароль из шага 2
AUTH_URL=https://functions.poehali.dev/xxx  # URL функции
PASSWORD_RESET_URL=https://your-site.com/reset-password  # страница сброса на сайте
REQUIRE_EMAIL_VERIFICATION=true  # требовать подтверждение
```

**Важно:**
- Обычный пароль от Gmail НЕ подойдёт — только App Password
- App Password работает только при включённой 2FA
- Лимит Gmail: ~500 писем/день

---

## После деплоя

### 1. ВАЖНО: Обновить AUTH_URL

URL функции появится в `backend/func2url.json`. Обнови в коде:

```tsx
const AUTH_URL = "https://functions.poehali.dev/xxx"; // ← заменить
```

### 2. Проверить схему БД

```bash
curl "https://functions.poehali.dev/xxx?action=health"
```

---

## API

```
GET  /auth?action=health          - Проверка БД
GET  /auth?action=verify-email    - Подтверждение email (ссылка из письма)
POST /auth?action=register        - Регистрация
POST /auth?action=login           - Вход
POST /auth?action=refresh         - Обновление токена
POST /auth?action=logout          - Выход
POST /auth?action=reset-password  - Сброс пароля
```

### POST /auth?action=register

```json
{ "email": "user@example.com", "password": "SecurePass123", "name": "Иван" }

// Ответ (без email верификации):
{ "user_id": 1, "message": "Регистрация успешна", "email_verification_required": false }

// Ответ (с email верификацией):
{ "user_id": 1, "message": "Проверьте почту для подтверждения.", "email_verification_required": true }
```

### POST /auth?action=login

```json
{ "email": "user@example.com", "password": "SecurePass123" }

// Ответ:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 900,
  "user": { "id": 1, "email": "...", "name": "...", "email_verified": true }
}

// Ошибка (email не подтверждён):
{ "error": "Email не подтверждён. Проверьте почту." }
```

### POST /auth?action=reset-password

```json
// Запрос сброса:
{ "email": "user@example.com" }
// Если SMTP настроен — письмо отправится автоматически
// Если нет — токен вернётся в ответе (для разработки)

// Установка нового пароля:
{ "token": "...", "new_password": "NewPass123" }
```

---

## Frontend

```tsx
import { useAuth } from "./useAuth";

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
```

---

## Требования к паролю

- 8-128 символов
- Минимум 1 буква
- Минимум 1 цифра

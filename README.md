# Auth Email Extension

Авторизация и регистрация пользователей по email и паролю.

## Что включено

- `backend/auth-register/` — регистрация нового пользователя
- `backend/auth-login/` — вход с email и паролем
- `backend/auth-reset-password/` — сброс пароля
- `frontend/useAuth.ts` — React хук для управления авторизацией
- `frontend/LoginForm.tsx` — форма входа (shadcn/ui)
- `frontend/RegisterForm.tsx` — форма регистрации (shadcn/ui)
- `frontend/ResetPasswordForm.tsx` — форма сброса пароля (shadcn/ui)

## Установка

### 1. База данных

Выполни миграцию для создания таблиц:

```sql
-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- Сессии
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Токены сброса пароля
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
```

### 2. Секреты

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SESSION_LIFETIME_DAYS` | Время жизни сессии в днях (по умолчанию 30) |

### 3. Backend

Скопируй папки `backend/*` в свой проект и выполни sync_backend.

### 4. Frontend

Скопируй файлы из `frontend/` в свой проект:

```tsx
import { useAuth } from "@/lib/useAuth";
import { LoginForm } from "@/components/LoginForm";
import { RegisterForm } from "@/components/RegisterForm";
import { ResetPasswordForm } from "@/components/ResetPasswordForm";

function AuthPage() {
  const [view, setView] = useState<"login" | "register" | "reset">("login");

  const auth = useAuth({
    apiUrls: {
      login: func2url["auth-login"],
      register: func2url["auth-register"],
      resetPassword: func2url["auth-reset-password"],
    },
    onAuthChange: (user) => {
      if (user) router.push("/dashboard");
    },
  });

  if (view === "register") {
    return (
      <RegisterForm
        onRegister={auth.register}
        onSuccess={() => router.push("/dashboard")}
        onLoginClick={() => setView("login")}
        error={auth.error}
        isLoading={auth.isLoading}
        className="w-full max-w-md"
      />
    );
  }

  if (view === "reset") {
    return (
      <ResetPasswordForm
        onRequestReset={auth.requestPasswordReset}
        onResetPassword={auth.resetPassword}
        onLoginClick={() => setView("login")}
        error={auth.error}
        className="w-full max-w-md"
      />
    );
  }

  return (
    <LoginForm
      onLogin={auth.login}
      onSuccess={() => router.push("/dashboard")}
      onRegisterClick={() => setView("register")}
      onForgotPasswordClick={() => setView("reset")}
      error={auth.error}
      isLoading={auth.isLoading}
      className="w-full max-w-md"
    />
  );
}
```

## API

### POST /auth-register

Регистрация нового пользователя.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepass123",
  "name": "Иван Иванов"
}
```

**Response (201):**
```json
{
  "user_id": 1,
  "message": "Регистрация успешна"
}
```

### POST /auth-login

Авторизация пользователя.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepass123"
}
```

**Response (200):**
```json
{
  "session_token": "abc123...",
  "expires_at": "2025-01-28T10:00:00Z",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "Иван Иванов"
  }
}
```

### POST /auth-reset-password

**Шаг 1: Запрос сброса**
```json
{ "email": "user@example.com" }
```

**Шаг 2: Сброс пароля**
```json
{
  "token": "reset_token_here",
  "new_password": "newSecurePass123"
}
```

## Безопасность

- Пароли хранятся как SHA-256 хеш с уникальной солью
- Сессионные токены: 256-bit secure random
- Токены сброса пароля действуют 24 часа
- При сбросе пароля все сессии пользователя инвалидируются

## Требования к паролю

- Минимум 8 символов
- Хотя бы одна буква
- Хотя бы одна цифра

## Чеклист

- [ ] Миграция БД применена
- [ ] Backend функции задеплоены
- [ ] Frontend компоненты добавлены
- [ ] shadcn/ui компоненты установлены (Button, Input, Label, Card)
- [ ] Тестовая регистрация проходит
- [ ] Тестовый вход проходит

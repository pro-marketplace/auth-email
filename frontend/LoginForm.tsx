/**
 * Auth Email Extension - Login Form
 *
 * Форма входа с использованием shadcn/ui компонентов.
 */
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// ============================================================================
// ТИПЫ
// ============================================================================

interface LoginFormProps {
  /** Функция входа из useAuth */
  onLogin: (payload: { email: string; password: string }) => Promise<boolean>;
  /** Callback после успешного входа */
  onSuccess?: () => void;
  /** Переход на регистрацию */
  onRegisterClick?: () => void;
  /** Переход на сброс пароля */
  onForgotPasswordClick?: () => void;
  /** Ошибка из useAuth */
  error?: string | null;
  /** Сообщение об успехе (например, после сброса пароля) */
  successMessage?: string | null;
  /** Состояние загрузки */
  isLoading?: boolean;
  /** CSS класс для Card */
  className?: string;
}

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

export function LoginForm({
  onLogin,
  onSuccess,
  onRegisterClick,
  onForgotPasswordClick,
  error,
  successMessage,
  isLoading = false,
  className = "",
}: LoginFormProps): React.ReactElement {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (!email || !password) {
      setLocalError("Заполните все поля");
      return;
    }

    const success = await onLogin({ email, password });
    if (success) {
      onSuccess?.();
    }
  };

  const displayError = error || localError;

  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Вход</CardTitle>
        <CardDescription>
          Введите email и пароль для входа в аккаунт
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {successMessage && (
            <div className="text-sm text-green-600 bg-green-50 p-3 rounded-md">
              {successMessage}
            </div>
          )}

          {displayError && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
              {displayError}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="mail@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              autoComplete="email"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Пароль</Label>
              {onForgotPasswordClick && (
                <button
                  type="button"
                  onClick={onForgotPasswordClick}
                  className="text-sm text-muted-foreground hover:text-primary underline-offset-4 hover:underline"
                >
                  Забыли пароль?
                </button>
              )}
            </div>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              autoComplete="current-password"
            />
          </div>
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Вход..." : "Войти"}
          </Button>

          {onRegisterClick && (
            <p className="text-sm text-muted-foreground text-center">
              Нет аккаунта?{" "}
              <button
                type="button"
                onClick={onRegisterClick}
                className="text-primary hover:underline underline-offset-4"
              >
                Зарегистрироваться
              </button>
            </p>
          )}
        </CardFooter>
      </form>
    </Card>
  );
}

// ============================================================================
// ПРИМЕР ИСПОЛЬЗОВАНИЯ
// ============================================================================

/*
import { useAuth } from "./useAuth";
import { LoginForm } from "./LoginForm";

// URL функции из настроек расширения (обновляется после деплоя)
const AUTH_URL = "https://functions.poehali.dev/xxx";

function AuthPage() {
  const { login, error, isLoading } = useAuth({
    apiUrls: {
      login: `${AUTH_URL}?action=login`,
      register: `${AUTH_URL}?action=register`,
      refresh: `${AUTH_URL}?action=refresh`,
      logout: `${AUTH_URL}?action=logout`,
      resetPassword: `${AUTH_URL}?action=reset-password`,
    },
  });

  return (
    <div className="min-h-screen flex items-center justify-center">
      <LoginForm
        onLogin={login}
        onSuccess={() => window.location.href = "/dashboard"}
        onRegisterClick={() => setView("register")}
        onForgotPasswordClick={() => setView("forgot")}
        error={error}
        isLoading={isLoading}
        className="w-full max-w-md"
      />
    </div>
  );
}
*/

export default LoginForm;

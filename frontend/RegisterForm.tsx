/**
 * Auth Email Extension - Register Form
 *
 * Форма регистрации с использованием shadcn/ui компонентов.
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

interface RegisterFormProps {
  /** Функция регистрации из useAuth */
  onRegister: (payload: {
    email: string;
    password: string;
    name?: string;
  }) => Promise<boolean>;
  /** Callback после успешной регистрации */
  onSuccess?: () => void;
  /** Переход на вход */
  onLoginClick?: () => void;
  /** Ошибка из useAuth */
  error?: string | null;
  /** Состояние загрузки */
  isLoading?: boolean;
  /** CSS класс для Card */
  className?: string;
}

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

export function RegisterForm({
  onRegister,
  onSuccess,
  onLoginClick,
  error,
  isLoading = false,
  className = "",
}: RegisterFormProps): React.ReactElement {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (!email || !password) {
      setLocalError("Заполните обязательные поля");
      return;
    }

    if (password !== confirmPassword) {
      setLocalError("Пароли не совпадают");
      return;
    }

    if (password.length < 8) {
      setLocalError("Пароль должен содержать минимум 8 символов");
      return;
    }

    const success = await onRegister({
      email,
      password,
      name: name || undefined,
    });

    if (success) {
      onSuccess?.();
    }
  };

  const displayError = error || localError;

  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Регистрация</CardTitle>
        <CardDescription>
          Создайте аккаунт для начала работы
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {displayError && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
              {displayError}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="name">Имя</Label>
            <Input
              id="name"
              type="text"
              placeholder="Иван Иванов"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={isLoading}
              autoComplete="name"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">
              Email <span className="text-destructive">*</span>
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="mail@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              autoComplete="email"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">
              Пароль <span className="text-destructive">*</span>
            </Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              autoComplete="new-password"
              required
            />
            <p className="text-xs text-muted-foreground">
              Минимум 8 символов, буквы и цифры
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword">
              Подтвердите пароль <span className="text-destructive">*</span>
            </Label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={isLoading}
              autoComplete="new-password"
              required
            />
          </div>
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Регистрация..." : "Зарегистрироваться"}
          </Button>

          {onLoginClick && (
            <p className="text-sm text-muted-foreground text-center">
              Уже есть аккаунт?{" "}
              <button
                type="button"
                onClick={onLoginClick}
                className="text-primary hover:underline underline-offset-4"
              >
                Войти
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
import { RegisterForm } from "./RegisterForm";

function AuthPage() {
  const { register, error, isLoading } = useAuth({
    apiUrls: {
      login: func2url["auth-login"],
      register: func2url["auth-register"],
      resetPassword: func2url["auth-reset-password"],
    },
  });

  return (
    <div className="min-h-screen flex items-center justify-center">
      <RegisterForm
        onRegister={register}
        onSuccess={() => window.location.href = "/dashboard"}
        onLoginClick={() => setView("login")}
        error={error}
        isLoading={isLoading}
        className="w-full max-w-md"
      />
    </div>
  );
}
*/

/**
 * Auth Email Extension - Register Form
 *
 * Форма регистрации с поддержкой верификации email через 6-значный код.
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
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";

// ============================================================================
// ТИПЫ
// ============================================================================

interface RegisterResult {
  success: boolean;
  emailVerificationRequired: boolean;
  message?: string;
}

interface RegisterFormProps {
  /** Функция регистрации из useAuth */
  onRegister: (payload: {
    email: string;
    password: string;
    name?: string;
  }) => Promise<RegisterResult>;
  /** Функция верификации email из useAuth */
  onVerifyEmail: (email: string, code: string) => Promise<boolean>;
  /** Функция входа из useAuth */
  onLogin: (payload: { email: string; password: string }) => Promise<boolean>;
  /** Callback после успешной регистрации и входа */
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

type Step = "register" | "verify";

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

export function RegisterForm({
  onRegister,
  onVerifyEmail,
  onLogin,
  onSuccess,
  onLoginClick,
  error,
  isLoading = false,
  className = "",
}: RegisterFormProps): React.ReactElement {
  const [step, setStep] = useState<Step>("register");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [code, setCode] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
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

    const result = await onRegister({
      email,
      password,
      name: name || undefined,
    });

    if (result.success) {
      if (result.emailVerificationRequired) {
        setMessage(result.message || "Код отправлен на email");
        setStep("verify");
      } else {
        onSuccess?.();
      }
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (code.length !== 6) {
      setLocalError("Введите 6-значный код");
      return;
    }

    const verified = await onVerifyEmail(email, code);

    if (verified) {
      // Auto-login after verification
      const loggedIn = await onLogin({ email, password });
      if (loggedIn) {
        onSuccess?.();
      } else {
        // If auto-login failed, redirect to login page
        onLoginClick?.();
      }
    }
  };

  const handleResend = async () => {
    setLocalError(null);
    setCode("");
    setIsResending(true);

    try {
      const result = await onRegister({
        email,
        password,
        name: name || undefined,
      });

      if (result.success) {
        setMessage("Код отправлен повторно");
      }
    } finally {
      setIsResending(false);
    }
  };

  const displayError = error || localError;

  // ============================================================================
  // STEP: VERIFY EMAIL
  // ============================================================================

  if (step === "verify") {
    return (
      <Card className={className}>
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl">Подтверждение email</CardTitle>
          <CardDescription>
            Введите 6-значный код, отправленный на {email}
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleVerify}>
          <CardContent className="space-y-4">
            {message && (
              <div className="text-sm text-green-600 bg-green-50 p-3 rounded-md">
                {message}
              </div>
            )}

            {displayError && (
              <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                {displayError}
              </div>
            )}

            <div className="flex justify-center py-4">
              <InputOTP
                maxLength={6}
                value={code}
                onChange={setCode}
                disabled={isLoading}
              >
                <InputOTPGroup>
                  <InputOTPSlot index={0} />
                  <InputOTPSlot index={1} />
                  <InputOTPSlot index={2} />
                  <InputOTPSlot index={3} />
                  <InputOTPSlot index={4} />
                  <InputOTPSlot index={5} />
                </InputOTPGroup>
              </InputOTP>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={isLoading || code.length !== 6}>
              {isLoading ? "Проверка..." : "Подтвердить"}
            </Button>

            <div className="flex items-center justify-between w-full text-sm">
              <button
                type="button"
                onClick={() => setStep("register")}
                className="text-muted-foreground hover:text-primary"
              >
                ← Назад
              </button>
              <button
                type="button"
                onClick={handleResend}
                disabled={isLoading || isResending}
                className="text-primary hover:underline underline-offset-4 disabled:opacity-50"
              >
                {isResending ? "Отправка..." : "Отправить код повторно"}
              </button>
            </div>
          </CardFooter>
        </form>
      </Card>
    );
  }

  // ============================================================================
  // STEP: REGISTER
  // ============================================================================

  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Регистрация</CardTitle>
        <CardDescription>
          Создайте аккаунт для начала работы
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleRegister}>
        <CardContent className="space-y-4">
          {displayError && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
              {displayError}
              {displayError?.includes("уже существует") && onLoginClick && (
                <button
                  type="button"
                  onClick={onLoginClick}
                  className="block mt-2 text-primary hover:underline underline-offset-4"
                >
                  Войти в существующий аккаунт
                </button>
              )}
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

const AUTH_URL = "https://functions.poehali.dev/xxx";

function AuthPage() {
  const { register, verifyEmail, login, error, isLoading } = useAuth({
    apiUrls: {
      login: `${AUTH_URL}?action=login`,
      register: `${AUTH_URL}?action=register`,
      verifyEmail: `${AUTH_URL}?action=verify-email`,
      refresh: `${AUTH_URL}?action=refresh`,
      logout: `${AUTH_URL}?action=logout`,
      resetPassword: `${AUTH_URL}?action=reset-password`,
    },
  });

  return (
    <div className="min-h-screen flex items-center justify-center">
      <RegisterForm
        onRegister={register}
        onVerifyEmail={verifyEmail}
        onLogin={login}
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

export default RegisterForm;

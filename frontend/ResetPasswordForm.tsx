/**
 * Auth Email Extension - Reset Password Form
 *
 * Форма сброса пароля с использованием 6-значных кодов.
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

interface ResetPasswordFormProps {
  /** Запрос сброса пароля (отправка кода на email) */
  onRequestReset: (email: string) => Promise<{ code?: string }>;
  /** Сброс пароля с кодом */
  onResetPassword: (
    email: string,
    code: string,
    newPassword: string
  ) => Promise<boolean>;
  /** Callback после успешного сброса */
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

type Step = "request" | "reset" | "success";

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

export function ResetPasswordForm({
  onRequestReset,
  onResetPassword,
  onSuccess,
  onLoginClick,
  error,
  isLoading = false,
  className = "",
}: ResetPasswordFormProps): React.ReactElement {
  const [step, setStep] = useState<Step>("request");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localLoading, setLocalLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loading = isLoading || localLoading;

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    setMessage(null);

    if (!email) {
      setLocalError("Введите email");
      return;
    }

    setLocalLoading(true);

    try {
      const result = await onRequestReset(email);

      // Если SMTP не настроен, код приходит в ответе
      if (result.code) {
        setCode(result.code);
        setMessage("Код получен (SMTP не настроен)");
      } else {
        setMessage("Код отправлен на email");
      }
      setStep("reset");
    } catch {
      setLocalError("Ошибка отправки");
    } finally {
      setLocalLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (code.length !== 6) {
      setLocalError("Введите 6-значный код");
      return;
    }

    if (!newPassword) {
      setLocalError("Введите новый пароль");
      return;
    }

    if (newPassword !== confirmPassword) {
      setLocalError("Пароли не совпадают");
      return;
    }

    if (newPassword.length < 8) {
      setLocalError("Пароль должен содержать минимум 8 символов");
      return;
    }

    setLocalLoading(true);

    try {
      const success = await onResetPassword(email, code, newPassword);
      if (success) {
        setStep("success");
        onSuccess?.();
      }
    } catch {
      setLocalError("Ошибка сброса пароля");
    } finally {
      setLocalLoading(false);
    }
  };

  const handleResend = async () => {
    setLocalError(null);
    setCode("");
    setLocalLoading(true);

    try {
      const result = await onRequestReset(email);
      if (result.code) {
        setCode(result.code);
        setMessage("Код получен повторно");
      } else {
        setMessage("Код отправлен повторно");
      }
    } catch {
      setLocalError("Ошибка отправки");
    } finally {
      setLocalLoading(false);
    }
  };

  const displayError = error || localError;

  // ============================================================================
  // STEP: SUCCESS
  // ============================================================================

  if (step === "success") {
    return (
      <Card className={className}>
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl">Готово</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-green-600 bg-green-50 p-3 rounded-md">
            Пароль успешно изменён. Теперь вы можете войти с новым паролем.
          </div>
        </CardContent>
        <CardFooter>
          {onLoginClick && (
            <Button onClick={onLoginClick} className="w-full">
              Войти
            </Button>
          )}
        </CardFooter>
      </Card>
    );
  }

  // ============================================================================
  // STEP: RESET (ввод кода и нового пароля)
  // ============================================================================

  if (step === "reset") {
    return (
      <Card className={className}>
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl">Новый пароль</CardTitle>
          <CardDescription>
            Введите код и новый пароль для {email}
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleResetPassword}>
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

            <div className="space-y-2">
              <Label>Код подтверждения</Label>
              <div className="flex justify-center py-2">
                <InputOTP
                  maxLength={6}
                  value={code}
                  onChange={setCode}
                  disabled={loading}
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
            </div>

            <div className="space-y-2">
              <Label htmlFor="newPassword">Новый пароль</Label>
              <Input
                id="newPassword"
                type="password"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={loading}
                autoComplete="new-password"
              />
              <p className="text-xs text-muted-foreground">
                Минимум 8 символов, буквы и цифры
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Подтвердите пароль</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading}
                autoComplete="new-password"
              />
            </div>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button
              type="submit"
              className="w-full"
              disabled={loading || code.length !== 6}
            >
              {loading ? "Сохранение..." : "Сохранить пароль"}
            </Button>

            <div className="flex items-center justify-between w-full text-sm">
              <button
                type="button"
                onClick={() => {
                  setStep("request");
                  setCode("");
                  setMessage(null);
                }}
                className="text-muted-foreground hover:text-primary"
              >
                ← Назад
              </button>
              <button
                type="button"
                onClick={handleResend}
                disabled={loading}
                className="text-primary hover:underline underline-offset-4 disabled:opacity-50"
              >
                {loading ? "Отправка..." : "Отправить код повторно"}
              </button>
            </div>
          </CardFooter>
        </form>
      </Card>
    );
  }

  // ============================================================================
  // STEP: REQUEST (ввод email)
  // ============================================================================

  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Сброс пароля</CardTitle>
        <CardDescription>
          Введите email для получения кода сброса пароля
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleRequestReset}>
        <CardContent className="space-y-4">
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
              disabled={loading}
              autoComplete="email"
            />
          </div>
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Отправка..." : "Получить код"}
          </Button>

          {onLoginClick && (
            <button
              type="button"
              onClick={onLoginClick}
              className="text-sm text-muted-foreground hover:text-primary underline-offset-4 hover:underline"
            >
              Вернуться ко входу
            </button>
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
import { ResetPasswordForm } from "./ResetPasswordForm";

const AUTH_URL = "https://functions.poehali.dev/xxx";

function ResetPasswordPage() {
  const { requestPasswordReset, resetPassword, error, isLoading } = useAuth({
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
      <ResetPasswordForm
        onRequestReset={requestPasswordReset}
        onResetPassword={resetPassword}
        onSuccess={() => setView("login")}
        onLoginClick={() => setView("login")}
        error={error}
        isLoading={isLoading}
        className="w-full max-w-md"
      />
    </div>
  );
}
*/

export default ResetPasswordForm;

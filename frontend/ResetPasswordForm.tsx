/**
 * Auth Email Extension - Reset Password Form
 *
 * Форма сброса пароля с использованием shadcn/ui компонентов.
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

interface ResetPasswordFormProps {
  /** Запрос сброса пароля (отправка email) */
  onRequestReset: (email: string) => Promise<{ token?: string }>;
  /** Сброс пароля с токеном */
  onResetPassword: (token: string, newPassword: string) => Promise<boolean>;
  /** Callback после успешного сброса */
  onSuccess?: () => void;
  /** Переход на вход */
  onLoginClick?: () => void;
  /** Ошибка из useAuth */
  error?: string | null;
  /** Токен из URL (если есть) */
  initialToken?: string;
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
  initialToken,
  className = "",
}: ResetPasswordFormProps): React.ReactElement {
  const [step, setStep] = useState<Step>(initialToken ? "reset" : "request");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState(initialToken || "");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (!email) {
      setLocalError("Введите email");
      return;
    }

    setIsLoading(true);

    try {
      const result = await onRequestReset(email);
      setSuccessMessage("Инструкции отправлены на email");

      // For demo: if token returned, go to reset step
      if (result.token) {
        setToken(result.token);
        setStep("reset");
        setSuccessMessage(null);
      }
    } catch {
      setLocalError("Ошибка отправки");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (!token || !newPassword) {
      setLocalError("Заполните все поля");
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

    setIsLoading(true);

    try {
      const success = await onResetPassword(token, newPassword);
      if (success) {
        setStep("success");
        onSuccess?.();
      }
    } catch {
      setLocalError("Ошибка сброса пароля");
    } finally {
      setIsLoading(false);
    }
  };

  const displayError = error || localError;

  // Success state
  if (step === "success") {
    return (
      <Card className={className}>
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl">Пароль изменён</CardTitle>
          <CardDescription>
            Ваш пароль успешно обновлён. Теперь вы можете войти с новым паролем.
          </CardDescription>
        </CardHeader>
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

  // Request reset step
  if (step === "request") {
    return (
      <Card className={className}>
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl">Сброс пароля</CardTitle>
          <CardDescription>
            Введите email и мы отправим инструкции для сброса пароля
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleRequestReset}>
          <CardContent className="space-y-4">
            {displayError && (
              <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                {displayError}
              </div>
            )}

            {successMessage && (
              <div className="text-sm text-primary bg-primary/10 p-3 rounded-md">
                {successMessage}
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
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Отправка..." : "Отправить"}
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

  // Reset password step
  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Новый пароль</CardTitle>
        <CardDescription>Введите новый пароль для вашего аккаунта</CardDescription>
      </CardHeader>
      <form onSubmit={handleResetPassword}>
        <CardContent className="space-y-4">
          {displayError && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
              {displayError}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="newPassword">Новый пароль</Label>
            <Input
              id="newPassword"
              type="password"
              placeholder="••••••••"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={isLoading}
              autoComplete="new-password"
            />
            <p className="text-xs text-muted-foreground">
              Минимум 8 символов
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
              disabled={isLoading}
              autoComplete="new-password"
            />
          </div>
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Сохранение..." : "Сохранить пароль"}
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

export default ResetPasswordForm;

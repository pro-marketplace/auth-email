/**
 * Auth Email Extension - User Profile
 *
 * Компонент отображения данных пользователя после входа.
 */
import React from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

// ============================================================================
// ТИПЫ
// ============================================================================

interface User {
  id: number;
  email: string;
  name: string | null;
  email_verified?: boolean;
}

interface UserProfileProps {
  /** Данные пользователя из useAuth */
  user: User;
  /** Функция выхода из useAuth */
  onLogout: () => Promise<void>;
  /** Состояние загрузки */
  isLoading?: boolean;
  /** CSS класс для Card */
  className?: string;
}

// ============================================================================
// КОМПОНЕНТ
// ============================================================================

export function UserProfile({
  user,
  onLogout,
  isLoading = false,
  className = "",
}: UserProfileProps): React.ReactElement {
  const initials = user.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user.email[0].toUpperCase();

  const handleLogout = async () => {
    await onLogout();
  };

  return (
    <Card className={className}>
      <CardHeader className="text-center">
        <div className="flex justify-center mb-4">
          <Avatar className="h-20 w-20">
            <AvatarFallback className="text-2xl bg-primary text-primary-foreground">
              {initials}
            </AvatarFallback>
          </Avatar>
        </div>
        <CardTitle className="text-xl">
          {user.name || "Пользователь"}
        </CardTitle>
        <CardDescription>{user.email}</CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">ID</span>
          <span className="font-mono">{user.id}</span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Email</span>
          <div className="flex items-center gap-2">
            <span>{user.email}</span>
            {user.email_verified !== undefined && (
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  user.email_verified
                    ? "bg-green-100 text-green-700"
                    : "bg-yellow-100 text-yellow-700"
                }`}
              >
                {user.email_verified ? "✓" : "не подтверждён"}
              </span>
            )}
          </div>
        </div>

        {user.name && (
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Имя</span>
            <span>{user.name}</span>
          </div>
        )}
      </CardContent>

      <CardFooter>
        <Button
          variant="outline"
          className="w-full"
          onClick={handleLogout}
          disabled={isLoading}
        >
          {isLoading ? "Выход..." : "Выйти"}
        </Button>
      </CardFooter>
    </Card>
  );
}

// ============================================================================
// ПРИМЕР ИСПОЛЬЗОВАНИЯ
// ============================================================================

/*
import { useAuth } from "./useAuth";
import { LoginForm } from "./LoginForm";
import { UserProfile } from "./UserProfile";

const AUTH_URL = "https://functions.poehali.dev/xxx";

function AuthPage() {
  const { user, isAuthenticated, login, logout, error, isLoading } = useAuth({
    apiUrls: {
      login: `${AUTH_URL}?action=login`,
      register: `${AUTH_URL}?action=register`,
      verifyEmail: `${AUTH_URL}?action=verify-email`,
      refresh: `${AUTH_URL}?action=refresh`,
      logout: `${AUTH_URL}?action=logout`,
      resetPassword: `${AUTH_URL}?action=reset-password`,
    },
  });

  // Показать профиль если авторизован
  if (isAuthenticated && user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <UserProfile
          user={user}
          onLogout={logout}
          isLoading={isLoading}
          className="w-full max-w-md"
        />
      </div>
    );
  }

  // Показать форму входа
  return (
    <div className="min-h-screen flex items-center justify-center">
      <LoginForm
        onLogin={login}
        error={error}
        isLoading={isLoading}
        className="w-full max-w-md"
      />
    </div>
  );
}
*/

export default UserProfile;

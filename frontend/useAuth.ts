/**
 * Auth Email Extension - useAuth Hook
 *
 * Хук для управления авторизацией в React приложении.
 */
import { useState, useCallback, useEffect } from "react";

// ============================================================================
// ТИПЫ
// ============================================================================

export interface User {
  id: number;
  email: string;
  name: string | null;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  name?: string;
}

export interface ResetPasswordPayload {
  email?: string;
  token?: string;
  newPassword?: string;
}

interface AuthApiUrls {
  login: string;
  register: string;
  resetPassword: string;
}

interface UseAuthOptions {
  apiUrls: AuthApiUrls;
  onAuthChange?: (user: User | null) => void;
  storageKey?: string;
}

interface UseAuthReturn {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (payload: LoginPayload) => Promise<boolean>;
  register: (payload: RegisterPayload) => Promise<boolean>;
  logout: () => void;
  requestPasswordReset: (email: string) => Promise<{ token?: string }>;
  resetPassword: (token: string, newPassword: string) => Promise<boolean>;
}

// ============================================================================
// КОНСТАНТЫ
// ============================================================================

const DEFAULT_STORAGE_KEY = "auth_session";

// ============================================================================
// ХУК
// ============================================================================

export function useAuth(options: UseAuthOptions): UseAuthReturn {
  const { apiUrls, onAuthChange, storageKey = DEFAULT_STORAGE_KEY } = options;

  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load session from storage on mount
  useEffect(() => {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      try {
        const session = JSON.parse(stored);
        if (session.expires_at && new Date(session.expires_at) > new Date()) {
          setUser(session.user);
        } else {
          localStorage.removeItem(storageKey);
        }
      } catch {
        localStorage.removeItem(storageKey);
      }
    }
    setIsLoading(false);
  }, [storageKey]);

  // Notify on auth change
  useEffect(() => {
    onAuthChange?.(user);
  }, [user, onAuthChange]);

  /**
   * Login with email and password
   */
  const login = useCallback(
    async (payload: LoginPayload): Promise<boolean> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(apiUrls.login, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (!response.ok) {
          setError(data.error || "Ошибка авторизации");
          return false;
        }

        // Save session
        localStorage.setItem(
          storageKey,
          JSON.stringify({
            token: data.session_token,
            expires_at: data.expires_at,
            user: data.user,
          })
        );

        setUser(data.user);
        return true;
      } catch (err) {
        setError("Ошибка сети");
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [apiUrls.login, storageKey]
  );

  /**
   * Register new user
   */
  const register = useCallback(
    async (payload: RegisterPayload): Promise<boolean> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(apiUrls.register, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (!response.ok) {
          setError(data.error || "Ошибка регистрации");
          return false;
        }

        // Auto-login after registration
        return await login({ email: payload.email, password: payload.password });
      } catch (err) {
        setError("Ошибка сети");
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [apiUrls.register, login]
  );

  /**
   * Logout user
   */
  const logout = useCallback(() => {
    localStorage.removeItem(storageKey);
    setUser(null);
  }, [storageKey]);

  /**
   * Request password reset
   */
  const requestPasswordReset = useCallback(
    async (email: string): Promise<{ token?: string }> => {
      setError(null);

      try {
        const response = await fetch(apiUrls.resetPassword, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        });

        const data = await response.json();

        if (!response.ok) {
          setError(data.error || "Ошибка");
          return {};
        }

        return { token: data.reset_token };
      } catch (err) {
        setError("Ошибка сети");
        return {};
      }
    },
    [apiUrls.resetPassword]
  );

  /**
   * Reset password with token
   */
  const resetPassword = useCallback(
    async (token: string, newPassword: string): Promise<boolean> => {
      setError(null);

      try {
        const response = await fetch(apiUrls.resetPassword, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, new_password: newPassword }),
        });

        const data = await response.json();

        if (!response.ok) {
          setError(data.error || "Ошибка сброса пароля");
          return false;
        }

        return true;
      } catch (err) {
        setError("Ошибка сети");
        return false;
      }
    },
    [apiUrls.resetPassword]
  );

  return {
    user,
    isAuthenticated: !!user,
    isLoading,
    error,
    login,
    register,
    logout,
    requestPasswordReset,
    resetPassword,
  };
}

// ============================================================================
// УТИЛИТЫ
// ============================================================================

/**
 * Get session token from storage
 */
export function getSessionToken(storageKey = DEFAULT_STORAGE_KEY): string | null {
  try {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      const session = JSON.parse(stored);
      if (session.expires_at && new Date(session.expires_at) > new Date()) {
        return session.token;
      }
    }
  } catch {
    // ignore
  }
  return null;
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(storageKey = DEFAULT_STORAGE_KEY): boolean {
  return !!getSessionToken(storageKey);
}

/**
 * Auth Email Extension - useAuth Hook
 *
 * JWT-based authentication with localStorage for token storage.
 * Supports email verification with 6-digit codes.
 *
 * Usage:
 * const AUTH_URL = "https://functions.poehali.dev/xxx";
 * const auth = useAuth({
 *   apiUrls: {
 *     login: `${AUTH_URL}?action=login`,
 *     register: `${AUTH_URL}?action=register`,
 *     verifyEmail: `${AUTH_URL}?action=verify-email`,
 *     refresh: `${AUTH_URL}?action=refresh`,
 *     logout: `${AUTH_URL}?action=logout`,
 *     resetPassword: `${AUTH_URL}?action=reset-password`,
 *   },
 * });
 */
import { useState, useCallback, useEffect, useRef } from "react";

// ============================================================================
// ТИПЫ
// ============================================================================

const REFRESH_TOKEN_KEY = "auth_refresh_token";

export interface User {
  id: number;
  email: string;
  name: string | null;
  email_verified?: boolean;
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

export interface RegisterResult {
  success: boolean;
  emailVerificationRequired: boolean;
  message?: string;
}

interface AuthApiUrls {
  login: string;
  register: string;
  verifyEmail: string;
  refresh: string;
  logout: string;
  resetPassword: string;
}

interface UseAuthOptions {
  apiUrls: AuthApiUrls;
  onAuthChange?: (user: User | null) => void;
  autoRefresh?: boolean;
  refreshBeforeExpiry?: number;
}

interface UseAuthReturn {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  accessToken: string | null;
  login: (payload: LoginPayload) => Promise<boolean>;
  register: (payload: RegisterPayload) => Promise<RegisterResult>;
  verifyEmail: (email: string, code: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  requestPasswordReset: (email: string) => Promise<{ code?: string }>;
  resetPassword: (email: string, code: string, newPassword: string) => Promise<boolean>;
  getAuthHeader: () => { Authorization: string } | {};
}

// ============================================================================
// ЛОКАЛЬНОЕ ХРАНИЛИЩЕ
// ============================================================================

function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function setStoredRefreshToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

function clearStoredRefreshToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// ============================================================================
// ХУК
// ============================================================================

export function useAuth(options: UseAuthOptions): UseAuthReturn {
  const {
    apiUrls,
    onAuthChange,
    autoRefresh = true,
    refreshBeforeExpiry = 60,
  } = options;

  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearAuth = useCallback(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    setAccessToken(null);
    setUser(null);
    clearStoredRefreshToken();
  }, []);

  const scheduleRefresh = useCallback(
    (expiresInSeconds: number, refreshFn: () => Promise<boolean>) => {
      if (!autoRefresh) return;

      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }

      const refreshIn = Math.max((expiresInSeconds - refreshBeforeExpiry) * 1000, 1000);

      refreshTimerRef.current = setTimeout(async () => {
        const success = await refreshFn();
        if (!success) {
          clearAuth();
        }
      }, refreshIn);
    },
    [autoRefresh, refreshBeforeExpiry, clearAuth]
  );

  const refreshTokenFn = useCallback(async (): Promise<boolean> => {
    const storedRefreshToken = getStoredRefreshToken();
    if (!storedRefreshToken) {
      return false;
    }

    try {
      const response = await fetch(apiUrls.refresh, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: storedRefreshToken }),
      });

      if (!response.ok) {
        clearAuth();
        return false;
      }

      const data = await response.json();
      setAccessToken(data.access_token);
      setUser(data.user);
      scheduleRefresh(data.expires_in, refreshTokenFn);
      return true;
    } catch {
      clearAuth();
      return false;
    }
  }, [apiUrls.refresh, clearAuth, scheduleRefresh]);

  useEffect(() => {
    const restoreSession = async () => {
      const hasToken = !!getStoredRefreshToken();
      if (hasToken) {
        await refreshTokenFn();
      }
      setIsLoading(false);
    };

    restoreSession();

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, [refreshTokenFn]);

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

        setAccessToken(data.access_token);
        setUser(data.user);
        setStoredRefreshToken(data.refresh_token);
        scheduleRefresh(data.expires_in, refreshTokenFn);
        return true;
      } catch (err) {
        setError("Ошибка сети");
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [apiUrls.login, scheduleRefresh, refreshTokenFn]
  );

  /**
   * Register new user
   * Returns { success, emailVerificationRequired }
   */
  const register = useCallback(
    async (payload: RegisterPayload): Promise<RegisterResult> => {
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
          return { success: false, emailVerificationRequired: false };
        }

        // If email verification required, don't auto-login
        if (data.email_verification_required) {
          return {
            success: true,
            emailVerificationRequired: true,
            message: data.message,
          };
        }

        // Auto-login if no verification needed
        const loginSuccess = await login({
          email: payload.email,
          password: payload.password,
        });

        return {
          success: loginSuccess,
          emailVerificationRequired: false,
        };
      } catch (err) {
        setError("Ошибка сети");
        return { success: false, emailVerificationRequired: false };
      } finally {
        setIsLoading(false);
      }
    },
    [apiUrls.register, login]
  );

  /**
   * Verify email with 6-digit code
   */
  const verifyEmail = useCallback(
    async (email: string, code: string): Promise<boolean> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(apiUrls.verifyEmail, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, code }),
        });

        const data = await response.json();

        if (!response.ok) {
          setError(data.error || "Неверный код");
          return false;
        }

        return true;
      } catch {
        setError("Ошибка сети");
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [apiUrls.verifyEmail]
  );

  /**
   * Logout user
   */
  const logout = useCallback(async () => {
    const storedRefreshToken = getStoredRefreshToken();

    try {
      await fetch(apiUrls.logout, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: storedRefreshToken || "" }),
      });
    } catch {
      // Ignore errors
    }

    clearAuth();
  }, [apiUrls.logout, clearAuth]);

  /**
   * Request password reset code
   */
  const requestPasswordReset = useCallback(
    async (email: string): Promise<{ code?: string }> => {
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

        // reset_code returned only in dev mode (no SMTP)
        return { code: data.reset_code };
      } catch {
        setError("Ошибка сети");
        return {};
      }
    },
    [apiUrls.resetPassword]
  );

  /**
   * Reset password with email, code and new password
   */
  const resetPassword = useCallback(
    async (email: string, code: string, newPassword: string): Promise<boolean> => {
      setError(null);

      try {
        const response = await fetch(apiUrls.resetPassword, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, code, new_password: newPassword }),
        });

        const data = await response.json();

        if (!response.ok) {
          setError(data.error || "Ошибка сброса пароля");
          return false;
        }

        return true;
      } catch {
        setError("Ошибка сети");
        return false;
      }
    },
    [apiUrls.resetPassword]
  );

  /**
   * Get Authorization header for API requests
   */
  const getAuthHeader = useCallback(() => {
    if (!accessToken) return {};
    return { Authorization: `Bearer ${accessToken}` };
  }, [accessToken]);

  return {
    user,
    isAuthenticated: !!user && !!accessToken,
    isLoading,
    error,
    accessToken,
    login,
    register,
    verifyEmail,
    logout,
    refreshToken: refreshTokenFn,
    requestPasswordReset,
    resetPassword,
    getAuthHeader,
  };
}

// ============================================================================
// УТИЛИТЫ
// ============================================================================

export function mightBeAuthenticated(): boolean {
  return !!getStoredRefreshToken();
}

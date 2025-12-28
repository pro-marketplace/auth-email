/**
 * Auth Email Extension - useAuth Hook (Secure)
 *
 * JWT-based authentication with HttpOnly cookie for refresh token.
 * Access token in memory, refresh token in HttpOnly cookie (XSS-safe).
 *
 * Usage:
 * const AUTH_URL = func2url["auth"];
 * const auth = useAuth({
 *   apiUrls: {
 *     login: `${AUTH_URL}?action=login`,
 *     register: `${AUTH_URL}?action=register`,
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

export interface User {
  id: number;
  email: string;
  name: string | null;
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

interface AuthApiUrls {
  login: string;
  register: string;
  refresh: string;
  logout: string;
  resetPassword: string;
}

interface UseAuthOptions {
  apiUrls: AuthApiUrls;
  onAuthChange?: (user: User | null) => void;
  /** Auto-refresh access token before expiry (default: true) */
  autoRefresh?: boolean;
  /** Refresh token N seconds before expiry (default: 60) */
  refreshBeforeExpiry?: number;
}

interface UseAuthReturn {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  accessToken: string | null;
  login: (payload: LoginPayload) => Promise<boolean>;
  register: (payload: RegisterPayload) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  requestPasswordReset: (email: string) => Promise<{ token?: string }>;
  resetPassword: (token: string, newPassword: string) => Promise<boolean>;
  getAuthHeader: () => { Authorization: string } | {};
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

  // Clear state
  const clearAuth = useCallback(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    setAccessToken(null);
    setUser(null);
  }, []);

  // Schedule token refresh
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

  // Refresh access token using HttpOnly cookie
  const refreshTokenFn = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(apiUrls.refresh, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // Send HttpOnly cookie
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

  // Try to restore session on mount
  useEffect(() => {
    const restoreSession = async () => {
      // Try to refresh - if cookie exists, we'll get a new access token
      await refreshTokenFn();
      setIsLoading(false);
    };

    restoreSession();

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, [refreshTokenFn]);

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
          credentials: "include", // Accept Set-Cookie
          body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (!response.ok) {
          setError(data.error || "Ошибка авторизации");
          return false;
        }

        setAccessToken(data.access_token);
        setUser(data.user);
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
  const logout = useCallback(async () => {
    try {
      await fetch(apiUrls.logout, {
        method: "POST",
        credentials: "include", // Send cookie to revoke, receive Set-Cookie to clear
      });
    } catch {
      // Ignore errors
    }

    clearAuth();
  }, [apiUrls.logout, clearAuth]);

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
      } catch {
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

/**
 * Check if user might be authenticated (has session).
 * Note: This doesn't verify the token, just checks if refresh might work.
 * For actual auth state, use the useAuth hook.
 */
export function mightBeAuthenticated(): boolean {
  // We can't check HttpOnly cookies from JS
  // This function exists for API compatibility but always returns false
  // Use useAuth().isAuthenticated for actual auth state
  return false;
}

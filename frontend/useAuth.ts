/**
 * Auth Email Extension - useAuth Hook
 *
 * JWT-based authentication with automatic token refresh.
 * Adapted for Yandex Cloud Functions (no HttpOnly cookies).
 * Refresh token stored in localStorage, passed via X-Refresh-Token header.
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
  /** Storage key prefix (default: "auth") */
  storagePrefix?: string;
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
    storagePrefix = "auth",
  } = options;

  const KEYS = {
    accessToken: `${storagePrefix}_access_token`,
    refreshToken: `${storagePrefix}_refresh_token`,
    accessExpiry: `${storagePrefix}_access_expiry`,
    refreshExpiry: `${storagePrefix}_refresh_expiry`,
    user: `${storagePrefix}_user`,
  };

  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear all tokens
  const clearTokens = useCallback(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }

    setAccessToken(null);
    setUser(null);

    Object.values(KEYS).forEach((key) => localStorage.removeItem(key));
  }, [KEYS]);

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
          clearTokens();
        }
      }, refreshIn);
    },
    [autoRefresh, refreshBeforeExpiry, clearTokens]
  );

  // Save tokens to state and localStorage
  const saveTokens = useCallback(
    (
      newAccessToken: string,
      newRefreshToken: string,
      accessExpiresIn: number,
      refreshExpiresIn: number,
      userData: User,
      refreshFn: () => Promise<boolean>
    ) => {
      const accessExpiry = Date.now() + accessExpiresIn * 1000;
      const refreshExpiry = Date.now() + refreshExpiresIn * 1000;

      setAccessToken(newAccessToken);
      setUser(userData);

      localStorage.setItem(KEYS.accessToken, newAccessToken);
      localStorage.setItem(KEYS.refreshToken, newRefreshToken);
      localStorage.setItem(KEYS.accessExpiry, accessExpiry.toString());
      localStorage.setItem(KEYS.refreshExpiry, refreshExpiry.toString());
      localStorage.setItem(KEYS.user, JSON.stringify(userData));

      scheduleRefresh(accessExpiresIn, refreshFn);
    },
    [KEYS, scheduleRefresh]
  );

  // Update only access token (after refresh)
  const updateAccessToken = useCallback(
    (newAccessToken: string, expiresIn: number, userData: User, refreshFn: () => Promise<boolean>) => {
      const accessExpiry = Date.now() + expiresIn * 1000;

      setAccessToken(newAccessToken);
      setUser(userData);

      localStorage.setItem(KEYS.accessToken, newAccessToken);
      localStorage.setItem(KEYS.accessExpiry, accessExpiry.toString());
      localStorage.setItem(KEYS.user, JSON.stringify(userData));

      scheduleRefresh(expiresIn, refreshFn);
    },
    [KEYS, scheduleRefresh]
  );

  // Refresh access token
  const refreshTokenFn = useCallback(async (): Promise<boolean> => {
    const storedRefreshToken = localStorage.getItem(KEYS.refreshToken);
    const refreshExpiry = localStorage.getItem(KEYS.refreshExpiry);

    if (!storedRefreshToken || !refreshExpiry) {
      return false;
    }

    // Check if refresh token expired
    if (parseInt(refreshExpiry, 10) < Date.now()) {
      clearTokens();
      return false;
    }

    try {
      const response = await fetch(apiUrls.refresh, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Refresh-Token": storedRefreshToken,
        },
      });

      if (!response.ok) {
        clearTokens();
        return false;
      }

      const data = await response.json();
      updateAccessToken(data.access_token, data.expires_in, data.user, refreshTokenFn);
      return true;
    } catch {
      clearTokens();
      return false;
    }
  }, [apiUrls.refresh, KEYS, clearTokens, updateAccessToken]);

  // Load session on mount
  useEffect(() => {
    const loadSession = async () => {
      const storedAccessToken = localStorage.getItem(KEYS.accessToken);
      const storedAccessExpiry = localStorage.getItem(KEYS.accessExpiry);
      const storedUser = localStorage.getItem(KEYS.user);

      if (storedAccessToken && storedAccessExpiry && storedUser) {
        const expiry = parseInt(storedAccessExpiry, 10);
        const now = Date.now();

        if (expiry > now) {
          // Access token still valid
          const remainingSeconds = Math.floor((expiry - now) / 1000);
          setAccessToken(storedAccessToken);
          setUser(JSON.parse(storedUser));
          scheduleRefresh(remainingSeconds, refreshTokenFn);
        } else {
          // Access token expired, try refresh
          await refreshTokenFn();
        }
      }

      setIsLoading(false);
    };

    loadSession();

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, [KEYS, refreshTokenFn, scheduleRefresh]);

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

        saveTokens(
          data.access_token,
          data.refresh_token,
          data.expires_in,
          data.refresh_expires_in,
          data.user,
          refreshTokenFn
        );
        return true;
      } catch (err) {
        setError("Ошибка сети");
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [apiUrls.login, saveTokens, refreshTokenFn]
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
    const storedRefreshToken = localStorage.getItem(KEYS.refreshToken);

    if (storedRefreshToken) {
      try {
        await fetch(apiUrls.logout, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Refresh-Token": storedRefreshToken,
          },
        });
      } catch {
        // Ignore errors, clear locally anyway
      }
    }

    clearTokens();
  }, [apiUrls.logout, KEYS, clearTokens]);

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
 * Get access token from storage (for non-React code)
 */
export function getAccessToken(storagePrefix = "auth"): string | null {
  const token = localStorage.getItem(`${storagePrefix}_access_token`);
  const expiry = localStorage.getItem(`${storagePrefix}_access_expiry`);

  if (token && expiry && parseInt(expiry, 10) > Date.now()) {
    return token;
  }

  return null;
}

/**
 * Check if user is authenticated (for non-React code)
 */
export function isAuthenticated(storagePrefix = "auth"): boolean {
  return !!getAccessToken(storagePrefix);
}

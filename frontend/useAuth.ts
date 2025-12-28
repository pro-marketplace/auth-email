/**
 * Auth Email Extension - useAuth Hook (Secure)
 *
 * JWT-based authentication with automatic token refresh.
 * Refresh token stored in HttpOnly cookie (handled by backend).
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
// КОНСТАНТЫ
// ============================================================================

const ACCESS_TOKEN_KEY = "access_token";
const TOKEN_EXPIRY_KEY = "token_expiry";
const USER_KEY = "auth_user";

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

  // Schedule token refresh
  const scheduleRefresh = useCallback(
    (expiresIn: number) => {
      if (!autoRefresh) return;

      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }

      const refreshIn = Math.max((expiresIn - refreshBeforeExpiry) * 1000, 0);

      refreshTimerRef.current = setTimeout(async () => {
        await refreshTokenFn();
      }, refreshIn);
    },
    [autoRefresh, refreshBeforeExpiry]
  );

  // Save tokens to memory and localStorage (for access token only)
  const saveTokens = useCallback(
    (token: string, expiresIn: number, userData: User) => {
      const expiry = Date.now() + expiresIn * 1000;

      setAccessToken(token);
      setUser(userData);

      // Store in localStorage for persistence across tabs
      localStorage.setItem(ACCESS_TOKEN_KEY, token);
      localStorage.setItem(TOKEN_EXPIRY_KEY, expiry.toString());
      localStorage.setItem(USER_KEY, JSON.stringify(userData));

      scheduleRefresh(expiresIn);
    },
    [scheduleRefresh]
  );

  // Clear tokens
  const clearTokens = useCallback(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }

    setAccessToken(null);
    setUser(null);

    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  // Refresh access token using HttpOnly cookie
  const refreshTokenFn = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(apiUrls.refresh, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // Include HttpOnly cookie
      });

      if (!response.ok) {
        clearTokens();
        return false;
      }

      const data = await response.json();
      saveTokens(data.access_token, data.expires_in, data.user);
      return true;
    } catch {
      clearTokens();
      return false;
    }
  }, [apiUrls.refresh, saveTokens, clearTokens]);

  // Load session on mount
  useEffect(() => {
    const loadSession = async () => {
      const storedToken = localStorage.getItem(ACCESS_TOKEN_KEY);
      const storedExpiry = localStorage.getItem(TOKEN_EXPIRY_KEY);
      const storedUser = localStorage.getItem(USER_KEY);

      if (storedToken && storedExpiry && storedUser) {
        const expiry = parseInt(storedExpiry, 10);
        const now = Date.now();

        if (expiry > now) {
          // Token still valid
          const remainingSeconds = Math.floor((expiry - now) / 1000);
          setAccessToken(storedToken);
          setUser(JSON.parse(storedUser));
          scheduleRefresh(remainingSeconds);
        } else {
          // Token expired, try refresh
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
  }, [refreshTokenFn, scheduleRefresh]);

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
          credentials: "include", // Accept HttpOnly cookie
          body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (!response.ok) {
          setError(data.error || "Ошибка авторизации");
          return false;
        }

        saveTokens(data.access_token, data.expires_in, data.user);
        return true;
      } catch (err) {
        setError("Ошибка сети");
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [apiUrls.login, saveTokens]
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
        credentials: "include", // Clear HttpOnly cookie
      });
    } catch {
      // Ignore errors, clear locally anyway
    }

    clearTokens();
  }, [apiUrls.logout, clearTokens]);

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
export function getAccessToken(): string | null {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY);

  if (token && expiry && parseInt(expiry, 10) > Date.now()) {
    return token;
  }

  return null;
}

/**
 * Check if user is authenticated (for non-React code)
 */
export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

/** Authentication Context & State Management.
 *
 * Manages:
 * - Current authenticated user profile
 * - Active JWT access token
 * - Initial session restoration from localStorage
 * - Global 401 unauthorized session eviction
 * - Login, Registration, and Sign-out methods
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type {
  AuthUser,
  LoginPayload,
  RegisterPayload,
} from "../types";
import {
  clearAuthToken,
  fetchCurrentUser,
  getAuthToken,
  loginUser,
  onUnauthorized,
  registerUser,
  setAuthToken,
} from "../lib/authApi";

export interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginPayload) => Promise<AuthUser>;
  register: (payload: RegisterPayload) => Promise<AuthUser>;
  logout: () => void;
  refreshUser: () => Promise<AuthUser | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(() => getAuthToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    clearAuthToken();
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async (): Promise<AuthUser | null> => {
    const activeToken = getAuthToken();
    if (!activeToken) {
      setUser(null);
      return null;
    }

    try {
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
      return currentUser;
    } catch {
      logout();
      return null;
    }
  }, [logout]);

  // Initial session restoration on application startup
  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      const savedToken = getAuthToken();
      if (!savedToken) {
        if (isMounted) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const currentUser = await fetchCurrentUser();
        if (isMounted) {
          setUser(currentUser);
          setToken(savedToken);
        }
      } catch {
        if (isMounted) {
          clearAuthToken();
          setToken(null);
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void restoreSession();

    // Subscribe to global 401 unauthorized notifications from API clients
    const unsubscribe = onUnauthorized(() => {
      logout();
    });

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [logout]);

  const login = useCallback(
    async (credentials: LoginPayload): Promise<AuthUser> => {
      const response = await loginUser(credentials);
      setAuthToken(response.access_token);
      setToken(response.access_token);
      setUser(response.user);
      return response.user;
    },
    [],
  );

  const register = useCallback(
    async (payload: RegisterPayload): Promise<AuthUser> => {
      const response = await registerUser(payload);
      setAuthToken(response.access_token);
      setToken(response.access_token);
      setUser(response.user);
      return response.user;
    },
    [],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isLoading,
      isAuthenticated: Boolean(user && token),
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, token, isLoading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

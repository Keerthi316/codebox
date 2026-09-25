import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError, getToken, setToken, setUnauthorizedHandler } from "../api/client";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  /** True when the server rejected a stored token (expired or revoked). */
  sessionExpired: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => getToken() !== null);
  const [sessionExpired, setSessionExpired] = useState(false);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSessionExpired(true);
      logout();
    });
    if (!getToken()) return;
    api
      .me()
      .then(setUser)
      .catch((err) => {
        // Only a rejected token ends the session; a network error keeps it for a retry.
        if (err instanceof ApiError && err.status === 401) {
          setToken(null);
          setSessionExpired(true);
        }
      })
      .finally(() => setLoading(false));
  }, [logout]);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      sessionExpired,
      logout,
      login: async (username, password) => {
        const res = await api.login(username, password);
        setToken(res.access_token);
        setSessionExpired(false);
        setUser(res.user);
      },
      register: async (username, email, password) => {
        const res = await api.register(username, email, password);
        setToken(res.access_token);
        setSessionExpired(false);
        setUser(res.user);
      },
    }),
    [user, loading, sessionExpired, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

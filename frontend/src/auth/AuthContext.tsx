import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import * as authApi from "../api/auth";
import { setUnauthorizedHandler, tokens } from "../api/client";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  loading: boolean; // true while restoring a session on first load
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(tokens.access));

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (!tokens.access) return;
    authApi
      .fetchMe()
      .then(setUser)
      .catch(() => tokens.clear())
      .finally(() => setLoading(false));
  }, [logout]);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      login: async (u, p) => setUser(await authApi.login(u, p)),
      register: async (u, e, p) => setUser(await authApi.register(u, e, p)),
      logout,
    }),
    [user, loading, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

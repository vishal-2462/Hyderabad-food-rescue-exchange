"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { clearStoredAuth, fetchCurrentUser, getStoredToken, loginUser, logoutUser, registerUser } from "@/app/_lib/auth-client";
import type { AuthCredentials, AuthUser } from "@/app/_lib/types";

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  login: (credentials: AuthCredentials) => Promise<AuthUser>;
  register: (credentials: AuthCredentials) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children, initialUser }: { children: React.ReactNode; initialUser: AuthUser | null }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(initialUser);
  const [loading, setLoading] = useState<boolean>(!initialUser);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (initialUser) {
        setUser(initialUser);
        setLoading(false);
        return;
      }

      const token = getStoredToken();
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const nextUser = await fetchCurrentUser(token);
        if (!cancelled) {
          setUser(nextUser);
        }
      } catch {
        clearStoredAuth();
        if (!cancelled) {
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [initialUser]);

  async function login(credentials: AuthCredentials): Promise<AuthUser> {
    const session = await loginUser(credentials);
    setUser(session.user);
    return session.user;
  }

  async function register(credentials: AuthCredentials): Promise<AuthUser> {
    const session = await registerUser(credentials);
    setUser(session.user);
    return session.user;
  }

  async function logout(): Promise<void> {
    await logoutUser();
    setUser(null);
    router.replace("/login");
    router.refresh();
  }

  async function refreshUser(): Promise<void> {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      return;
    }

    const nextUser = await fetchCurrentUser(token);
    setUser(nextUser);
  }

  return <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

import { API_BASE_URL } from "@/app/_lib/api-config";
import { AUTH_COOKIE_NAME, AUTH_SESSION_MAX_AGE, AUTH_STORAGE_KEY } from "@/app/_lib/auth-shared";
import type { AuthCredentials, AuthSession, AuthUser } from "@/app/_lib/types";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const entry = document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith(`${name}=`));

  if (!entry) {
    return null;
  }

  return decodeURIComponent(entry.slice(name.length + 1));
}

function writeCookie(name: string, value: string, maxAge: number) {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAge}; SameSite=Lax`;
}

function clearCookie(name: string) {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${name}=; Path=/; Max-Age=0; SameSite=Lax`;
}

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request failed with ${response.status}`;
  } catch {
    return `Request failed with ${response.status}`;
  }
}

function persistToken(token: string) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(AUTH_STORAGE_KEY, token);
  }
  writeCookie(AUTH_COOKIE_NAME, token, AUTH_SESSION_MAX_AGE);
}

export function clearStoredAuth() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }
  clearCookie(AUTH_COOKIE_NAME);
}

export function getStoredToken(): string | null {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (token) {
      return token;
    }
  }

  return readCookie(AUTH_COOKIE_NAME);
}

export function createAuthorizedRequestInit(init: RequestInit = {}): RequestInit {
  const headers = new Headers(init.headers);
  const token = getStoredToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return {
    ...init,
    credentials: init.credentials ?? "include",
    headers,
  };
}

export async function loginUser(payload: AuthCredentials): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  const session = (await response.json()) as AuthSession;
  persistToken(session.token);
  return session;
}

export async function registerUser(payload: AuthCredentials): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  const session = (await response.json()) as AuthSession;
  persistToken(session.token);
  return session;
}

export async function logoutUser(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, createAuthorizedRequestInit({ method: "POST" }));
  } finally {
    clearStoredAuth();
  }
}

export async function fetchCurrentUser(token?: string): Promise<AuthUser> {
  const headers = new Headers();
  const resolvedToken = token ?? getStoredToken();
  if (resolvedToken) {
    headers.set("Authorization", `Bearer ${resolvedToken}`);
  }

  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: "GET",
    headers,
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  return (await response.json()) as AuthUser;
}

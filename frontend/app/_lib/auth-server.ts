import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { API_BASE_URL } from "@/app/_lib/api-config";
import { AUTH_COOKIE_NAME, getRoleHome } from "@/app/_lib/auth-shared";
import type { AuthUser, UserRole } from "@/app/_lib/types";

async function fetchUserForToken(token: string): Promise<AuthUser | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as AuthUser;
  } catch {
    return null;
  }
}

export async function getOptionalAuthUser(): Promise<AuthUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return null;
  }

  return fetchUserForToken(token);
}

export async function redirectIfAuthenticated(): Promise<void> {
  const user = await getOptionalAuthUser();
  if (user) {
    redirect(getRoleHome(user.role));
  }
}

export async function requireAuth(role?: UserRole): Promise<AuthUser> {
  const user = await getOptionalAuthUser();
  if (!user) {
    redirect("/login");
  }

  if (role && user.role !== role) {
    redirect(getRoleHome(user.role));
  }

  return user;
}

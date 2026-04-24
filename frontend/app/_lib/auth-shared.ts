import type { UserRole } from "@/app/_lib/types";

export const AUTH_COOKIE_NAME = "ps12_auth_token";
export const AUTH_STORAGE_KEY = "ps12_auth_token";
export const AUTH_SESSION_MAX_AGE = 60 * 60 * 8;

export function getRoleHome(role: UserRole): string {
  return role === "donor" ? "/donations" : "/ngo";
}

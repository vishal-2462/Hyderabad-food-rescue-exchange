"use client";

import Link from "next/link";
import { useTransition } from "react";
import { usePathname } from "next/navigation";

import { useAuth } from "@/app/_components/auth-provider";

export function PlatformNav() {
  const pathname = usePathname();
  const { loading, logout, user } = useAuth();
  const [isPending, startTransition] = useTransition();

  const items = [
    { href: "/", label: "Overview" },
    { href: "/donor", label: "Donor" },
    ...(user?.role === "ngo" ? [{ href: "/ngo", label: "NGO" }] : []),
    ...(user?.role === "donor" ? [{ href: "/donations", label: "Donations" }] : []),
    { href: "/admin", label: "Admin" },
    { href: "/impact", label: "Impact" },
    ...(!user
      ? [
          { href: "/login", label: "Login" },
          { href: "/register", label: "Register" },
        ]
      : []),
  ];

  return (
    <div className="flex flex-col gap-3 lg:items-end">
      <nav className="flex flex-wrap items-center gap-2 lg:justify-end">
        {items.map((item) => {
          const active = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                active
                  ? "bg-slate-950 text-white shadow-lg shadow-slate-950/15"
                  : "bg-white/75 text-slate-700 ring-1 ring-slate-200 hover:bg-white"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {loading ? (
        <p className="text-sm text-slate-500">Checking session...</p>
      ) : user ? (
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600 lg:justify-end">
          <span className="rounded-full bg-slate-100 px-3 py-1 font-medium text-slate-700">{user.role.toUpperCase()}</span>
          <span>{user.email}</span>
          <button
            type="button"
            onClick={() => {
              startTransition(() => {
                void logout();
              });
            }}
            className="rounded-full border border-slate-200 px-4 py-2 font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
            disabled={isPending}
          >
            {isPending ? "Signing out..." : "Logout"}
          </button>
        </div>
      ) : (
        <p className="text-sm text-slate-500">Sign in as a donor or NGO to open the protected workspaces.</p>
      )}
    </div>
  );
}

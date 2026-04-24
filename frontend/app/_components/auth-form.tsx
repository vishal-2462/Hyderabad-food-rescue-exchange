"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { useAuth } from "@/app/_components/auth-provider";
import { getRoleHome } from "@/app/_lib/auth-shared";
import type { AuthCredentials, UserRole } from "@/app/_lib/types";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const { login, register } = useAuth();
  const [role, setRole] = useState<UserRole>("donor");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const isLogin = mode === "login";

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    startTransition(() => {
      void handleSubmit();
    });
  }

  async function handleSubmit() {
    try {
      const credentials: AuthCredentials = {
        email: email.trim().toLowerCase(),
        password,
        role,
      };

      const user = isLogin ? await login(credentials) : await register(credentials);
      router.replace(getRoleHome(user.role));
      router.refresh();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to complete the authentication request right now.");
    }
  }

  return (
    <div className="mx-auto max-w-xl rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-sky-700">Access control</p>
      <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{isLogin ? "Sign in to your workspace" : "Create your donor or NGO account"}</h2>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        {isLogin
          ? "Choose your role, enter your email, and continue to the dashboard that matches your organization."
          : "Registration signs you in immediately and redirects you to the protected surface for your selected role."}
      </p>

      <form className="mt-8 space-y-5" onSubmit={submit}>
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">Role</label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { value: "donor", label: "Donor" },
              { value: "ngo", label: "NGO" },
            ].map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setRole(option.value as UserRole)}
                className={`rounded-2xl border px-4 py-3 text-sm font-semibold transition ${
                  role === option.value
                    ? "border-slate-950 bg-slate-950 text-white"
                    : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:bg-white"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-700">Email</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
            placeholder="name@organization.org"
            required
          />
        </label>

        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-700">Password</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
            placeholder="At least 8 characters"
            minLength={8}
            required
          />
        </label>

        {error ? <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}

        <button
          type="submit"
          className="w-full rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={isPending}
        >
          {isPending ? (isLogin ? "Signing in..." : "Creating account...") : isLogin ? "Sign in" : "Create account"}
        </button>
      </form>

      <div className="mt-6 rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        <p className="font-semibold text-slate-900">Demo accounts</p>
        <p className="mt-2">Donor: <code>donor@example.com</code> / <code>password123</code></p>
        <p className="mt-1">NGO: <code>ngo@example.com</code> / <code>password123</code></p>
      </div>

      <p className="mt-6 text-sm text-slate-600">
        {isLogin ? "Need an account?" : "Already have an account?"}{" "}
        <Link href={isLogin ? "/register" : "/login"} className="font-semibold text-sky-700 hover:text-sky-800">
          {isLogin ? "Register here" : "Log in instead"}
        </Link>
      </p>
    </div>
  );
}

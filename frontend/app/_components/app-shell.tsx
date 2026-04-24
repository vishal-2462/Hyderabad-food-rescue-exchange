"use client";

import { usePathname } from "next/navigation";

import { PlatformNav } from "@/app/_components/platform-nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthRoute = pathname === "/login" || pathname === "/register";

  if (isAuthRoute) {
    return <main className="flex min-h-screen items-center justify-center px-4 py-10">{children}</main>;
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col px-4 py-6 sm:px-6 lg:px-10">
      <header className="mb-8 rounded-[2rem] border border-slate-200 bg-white px-6 py-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-sky-700">PS-12 control room</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Hyderabad food rescue exchange</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              One shared surface for donor dispatch, NGO intake, matching transparency, admin oversight, and impact reporting.
            </p>
          </div>
          <PlatformNav />
        </div>
      </header>
      <main className="flex-1 pb-8">{children}</main>
    </div>
  );
}

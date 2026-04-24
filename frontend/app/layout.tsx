import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { AppShell } from "@/app/_components/app-shell";
import { AuthProvider } from "@/app/_components/auth-provider";
import { getOptionalAuthUser } from "@/app/_lib/auth-server";
import "@/app/globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PS-12 Frontend",
  description: "Hyderabad donor, NGO, admin, and impact dashboards for the PS-12 project.",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const currentUser = await getOptionalAuthUser();

  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="font-sans text-foreground antialiased">
        <AuthProvider initialUser={currentUser}>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}

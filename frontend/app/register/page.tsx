import { AuthForm } from "@/app/_components/auth-form";
import { redirectIfAuthenticated } from "@/app/_lib/auth-server";

export default async function RegisterPage() {
  await redirectIfAuthenticated();

  return <AuthForm mode="register" />;
}

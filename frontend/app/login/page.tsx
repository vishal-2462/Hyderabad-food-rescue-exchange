import { AuthForm } from "@/app/_components/auth-form";
import { redirectIfAuthenticated } from "@/app/_lib/auth-server";

export default async function LoginPage() {
  await redirectIfAuthenticated();

  return <AuthForm mode="login" />;
}

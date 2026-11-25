import { LoginScreen } from "@/features/accounts/auth/AuthScreen";
import { LoginForm } from "@/features/accounts/auth/LoginForm";
import { safeNextPath } from "@/features/accounts/auth/api";

interface LoginPageProps {
  searchParams: Promise<{ email?: string | string[]; next?: string | string[] }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { email, next } = await searchParams;
  const prefilledEmail = typeof email === "string" ? email.slice(0, 254) : undefined;
  const redirect = typeof next === "string" ? safeNextPath(next) : undefined;
  return (
    <LoginScreen>
      <LoginForm key={prefilledEmail} email={prefilledEmail} next={redirect} />
    </LoginScreen>
  );
}

import { LoginScreen } from "@/features/accounts/auth/AuthScreen";
import { LoginForm } from "@/features/accounts/auth/LoginForm";
import { safeNextPath } from "@/features/accounts/auth/api";

interface LoginPageProps {
  searchParams: Promise<{
    email?: string | string[];
    next?: string | string[];
    reason?: string | string[];
  }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { email, next, reason } = await searchParams;
  const prefilledEmail = typeof email === "string" ? email.slice(0, 254) : undefined;
  const redirect = typeof next === "string" ? safeNextPath(next) : undefined;
  // 마이페이지에서 비밀번호를 바꾸면 세션을 끊고 여기로 보낸다 (A82)
  const notice =
    reason === "password_changed"
      ? "비밀번호를 바꿨어요. 새 비밀번호로 다시 로그인해 주세요."
      : undefined;
  return (
    <LoginScreen>
      <LoginForm key={prefilledEmail} email={prefilledEmail} next={redirect} notice={notice} />
    </LoginScreen>
  );
}

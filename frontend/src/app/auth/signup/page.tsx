import Link from "next/link";
import { SignupScreen } from "@/features/accounts/auth/AuthScreen";
import { SignupForm } from "@/features/accounts/auth/SignupForm";
import { authLink, safeNextPath } from "@/features/accounts/auth/api";
import { currentBirthYear } from "@/features/accounts/auth/validators";

interface SignupPageProps {
  searchParams: Promise<{ next?: string | string[] }>;
}

export default async function SignupPage({ searchParams }: SignupPageProps) {
  const { next } = await searchParams;
  const redirect = typeof next === "string" ? safeNextPath(next) : undefined;
  return (
    <SignupScreen footer={(
      <>
        이미 계정이 있나요?{" "}
        <Link href={authLink("/auth/login", { next: redirect })} className="font-extrabold text-brand underline underline-offset-2">
          로그인
        </Link>
      </>
    )}>
      <SignupForm next={redirect} maxBirthYear={currentBirthYear()} />
    </SignupScreen>
  );
}

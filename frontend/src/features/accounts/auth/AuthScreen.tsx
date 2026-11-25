import Link from "next/link";
import { ArrowLeft, FerrisWheel, Sparkles, Tent } from "lucide-react";
import type { ReactNode } from "react";
import { BrandLogo as BrandLogoImage } from "@/components/BrandLogo";
import styles from "./AuthScreen.module.css";

function BrandLogo() {
  return (
    <Link
      href="/"
      aria-label="놀다가 홈"
      className="inline-flex items-center"
    >
      <BrandLogoImage priority className="h-auto w-full" />
    </Link>
  );
}

export function LoginScreen({ children }: { children: ReactNode }) {
  return (
    <div className={`${styles.screen} ${styles.login} min-h-dvh bg-surface px-5 pb-14 pt-16`}>
      <div className="mx-auto max-w-[330px] text-center text-ink">
        <div className="mx-auto w-[285px]"><BrandLogo /></div>
        <h1 className="mt-10 text-[30px] font-black leading-tight tracking-tight">
          <span className="text-brand">놀다가</span>에 오신 것을 환영해요!
        </h1>
        <p className="mt-3 text-base font-semibold text-ink">축제도, 즐길도, 안전한 귀가까지 한 번에!</p>
        <FestivalIllustration />
      </div>
      <div className="mx-auto mt-8 max-w-[350px]">
        {children}
      </div>
    </div>
  );
}

export function SignupScreen({ children, footer }: { children: ReactNode; footer: ReactNode }) {
  return (
    <div className={`${styles.screen} ${styles.signup} min-h-dvh bg-surface px-5 pb-10 pt-4`}>
      <div className="relative flex h-14 items-center justify-center">
        <Link href="/auth/login" aria-label="로그인으로 돌아가기" className="absolute left-0 grid h-11 w-11 place-items-center rounded-chip text-ink">
          <ArrowLeft className="h-6 w-6" aria-hidden="true" />
        </Link>
        <span className="text-xl font-extrabold">회원가입</span>
      </div>
      <div className="mx-auto max-w-[350px]">
        <div className="mx-auto mt-5 w-[270px]"><BrandLogo /></div>
        <h1 className="mt-4 text-center text-[25px] font-black leading-tight tracking-tight text-ink">
          <span className="text-brand">놀다가</span>와 함께 시작해요!
        </h1>
        <p className="mt-2 text-center text-sm font-medium text-muted">
          간단한 정보를 입력하고 취향에 맞는 축제를 만나보세요.
        </p>
      </div>
      <div className="mx-auto mt-6 max-w-[350px]">
        {children}
      </div>
      <div className="mx-auto mt-5 max-w-[350px] text-center text-sm font-medium text-muted">{footer}</div>
    </div>
  );
}

function FestivalIllustration() {
  return (
    <div aria-hidden="true" className="relative mx-auto mt-6 h-40 w-72">
      <div className="absolute inset-x-2 bottom-0 h-16 rounded-[50%] bg-brand-soft blur-sm" />
      <Sparkles className="absolute left-16 top-0 h-10 w-10 text-brand" strokeWidth={1.4} />
      <FerrisWheel className="absolute bottom-2 right-4 h-24 w-24 text-ink" strokeWidth={1.35} />
      <Tent className="absolute bottom-0 left-12 h-24 w-32 fill-brand/25 text-brand" strokeWidth={1.45} />
    </div>
  );
}

import Image from "next/image";
import Link from "next/link";
import { FerrisWheel, Sparkles, Tent, TentTree } from "lucide-react";
import type { ReactNode } from "react";
import styles from "./AuthScreen.module.css";

function BrandLogo({ onDark = false }: { onDark?: boolean }) {
  return (
    <Link
      href="/"
      aria-label="놀다가 홈"
      className={
        onDark
          ? "inline-flex items-center rounded-chip bg-surface/95 px-4 py-1.5 shadow-md"
          : "inline-flex items-center"
      }
    >
      <Image
        src="/logo-noldaga.png"
        alt="NOLDAGA"
        width={138}
        height={46}
        priority
        unoptimized
        className="h-7 w-auto object-contain mix-blend-multiply"
      />
    </Link>
  );
}

export function LoginScreen({ children }: { children: ReactNode }) {
  return (
    <div className={`${styles.screen} ${styles.login} relative isolate grid min-h-dvh content-center gap-5 overflow-hidden px-[8.5%] pb-14 pt-10`}>
      <div aria-hidden="true" className="absolute inset-0 -z-10 overflow-hidden">
        <Sparkles strokeWidth={1} className="absolute -right-3 top-6 h-28 w-28 text-surface/85 drop-shadow-[0_0_10px_var(--color-brand)]" />
        <Sparkles strokeWidth={1} className="absolute right-[14%] top-[21%] h-10 w-10 text-surface/70" />
        <TentTree className="absolute -bottom-4 -left-3 h-28 w-28 text-ink/85" />
        <TentTree className="absolute -bottom-6 right-0 h-28 w-28 text-ink/85" />
        <div className="absolute bottom-9 left-[18%] right-[18%] h-10 rounded-b-[50%] border-b-2 border-dotted border-surface-soft/80" />
      </div>
      <div className="text-center text-surface">
        <BrandLogo onDark />
        <p className="mx-auto mt-3 w-fit -rotate-3 border-b-[5px] border-brand pb-1 text-5xl font-black italic leading-none tracking-tight">놀다가</p>
        <p className="mt-3 text-sm font-semibold text-surface/95">축제를 더 안전하고, 더 즐겁게</p>
      </div>
      <div className={`${styles.loginCard} rounded-[25px] px-[7%] py-6 shadow-xl`}>
        {children}
      </div>
    </div>
  );
}

export function SignupScreen({ children, footer }: { children: ReactNode; footer: ReactNode }) {
  return (
    <div className={`${styles.screen} ${styles.signup} min-h-dvh px-4 pb-8 pt-4`}>
      <div className="relative isolate mb-4 overflow-hidden px-1">
        <BrandLogo />
        <div className="pointer-events-none absolute -right-1 bottom-0 -z-10 w-[40%] text-brand" aria-hidden="true">
          <FerrisWheel strokeWidth={1.3} className="absolute bottom-4 right-1 h-16 w-16 text-ink/70" />
          <Sparkles strokeWidth={1.3} className="absolute bottom-[68px] left-5 h-7 w-7 text-brand/75" />
          <Tent strokeWidth={1.4} className="relative ml-1 h-14 w-20 fill-brand/25" />
        </div>
        <h1 className="mt-5 text-[clamp(24px,6.8vw,30px)] font-black leading-tight tracking-tight text-ink">
          <span className="text-brand">놀다가</span> 시작하기
        </h1>
        <p className="mt-1 text-sm font-medium leading-snug text-muted">
          축제를 더 편하게 즐기기 위한
          <br />
          기본 정보를 입력해 주세요
        </p>
      </div>
      <div className="rounded-[24px] border border-line-light bg-surface p-5 shadow-md">
        {children}
      </div>
      <div className="mt-4 text-center text-sm font-medium text-muted">{footer}</div>
    </div>
  );
}

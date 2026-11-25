"use client";

import Link from "next/link";
import { HeartHandshake, Home, Sparkles } from "lucide-react";
import { BrandLogo } from "@/components/BrandLogo";
import { RequireAuth } from "@/components/RequireAuth";

export function OnboardingCompleteView() {
  return (
    <RequireAuth nextPath="/onboarding/complete">
      <main className="min-h-dvh bg-surface px-6 pb-12 pt-16 text-ink">
        <BrandLogo priority className="mx-auto h-auto w-[285px]" />
        <div className="mx-auto mt-16 grid h-36 w-36 place-items-center rounded-chip bg-surface-soft text-brand">
          <HeartHandshake className="h-20 w-20" strokeWidth={1.7} aria-hidden="true" />
        </div>
        <h1 className="mt-7 text-center text-[32px] font-black tracking-tight">취향 선택 <span className="text-brand">완료!</span></h1>
        <p className="mt-4 text-center text-lg text-muted">좋아하는 축제 스타일을 확인했어요.</p>
        <h2 className="mt-10 text-center text-[26px] font-extrabold">이제 어디로 가볼까요?</h2>

        <section className="mt-10 rounded-panel bg-surface-soft p-5">
          <h3 className="flex items-center gap-2 text-lg font-extrabold"><span className="text-brand">♡</span> 내가 선택한 축제 취향</h3>
          <div className="mt-4 flex flex-wrap gap-2">
            {["가족과 함께", "반려동물과 함께", "포토존이 많은 축제"].map((label) => (
              <span key={label} className="rounded-chip bg-surface px-4 py-2 text-sm font-bold shadow-sm">{label}</span>
            ))}
          </div>
        </section>

        <Link href="/recommendations" className="mt-7 block rounded-panel border-2 border-brand p-5 shadow-card">
          <div className="flex items-start gap-4">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-card-lg bg-surface-soft text-brand"><Sparkles className="h-7 w-7" aria-hidden="true" /></span>
            <div><h3 className="text-xl font-extrabold">내 취향 축제 먼저 보기</h3><p className="mt-1 text-sm text-muted">내가 선택한 취향에 맞는 축제를 추천받아요.</p></div>
          </div>
          <span className="mt-5 flex min-h-14 items-center justify-center rounded-card-lg bg-brand text-lg font-extrabold text-surface">맞춤 축제 보러 가기 →</span>
        </Link>

        <Link href="/" className="mt-5 flex items-center gap-4 rounded-panel border border-line-light p-5">
          <span className="grid h-14 w-14 place-items-center rounded-card-lg bg-surface-soft text-brand"><Home className="h-7 w-7" aria-hidden="true" /></span>
          <div className="flex-1"><h3 className="text-xl font-extrabold">놀다가 홈으로 가기</h3><p className="mt-1 text-sm text-muted">축제부터 동행·귀가 서비스까지 둘러봐요.</p></div>
          <span className="text-2xl text-brand">›</span>
        </Link>
      </main>
    </RequireAuth>
  );
}

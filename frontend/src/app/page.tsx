"use client";

import Link from "next/link";
import { ArrowRight, BusFront, FerrisWheel, Map, MapPin, Sparkles, TentTree, Users } from "lucide-react";
import { useState } from "react";
import { AssistantPrompt } from "@/features/assistant/chatbot/AssistantPrompt";
import { FeaturedFestivals } from "@/features/accounts/favorites/FeaturedFestivals";

export default function HomePage() {
  const [showRecommendationNotice, setShowRecommendationNotice] = useState(false);
  const shortcutClass = "flex min-h-12 items-center gap-2 rounded-2xl border border-line-dark bg-dark-surface px-3 py-2 text-left text-sm font-bold leading-tight hover:border-dark-muted";

  return (
    <div className="space-y-5 px-[4.7%] pb-1 pt-5">
      <section className="relative isolate min-h-[130px]">
        <div aria-hidden="true" className="absolute -right-[5.2%] bottom-0 top-2 -z-10 w-[56%] overflow-hidden rounded-tl-[50px] bg-gradient-to-b from-ink via-accent/35 to-brand/45 [clip-path:polygon(25%_0,100%_0,100%_100%,0_100%)]">
          <div className="absolute -bottom-7 right-4 h-32 w-32 rounded-full bg-brand/45 blur-2xl" />
          <FerrisWheel className="absolute bottom-1 right-[15%] h-[88%] w-[60%] text-brand drop-shadow-[0_0_8px_var(--color-brand)]" strokeWidth={1.25} />
          <TentTree className="absolute bottom-1 right-0 h-10 w-[32%] text-neon" />
          <Sparkles className="absolute left-[24%] top-[32%] h-6 w-6 text-neon" />
        </div>
        <h1 className="text-[clamp(29px,9.6vw,46px)] font-black italic leading-[0.99] tracking-tight">
          오늘,<br />
          어디서 <span className="text-neon">놀까?</span>
        </h1>
        <p className="mt-3 pb-1 text-[13px] font-semibold leading-snug">
          전국의 축제부터 귀갓길까지,<br /> 놀다가와 함께!
        </p>
      </section>

      <AssistantPrompt />

      <section className="relative isolate min-h-[165px] overflow-hidden rounded-[20px] bg-neon px-5 py-3.5 text-ink">
        <div className="absolute inset-y-0 right-0 -z-10 w-[52%]" aria-hidden="true">
          <div className="absolute -bottom-8 inset-x-0 top-1/2 bg-dark-bg [clip-path:polygon(42%_0,64%_0,100%_100%,0_100%)]" />
          <MapPin className="absolute right-[14%] top-[9%] h-11 w-11 fill-ink stroke-neon" />
          <BusFront className="absolute bottom-[13%] right-[22%] h-[57%] w-[58%] fill-dark-bg stroke-neon drop-shadow-[0_0_2px_var(--color-ink)]" strokeWidth={1.2} />
        </div>
        <span className="inline-flex items-center gap-1 rounded-chip bg-dark-bg px-2.5 py-1 text-[11px] font-semibold text-surface">
          <Sparkles size={13} className="text-neon" aria-hidden="true" /> 핵심 서비스
        </span>
        <h2 className="mt-2 text-[clamp(23px,6.9vw,32px)] font-black leading-none tracking-tight">AI 안심 귀가</h2>
        <p className="mt-2 text-xs font-semibold leading-tight">
          축제 종료 후,<br /> 나에게 맞는 안전한 귀갓길을<br /> AI가 안내해드려요!
        </p>
        <Link href="/routes/return" className="mt-2 inline-flex items-center gap-2 rounded-chip bg-dark-bg px-3.5 py-1.5 text-xs font-bold text-surface">
          귀가 경로 조회하기 <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </section>

      <div>
        <div className="grid grid-cols-2 gap-2.5">
          <button type="button" className={shortcutClass} onClick={() => setShowRecommendationNotice((value) => !value)} aria-expanded={showRecommendationNotice}>
            <Sparkles size={24} className="shrink-0 text-neon" aria-hidden="true" />
            <span className="flex-1">내 취향<br />축제 추천</span>
            <ArrowRight size={15} className="shrink-0" aria-hidden="true" />
          </button>
          <Link href="/companions" className={shortcutClass}>
            <Users size={24} className="shrink-0 text-neon" aria-hidden="true" />
            <span className="flex-1">동행 찾기</span>
            <ArrowRight size={15} className="shrink-0" aria-hidden="true" />
          </Link>
        </div>
        {showRecommendationNotice && <p role="status" className="mt-2 text-sm text-dark-muted">준비 중이에요.</p>}
      </div>

      <FeaturedFestivals />

      <Link href="/festivals" className="flex items-center gap-3 rounded-[18px] bg-neon px-3.5 py-3 text-ink">
        <div className="relative shrink-0 border-r border-dark-bg/50 pr-2.5" aria-hidden="true">
          <Map size={38} />
          <MapPin size={24} className="absolute -top-1.5 left-3 fill-dark-bg stroke-neon" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-black leading-tight tracking-tight">전국 축제 둘러보기</h2>
          <p className="mt-0.5 text-[11px] font-semibold">지역별 축제를 찾아보세요!</p>
        </div>
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-chip bg-dark-bg text-surface">
          <ArrowRight size={18} aria-hidden="true" />
        </span>
      </Link>
    </div>
  );
}

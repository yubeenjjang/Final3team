"use client";

import Link from "next/link";
import {
  ArrowRight,
  Building2,
  BusFront,
  ChevronRight,
  FerrisWheel,
  MapPin,
  MapPinned,
  MoonStar,
  ShieldCheck,
  Sparkles,
  Tent,
  Users,
} from "lucide-react";
import { AssistantPrompt } from "@/features/assistant/chatbot/AssistantPrompt";
import { FeaturedFestivals } from "@/features/accounts/favorites/FeaturedFestivals";

const PERSONAL_PLACEHOLDER_CARDS = [
  { id: "taste", title: "취향 맞춤 추천", sub: "준비 중" },
  { id: "region", title: "관심 지역 축제", sub: "준비 중" },
  { id: "theme", title: "지금 뜨는 테마", sub: "준비 중" },
] as const;

export default function HomePage() {
  const shortcutClass =
    "flex min-h-13 items-center gap-2.5 rounded-card border border-line-light bg-surface px-3.5 py-3 text-left text-sm font-bold text-ink shadow-sm transition-colors hover:border-brand/40 hover:bg-surface-soft/40";

  return (
    <div className="space-y-6 px-4 pb-4 pt-3">
      {/* 히어로 */}
      <section className="relative isolate overflow-hidden pt-2">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-2 bottom-0 top-0 -z-10 w-[46%]"
        >
          <div className="absolute bottom-0 right-2 h-20 w-36 rounded-full bg-surface-soft blur-xl" />
          <Sparkles className="absolute left-4 top-0 h-5 w-5 text-brand/70" strokeWidth={1.6} />
          <FerrisWheel className="absolute bottom-1 right-2 h-20 w-20 text-ink/75" strokeWidth={1.25} />
          <Tent className="absolute bottom-0 right-16 h-16 w-20 fill-brand/25 text-brand" strokeWidth={1.5} />
        </div>
        <h1 className="text-[clamp(26px,7.5vw,32px)] font-black leading-tight tracking-tight text-ink">
          오늘, 여기서 <span className="text-brand">놀다가!</span>
        </h1>
        <p className="mt-1.5 text-[13px] font-medium text-muted">
          축제도, 즐길 거리도, 안전한 귀가까지 한 번에!
        </p>
      </section>

      {/* AI 질문 입력 + 예시 칩 */}
      <AssistantPrompt />

      {/* 지금, 여기서 열리는 축제 */}
      <FeaturedFestivals />

      {/* 나만을 위한 축제 (준비 중) */}
      <section aria-labelledby="personal-festivals-title">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2
            id="personal-festivals-title"
            className="flex items-center gap-2 text-base font-extrabold tracking-tight text-ink"
          >
            <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
            나만을 위한 축제
          </h2>
          <span className="flex items-center gap-0.5 text-xs font-semibold text-muted">
            준비 중 <ChevronRight size={14} aria-hidden="true" />
          </span>
        </div>

        <ul className="flex snap-x snap-mandatory gap-2.5 overflow-x-auto pb-1">
          {PERSONAL_PLACEHOLDER_CARDS.map((card) => (
            <li
              key={card.id}
              className="relative flex h-[176px] w-[138px] shrink-0 snap-start flex-col justify-between overflow-hidden rounded-card border border-line-light bg-gradient-to-b from-surface-soft/75 via-surface to-surface-muted/60 p-3 shadow-sm sm:w-[144px]"
            >
              <span className="w-fit rounded-chip bg-brand/15 px-2 py-0.5 text-[10px] font-extrabold text-brand">
                준비 중
              </span>
              <div className="flex flex-col items-center justify-center py-2 text-center">
                <Sparkles className="mb-1.5 h-6 w-6 text-brand/60" aria-hidden="true" />
                <p className="text-xs font-extrabold text-ink">{card.title}</p>
                <p className="mt-0.5 text-[11px] font-medium text-muted">{card.sub}</p>
              </div>
              <div className="h-1.5 w-12 rounded-chip bg-line-light/80" aria-hidden="true" />
            </li>
          ))}
        </ul>
      </section>

      {/* AI 안심 귀가 진한 회색 배너 */}
      <section className="relative isolate overflow-hidden rounded-[20px] bg-banner-dark px-4 py-4 text-surface shadow-md">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-3 -z-10 flex items-end gap-1.5 opacity-80"
        >
          <Building2 className="h-11 w-11 text-muted/60" strokeWidth={1.5} />
          <MapPin className="mb-4 h-7 w-7 fill-brand text-surface" strokeWidth={1.8} />
          <div className="flex flex-col items-end">
            <MoonStar className="mb-1 h-4 w-4 text-crowd-yellow" />
            <BusFront className="h-8 w-8 text-surface/90" strokeWidth={1.6} />
          </div>
        </div>

        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-brand/20 ring-1 ring-brand/40">
            <ShieldCheck className="h-6 w-6 fill-brand text-surface" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1 pr-14">
            <h2 className="text-base font-black tracking-tight text-surface">AI 안심 귀가</h2>
            <p className="mt-1 text-[11px] leading-relaxed text-surface/80">
              축제 종료 후, 혼잡도와 동선을 고려한
              <br />
              가장 안전한 귀갓길을 안내해요!
            </p>
          </div>
        </div>

        <div className="mt-3 flex justify-end">
          <Link
            href="/routes/return"
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-extrabold text-surface shadow-sm transition-opacity hover:opacity-90"
          >
            지금 귀가 경로 확인하기 <ArrowRight size={14} aria-hidden="true" />
          </Link>
        </div>
      </section>

      {/* 하단 바로가기 버튼 2개 */}
      <div className="grid grid-cols-2 gap-2.5">
        <Link href="/map" className={shortcutClass}>
          <MapPinned size={22} className="shrink-0 text-brand" aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate">지도에서 축제찾기</span>
          <ArrowRight size={15} className="shrink-0 text-ink/70" aria-hidden="true" />
        </Link>
        <Link href="/companions" className={shortcutClass}>
          <Users size={22} className="shrink-0 text-brand" aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate">동행 찾기</span>
          <ArrowRight size={15} className="shrink-0 text-ink/70" aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
}

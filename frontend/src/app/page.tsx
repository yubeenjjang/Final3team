"use client";

import Link from "next/link";
import Image from "next/image";
import {
  ArrowRight,
  MapPinned,
  Users,
} from "lucide-react";
import { TabPageHero } from "@/components/TabPageHero";
import { AssistantPrompt } from "@/features/assistant/chatbot/AssistantPrompt";
import { FeaturedFestivals } from "@/features/festivals/explore/FeaturedFestivals";

export default function HomePage() {
  const shortcutClass =
    "grid h-[68px] grid-cols-[24px_minmax(0,1fr)_16px] items-center gap-2.5 rounded-card border border-line-light bg-surface px-3.5 text-left text-sm font-bold text-ink shadow-sm transition-colors hover:border-brand/40 hover:bg-surface-soft/40";

  return (
    <div className="space-y-4 px-4 py-4">
      {/* 히어로 */}
      <TabPageHero
        title={<>오늘, 여기서 <span className="text-brand">놀다가!</span></>}
        subtitle="축제도, 즐길 거리도, 안전한 귀가까지 한 번에!"
        aside={
          <div className="relative h-14 w-[104px]">
            <Image
              src="/brand/festival-hero-compact.png"
              alt=""
              fill
              sizes="104px"
              className="object-contain object-right"
            />
          </div>
        }
      />

      {/* AI 질문 입력 + 예시 칩 */}
      <AssistantPrompt />

      {/* 인기있는 축제 */}
      <FeaturedFestivals />

      <FeaturedFestivals
        title="나만을 위한 축제"
        status="upcoming"
        moreLabel="더보기"
        moreHref="/festivals/all?section=personal"
      />

      {/* AI 안심 귀가 진한 회색 배너 */}
      <section className="relative flex min-h-[94px] items-center gap-3 overflow-hidden rounded-[20px] border border-brand/10 bg-gradient-to-r from-banner-dark to-ink px-4 py-3.5 text-surface shadow-md">
        <span className="absolute bottom-3 left-0 top-3 w-1 rounded-r-chip bg-brand" aria-hidden="true" />
        <div className="min-w-0 flex-1 pl-1">
          <h2 className="text-base font-black tracking-tight text-surface">AI 안심 귀가</h2>
          <p className="mt-1 text-[11px] font-medium leading-[1.45] text-surface/80">
            혼잡한 동선을 고려한
            <br />
            안전한 귀갓길을 안내해요!
          </p>
        </div>
        <Link
          href="/routes/return"
          className="inline-flex min-h-10 shrink-0 items-center gap-1 rounded-chip bg-brand px-3.5 py-2 text-[11px] font-extrabold text-surface shadow-sm transition-opacity hover:opacity-90"
        >
          경로 확인하기 <ArrowRight size={13} aria-hidden="true" />
        </Link>
      </section>

      {/* 하단 바로가기 버튼 2개 */}
      <div className="grid grid-cols-2 gap-2.5">
        <Link href="/map" className={shortcutClass}>
          <MapPinned size={22} className="shrink-0 text-brand" aria-hidden="true" />
          <span className="min-w-0 leading-tight">지도에서<br />축제찾기</span>
          <ArrowRight size={15} className="shrink-0 text-ink/70" aria-hidden="true" />
        </Link>
        <Link href="/companions" className={shortcutClass}>
          <Users size={22} className="shrink-0 text-brand" aria-hidden="true" />
          <span className="min-w-0 leading-tight">동행 찾기</span>
          <ArrowRight size={15} className="shrink-0 text-ink/70" aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
}

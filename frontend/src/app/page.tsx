"use client";

import Link from "next/link";
import Image from "next/image";
import {
  ArrowRight,
  MapPinned,
  Users,
} from "lucide-react";
import { TabPageHero } from "@/components/TabPageHero";
import { SafeReturnBanner } from "@/components/SafeReturnBanner";
import { AssistantPrompt } from "@/features/assistant/chatbot/AssistantPrompt";
import { FeaturedFestivals } from "@/features/festivals/explore/FeaturedFestivals";
import { PreferenceSetupCta } from "@/features/accounts/profile/PreferenceSetupCta";
import { useFestivalPreferenceStatus } from "@/features/accounts/profile/useFestivalPreferenceStatus";

export default function HomePage() {
  const preferenceStatus = useFestivalPreferenceStatus();
  const hasPersonalRecommendations = preferenceStatus === "completed";
  const shortcutClass =
    "grid h-[68px] grid-cols-[24px_minmax(0,1fr)_16px] items-center gap-2.5 rounded-card border border-line-light bg-surface px-3.5 text-left text-sm font-bold text-ink shadow-sm transition-colors hover:border-brand/40 hover:bg-surface-soft/40";

  return (
    <div className="space-y-4 px-4 py-4 md:grid md:grid-cols-[minmax(0,1.65fr)_minmax(280px,0.75fr)] md:gap-x-8 md:gap-y-6 md:space-y-0 md:px-8 md:py-8">
      {/* 히어로 */}
      <div className="md:col-start-1 md:row-start-1">
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
      </div>

      {/* AI 질문 입력 + 예시 칩 */}
      <div className="md:col-start-1 md:row-start-2">
        <AssistantPrompt />
      </div>

      {/* 인기있는 축제 */}
      <div className="md:col-span-2 md:row-start-3">
        <FeaturedFestivals />
      </div>

      <div className="md:col-span-2 md:row-start-4">
        <FeaturedFestivals
          title={hasPersonalRecommendations ? "나만을 위한 축제" : "새로 올라온 축제"}
          status="upcoming"
          moreLabel="더보기"
          moreHref={hasPersonalRecommendations ? "/festivals/all?section=personal" : "/festivals/all?section=new"}
          sort={hasPersonalRecommendations ? undefined : "-start_date"}
        />
      </div>

      <SafeReturnBanner className="md:col-start-2 md:row-span-2 md:row-start-1 md:self-center" />

      {/* 하단 바로가기 버튼 2개 */}
      <div className="grid w-full grid-cols-2 gap-2.5 md:col-span-2 md:row-start-5">
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
      {preferenceStatus !== "completed" && preferenceStatus !== "loading" ? (
        <div className="md:col-span-2 md:row-start-6">
          <PreferenceSetupCta />
        </div>
      ) : null}
    </div>
  );
}

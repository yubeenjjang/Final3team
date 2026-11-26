"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, CalendarDays, MapPin, SlidersHorizontal, UsersRound } from "lucide-react";
import { useEffect, useState } from "react";
import { BrandLogo } from "@/components/BrandLogo";
import { FestivalImagePlaceholder } from "@/components/FestivalImagePlaceholder";
import { RequireAuth } from "@/components/RequireAuth";
import { getFestivalPreferences, SCENARIO_OPTIONS, type Scenario } from "@/features/accounts/profile/api";
import { listFestivals, type FestivalListItem } from "@/features/festivals/explore/api";
import { formatFestivalPeriod } from "@/features/festivals/explore/dday";
import { getRegionLabel } from "@/features/festivals/explore/regions";

export function RecommendationsView() {
  const [items, setItems] = useState<FestivalListItem[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      listFestivals({ page: 1, page_size: 5 }, controller.signal),
      getFestivalPreferences(controller.signal),
    ])
      .then(([result, preferences]) => {
        setItems(result.items.slice(0, 5));
        setScenarios(preferences.scenarios);
      })
      .catch(() => {
        setItems([]);
        setScenarios([]);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const preferenceLabels = SCENARIO_OPTIONS
    .filter((option) => scenarios.includes(option.value))
    .map((option) => option.tag);

  return (
    <RequireAuth nextPath="/recommendations">
    <main className="min-h-dvh bg-screen-dark pb-14 pt-7 text-surface">
      <header className="flex items-center justify-between px-5">
        <Link href="/onboarding/complete" aria-label="뒤로" className="grid h-11 w-11 place-items-center rounded-chip"><ArrowLeft aria-hidden="true" /></Link>
        <BrandLogo priority className="h-9 w-auto brightness-0 invert" />
        <button type="button" aria-label="추천 필터" className="grid h-11 w-11 place-items-center rounded-chip"><SlidersHorizontal aria-hidden="true" /></button>
      </header>
      <section className="px-6 pt-10 text-center">
        <h1 className="text-[30px] font-black leading-tight">취향에 딱 맞는 <span className="text-brand">축제</span>를 찾았어요!</h1>
        <p className="mt-4 text-base text-surface/75">선택한 취향을 바탕으로 추천해드려요.</p>
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          {preferenceLabels.slice(0, 3).map((label, index) => (
            <span key={label} className={`rounded-chip px-4 py-2 text-sm font-bold ${index === 0 ? "border-2 border-brand" : "border border-surface/70"}`}>
              {index === 0 ? "♡ " : ""}{label}
            </span>
          ))}
        </div>
      </section>

      {loading ? <div className="mx-10 mt-8 h-[500px] animate-pulse rounded-panel bg-surface/10" /> : (
        <div className="mt-8 flex snap-x snap-mandatory gap-4 overflow-x-auto px-[42px] pb-5">
          {items.map((item) => (
            <article key={item.festival_id} className="relative h-[500px] w-[310px] shrink-0 snap-center overflow-hidden rounded-[28px] border-[3px] border-surface bg-screen-dark shadow-xl">
              <div className="absolute inset-0">
                {item.thumbnail_url ? <Image src={item.thumbnail_url} alt="" fill unoptimized className="object-cover" /> : <FestivalImagePlaceholder />}
              </div>
              <div className="absolute inset-0 bg-gradient-to-t from-screen-dark via-transparent to-transparent" />
              <span className="absolute left-4 top-4 inline-flex items-center gap-2 rounded-chip bg-brand px-4 py-2 text-sm font-extrabold"><UsersRound className="h-5 w-5" aria-hidden="true" /> 취향 맞춤 추천</span>
              <div className="absolute inset-x-0 bottom-0 p-5">
                <h2 className="text-[28px] font-black leading-tight">{item.name}</h2>
                <p className="mt-3 flex items-center gap-2 text-sm"><CalendarDays className="h-5 w-5" aria-hidden="true" /> {formatFestivalPeriod(item.start_date, item.end_date)}</p>
                <p className="mt-1 flex items-center gap-2 text-sm"><MapPin className="h-5 w-5" aria-hidden="true" /> {getRegionLabel(item.region_code)}</p>
                <Link href={`/festivals/${item.festival_id}`} className="mt-5 flex min-h-14 items-center justify-center rounded-card-lg bg-brand text-lg font-extrabold">축제 상세보기 →</Link>
              </div>
            </article>
          ))}
        </div>
      )}
      <p className="mx-10 mt-6 rounded-chip border border-surface/60 px-5 py-3 text-center text-sm text-surface/80">↔ 좌우로 넘겨 다른 추천 축제도 확인해보세요!</p>
    </main>
    </RequireAuth>
  );
}

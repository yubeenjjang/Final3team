"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Bus,
  CalendarDays,
  Compass,
  Hospital,
  MapPin,
  ParkingCircle,
  RotateCcw,
  Ticket,
  TrainFront,
  Utensils,
  Users,
} from "lucide-react";
import { FestivalImagePlaceholder } from "@/components/FestivalImagePlaceholder";
import { KakaoMap } from "@/components/KakaoMap";
import { SafeReturnBanner } from "@/components/SafeReturnBanner";
import { FavoriteButton } from "@/features/favorites/FavoriteButton";
import { ApiError } from "@/lib/api/client";
import {
  FACILITY_LABELS,
  FACILITY_SYMBOLS,
  listMapFacilities,
  type FacilityCategory,
  type FacilityGroup,
  type MapFacility,
} from "../map/api";
import { dday, formatFestivalPeriod } from "../explore/dday";
import { getRegionLabel } from "../explore/regions";
import { LiveInfoSection } from "../live-info/LiveInfoSection";
import { getFestivalDetail, type FestivalDetail } from "./api";
import { FestivalAiPrompt } from "./FestivalAiPrompt";

export interface FestivalDetailViewProps {
  festivalId: string;
}

const NEARBY_ITEMS = [
  { id: "restroom", label: "화장실", icon: Users, group: "safety", category: "toilet" },
  { id: "parking", label: "주차장", icon: ParkingCircle, group: "safety", category: "parking" },
  { id: "food", label: "맛집", icon: Utensils, group: "food", category: "food" },
  { id: "hospital", label: "병원", icon: Hospital, group: "safety", category: "hospital" },
  { id: "subway", label: "지하철", icon: TrainFront, group: "transport", category: "subway_station" },
  { id: "bus", label: "버스", icon: Bus, group: "transport", category: "bus_stop" },
] as const;

function formatDistance(distance: number): string {
  return distance < 1000
    ? `${Math.round(distance)}m`
    : `${(distance / 1000).toFixed(1)}km`;
}

function estimateWalkingMinutes(distance: number): number {
  return Math.max(1, Math.ceil(distance / 80));
}

export function FestivalDetailView({ festivalId }: FestivalDetailViewProps) {
  const [festival, setFestival] = useState<FestivalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const [failedHeroSrc, setFailedHeroSrc] = useState<string | null>(null);
  const [nearbyItemId, setNearbyItemId] = useState<string | null>(null);
  const [nearbyFacilities, setNearbyFacilities] = useState<MapFacility[]>([]);
  const [nearbyLoading, setNearbyLoading] = useState(false);
  const [nearbyError, setNearbyError] = useState(false);
  const [nearbyReloadTick, setNearbyReloadTick] = useState(0);
  const [selectedFacilityId, setSelectedFacilityId] = useState<string | null>(null);

  const activeNearbyItem = NEARBY_ITEMS.find((item) => item.id === nearbyItemId) ?? null;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    async function load() {
      setLoading(true);
      setNotFound(false);
      setErrorMessage(null);
      try {
        const detail = await getFestivalDetail(festivalId, controller.signal);
        if (!active) {
          return;
        }
        setFestival(detail);
      } catch (error) {
        if (!active || (error instanceof Error && error.name === "AbortError")) {
          return;
        }
        if (error instanceof ApiError && error.status === 404) {
          setNotFound(true);
        } else {
          setErrorMessage(
            error instanceof ApiError
              ? error.message
              : "축제 정보를 불러오지 못했어요",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      active = false;
      controller.abort();
    };
  }, [festivalId, reloadTick]);

  useEffect(() => {
    if (
      !activeNearbyItem ||
      !festival ||
      festival.lat === null ||
      festival.lng === null
    ) {
      return;
    }

    const controller = new AbortController();
    setNearbyLoading(true);
    setNearbyError(false);

    listMapFacilities({
      festivalId: festival.festival_id,
      lat: festival.lat,
      lng: festival.lng,
      group: activeNearbyItem.group as FacilityGroup,
      signal: controller.signal,
    })
      .then((items) => {
        if (!controller.signal.aborted) {
          setNearbyFacilities(items);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setNearbyFacilities([]);
          setNearbyError(true);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setNearbyLoading(false);
        }
      });

    return () => controller.abort();
  }, [activeNearbyItem?.group, festival, nearbyReloadTick]);

  const visibleNearbyFacilities = useMemo(
    () =>
      activeNearbyItem
        ? nearbyFacilities.filter(
            (facility) => facility.category === activeNearbyItem.category,
          )
        : [],
    [activeNearbyItem, nearbyFacilities],
  );
  const selectedFacility = visibleNearbyFacilities.find(
    (facility) => facility.facility_id === selectedFacilityId,
  );

  if (loading) {
    return (
      <div className="space-y-4 px-4 py-4">
        <div className="h-56 animate-pulse rounded-card bg-surface-muted" />
        <div className="h-8 w-2/3 animate-pulse rounded-card bg-surface-muted" />
        <div className="h-24 animate-pulse rounded-card bg-surface-muted" />
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 px-4 py-12 text-center">
        <p className="text-base font-bold text-ink">축제를 찾을 수 없어요</p>
        <p className="text-xs text-muted">
          요청하신 축제가 삭제되었거나 존재하지 않습니다.
        </p>
        <Link
          href="/festivals"
          className="mt-1 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface shadow-sm"
        >
          목록으로
        </Link>
      </div>
    );
  }

  if (errorMessage || !festival) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 px-4 py-12 text-center">
        <p className="text-sm font-semibold text-ink">
          {errorMessage ?? "축제 정보를 불러오지 못했어요"}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setReloadTick((prev) => prev + 1)}
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface shadow-sm"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>다시 시도</span>
          </button>
          <Link
            href="/festivals"
            className="rounded-chip border border-line-light bg-surface px-4 py-2 text-xs font-bold text-ink"
          >
            목록으로
          </Link>
        </div>
      </div>
    );
  }

  const heroImage = festival.image_url ?? festival.thumbnail_url;
  const showHeroImage = Boolean(heroImage) && failedHeroSrc !== heroImage;
  const badge =
    festival.event_status === "cancelled"
      ? "취소"
      : dday(festival.start_date, festival.end_date);
  const periodText = formatFestivalPeriod(
    festival.start_date,
    festival.end_date,
  );
  const regionLabel = getRegionLabel(festival.region_code);
  const hasCoordinates = festival.lat !== null && festival.lng !== null;

  return (
    <div className="space-y-6 px-4 py-3 pb-6">
      <FestivalAiPrompt festivalId={festival.festival_id} />

      <section className="space-y-4">
        <div className="relative aspect-[3/1] w-full overflow-hidden rounded-card-lg border border-line-light bg-surface-soft/45 shadow-card">
          {showHeroImage && heroImage ? (
            <Image
              src={heroImage}
              alt={festival.name}
              fill
              sizes="(max-width: 767px) 100vw, 1100px"
              unoptimized
              onError={() => setFailedHeroSrc(heroImage)}
              className="bg-ink/5 object-cover object-center"
            />
          ) : (
            <FestivalImagePlaceholder />
          )}

          {badge ? (
            <span className="absolute left-3 top-3 rounded-chip bg-brand px-2.5 py-1 text-xs font-extrabold text-surface shadow-sm">
              {badge}
            </span>
          ) : null}
          <FavoriteButton
            festivalId={festival.festival_id}
            appearance="icon"
            className="absolute right-2 top-0.5 z-10"
          />
        </div>

        <div className="min-w-0 space-y-2">
          <div className="flex items-start gap-2">
            <span className="mt-1 h-6 w-1.5 shrink-0 rounded-chip bg-brand" />
            <h1 className="text-[24px] font-black leading-tight tracking-tight text-ink">{festival.name}</h1>
          </div>
          {festival.overview ? <p className="text-sm leading-relaxed text-muted">{festival.overview}</p> : null}
        </div>
      </section>

      <div aria-label="기본 정보" className="grid grid-cols-2 gap-2">
        <div className="flex items-center gap-2 rounded-chip bg-surface-muted px-3 py-2.5 text-[11px]"><CalendarDays className="h-4 w-4 shrink-0 text-ink" aria-hidden="true" /><span className="font-semibold">{periodText}</span></div>
        <div className="flex items-center gap-2 rounded-chip bg-surface-muted px-3 py-2.5 text-[11px]"><MapPin className="h-4 w-4 shrink-0 text-ink" aria-hidden="true" /><span className="truncate font-semibold">{festival.venue_name ?? festival.address ?? "장소 미정"}</span></div>
        {festival.fee_text ? <div className="flex items-center gap-2 rounded-chip bg-surface-muted px-3 py-2.5 text-[11px]"><Ticket className="h-4 w-4 shrink-0 text-ink" aria-hidden="true" /><span className="truncate font-semibold">{festival.fee_text}</span></div> : null}
        <div className="flex items-center gap-2 rounded-chip bg-surface-muted px-3 py-2.5 text-[11px]"><Compass className="h-4 w-4 shrink-0 text-ink" aria-hidden="true" /><span className="truncate font-semibold">{regionLabel}</span></div>
      </div>

      {/* 축제 정보 박스 */}
      {festival.address || festival.homepage_url ? (
        <section className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
            <h2 className="text-base font-extrabold text-ink">축제 정보</h2>
          </div>
          <div className="space-y-1.5 rounded-card bg-surface-soft/75 px-4 py-3.5 text-xs leading-relaxed text-ink shadow-sm">
            {festival.address ? (
              <p>
                <span className="font-bold">주소: </span>
                <span>{festival.address}</span>
              </p>
            ) : null}
            {festival.homepage_url ? (
              <p className="truncate">
                <span className="font-bold">홈페이지: </span>
                <a
                  href={festival.homepage_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-brand underline underline-offset-2"
                >
                  {festival.homepage_url}
                </a>
              </p>
            ) : null}
          </div>
        </section>
      ) : null}

      {/* 현장 정보 (주변 지역 혼잡 · 날씨 · 공지) */}
      <LiveInfoSection festivalId={festival.festival_id} />

      {/* 주변 정보 아이콘 + 지도 */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
          <h2 className="text-base font-extrabold text-ink">주변 정보</h2>
        </div>

        <div className="grid grid-cols-6 gap-1.5">
          {NEARBY_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = activeNearbyItem?.id === item.id;
            return (
              <button
                type="button"
                key={item.id}
                aria-label={`주변 ${item.label} 정보 보기`}
                aria-pressed={active}
                aria-controls="festival-nearby-results"
                disabled={!hasCoordinates}
                onClick={() => {
                  setNearbyItemId(item.id);
                  setSelectedFacilityId(null);
                }}
                className={`flex flex-col items-center justify-center gap-1 rounded-card border px-1 py-2.5 text-center shadow-sm transition-colors disabled:cursor-not-allowed disabled:opacity-45 ${
                  active
                    ? "border-brand bg-brand text-surface"
                    : "border-line-light bg-surface-soft/45 text-ink hover:border-brand/40 hover:bg-surface-soft"
                }`}
              >
                <Icon
                  className={`h-4 w-4 ${active ? "text-surface" : "text-brand"}`}
                  aria-hidden="true"
                />
                <span className="text-[11px] font-semibold">
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>

        {hasCoordinates && festival.lat !== null && festival.lng !== null ? (
          <div className="space-y-2">
            <KakaoMap
              center={
                selectedFacility
                  ? { lat: selectedFacility.lat, lng: selectedFacility.lng }
                  : { lat: festival.lat, lng: festival.lng }
              }
              markers={[
                {
                  id: `festival:${festival.festival_id}`,
                  lat: festival.lat,
                  lng: festival.lng,
                  title: festival.name,
                  label: "축제장",
                  icon: "festival",
                  variant: "festival",
                  selected: selectedFacilityId === null,
                },
                ...visibleNearbyFacilities.map((facility) => ({
                  id: `facility:${facility.facility_id}`,
                  lat: facility.lat,
                  lng: facility.lng,
                  title: `${facility.name} · ${FACILITY_LABELS[facility.category]}`,
                  label: FACILITY_SYMBOLS[facility.category],
                  icon:
                    facility.category === "subway_station"
                      ? ("subway" as const)
                      : facility.category === "toilet"
                        ? ("toilet" as const)
                        : undefined,
                  variant: activeNearbyItem?.group,
                  selected: selectedFacilityId === facility.facility_id,
                })),
              ]}
              onMarkerClick={(marker) => {
                if (marker.id?.startsWith("facility:")) {
                  setSelectedFacilityId(marker.id.slice("facility:".length));
                } else if (marker.id?.startsWith("festival:")) {
                  setSelectedFacilityId(null);
                }
              }}
              className="h-44 w-full shadow-sm"
            />
            {festival.venue_name || festival.address ? (
              <div className="flex items-center gap-2 rounded-card border border-line-light bg-surface px-3.5 py-2.5 text-xs text-ink shadow-sm">
                <MapPin className="h-4 w-4 shrink-0 text-brand" aria-hidden="true" />
                <div className="min-w-0">
                  {festival.venue_name ? (
                    <p className="truncate font-bold">{festival.venue_name}</p>
                  ) : null}
                  {festival.address ? (
                    <p className="truncate text-[11px] text-muted">
                      {festival.address}
                    </p>
                  ) : null}
                </div>
              </div>
            ) : null}

            <div id="festival-nearby-results" aria-live="polite">
              {activeNearbyItem ? (
                <div className="space-y-2 rounded-card-lg border border-line-light bg-surface-soft/35 p-3 shadow-sm">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-extrabold text-ink">
                      주변 {activeNearbyItem.label}
                      <span className="ml-1.5 text-xs font-semibold text-muted">
                        ({nearbyLoading ? "…" : `${visibleNearbyFacilities.length}곳`})
                      </span>
                    </p>
                    <span className="rounded-chip border border-line-light bg-surface px-2.5 py-1 text-[10px] font-bold text-muted">
                      거리순
                    </span>
                  </div>

                  {selectedFacility ? (
                    <article
                      aria-label={`${selectedFacility.name} 상세 정보`}
                      className="rounded-card border border-brand/35 bg-brand-soft/40 p-3"
                    >
                      <div className="flex items-start gap-2.5">
                        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-card bg-surface font-black text-brand shadow-sm" aria-hidden="true">
                          {FACILITY_SYMBOLS[selectedFacility.category]}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <h3 className="text-sm font-black text-ink">{selectedFacility.name}</h3>
                            <span className="rounded-chip bg-brand px-2 py-0.5 text-[9px] font-extrabold text-surface">
                              {FACILITY_LABELS[selectedFacility.category]}
                            </span>
                          </div>
                          <p className="mt-1 text-[11px] leading-relaxed text-muted">
                            {selectedFacility.address || "주소 정보가 제공되지 않았어요."}
                          </p>
                          <p className="mt-1 text-[11px] font-bold text-ink">
                            축제장에서 {formatDistance(selectedFacility.distance_m)} · 도보 약 {estimateWalkingMinutes(selectedFacility.distance_m)}분
                          </p>
                        </div>
                      </div>
                    </article>
                  ) : null}

                  {nearbyLoading ? (
                    <div role="status" className="space-y-2">
                      {[0, 1].map((item) => (
                        <div key={item} className="h-14 animate-pulse rounded-card bg-surface-muted" />
                      ))}
                    </div>
                  ) : nearbyError ? (
                    <div className="flex items-center justify-between gap-3 rounded-card bg-surface px-3 py-3 text-xs text-muted">
                      <span>주변 정보를 불러오지 못했어요.</span>
                      <button
                        type="button"
                        onClick={() => setNearbyReloadTick((value) => value + 1)}
                        className="inline-flex shrink-0 items-center gap-1 rounded-chip border border-line-light px-2.5 py-1.5 font-bold text-ink"
                      >
                        <RotateCcw className="h-3 w-3" aria-hidden="true" />
                        다시 시도
                      </button>
                    </div>
                  ) : visibleNearbyFacilities.length === 0 ? (
                    <p className="rounded-card bg-surface px-3 py-5 text-center text-xs font-semibold text-muted">
                      주변 {activeNearbyItem.label} 정보가 없어요.
                    </p>
                  ) : (
                    <ul className="grid gap-2 sm:grid-cols-2">
                      {visibleNearbyFacilities
                        .slice()
                        .sort((left, right) => left.distance_m - right.distance_m)
                        .map((facility) => {
                          const selected = selectedFacilityId === facility.facility_id;
                          return (
                            <li key={facility.facility_id}>
                              <button
                                type="button"
                                aria-label={`${facility.name} 상세 정보 보기`}
                                aria-pressed={selected}
                                onClick={() => setSelectedFacilityId(facility.facility_id)}
                                className={`flex w-full items-center gap-2.5 rounded-card border px-3 py-2.5 text-left transition-colors ${
                                  selected
                                    ? "border-brand bg-brand-soft/45"
                                    : "border-line-light bg-surface hover:border-brand/40"
                                }`}
                              >
                                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-card bg-brand-soft text-xs font-black text-brand" aria-hidden="true">
                                  {FACILITY_SYMBOLS[facility.category]}
                                </span>
                                <span className="min-w-0 flex-1">
                                  <strong className="block truncate text-xs font-extrabold text-ink">{facility.name}</strong>
                                  <span className="mt-0.5 block text-[10px] font-medium text-muted">
                                    {formatDistance(facility.distance_m)} · 도보 약 {estimateWalkingMinutes(facility.distance_m)}분
                                  </span>
                                </span>
                              </button>
                            </li>
                          );
                        })}
                    </ul>
                  )}
                </div>
              ) : (
                <p className="rounded-card border border-dashed border-line-light bg-surface-soft/35 px-3 py-3 text-center text-xs font-semibold text-muted">
                  위 버튼을 누르면 주변 시설을 이 지도에서 바로 확인할 수 있어요.
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="flex h-28 items-center justify-center rounded-card border border-line-light bg-surface-muted/60 text-xs font-medium text-muted">
            위치 정보가 없어요
          </div>
        )}
      </section>

      <SafeReturnBanner festivalId={festival.festival_id} />

      <section className="space-y-3">
        <div className="flex items-end justify-between"><div><h2 className="flex items-center gap-2 text-xl font-black"><span className="h-5 w-1.5 rounded-chip bg-brand" />동행 모집</h2><p className="ml-3.5 mt-1 text-xs text-muted">함께 축제를 즐길 동행을 찾아보세요!</p></div><Link href={`/companions?festivalId=${encodeURIComponent(festival.festival_id)}`} className="text-sm font-extrabold text-brand">전체보기 ›</Link></div>
        <div className="grid grid-cols-2 gap-3">
          {["이 축제 같이 가요!", "사진 같이 찍어요!"].map((title, index) => (
            <Link key={title} href={`/companions?festivalId=${encodeURIComponent(festival.festival_id)}`} className="rounded-card-lg border border-brand/20 bg-surface-soft p-3 shadow-sm">
              <div className="flex items-center gap-2"><span className="grid h-10 w-10 place-items-center rounded-chip bg-surface text-brand"><Users className="h-5 w-5" /></span><div><p className="line-clamp-1 text-xs font-extrabold">{title}</p><p className="mt-1 text-[11px] text-muted">12.0{index + 6} · <b className="text-brand">{index + 2} / {index + 4}명</b></p></div></div>
            </Link>
          ))}
        </div>
      </section>

    </div>
  );
}

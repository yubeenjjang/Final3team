"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  CalendarDays,
  ChevronDown,
  ChevronRight,
  MapPin,
  RotateCcw,
  Search,
  ShieldCheck,
  TrainFront,
  Utensils,
  Users,
} from "lucide-react";
import { KakaoMap } from "@/components/KakaoMap";
import { OpenStreetMap } from "@/components/OpenStreetMap";
import { getKakaoJsKey } from "@/lib/kakao";
import {
  listFestivals,
  type FestivalListItem,
  type ListFestivalsQuery,
} from "@/features/festivals/explore/api";
import { formatFestivalPeriod } from "@/features/festivals/explore/dday";
import { getRegionLabel } from "@/features/festivals/explore/regions";
import { getFestivalDetail } from "@/features/festivals/detail/api";
import {
  FACILITY_GROUPS,
  FACILITY_LABELS,
  FACILITY_SYMBOLS,
  getMapCrowd,
  listMapFacilities,
  type FacilityGroup,
  type FacilityCategory,
  type MapCrowd,
  type MapFacility,
} from "./api";

type LocatedFestival = FestivalListItem & { lat: number; lng: number };

function hasLocation(festival: FestivalListItem): festival is LocatedFestival {
  return typeof festival.lat === "number" && typeof festival.lng === "number";
}

// 검색은 서버(A02 q)에서 한다. 기본 목록(진행 중·예정)만으로는 다른 축제를 찾을 수 없다.
const SEARCH_DEBOUNCE_MS = 300;
// A02는 쉼표로 여러 상태를 받지만 생성된 타입은 한 값만 허용해서 맞춰 준다 (explore/api.ts와 같은 방식)
const SEARCH_STATUSES = "ongoing,upcoming,ended" as ListFestivalsQuery["status"];

function formatDistance(distance: number): string {
  return distance < 1000
    ? `${Math.round(distance)}m`
    : `${(distance / 1000).toFixed(1)}km`;
}

interface FestivalMapViewProps {
  initialFestivalId?: string | null;
  initialGroup?: FacilityGroup;
  initialCategory?: FacilityCategory | "all";
}

export function FestivalMapView({
  initialFestivalId = null,
  initialGroup = "transport",
  initialCategory = "all",
}: FestivalMapViewProps = {}) {
  const [festivals, setFestivals] = useState<LocatedFestival[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(initialFestivalId);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<LocatedFestival[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchFailed, setSearchFailed] = useState(false);
  const [picked, setPicked] = useState<LocatedFestival | null>(null);
  const [facilityGroup, setFacilityGroup] = useState<FacilityGroup>(initialGroup);
  const [facilityCategory, setFacilityCategory] = useState<FacilityCategory | "all">(initialCategory);
  const [facilities, setFacilities] = useState<MapFacility[]>([]);
  const [facilitiesLoading, setFacilitiesLoading] = useState(true);
  const [crowd, setCrowd] = useState<MapCrowd | null>(null);
  const [crowdLoading, setCrowdLoading] = useState(true);
  const [festivalMenuOpen, setFestivalMenuOpen] = useState(false);
  const [selectedFacilityId, setSelectedFacilityId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    listFestivals({ page: 1, page_size: 100 }, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        const located = result.items.filter(hasLocation);
        setFestivals(located);
        setSelectedId((current) => current ?? located[0]?.festival_id ?? null);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [attempt]);

  // 상세에서 넘어온 축제가 기본 목록(진행 중·예정)에 없으면 A03으로 받아 지도에 추가한다.
  useEffect(() => {
    if (loading || !initialFestivalId) return;
    if (festivals.some((festival) => festival.festival_id === initialFestivalId)) return;
    const controller = new AbortController();
    getFestivalDetail(initialFestivalId, controller.signal)
      .then((detail) => {
        if (controller.signal.aborted) return;
        const item: FestivalListItem = {
          festival_id: detail.festival_id,
          name: detail.name,
          region_code: detail.region_code,
          venue_name: detail.venue_name,
          lat: detail.lat,
          lng: detail.lng,
          start_date: detail.start_date,
          end_date: detail.end_date,
          event_status: detail.event_status,
          thumbnail_url: detail.thumbnail_url,
          image_credit: detail.image_credit,
          source: detail.source,
          last_synced_at: detail.last_synced_at,
        };
        if (hasLocation(item)) setPicked(item);
      })
      .catch(() => {
        // 찾을 수 없으면 기본 목록의 첫 축제를 그대로 보여 준다.
      });
    return () => controller.abort();
  }, [festivals, initialFestivalId, loading]);

  const trimmedQuery = query.trim().slice(0, 50);
  const visibleFestivals = trimmedQuery ? searchResults : festivals;

  // 지도에 찍는 축제 = 기본 목록 + 검색으로 고른 축제. 검색어를 칠 때마다 마커가 바뀌지 않게 한다.
  const mapFestivals = useMemo(
    () =>
      picked && !festivals.some((festival) => festival.festival_id === picked.festival_id)
        ? [...festivals, picked]
        : festivals,
    [festivals, picked],
  );

  const selected =
    mapFestivals.find((festival) => festival.festival_id === selectedId) ??
    mapFestivals[0];
  const selectedIdRef = useRef<string | null>(null);
  const selectedFestivalId = selected?.festival_id ?? null;
  useEffect(() => {
    selectedIdRef.current = selectedFestivalId;
  }, [selectedFestivalId]);
  const kakaoKey = getKakaoJsKey();

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    listMapFacilities({
      festivalId: selected.festival_id,
      lat: selected.lat,
      lng: selected.lng,
      group: facilityGroup,
      signal: controller.signal,
    })
      .then((items) => {
        if (!controller.signal.aborted) setFacilities(items);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFacilities([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setFacilitiesLoading(false);
      });
    return () => controller.abort();
  }, [facilityGroup, selected]);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    getMapCrowd(selected.festival_id, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setCrowd(value);
      })
      .catch(() => {
        if (!controller.signal.aborted) setCrowd(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setCrowdLoading(false);
      });
    return () => controller.abort();
  }, [selected]);

  function selectFestival(festival: LocatedFestival) {
    setPicked(festival);
    setSelectedId(festival.festival_id);
    setFacilities([]);
    setFacilitiesLoading(true);
    setCrowd(null);
    setCrowdLoading(true);
    setFestivalMenuOpen(false);
    setSelectedFacilityId(null);
  }

  function selectFacilityGroup(group: FacilityGroup) {
    setFacilityGroup(group);
    setFacilityCategory("all");
    setFacilities([]);
    setFacilitiesLoading(true);
    setSelectedFacilityId(null);
  }

  function changeQuery(value: string) {
    setQuery(value);
    setSearching(Boolean(value.trim()));
    setSearchFailed(false);
  }

  useEffect(() => {
    if (!trimmedQuery) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      listFestivals(
        { q: trimmedQuery, status: SEARCH_STATUSES, sort: "-start_date", page: 1, page_size: 20 },
        controller.signal,
      )
        .then((result) => {
          if (controller.signal.aborted) return;
          const located = result.items.filter(hasLocation);
          setSearchFailed(false);
          setSearchResults(located);
          const first = located[0];
          if (first && first.festival_id !== selectedIdRef.current) selectFestival(first);
        })
        .catch(() => {
          // 서버 오류를 '결과 없음'으로 보이지 않게 따로 표시한다 (취소된 요청은 무시).
          if (controller.signal.aborted) return;
          setSearchResults([]);
          setSearchFailed(true);
        })
        .finally(() => {
          if (!controller.signal.aborted) setSearching(false);
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // 검색어가 바뀔 때만 다시 찾는다 (selectFestival은 setter만 쓴다)
  }, [trimmedQuery]);

  const groupOptions: Array<{
    key: FacilityGroup;
    label: string;
    Icon: typeof TrainFront;
  }> = [
    { key: "transport", label: "교통", Icon: TrainFront },
    { key: "food", label: "맛집·관광", Icon: Utensils },
    { key: "safety", label: "편의·안전", Icon: ShieldCheck },
  ];

  const visibleFacilities = useMemo(
    () =>
      facilityCategory === "all"
        ? facilities
        : facilities.filter((facility) => facility.category === facilityCategory),
    [facilities, facilityCategory],
  );
  // 렌더마다 새 배열을 넘기면 지도가 매번 다시 그려지므로 묶어 둔다.
  const kakaoMarkers = useMemo(
    () =>
      mapFestivals
        .map((festival) => ({ lat: festival.lat, lng: festival.lng, title: festival.name }))
        .concat(
          visibleFacilities.map((facility) => ({
            lat: facility.lat,
            lng: facility.lng,
            title: facility.name,
          })),
        ),
    [mapFestivals, visibleFacilities],
  );
  const selectedFacility = visibleFacilities.find(
    (facility) => facility.facility_id === selectedFacilityId,
  );
  const mapCenter = selectedFacility
    ? { lat: selectedFacility.lat, lng: selectedFacility.lng }
    : selected
      ? { lat: selected.lat, lng: selected.lng }
      : null;

  const crowdColorClass: Record<MapCrowd["color"], string> = {
    green: "bg-crowd-green text-ink",
    yellow: "bg-crowd-yellow text-ink",
    orange: "bg-crowd-orange text-ink",
    red: "bg-crowd-red text-ink",
  };

  const facilitySectionTitle: Record<FacilityGroup, string> = {
    transport: "주변 교통",
    food: "주변 맛집·관광",
    safety: "주변 편의·안전시설",
  };

  return (
    <div className="space-y-4 px-4 pb-4 pt-3">
      <section aria-label="지도 검색" className="relative z-30">
        <label className="relative block">
          <span className="sr-only">축제명 또는 장소 검색</span>
          <Search
            className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted"
            aria-hidden="true"
          />
          <input
            type="search"
            value={query}
            onChange={(event) => changeQuery(event.target.value)}
            placeholder="축제명, 장소 검색"
            aria-label="축제명 또는 장소 검색"
            className="h-12 w-full rounded-input border border-line-light bg-surface pl-12 pr-4 text-sm font-semibold text-ink shadow-card placeholder:font-medium placeholder:text-muted focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/15"
          />
        </label>
        {trimmedQuery && !searching && visibleFestivals.length === 0 ? (
          <p
            role={searchFailed ? "alert" : "status"}
            className="absolute inset-x-0 top-14 z-30 rounded-card-lg border border-line-light bg-surface px-4 py-3 text-xs font-semibold text-muted shadow-xl"
          >
            {searchFailed
              ? "검색 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요."
              : "검색 조건에 맞는 축제가 없어요."}
          </p>
        ) : null}
        {trimmedQuery && visibleFestivals.length > 0 ? (
          <div className="absolute inset-x-0 top-14 z-30 max-h-52 overflow-y-auto rounded-card-lg border border-line-light bg-surface p-2 shadow-xl">
            {visibleFestivals.map((festival) => (
              <button
                key={festival.festival_id}
                type="button"
                onClick={() => {
                  selectFestival(festival);
                  setQuery("");
                }}
                className="flex w-full items-center justify-between gap-3 rounded-card px-3 py-2.5 text-left hover:bg-surface-muted"
              >
                <span className="min-w-0">
                  <strong className="block truncate text-xs font-extrabold text-ink">{festival.name}</strong>
                  <span className="mt-0.5 block truncate text-[10px] text-muted">
                    {getRegionLabel(festival.region_code)} · {festival.venue_name ?? "장소 미정"}
                  </span>
                </span>
                <ChevronRight className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
              </button>
            ))}
          </div>
        ) : null}
      </section>

      {loading ? (
        <div
          role="status"
          className="h-[360px] animate-pulse rounded-card-lg border border-line-light bg-surface-muted"
        >
          <span className="sr-only">축제 지도를 불러오는 중이에요.</span>
        </div>
      ) : failed ? (
        <div className="flex min-h-72 flex-col items-center justify-center gap-3 rounded-card-lg border border-line-light bg-surface px-4 text-center">
          <p className="text-sm font-semibold text-ink">축제 위치를 불러오지 못했어요.</p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              setFailed(false);
              setAttempt((value) => value + 1);
            }}
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> 다시 시도
          </button>
        </div>
      ) : !selected ? (
        <div className="flex min-h-72 items-center justify-center rounded-card-lg border border-line-light bg-surface px-4 text-center text-sm font-semibold text-muted">
          {query ? "검색 조건에 맞는 축제가 없어요." : "지도에 표시할 축제 위치가 없어요."}
        </div>
      ) : (
        <>
          <section className="relative z-20 grid grid-cols-[minmax(0,1fr)_auto] gap-2" aria-label="선택한 축제와 혼잡도">
            <button
              type="button"
              aria-expanded={festivalMenuOpen}
              onClick={() => setFestivalMenuOpen((open) => !open)}
              className="flex min-w-0 items-center gap-2 rounded-input border border-line-light bg-surface px-3 py-2.5 text-left shadow-card"
            >
              <CalendarDays className="h-5 w-5 shrink-0 text-ink" aria-hidden="true" />
              <span className="min-w-0 flex-1">
                <strong className="block truncate text-xs font-extrabold text-ink">
                  {selected.name} ({getRegionLabel(selected.region_code)})
                </strong>
                <span className="mt-0.5 block truncate text-[9px] font-medium text-muted">
                  {formatFestivalPeriod(selected.start_date, selected.end_date)} · {selected.venue_name ?? "장소 미정"}
                </span>
              </span>
              <ChevronDown className="h-4 w-4 shrink-0 text-ink" aria-hidden="true" />
            </button>
            <div className="flex min-w-[104px] items-center justify-center gap-1.5 rounded-input border border-brand/20 bg-surface px-2.5 shadow-card">
              <Users className="h-4 w-4 shrink-0 text-brand" aria-hidden="true" />
              <span className="text-[10px] font-bold text-ink">현재 혼잡도</span>
              <span
                className={`rounded-chip px-2 py-1 text-[10px] font-extrabold ${
                  crowd ? crowdColorClass[crowd.color] : "bg-surface-muted text-muted"
                }`}
              >
                {crowdLoading ? "확인 중" : crowd?.level ?? "정보 없음"}
              </span>
            </div>

            {festivalMenuOpen ? (
              <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-30 max-h-64 overflow-y-auto rounded-card-lg border border-line-light bg-surface p-2 shadow-xl">
                {festivals.map((festival) => (
                  <button
                    key={festival.festival_id}
                    type="button"
                    onClick={() => selectFestival(festival)}
                    className="flex w-full items-center justify-between gap-2 rounded-card px-3 py-2.5 text-left hover:bg-surface-muted"
                  >
                    <span className="min-w-0">
                      <strong className="block truncate text-xs font-extrabold text-ink">{festival.name}</strong>
                      <span className="block truncate text-[10px] text-muted">
                        {getRegionLabel(festival.region_code)} · {festival.venue_name ?? "장소 미정"}
                      </span>
                    </span>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
                  </button>
                ))}
              </div>
            ) : null}
          </section>

          <div className="grid grid-cols-3 rounded-panel bg-surface p-1 shadow-card" role="group" aria-label="지도 정보 종류">
            {groupOptions.map(({ key, label, Icon }) => {
              const active = facilityGroup === key;
              return (
                <button
                  key={key}
                  type="button"
                  aria-pressed={active}
                  onClick={() => selectFacilityGroup(key)}
                  className={
                    active
                      ? "flex h-12 items-center justify-center gap-1.5 rounded-input bg-brand px-2 text-xs font-extrabold text-surface"
                      : "flex h-12 items-center justify-center gap-1.5 rounded-input px-2 text-xs font-bold text-ink"
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span className="truncate">{label}</span>
                </button>
              );
            })}
          </div>

          <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1" role="group" aria-label="세부 시설 종류">
            <button
              type="button"
              aria-pressed={facilityCategory === "all"}
              onClick={() => {
                setFacilityCategory("all");
                setSelectedFacilityId(null);
              }}
              className={
                facilityCategory === "all"
                  ? "shrink-0 rounded-chip border border-brand bg-brand-soft px-4 py-2 text-xs font-extrabold text-brand"
                  : "shrink-0 rounded-chip border border-line-light bg-surface px-4 py-2 text-xs font-bold text-muted"
              }
            >
              전체
            </button>
            {FACILITY_GROUPS[facilityGroup].map((category) => (
              <button
                key={category}
                type="button"
                aria-pressed={facilityCategory === category}
                onClick={() => {
                  setFacilityCategory(category);
                  setSelectedFacilityId(null);
                }}
                className={
                  facilityCategory === category
                    ? "shrink-0 rounded-chip border border-brand bg-brand-soft px-4 py-2 text-xs font-extrabold text-brand"
                    : "shrink-0 rounded-chip border border-line-light bg-surface px-4 py-2 text-xs font-bold text-muted"
                }
              >
                <span className="mr-1">{FACILITY_SYMBOLS[category]}</span>
                {FACILITY_LABELS[category]}
              </button>
            ))}
          </div>

          <section aria-label="축제 위치 지도" className="relative">
            {kakaoKey ? (
              <KakaoMap
                center={mapCenter ?? { lat: selected.lat, lng: selected.lng }}
                markers={kakaoMarkers}
                level={12}
                className="h-[360px] w-full"
              />
            ) : (
              <OpenStreetMap
                center={mapCenter ?? { lat: selected.lat, lng: selected.lng }}
                title={selectedFacility?.name ?? selected.name}
                markers={visibleFacilities.map((facility) => ({
                  lat: facility.lat,
                  lng: facility.lng,
                  title: facility.name,
                  label: FACILITY_SYMBOLS[facility.category],
                }))}
                className="h-[320px] w-full"
              />
            )}
            <span className="absolute left-3 top-3 z-10 rounded-chip bg-surface/95 px-3 py-1.5 text-[11px] font-extrabold text-ink shadow-card backdrop-blur-sm">
              {facilitiesLoading
                ? "주변 시설 확인 중"
                : `${FACILITY_LABELS[FACILITY_GROUPS[facilityGroup][0]]} 등 ${facilities.length}곳`}
            </span>
          </section>

          <section aria-label="주변 시설 목록" className="-mx-4 rounded-t-[28px] border-t border-line-light bg-surface px-4 pb-2 pt-3 shadow-[0_-8px_24px_rgba(52,53,54,0.08)]">
            <div className="flex items-center justify-between gap-2">
              <div className="flex min-w-0 items-center gap-2">
                <span className="h-6 w-1.5 shrink-0 rounded-chip bg-brand" aria-hidden="true" />
                <h2 className="truncate text-lg font-black text-ink">{facilitySectionTitle[facilityGroup]}</h2>
                <span className="shrink-0 text-xs font-semibold text-muted">
                  ({facilitiesLoading ? "…" : `${visibleFacilities.length}곳`})
                </span>
              </div>
              <span className="shrink-0 rounded-chip border border-line-light px-3 py-1.5 text-[10px] font-bold text-muted">거리순</span>
            </div>

            {facilitiesLoading ? (
              <div role="status" className="mt-3 space-y-2">
                {[0, 1, 2].map((item) => (
                  <div key={item} className="h-16 animate-pulse rounded-card bg-surface-muted" />
                ))}
              </div>
            ) : visibleFacilities.length === 0 ? (
              <p className="py-10 text-center text-xs font-semibold text-muted">선택한 종류의 주변 시설 정보가 없어요.</p>
            ) : (
              <ul className="mt-3 space-y-2">
                {visibleFacilities
                  .slice()
                  .sort((left, right) => left.distance_m - right.distance_m)
                  .map((facility) => (
                    <li key={facility.facility_id}>
                      <button
                        type="button"
                        aria-label={`${facility.name} 지도에서 보기`}
                        aria-pressed={selectedFacilityId === facility.facility_id}
                        onClick={() => setSelectedFacilityId(facility.facility_id)}
                        className={`flex w-full items-center gap-3 rounded-card border px-3 py-3 text-left shadow-sm transition-colors ${
                          selectedFacilityId === facility.facility_id
                            ? "border-brand bg-brand-soft/40"
                            : "border-line-light bg-surface hover:border-brand/40"
                        }`}
                      >
                        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-card bg-brand-soft text-sm font-black text-brand">
                          {FACILITY_SYMBOLS[facility.category]}
                        </span>
                        <span className="min-w-0 flex-1">
                          <strong className="block truncate text-sm font-extrabold text-ink">{facility.name}</strong>
                          <span className="mt-1 flex items-center gap-1 text-[11px] font-medium text-muted">
                            <MapPin className="h-3 w-3 shrink-0" aria-hidden="true" />
                            축제장에서 {formatDistance(facility.distance_m)} · {FACILITY_LABELS[facility.category]}
                          </span>
                        </span>
                        {facilityGroup === "safety" ? (
                          <span className="shrink-0 rounded-chip bg-crowd-green/30 px-2 py-1 text-[10px] font-bold text-ink">운영 중</span>
                        ) : null}
                        <ChevronRight className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
                      </button>
                    </li>
                  ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}

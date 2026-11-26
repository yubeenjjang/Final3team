"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { KakaoMap, type KakaoMapArea, type KakaoMapMarker } from "@/components/KakaoMap";
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
import { formatDateTimeShort } from "@/features/festivals/live-info/liveInfoUtils";
import {
  FACILITY_GROUPS,
  FACILITY_LABELS,
  FACILITY_SYMBOLS,
  getMapCrowd,
  listMapFacilities,
  type FacilityGroup,
  type FacilityCategory,
  type AvailableMapCrowd,
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

function estimateWalkingMinutes(distance: number): number {
  return Math.max(1, Math.ceil(distance / 80));
}

function createCrowdCircle(
  center: { lat: number; lng: number },
  radiusM = 420,
): Array<{ lat: number; lng: number }> {
  const latitudeRadius = radiusM / 111_320;
  const longitudeRadius = radiusM / (111_320 * Math.cos((center.lat * Math.PI) / 180));
  return Array.from({ length: 32 }, (_, index) => {
    const angle = (index / 32) * Math.PI * 2;
    return {
      lat: center.lat + Math.sin(angle) * latitudeRadius,
      lng: center.lng + Math.cos(angle) * longitudeRadius,
    };
  });
}

function getFacilitySourceLabel(source?: string | null): string | null {
  if (!source) return null;
  if (source === "kakao_local") return "카카오 장소 검색";
  if (source.startsWith("seoul_")) return "서울 공공데이터";
  return "공공·제휴 데이터";
}

const FACILITY_EXTRA_LABELS: Record<string, string> = {
  phone: "전화번호",
  telephone: "전화번호",
  tel: "전화번호",
  opening_hours: "운영시간",
  operating_hours: "운영시간",
  line: "노선",
  capacity: "수용 정보",
};

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
  const [crowdAttempt, setCrowdAttempt] = useState(0);
  const [crowdOpen, setCrowdOpen] = useState(false);
  const [festivalMenuOpen, setFestivalMenuOpen] = useState(false);
  const [selectedFacilityId, setSelectedFacilityId] = useState<string | null>(null);
  const facilityListRef = useRef<HTMLElement | null>(null);

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
    setCrowdLoading(true);
    setCrowd(null);
    getMapCrowd(selected.festival_id, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setCrowd(value);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setCrowd({
            available: false,
            reason: "조회 지연",
            message: "혼잡 정보를 불러오지 못했어요. 잠시 후 다시 확인해 주세요.",
          });
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setCrowdLoading(false);
      });
    return () => controller.abort();
  }, [crowdAttempt, selected]);

  function selectFestival(festival: LocatedFestival) {
    setPicked(festival);
    setSelectedId(festival.festival_id);
    setFacilities([]);
    setFacilitiesLoading(true);
    setCrowd(null);
    setCrowdLoading(true);
    setCrowdOpen(false);
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
  const mapMarkers = useMemo<KakaoMapMarker[]>(
    () => [
      ...(selected
        ? [{
            id: `festival:${selected.festival_id}`,
            lat: selected.lat,
            lng: selected.lng,
            title: `${selected.name} 축제장`,
            label: "🎪",
            icon: "festival" as const,
            variant: "festival" as const,
            selected: selectedFacilityId === null,
          }]
        : []),
      ...visibleFacilities.map((facility) => ({
        id: `facility:${facility.facility_id}`,
        lat: facility.lat,
        lng: facility.lng,
        title: `${facility.name} · ${FACILITY_LABELS[facility.category]}`,
        label: FACILITY_SYMBOLS[facility.category],
        icon:
          facility.category === "subway_station"
            ? "subway" as const
            : facility.category === "toilet"
              ? "toilet" as const
              : undefined,
        variant: facilityGroup,
        selected: selectedFacilityId === facility.facility_id,
      })),
    ],
    [facilityGroup, selected, selectedFacilityId, visibleFacilities],
  );

  const handleMarkerClick = useCallback((marker: KakaoMapMarker) => {
    if (marker.id?.startsWith("facility:")) {
      setSelectedFacilityId(marker.id.slice("facility:".length));
      window.requestAnimationFrame(() => {
        facilityListRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
      });
      return;
    }
    if (marker.id?.startsWith("festival:")) setSelectedFacilityId(null);
  }, []);
  const selectedFacility = visibleFacilities.find(
    (facility) => facility.facility_id === selectedFacilityId,
  );
  const selectedFacilityExtras = selectedFacility?.extra
    ? Object.entries(selectedFacility.extra)
        .filter(([key, value]) => FACILITY_EXTRA_LABELS[key] && value != null && value !== "")
        .map(([key, value]) => ({ label: FACILITY_EXTRA_LABELS[key], value: String(value) }))
    : [];
  const mapCenter = selectedFacility
    ? { lat: selectedFacility.lat, lng: selectedFacility.lng }
    : selected
      ? { lat: selected.lat, lng: selected.lng }
      : null;

  const crowdColorClass: Record<AvailableMapCrowd["color"], string> = {
    green: "bg-crowd-green text-ink",
    yellow: "bg-crowd-yellow text-ink",
    orange: "bg-crowd-orange text-ink",
    red: "bg-crowd-red text-ink",
  };
  const crowdMapColor: Record<AvailableMapCrowd["color"], string> = {
    green: "#22c55e",
    yellow: "#facc15",
    orange: "#f97316",
    red: "#ef4444",
  };
  const crowdMapAreas = useMemo<KakaoMapArea[]>(() => {
    if (!crowd?.available || !selected) return [];
    const color = crowdMapColor[crowd.color];
    const paths = crowd.boundary.length > 0
      ? crowd.boundary
      : [createCrowdCircle(crowd.center ?? { lat: selected.lat, lng: selected.lng })];
    return [{
      id: `crowd-${selected?.festival_id ?? "festival"}`,
      label: `${crowd.areaName} · 혼잡도 ${crowd.level}`,
      paths,
      fillColor: color,
      strokeColor: color,
    }];
  }, [crowd, selected?.festival_id]);
  const crowdLabel = crowd?.available ? crowd.level : crowd?.reason ?? "정보 없음";

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
            <button
              type="button"
              aria-expanded={crowdOpen}
              aria-label={`현재 혼잡도 ${crowdLabel}`}
              onClick={() => setCrowdOpen((open) => !open)}
              className="flex min-w-[104px] items-center justify-center gap-1.5 rounded-input border border-brand/20 bg-surface px-2.5 shadow-card"
            >
              <Users className="h-4 w-4 shrink-0 text-brand" aria-hidden="true" />
              <span className="text-[10px] font-bold text-ink">현재 혼잡도</span>
              <span
                className={`rounded-chip px-2 py-1 text-[10px] font-extrabold ${
                  crowd?.available ? crowdColorClass[crowd.color] : "bg-surface-muted text-muted"
                }`}
              >
                {crowdLoading ? "확인 중" : crowdLabel}
              </span>
            </button>

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

          {crowdOpen ? (
            <section
              aria-label="혼잡도 상세"
              className="rounded-card border border-line-light bg-surface-soft/70 px-4 py-3 shadow-sm"
            >
              {crowdLoading ? (
                <p className="text-xs font-semibold text-muted">혼잡 정보를 확인하고 있어요.</p>
              ) : crowd?.available ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <strong className="truncate text-sm font-extrabold text-ink">{crowd.areaName}</strong>
                    <span className={`shrink-0 rounded-chip px-2.5 py-1 text-[11px] font-extrabold ${crowdColorClass[crowd.color]}`}>
                      {crowd.level}
                    </span>
                  </div>
                  {crowd.message ? <p className="text-xs leading-relaxed text-ink">{crowd.message}</p> : null}
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] font-medium text-muted">
                    {crowd.populationMin != null && crowd.populationMax != null ? (
                      <span>예상 인구 {crowd.populationMin.toLocaleString()}~{crowd.populationMax.toLocaleString()}명</span>
                    ) : null}
                    {crowd.observedAt ? <span>관측 {formatDateTimeShort(crowd.observedAt)}</span> : null}
                    {crowd.isEstimate ? <span>추정 정보</span> : null}
                    {crowd.stale ? <span className="font-bold text-brand">업데이트 지연</span> : null}
                  </div>
                </div>
              ) : crowd ? (
                <div className="flex items-center justify-between gap-3">
                  <div className="space-y-1">
                    <p className="text-xs font-extrabold text-ink">{crowd.reason}</p>
                    <p className="text-xs font-semibold leading-relaxed text-muted">
                      {crowd.message || "이 축제 주변의 실시간 혼잡 정보를 제공하지 않아요."}
                    </p>
                  </div>
                  {crowd.reason === "조회 지연" ? (
                    <button
                      type="button"
                      onClick={() => setCrowdAttempt((value) => value + 1)}
                      className="inline-flex shrink-0 items-center gap-1 rounded-chip border border-line-light bg-surface px-3 py-1.5 text-[10px] font-extrabold text-ink"
                    >
                      <RotateCcw className="h-3 w-3" aria-hidden="true" />
                      다시 확인
                    </button>
                  ) : null}
                </div>
              ) : (
                <p className="text-xs font-semibold text-muted">이 축제 주변의 혼잡 정보를 확인하지 못했어요.</p>
              )}
            </section>
          ) : null}

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
                markers={mapMarkers}
                areas={crowdMapAreas}
                onMarkerClick={handleMarkerClick}
                level={4}
                className="h-[360px] w-full"
              />
            ) : (
              <OpenStreetMap
                center={mapCenter ?? { lat: selected.lat, lng: selected.lng }}
                title={selectedFacility?.name ?? selected.name}
                markers={mapMarkers.map((marker) => ({
                  ...marker,
                  title: marker.title ?? "지도 위치",
                  label: marker.label ?? "●",
                }))}
                areas={crowdMapAreas}
                onMarkerClick={handleMarkerClick}
                className="h-[320px] w-full"
              />
            )}
            <span className="absolute left-3 top-3 z-10 rounded-chip bg-surface/95 px-3 py-1.5 text-[11px] font-extrabold text-ink shadow-card backdrop-blur-sm">
              {facilitiesLoading
                ? "주변 시설 확인 중"
                : `${FACILITY_LABELS[FACILITY_GROUPS[facilityGroup][0]]} 등 ${facilities.length}곳`}
            </span>
            {crowdLoading ? (
              <span className="absolute bottom-3 right-3 z-10 inline-flex items-center gap-2 rounded-chip bg-surface/95 px-3 py-1.5 text-[11px] font-extrabold text-muted shadow-card backdrop-blur-sm">
                <span className="h-3 w-3 animate-pulse rounded-full bg-line-light" aria-hidden="true" />
                혼잡도 확인 중
              </span>
            ) : crowd?.available ? (
              <span className="absolute bottom-3 right-3 z-10 inline-flex items-center gap-2 rounded-chip bg-surface/95 px-3 py-1.5 text-[11px] font-extrabold text-ink shadow-card backdrop-blur-sm">
                <span className={`h-3 w-3 rounded-full ${crowdColorClass[crowd.color].split(" ")[0]}`} aria-hidden="true" />
                혼잡도 {crowd.level}
              </span>
            ) : crowd ? (
              <button
                type="button"
                onClick={() => setCrowdOpen(true)}
                className="absolute bottom-3 right-3 z-10 inline-flex items-center gap-2 rounded-chip bg-surface/95 px-3 py-1.5 text-[11px] font-extrabold text-muted shadow-card backdrop-blur-sm"
              >
                혼잡도 {crowd.reason}
              </button>
            ) : null}
          </section>

          <div
            aria-label="지도 마커 범례"
            className="no-scrollbar flex items-center gap-2 overflow-x-auto rounded-card border border-line-light bg-surface px-3 py-2 text-[10px] font-bold text-ink shadow-sm"
          >
            <span className="flex shrink-0 items-center gap-1.5">
              <span className="h-3 w-3 rounded-full bg-brand" aria-hidden="true" /> 축제장
            </span>
            {Array.from(new Set(visibleFacilities.map((facility) => facility.category))).map((category) => (
              <span key={category} className="flex shrink-0 items-center gap-1">
                <span aria-hidden="true">{FACILITY_SYMBOLS[category]}</span>
                {FACILITY_LABELS[category]}
              </span>
            ))}
          </div>

          <section ref={facilityListRef} aria-label="주변 시설 목록" className="-mx-4 scroll-mt-24 rounded-t-[28px] border-t border-line-light bg-surface px-4 pb-2 pt-3 shadow-[0_-8px_24px_rgba(52,53,54,0.08)]">
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

            {selectedFacility ? (
              <article
                aria-label={`${selectedFacility.name} 상세 정보`}
                className="mt-3 rounded-card-lg border border-brand/35 bg-brand-soft/35 p-4 shadow-sm"
              >
                <div className="flex items-start gap-3">
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-card bg-surface text-lg font-black text-brand shadow-sm" aria-hidden="true">
                    {FACILITY_SYMBOLS[selectedFacility.category]}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-black text-ink">{selectedFacility.name}</h3>
                      <span className="rounded-chip bg-brand px-2 py-1 text-[10px] font-extrabold text-surface">
                        {FACILITY_LABELS[selectedFacility.category]}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] font-semibold text-muted">선택한 지도 위치의 상세 정보예요.</p>
                  </div>
                </div>

                <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                  <div className="rounded-card bg-surface px-3 py-2.5">
                    <dt className="font-bold text-muted">주소</dt>
                    <dd className="mt-1 font-semibold leading-relaxed text-ink">
                      {selectedFacility.address || "주소 정보가 제공되지 않았어요."}
                    </dd>
                  </div>
                  <div className="rounded-card bg-surface px-3 py-2.5">
                    <dt className="font-bold text-muted">축제장에서</dt>
                    <dd className="mt-1 font-semibold text-ink">
                      {formatDistance(selectedFacility.distance_m)} · 도보 약 {estimateWalkingMinutes(selectedFacility.distance_m)}분
                    </dd>
                  </div>
                  {selectedFacilityExtras.map((item) => (
                    <div key={`${item.label}-${item.value}`} className="rounded-card bg-surface px-3 py-2.5">
                      <dt className="font-bold text-muted">{item.label}</dt>
                      <dd className="mt-1 font-semibold text-ink">{item.value}</dd>
                    </div>
                  ))}
                  {getFacilitySourceLabel(selectedFacility.source) ? (
                    <div className="rounded-card bg-surface px-3 py-2.5">
                      <dt className="font-bold text-muted">정보 출처</dt>
                      <dd className="mt-1 font-semibold text-ink">{getFacilitySourceLabel(selectedFacility.source)}</dd>
                    </div>
                  ) : null}
                </dl>
              </article>
            ) : null}

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
                  .sort((left, right) => {
                    if (left.facility_id === selectedFacilityId) return -1;
                    if (right.facility_id === selectedFacilityId) return 1;
                    return left.distance_m - right.distance_m;
                  })
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
                        {selectedFacilityId === facility.facility_id ? (
                          <span className="shrink-0 rounded-chip bg-brand px-2 py-1 text-[10px] font-extrabold text-surface">선택한 위치</span>
                        ) : facilityGroup === "safety" ? (
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

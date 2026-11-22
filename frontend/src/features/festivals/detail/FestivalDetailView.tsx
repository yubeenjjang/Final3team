"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import {
  ArrowLeft,
  Bus,
  CalendarDays,
  Compass,
  Heart,
  Hospital,
  ImageOff,
  MapPin,
  ParkingCircle,
  RotateCcw,
  ShieldCheck,
  Ticket,
  TrainFront,
  Utensils,
  Users,
} from "lucide-react";
import { KakaoMap } from "@/components/KakaoMap";
import {
  getAccessToken,
  getAuthSessionVersion,
  subscribeAuth,
} from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { dday, formatFestivalPeriod } from "../explore/dday";
import { getRegionLabel } from "../explore/regions";
import { LiveInfoSection } from "../live-info/LiveInfoSection";
import {
  deleteFavorite,
  getFestivalDetail,
  findFavorites,
  saveFavorite,
  type FestivalDetail,
} from "./api";
import { FestivalAiPrompt } from "./FestivalAiPrompt";

export interface FestivalDetailViewProps {
  festivalId: string;
}

const NEARBY_ITEMS = [
  { id: "restroom", label: "화장실", icon: Users },
  { id: "parking", label: "주차장", icon: ParkingCircle },
  { id: "food", label: "맛집", icon: Utensils },
  { id: "hospital", label: "병원", icon: Hospital },
  { id: "subway", label: "지하철", icon: TrainFront },
  { id: "bus", label: "버스", icon: Bus },
] as const;

export function FestivalDetailView({ festivalId }: FestivalDetailViewProps) {
  const router = useRouter();

  const [festival, setFestival] = useState<FestivalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const session = useSyncExternalStore(subscribeAuth, getAuthSessionVersion, () => 0);
  const signedIn = useSyncExternalStore(subscribeAuth, () => Boolean(getAccessToken()), () => false);
  const [favorite, setFavorite] = useState<{ session: number; festivalId: string; saved: boolean | null } | null>(null);
  const [favoriteBusy, setFavoriteBusy] = useState(false);
  const [favoriteError, setFavoriteError] = useState<string | null>(null);
  const lookupRequest = useRef<AbortController | null>(null);
  const currentFavorite = favorite?.session === session && favorite.festivalId === festivalId ? favorite : null;
  const favoriteLocked = signedIn && (!currentFavorite || favoriteBusy);
  const isFavorite = signedIn && currentFavorite?.saved === true;

  const [nearbyMessage, setNearbyMessage] = useState<string | null>(null);
  const [failedHeroSrc, setFailedHeroSrc] = useState<string | null>(null);

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
    if (!signedIn) return;
    const controller = new AbortController();
    lookupRequest.current = controller;

    function apply(saved: boolean | null) {
      if (!controller.signal.aborted && session === getAuthSessionVersion()) {
        setFavorite({ session, festivalId, saved });
      }
    }

    findFavorites([festivalId], controller.signal)
      .then((matches) => apply(matches.has(festivalId)))
      .catch(() => apply(null));

    return () => controller.abort();
  }, [festivalId, session, signedIn]);

  const handleToggleFavorite = useCallback(async () => {
    if (!getAccessToken()) {
      router.push(
        `/auth/login?next=${encodeURIComponent(`/festivals/${festivalId}`)}`,
      );
      return;
    }
    if (!currentFavorite || favoriteLocked || session !== getAuthSessionVersion()) return;

    lookupRequest.current?.abort();
    setFavoriteBusy(true);
    setFavoriteError(null);
    try {
      if (isFavorite) await deleteFavorite(festivalId);
      else await saveFavorite(festivalId);

      if (session === getAuthSessionVersion()) {
        setFavorite((current) =>
          current === currentFavorite ? { ...current, saved: !isFavorite } : current,
        );
      }
    } catch (error) {
      if (session === getAuthSessionVersion()) {
        setFavoriteError(
          error instanceof ApiError
            ? error.message
            : "찜 상태를 변경하지 못했어요",
        );
      }
    } finally {
      setFavoriteBusy(false);
    }
  }, [currentFavorite, favoriteLocked, festivalId, isFavorite, router, session]);

  if (loading) {
    return (
      <div className="space-y-4 px-4 py-4">
        <div className="h-56 animate-pulse rounded-card bg-surface" />
        <div className="h-8 w-2/3 animate-pulse rounded-card bg-surface" />
        <div className="h-24 animate-pulse rounded-card bg-surface" />
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
          className="mt-1 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
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
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
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
    <div className="space-y-5 px-4 py-3 pb-6">
      {/* 상단 내비게이션 줄 */}
      <div className="flex items-center justify-between">
        <Link
          href="/festivals"
          className="inline-flex items-center gap-1.5 text-sm font-bold text-ink hover:text-brand"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          <span>축제 상세</span>
        </Link>
      </div>

      {/* 대표 이미지 + D-day + 하트 */}
      <section className="space-y-2">
        <div className="relative h-56 w-full overflow-hidden rounded-card border border-line-light bg-surface-soft/50">
          {showHeroImage && heroImage ? (
            <>
              <Image
                src={heroImage}
                alt={festival.name}
                fill
                sizes="(max-width: 480px) 100vw, 448px"
                unoptimized
                onError={() => setFailedHeroSrc(heroImage)}
                className="object-contain p-1"
              />
              <span className="absolute bottom-2.5 right-2.5 rounded-chip bg-ink/70 px-2 py-0.5 text-[10px] font-medium text-surface backdrop-blur-sm">
                출처: 한국관광공사
              </span>
            </>
          ) : (
            <div className="flex h-full w-full flex-col items-center justify-center gap-1.5 text-muted">
              <ImageOff className="h-7 w-7" aria-hidden="true" />
              <span className="text-xs font-medium">이미지 준비 중</span>
            </div>
          )}

          {badge ? (
            <span className="absolute left-3 top-3 rounded-chip bg-brand px-2.5 py-1 text-xs font-bold text-surface shadow-sm">
              {badge}
            </span>
          ) : null}

          <button
            type="button"
            onClick={() => void handleToggleFavorite()}
            disabled={favoriteLocked}
            aria-label={isFavorite ? "찜 해제" : "찜하기"}
            aria-pressed={isFavorite}
            className="absolute right-3 top-3 flex h-9 w-9 items-center justify-center rounded-chip bg-surface/90 text-ink shadow-sm backdrop-blur-sm transition-transform hover:scale-105 disabled:opacity-60"
          >
            <Heart
              className={
                isFavorite
                  ? "h-5 w-5 fill-brand text-brand"
                  : "h-5 w-5 text-ink"
              }
              aria-hidden="true"
            />
          </button>
        </div>

        {favoriteError ? (
          <p role="alert" className="text-xs font-medium text-brand">
            {favoriteError}
          </p>
        ) : null}
      </section>

      {/* 제목 & 한 줄 소개 */}
      <section className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="h-5 w-1.5 rounded-chip bg-brand" aria-hidden="true" />
          <h1 className="text-xl font-extrabold tracking-tight text-ink">
            {festival.name}
          </h1>
        </div>
        {festival.overview ? (
          <p className="text-sm leading-relaxed text-muted">
            {festival.overview}
          </p>
        ) : null}
      </section>

      {/* AI 질문창 */}
      <FestivalAiPrompt festivalId={festival.festival_id} />

      {/* 정보 칩 2x2 */}
      <section aria-label="기본 정보" className="grid grid-cols-2 gap-2">
        <div className="flex items-center gap-2 rounded-card border border-line-light bg-surface px-3 py-2.5 text-xs">
          <CalendarDays className="h-4 w-4 shrink-0 text-ink" aria-hidden="true" />
          <span className="whitespace-normal font-medium leading-snug text-ink">
            {periodText}
          </span>
        </div>
        <div className="flex items-center gap-2 rounded-card border border-line-light bg-surface px-3 py-2.5 text-xs">
          <MapPin className="h-4 w-4 shrink-0 text-ink" aria-hidden="true" />
          <span className="truncate font-medium text-ink">
            {festival.venue_name ?? festival.address ?? "장소 미정"}
          </span>
        </div>
        <div className="flex items-center gap-2 rounded-card border border-line-light bg-surface px-3 py-2.5 text-xs">
          <Ticket className="h-4 w-4 shrink-0 text-ink" aria-hidden="true" />
          <span className="truncate font-medium text-ink">
            {festival.fee_text ?? "요금 정보 없음"}
          </span>
        </div>
        <div className="flex items-center gap-2 rounded-card border border-line-light bg-surface px-3 py-2.5 text-xs">
          <Compass className="h-4 w-4 shrink-0 text-ink" aria-hidden="true" />
          <span className="truncate font-medium text-ink">{regionLabel}</span>
        </div>
      </section>

      {/* 축제 정보 박스 */}
      {festival.address || festival.homepage_url ? (
        <section className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
            <h2 className="text-base font-extrabold text-ink">축제 정보</h2>
          </div>
          <div className="space-y-1.5 rounded-card bg-surface-soft/70 px-4 py-3 text-xs leading-relaxed text-ink">
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
                  className="font-medium text-accent underline"
                >
                  {festival.homepage_url}
                </a>
              </p>
            ) : null}
          </div>
        </section>
      ) : null}

      {/* 현장 정보 (혼잡 · 날씨 · 공지) */}
      <LiveInfoSection festivalId={festival.festival_id} />

      {/* 주변 정보 아이콘 + 작은 지도 */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
          <h2 className="text-base font-extrabold text-ink">주변 정보</h2>
        </div>

        <div className="grid grid-cols-6 gap-1.5">
          {NEARBY_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setNearbyMessage(`${item.label} 정보는 준비 중이에요`)}
                className="flex flex-col items-center justify-center gap-1 rounded-card border border-line-light bg-surface px-1 py-2.5 text-center transition-colors hover:bg-surface-soft"
              >
                <Icon className="h-4 w-4 text-brand" aria-hidden="true" />
                <span className="text-[11px] font-semibold text-ink">
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>

        {nearbyMessage ? (
          <p
            role="status"
            className="rounded-card bg-surface-soft px-3 py-2 text-center text-xs font-semibold text-ink"
          >
            {nearbyMessage}
          </p>
        ) : null}

        {hasCoordinates && festival.lat !== null && festival.lng !== null ? (
          <div className="space-y-2">
            <KakaoMap
              center={{ lat: festival.lat, lng: festival.lng }}
              markers={[
                {
                  lat: festival.lat,
                  lng: festival.lng,
                  title: festival.name,
                },
              ]}
              className="h-44 w-full"
            />
            {festival.venue_name || festival.address ? (
              <div className="flex items-center gap-2 rounded-card border border-line-light bg-surface px-3.5 py-2.5 text-xs text-ink">
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
          </div>
        ) : (
          <div className="flex h-28 items-center justify-center rounded-card border border-line-light bg-muted/10 text-xs font-medium text-muted">
            위치 정보가 없어요
          </div>
        )}
      </section>

      {/* AI 안심 귀가 배너 */}
      <section className="rounded-card bg-accent p-4 text-surface shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-card bg-surface/15">
              <ShieldCheck className="h-6 w-6 text-surface" aria-hidden="true" />
            </div>
            <div className="space-y-0.5">
              <h2 className="text-sm font-extrabold">AI 안심 귀가</h2>
              <p className="text-[11px] leading-snug text-surface/85">
                혼잡도와 동선을 고려한 안전한 귀갓길을 안내해요
              </p>
            </div>
          </div>

          <Link
            href={`/routes/return?festivalId=${encodeURIComponent(
              festival.festival_id,
            )}`}
            className="shrink-0 rounded-chip bg-surface px-3.5 py-2 text-xs font-extrabold text-brand shadow-sm transition-opacity hover:opacity-95"
          >
            귀가 경로 보기 →
          </Link>
        </div>
      </section>
    </div>
  );
}

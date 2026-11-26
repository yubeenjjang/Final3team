"use client";

import { useEffect, useState } from "react";
import { BusFront, CloudSun, Megaphone, TrainFront, Users } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import {
  getFestivalCrowd,
  getFestivalNotices,
  getFestivalTransit,
  getFestivalWeather,
  type CrowdResponse,
  type NoticeResponse,
  type TransitResponse,
  type WeatherResponse,
} from "./api";
import {
  formatDateTimeShort,
  getCrowdColorClass,
  getNoticeTypeLabel,
  getPrecipitationLabel,
} from "./liveInfoUtils";

interface AsyncCardState<T> {
  resolvedId: string | null;
  data: T | null;
  error: string | null;
}

export interface LiveInfoSectionProps {
  festivalId: string;
}

function formatAreaDistance(distanceM: number): string {
  if (!Number.isFinite(distanceM) || distanceM <= 0) {
    return "구역 내";
  }
  return `${Math.round(distanceM)}m`;
}

function formatArrivalTime(etaSeconds?: number | null, message?: string | null) {
  if (etaSeconds === 0) return "곧 도착";
  if (typeof etaSeconds === "number" && etaSeconds > 0) {
    return `${Math.max(1, Math.ceil(etaSeconds / 60))}분 후`;
  }
  return message || "도착 정보 확인 중";
}

export function LiveInfoSection({ festivalId }: LiveInfoSectionProps) {
  const [crowdState, setCrowdState] = useState<AsyncCardState<CrowdResponse>>({
    resolvedId: null,
    data: null,
    error: null,
  });
  const [weatherState, setWeatherState] =
    useState<AsyncCardState<WeatherResponse>>({
      resolvedId: null,
      data: null,
      error: null,
    });
  const [noticesState, setNoticesState] =
    useState<AsyncCardState<NoticeResponse>>({
      resolvedId: null,
      data: null,
      error: null,
    });
  const [transitState, setTransitState] =
    useState<AsyncCardState<TransitResponse>>({
      resolvedId: null,
      data: null,
      error: null,
    });

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    getFestivalCrowd(festivalId, controller.signal)
      .then((data) => {
        if (active) {
          setCrowdState({ resolvedId: festivalId, data, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!active || (error instanceof Error && error.name === "AbortError")) {
          return;
        }
        setCrowdState({
          resolvedId: festivalId,
          data: null,
          error:
            error instanceof ApiError
              ? error.message
              : "혼잡 정보를 불러오지 못했어요",
        });
      });

    getFestivalWeather(festivalId, controller.signal)
      .then((data) => {
        if (active) {
          setWeatherState({ resolvedId: festivalId, data, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!active || (error instanceof Error && error.name === "AbortError")) {
          return;
        }
        setWeatherState({
          resolvedId: festivalId,
          data: null,
          error:
            error instanceof ApiError
              ? error.message
              : "날씨 정보를 불러오지 못했어요",
        });
      });

    getFestivalNotices(festivalId, controller.signal)
      .then((data) => {
        if (active) {
          setNoticesState({ resolvedId: festivalId, data, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!active || (error instanceof Error && error.name === "AbortError")) {
          return;
        }
        setNoticesState({
          resolvedId: festivalId,
          data: null,
          error:
            error instanceof ApiError
              ? error.message
              : "공지 정보를 불러오지 못했어요",
        });
      });

    getFestivalTransit(festivalId, controller.signal)
      .then((data) => {
        if (active) {
          setTransitState({ resolvedId: festivalId, data, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!active || (error instanceof Error && error.name === "AbortError")) {
          return;
        }
        setTransitState({
          resolvedId: festivalId,
          data: null,
          error:
            error instanceof ApiError
              ? error.message
              : "실시간 교통 정보를 불러오지 못했어요",
        });
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [festivalId]);

  const crowdLoading = crowdState.resolvedId !== festivalId;
  const weatherLoading = weatherState.resolvedId !== festivalId;
  const noticesLoading = noticesState.resolvedId !== festivalId;
  const transitLoading = transitState.resolvedId !== festivalId;
  const nearbyAreas = crowdState.data?.nearby_areas ?? [];
  const fallbackAreas = crowdState.data?.areas ?? [];

  return (
    <section aria-label="현장 정보" className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
        <h2 className="text-base font-extrabold text-ink">현장 정보</h2>
      </div>

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {/* 주변 지역 혼잡 카드 (A10) */}
        <article
          data-testid="live-info-crowd"
          className="rounded-card border border-line-light bg-surface p-3.5 shadow-sm"
        >
          <div className="mb-2 flex items-center gap-1.5 text-xs font-bold text-ink">
            <Users className="h-4 w-4 text-brand" aria-hidden="true" />
            <span>주변 지역 혼잡</span>
          </div>

          {crowdLoading ? (
            <p className="text-xs text-muted">불러오는 중…</p>
          ) : crowdState.error ? (
            <p className="text-xs font-medium text-brand">{crowdState.error}</p>
          ) : crowdState.data?.status === "unsupported" ? (
            <p className="text-xs text-muted">이 지역은 아직 지원하지 않아요</p>
          ) : crowdState.data?.status === "unavailable" ? (
            <p className="text-xs font-medium text-brand">
              {crowdState.data.error?.message ?? "혼잡 정보를 불러올 수 없어요"}
            </p>
          ) : nearbyAreas.length > 0 ? (
            <div className="space-y-2">
              {crowdState.data?.status === "stale" ? (
                <p className="text-[11px] font-semibold text-ink">
                  정보가 오래됐어요
                </p>
              ) : null}
              <ul className="space-y-2">
                {nearbyAreas.map((area) => (
                  <li
                    key={area.area_code}
                    className="space-y-1 border-t border-line-light/70 pt-2 first:border-t-0 first:pt-0"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-1.5">
                      <span className="text-xs font-bold text-ink">
                        {area.area_name}
                        <span className="ml-1 text-[11px] font-medium text-muted">
                          ({formatAreaDistance(area.distance_m)})
                        </span>
                      </span>
                      {area.data ? (
                        <span
                          className={`rounded-chip px-2 py-0.5 text-[11px] font-bold ${getCrowdColorClass(
                            area.data.congest_color,
                          )}`}
                        >
                          {area.data.congest_level}
                        </span>
                      ) : (
                        <span className="rounded-chip bg-surface-muted px-2 py-0.5 text-[11px] font-semibold text-muted">
                          확인 불가
                        </span>
                      )}
                    </div>
                    {area.data ? (
                      <p className="text-[11px] text-muted">
                        추정 인구 {area.data.population_min.toLocaleString("ko-KR")}~
                        {area.data.population_max.toLocaleString("ko-KR")}명
                      </p>
                    ) : area.error?.message ? (
                      <p className="text-[11px] text-muted">{area.error.message}</p>
                    ) : null}
                    {area.status === "stale" && crowdState.data?.status !== "stale" ? (
                      <p className="text-[11px] font-semibold text-ink">
                        정보가 오래됐어요
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : fallbackAreas.length > 0 ? (
            <div className="space-y-2">
              {crowdState.data?.status === "stale" ? (
                <p className="text-[11px] font-semibold text-ink">
                  정보가 오래됐어요
                </p>
              ) : null}
              <ul className="space-y-2">
                {fallbackAreas.map((area) => (
                  <li
                    key={area.area_code}
                    className="space-y-1 border-t border-line-light/70 pt-2 first:border-t-0 first:pt-0"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-1.5">
                      <span className="text-xs font-bold text-ink">
                        {area.area_name}
                      </span>
                      <span
                        className={`rounded-chip px-2 py-0.5 text-[11px] font-bold ${getCrowdColorClass(
                          area.congest_color,
                        )}`}
                      >
                        {area.congest_level}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted">
                      추정 인구 {area.population_min.toLocaleString("ko-KR")}~
                      {area.population_max.toLocaleString("ko-KR")}명
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-xs text-muted">혼잡 정보가 없어요</p>
          )}
        </article>

        {/* 날씨 카드 (A09) */}
        <article
          data-testid="live-info-weather"
          className="rounded-card border border-line-light bg-surface p-3.5 shadow-sm"
        >
          <div className="mb-2 flex items-center gap-1.5 text-xs font-bold text-ink">
            <CloudSun className="h-4 w-4 text-brand" aria-hidden="true" />
            <span>현장 날씨</span>
          </div>

          {weatherLoading ? (
            <p className="text-xs text-muted">불러오는 중…</p>
          ) : weatherState.error ? (
            <p className="text-xs font-medium text-brand">
              {weatherState.error}
            </p>
          ) : weatherState.data?.status === "unsupported" ? (
            <p className="text-xs text-muted">이 지역은 아직 지원하지 않아요</p>
          ) : weatherState.data?.status === "unavailable" ||
            !weatherState.data?.data ? (
            <p className="text-xs font-medium text-brand">
              {weatherState.data?.error?.message ??
                "날씨 정보를 불러올 수 없어요"}
            </p>
          ) : (
            <div className="space-y-1">
              {weatherState.data.status === "stale" ? (
                <p className="text-[11px] font-semibold text-ink">
                  정보가 오래됐어요
                </p>
              ) : null}
              <div className="flex items-baseline gap-2">
                <span className="font-display text-lg font-extrabold text-ink">
                  {weatherState.data.data.temperature_c}°C
                </span>
                <span className="text-xs font-semibold text-muted">
                  {getPrecipitationLabel(
                    weatherState.data.data.precipitation_type,
                  )}
                  {weatherState.data.data.precipitation_mm > 0
                    ? ` (${weatherState.data.data.precipitation_mm}mm)`
                    : ""}
                </span>
              </div>
              {weatherState.data.observed_at ? (
                <p className="text-[11px] text-muted">
                  관측 {formatDateTimeShort(weatherState.data.observed_at)}
                </p>
              ) : null}
            </div>
          )}
        </article>
      </div>

      <article
        data-testid="live-info-transit"
        className="rounded-card border border-line-light bg-surface p-3.5 shadow-sm"
      >
        <div className="mb-2 flex items-center gap-1.5 text-xs font-bold text-ink">
          <BusFront className="h-4 w-4 text-brand" aria-hidden="true" />
          <span>실시간 버스 · 지하철 도착</span>
        </div>

        {transitLoading ? (
          <p className="text-xs text-muted">불러오는 중…</p>
        ) : transitState.error ? (
          <p className="text-xs font-medium text-brand">{transitState.error}</p>
        ) : transitState.data?.status === "unsupported" ? (
          <p className="text-xs text-muted">이 지역은 아직 지원하지 않아요</p>
        ) : transitState.data?.status === "unavailable" ? (
          <p className="text-xs font-medium text-brand">
            {transitState.data.error?.message ?? "도착 정보를 불러올 수 없어요"}
          </p>
        ) : !transitState.data?.stations?.length ? (
          <p className="text-xs text-muted">주변 도착 정보가 없어요</p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {transitState.data.stations.map((station) => {
              const StationIcon = station.type === "subway" ? TrainFront : BusFront;
              return (
                <li
                  key={`${station.type}-${station.station_id}`}
                  className="rounded-xl bg-surface-soft/55 px-3 py-2.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex min-w-0 items-center gap-1.5 text-xs font-bold text-ink">
                      <StationIcon className="h-4 w-4 shrink-0 text-brand" aria-hidden="true" />
                      <span className="truncate">{station.name}</span>
                    </span>
                    <span className="shrink-0 text-[10px] text-muted">
                      {Math.round(station.distance_m)}m
                    </span>
                  </div>
                  {station.arrivals.length ? (
                    <ul className="mt-2 space-y-1.5">
                      {station.arrivals.slice(0, 2).map((arrival, index) => (
                        <li
                          key={`${arrival.line}-${arrival.direction ?? ""}-${index}`}
                          className="flex items-center justify-between gap-2 text-[11px]"
                        >
                          <span className="min-w-0 truncate font-semibold text-ink">
                            {arrival.line}
                            {arrival.direction ? ` · ${arrival.direction}` : ""}
                          </span>
                          <span className="shrink-0 font-extrabold text-brand">
                            {formatArrivalTime(arrival.eta_s, arrival.message)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-[11px] text-muted">현재 도착 예정 정보가 없어요</p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </article>

      {/* 공지 카드 (A07) */}
      <article
        data-testid="live-info-notices"
        className="rounded-card border border-line-light bg-surface p-3.5 shadow-sm"
      >
        <div className="mb-2 flex items-center gap-1.5 text-xs font-bold text-ink">
          <Megaphone className="h-4 w-4 text-brand" aria-hidden="true" />
          <span>운영 · 교통 공지</span>
        </div>

        {noticesLoading ? (
          <p className="text-xs text-muted">불러오는 중…</p>
        ) : noticesState.error ? (
          <p className="text-xs font-medium text-brand">{noticesState.error}</p>
        ) : noticesState.data?.status === "unsupported" ? (
          <p className="text-xs text-muted">이 지역은 아직 지원하지 않아요</p>
        ) : noticesState.data?.status === "unavailable" ? (
          <p className="text-xs font-medium text-brand">
            {noticesState.data.error?.message ?? "공지 정보를 불러올 수 없어요"}
          </p>
        ) : !noticesState.data?.items || noticesState.data.items.length === 0 ? (
          <p className="text-xs text-muted">
            확인할 수 있는 공지 자료가 없어요
          </p>
        ) : (
          <div className="space-y-2.5">
            {noticesState.data.status === "stale" ? (
              <p className="text-[11px] font-semibold text-ink">
                정보가 오래됐어요
              </p>
            ) : null}
            <ul className="space-y-2">
              {noticesState.data.items.map((notice) => (
                <li
                  key={notice.notice_id}
                  className="rounded-xl bg-surface-soft/55 px-3 py-2.5"
                >
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="rounded-chip bg-brand/15 px-2 py-0.5 text-[10px] font-bold text-brand">
                      {getNoticeTypeLabel(notice.type)}
                    </span>
                    <span className="text-xs font-bold text-ink">
                      {notice.title}
                    </span>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-muted">
                    {notice.content}
                  </p>
                  <p className="mt-1 text-[11px] text-muted">
                    적용 기간: {formatDateTimeShort(notice.effective_from)} ~{" "}
                    {formatDateTimeShort(notice.effective_to)}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </article>
    </section>
  );
}

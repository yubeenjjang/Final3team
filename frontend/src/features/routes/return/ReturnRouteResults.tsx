import { useState } from "react";
import { BusFront, CarFront, ChevronRight, Clock, Crown, Footprints, MapPinOff, Route, Sparkles, TrainFront } from "lucide-react";
import { KakaoMap, type KakaoMapMarker, type KakaoMapPoint } from "@/components/KakaoMap";
import type { ReadyRoute, RouteCandidate, RoutePoint } from "./api";
import { RoutePreferences } from "./RoutePreferences";

const MODE_DETAILS = {
  walk: { label: "도보", Icon: Footprints },
  bus: { label: "버스", Icon: BusFront },
  subway: { label: "지하철", Icon: TrainFront },
  train: { label: "기차", Icon: TrainFront },
  car: { label: "자동차", Icon: CarFront },
  taxi: { label: "택시", Icon: CarFront },
  transit: { label: "대중교통", Icon: BusFront },
};

function modeDetails(mode: string) {
  return MODE_DETAILS[mode as keyof typeof MODE_DETAILS] ?? { label: "이동", Icon: Route };
}

function mapPoint(lat?: number | null, lng?: number | null): KakaoMapPoint | undefined {
  return lat != null && lng != null ? { lat, lng } : undefined;
}

function endpointMarker(endpoint: ReadyRoute["origin"], prefix: string, pathPoint?: RoutePoint): KakaoMapMarker | undefined {
  const point = mapPoint(endpoint.lat, endpoint.lng) ?? mapPoint(pathPoint?.[0], pathPoint?.[1]);
  const name = endpoint.name || endpoint.label;
  return point ? { ...point, title: name ? `${prefix} · ${name}` : prefix } : undefined;
}

function RouteMap({ route, candidate }: { route: ReadyRoute; candidate?: RouteCandidate }) {
  const paths = (candidate?.legs ?? []).flatMap((leg) => (leg.path?.length ? [leg.path] : []));
  const origin = endpointMarker(route.origin, "출발", paths[0]?.[0]);
  const destination = endpointMarker(route.destination, "도착", paths.at(-1)?.at(-1));
  const center = origin ?? destination;

  return (
    <div className="relative" role="region" aria-label="귀가 경로 지도">
      {center ? (
        <KakaoMap
          center={center}
          markers={[origin, destination].filter((marker) => marker !== undefined)}
          polylines={paths}
          className="h-[224px] w-full rounded-none border-x-0"
        />
      ) : (
        <div className="flex h-[224px] flex-col items-center justify-center gap-2 bg-surface-soft/50 text-sm font-medium text-muted">
          <MapPinOff size={22} aria-hidden="true" /> 지도에 표시할 위치가 없어요.
        </div>
      )}
    </div>
  );
}

export function RouteNotices({ notices }: { notices?: string[] }) {
  if (!notices?.length) return null;

  return (
    <ul aria-label="경로 안내" className="space-y-1 text-xs leading-relaxed text-muted">
      {notices.map((notice, index) => <li key={`${notice}-${index}`}>{notice}</li>)}
    </ul>
  );
}

export function ReturnRouteResults({ route, onEdit, fromLink }: {
  route: ReadyRoute;
  onEdit: () => void;
  fromLink: boolean;
}) {
  const candidates = route.route_candidates.slice(0, 3);
  const [selectedId, setSelectedId] = useState(candidates[0]?.candidate_id);
  const selected = candidates.find((candidate) => candidate.candidate_id === selectedId) ?? candidates[0];
  const origin = route.origin.name || route.origin.label;
  const destination = route.destination.name || route.destination.label;
  const isTmapRoute = route.provider?.toLowerCase() === "tmap";

  return (
    <>
      <div className="px-4 pb-3">
        <RoutePreferences value={route.route_preference} />
      </div>
      <div className="relative">
        <RouteMap route={route} candidate={selected} />
        {origin || destination ? (
          <div className="pointer-events-none absolute inset-x-3 top-3 flex items-start justify-between gap-2.5">
            {origin ? (
              <span className="inline-flex max-w-[48%] items-center gap-1.5 rounded-chip border border-brand/30 bg-surface/95 py-1 pl-1.5 pr-2.5 text-xs font-bold text-ink shadow-md backdrop-blur-sm">
                <span className="shrink-0 rounded-chip bg-brand px-2 py-0.5 text-[10px] font-extrabold text-surface">출발</span>
                <span className="truncate">{origin}</span>
              </span>
            ) : null}
            {destination ? (
              <span className="ml-auto inline-flex max-w-[48%] items-center gap-1.5 rounded-chip border border-brand/30 bg-surface/95 py-1 pl-1.5 pr-2.5 text-xs font-bold text-ink shadow-md backdrop-blur-sm">
                <span className="shrink-0 rounded-chip bg-banner-dark px-2 py-0.5 text-[10px] font-extrabold text-surface">도착</span>
                <span className="truncate">{destination}</span>
              </span>
            ) : null}
          </div>
        ) : null}
      </div>

      {isTmapRoute ? (
        <div className="bg-surface-muted/80 px-4 py-1.5 text-right text-[11px] font-semibold text-muted">
          경로 정보: TMAP
        </div>
      ) : null}

      <section
        aria-labelledby="return-results-heading"
        className={`relative ${isTmapRoute ? "mt-0" : "-mt-3"} space-y-3 rounded-t-[24px] border-t border-line-light bg-surface px-4 pb-4 pt-2.5 shadow-[0_-6px_20px_rgba(10,16,31,0.06)]`}
      >
        <div className="mx-auto h-1 w-9 rounded-chip bg-line-light" aria-hidden="true" />
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <h2 id="return-results-heading" className="flex items-center gap-1.5 text-base font-black tracking-tight text-ink">
            <Sparkles size={17} className="fill-brand text-brand" aria-hidden="true" />
            <span className="rounded-chip bg-brand px-2 py-0.5 text-[11px] font-extrabold text-surface">AI</span>
            <span>추천 귀가 경로</span>
          </h2>
          <span className="inline-flex items-center gap-1 text-xs font-medium text-muted">
            <Clock size={13} aria-hidden="true" /> 지금 출발 · {modeDetails(route.travel_mode).label}
          </span>
        </div>

        {candidates.length ? (
          <ol className="space-y-2.5">
            {candidates.map((candidate, index) => {
              const active = candidate === selected;

              return (
                <li key={candidate.candidate_id}>
                  <button
                    type="button"
                    aria-pressed={active}
                    onClick={() => setSelectedId(candidate.candidate_id)}
                    className={`w-full space-y-2.5 rounded-card border px-3.5 py-3 text-left shadow-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${
                      active
                        ? "border-brand bg-surface-soft/55"
                        : "border-line-light bg-surface hover:border-brand/40"
                    }`}
                  >
                    <span className="flex items-start gap-2.5">
                      <span
                        aria-hidden="true"
                        className={`rounded-lg px-2 py-1 text-xs font-extrabold ${
                          active ? "bg-brand text-surface" : "bg-surface-soft text-brand"
                        }`}
                      >
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
                          <span className="text-sm font-extrabold text-ink">{candidate.summary}</span>
                          {index === 0 && route.completed_valid_route ? (
                            <span className="inline-flex items-center gap-1 rounded-chip bg-brand px-2 py-0.5 text-[10px] font-extrabold text-surface">
                              <Crown size={11} aria-hidden="true" /> 추천
                            </span>
                          ) : null}
                        </span>
                        <span className="mt-1 flex flex-wrap gap-x-2.5 gap-y-1 text-xs text-muted">
                          <span className="inline-flex items-center gap-1">
                            <Footprints size={13} aria-hidden="true" />
                            {candidate.walk_m != null
                              ? `도보 ${candidate.walk_m.toLocaleString("ko-KR")}m`
                              : "도보 정보 없음"}
                          </span>
                          <span className="inline-flex items-center gap-1">
                            <BusFront size={13} aria-hidden="true" />
                            {candidate.transfers != null ? `환승 ${candidate.transfers}회` : "환승 정보 없음"}
                          </span>
                        </span>
                      </span>
                      <span className="flex shrink-0 items-center gap-0.5 whitespace-nowrap font-display text-2xl font-black tracking-tight text-brand">
                        {candidate.duration_min != null ? `${candidate.duration_min}분` : "시간 정보 없음"}
                        <ChevronRight size={17} className="text-brand/75" aria-hidden="true" />
                      </span>
                    </span>
                    <span className="flex flex-wrap items-center gap-x-1 gap-y-1.5 pl-1">
                      {candidate.legs.map((leg, legIndex) => {
                        const { label, Icon } = modeDetails(leg.mode);
                        return (
                          <span key={legIndex} className="inline-flex items-center gap-1">
                            {legIndex > 0 ? <span className="text-xs text-muted" aria-hidden="true">···</span> : null}
                            <span
                              className={`inline-flex items-center gap-1 rounded-chip px-2.5 py-0.5 text-[11px] font-bold ${
                                leg.mode === "walk"
                                  ? "bg-surface-muted text-muted"
                                  : "bg-surface-soft text-brand"
                              }`}
                            >
                              <Icon size={12} aria-hidden="true" /> {label}
                              {leg.line
                                ? ` ${leg.line}`
                                : leg.duration_min != null
                                  ? ` ${leg.duration_min}분`
                                  : " 시간 정보 없음"}
                            </span>
                          </span>
                        );
                      })}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        ) : (
          <p role="status" className="rounded-card border border-line-light bg-surface p-3.5 text-sm text-muted">표시할 경로가 없어요.</p>
        )}

        <RouteNotices notices={route.notices} />

        <button
          type="button"
          onClick={onEdit}
          className="rounded-chip border border-brand/35 bg-surface px-3.5 py-1.5 text-xs font-bold text-brand transition-colors hover:bg-surface-soft"
        >
          {fromLink ? "다른 경로 찾기" : "입력 수정"}
        </button>
      </section>
    </>
  );
}

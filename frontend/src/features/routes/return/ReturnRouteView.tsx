"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Building2, BusFront, FerrisWheel, Heart, House, LoaderCircle, MapPinned, MoonStar, Sparkles, Tent } from "lucide-react";
import { KakaoMap } from "@/components/KakaoMap";
import { ApiError } from "@/lib/api/client";
import { getFestivalDetail } from "@/features/festivals/detail/api";
import { MOCK_SCENARIOS, submitReturnRoute, type MockScenario, type ReadyRoute, type RouteAccess } from "./api";
import type { SelectedFestival } from "./FestivalPicker";
import { pollRoute } from "./pollRoute";
import { RETURN_FORM_ID, ReturnRouteForm, type RouteInputs } from "./ReturnRouteForm";
import { ReturnRouteResults, RouteNotices } from "./ReturnRouteResults";

type ViewState =
  | { kind: "input" }
  | { kind: "pending"; fromLink: boolean }
  | { kind: "ready"; route: ReadyRoute; fromLink: boolean }
  | { kind: "failed"; message: string; notices?: string[]; retry: boolean };

function outcome(result: Awaited<ReturnType<typeof pollRoute>>, fromLink: boolean): ViewState {
  if (result.type === "unconfirmed") {
    return { kind: "failed", message: "지금은 확인할 수 없어요", notices: result.notices, retry: true };
  }

  const { response } = result;
  if (response.route_status === "ready") return { kind: "ready", route: response, fromLink };

  const message = response.route_status === "timed_out" ? "경로를 찾는 시간이 초과됐어요." : "경로 정보를 가져오지 못했어요.";
  return {
    kind: "failed",
    message: ("error" in response && response.error?.message) || message,
    notices: response.notices,
    retry: true,
  };
}

function requestError(error: unknown): ViewState {
  if (error instanceof ApiError) {
    const overloaded = error.status === 503 && error.code === "ROUTE_OVERLOADED";
    return {
      kind: "failed",
      message: overloaded ? "요청이 많아요. 잠시 뒤 다시 시도해 주세요" : error.message,
      retry: overloaded || error.retryable,
    };
  }
  return { kind: "failed", message: "경로를 불러오지 못했어요.", retry: true };
}

function createRouteRequestId() {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();

  // randomUUID is restricted to secure contexts. Keep UUID v4 on HTTP as well.
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join("-");
}

function ReturnRouteHero({ ready }: { ready: boolean }) {
  return (
    <div className="relative isolate overflow-hidden px-4 pb-3 pt-4">
      <div aria-hidden="true" className="pointer-events-none absolute -right-2 bottom-0 -z-10 h-full w-[39%] bg-gradient-to-l from-accent/15 via-surface-soft/80 to-transparent">
        {ready ? (
          <>
            <FerrisWheel className="absolute right-5 top-2 size-11 text-accent/75" />
            <Tent className="absolute bottom-1 right-14 size-10 fill-brand/15 text-brand" />
            <Sparkles className="absolute right-28 top-3 size-5 text-brand/75" />
          </>
        ) : (
          <>
            <MoonStar className="absolute right-5 top-2 size-5 text-accent/75" />
            <Building2 className="absolute bottom-1 right-14 size-11 fill-accent/15 text-accent/60" />
            <BusFront className="absolute bottom-1 right-6 size-9 fill-bg text-accent" />
          </>
        )}
      </div>
      <h1 className="flex items-center gap-2 text-[26px] font-black leading-tight tracking-tight">
        {ready ? <House size={24} className="shrink-0 text-brand" aria-hidden="true" /> : null}
        <span>집으로 <span className="text-brand">가는 길</span></span>
        {ready ? null : <Heart size={20} className="shrink-0 fill-current text-brand" aria-hidden="true" />}
      </h1>
      <p className="mt-1 text-xs font-medium text-muted">축제의 마지막 귀갓길까지 함께해요.</p>
    </div>
  );
}

function FestivalMapPreview({ festival }: { festival: SelectedFestival | null }) {
  if (festival?.lat != null && festival.lng != null) {
    const center = { lat: festival.lat, lng: festival.lng };
    return (
      <KakaoMap
        center={center}
        markers={[{ ...center, title: festival.venue_name || festival.name }]}
        className="h-28 w-full"
      />
    );
  }

  return (
    <div className="flex h-28 flex-col items-center justify-center gap-2 rounded-card border border-line-light bg-gradient-to-br from-accent/10 via-bg to-surface-soft px-4 text-center text-xs font-medium text-muted shadow-sm">
      <MapPinned size={25} className="text-accent" aria-hidden="true" />
      {festival ? "지도에 표시할 축제 위치가 없어요." : "축제를 선택하면 지도에서 위치를 볼 수 있어요."}
    </div>
  );
}

export function ReturnRouteView({ festivalId, directRoute }: { festivalId?: string; directRoute?: RouteAccess }) {
  const [festival, setFestival] = useState<SelectedFestival | null>(null);
  const [festivalLoading, setFestivalLoading] = useState(Boolean(festivalId));
  const [festivalError, setFestivalError] = useState<string | null>(null);
  const [inputs, setInputs] = useState<RouteInputs>({ originType: "festival", originText: "", destination: "", preference: "fastest" });
  const [scenario, setScenario] = useState<MockScenario>("");
  const [state, setState] = useState<ViewState>(directRoute ? { kind: "pending", fromLink: true } : { kind: "input" });
  const activeRequest = useRef<AbortController | null>(null);
  const festivalRequest = useRef<AbortController | null>(null);

  const showMockTools = process.env.NEXT_PUBLIC_SHOW_MOCK_TOOLS === "1";
  const pending = state.kind === "pending";
  const routeId = directRoute?.id;
  const routeToken = directRoute?.token;

  useEffect(() => {
    if (!festivalId) return;

    const controller = new AbortController();
    festivalRequest.current = controller;
    const { signal } = controller;

    getFestivalDetail(festivalId, signal)
      .then((selected) => { if (!signal.aborted) setFestival(selected); })
      .catch((error: unknown) => {
        if (!signal.aborted) {
          setFestivalError(error instanceof ApiError ? error.message : "선택한 축제를 불러오지 못했어요.");
        }
      })
      .finally(() => { if (!signal.aborted) setFestivalLoading(false); });

    return () => controller.abort();
  }, [festivalId]);

  useEffect(() => {
    if (routeId && routeToken) {
      const controller = new AbortController();
      activeRequest.current = controller;
      const { signal } = controller;

      pollRoute({ id: routeId, token: routeToken }, signal, 0)
        .then((result) => { if (!signal.aborted) setState(outcome(result, true)); })
        .catch((error: unknown) => { if (!signal.aborted) setState(requestError(error)); });
    }

    return () => activeRequest.current?.abort();
  }, [routeId, routeToken]);

  async function findRoute(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending || festivalLoading) return;

    const destination = inputs.destination.trim();
    const origin = inputs.originText.trim();
    const originIsPlace = inputs.originType === "place";
    if (!festival || !destination || (originIsPlace && !origin)) {
      const message = !festival ? "축제를 검색해 선택해 주세요." : "출발지와 도착지를 확인해 주세요.";
      setState({ kind: "failed", message, retry: false });
      return;
    }

    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    const { signal } = controller;
    setState({ kind: "pending", fromLink: false });

    try {
      const submitted = await submitReturnRoute({
        request_id: createRouteRequestId(),
        festival_id: festival.festival_id,
        origin: originIsPlace ? { type: "place", query: origin } : { type: "festival" },
        destination: { type: "place", query: destination },
        route_preference: inputs.preference,
        travel_mode: "transit",
        departure: "now",
      }, showMockTools ? scenario : "", signal);

      if (signal.aborted) return;
      if (submitted.route_status === "ready") {
        setState({ kind: "ready", route: submitted, fromLink: false });
        return;
      }

      const result = await pollRoute({ id: submitted.route_request_id, token: submitted.route_access_token }, signal, submitted.retry_after_s);
      if (!signal.aborted) setState(outcome(result, false));
    } catch (error) {
      if (!signal.aborted) setState(requestError(error));
    }
  }

  return (
    <div className="pb-4">
      <ReturnRouteHero ready={state.kind === "ready"} />
      {state.kind === "ready" ? (
        <ReturnRouteResults key={state.route.route_request_id} route={state.route} fromLink={state.fromLink} onEdit={() => setState({ kind: "input" })} />
      ) : (
        <div className="space-y-3 px-4">
          {!(pending && state.fromLink) ? (
            <ReturnRouteForm
              inputs={inputs}
              onInputChange={(patch) => setInputs((previous) => ({ ...previous, ...patch }))}
              festival={festival}
              festivalLoading={festivalLoading}
              festivalError={festivalError}
              onFestivalChange={(selection) => {
                festivalRequest.current?.abort();
                setFestival(selection);
                setFestivalLoading(false);
                setFestivalError(null);
              }}
              pending={pending}
              onSubmit={findRoute}
            />
          ) : null}
          {pending ? (
            <p role="status" className="flex items-center gap-2 rounded-card border border-accent/25 bg-accent/5 px-4 py-3 text-sm font-medium">
              <LoaderCircle size={19} className="shrink-0 animate-spin text-accent motion-reduce:animate-none" aria-hidden="true" />
              경로를 찾고 있어요. 아직 확정된 경로가 아니에요
            </p>
          ) : null}
          {state.kind === "failed" ? (
            <div className="space-y-2 rounded-card border border-brand/35 bg-surface-soft px-4 py-3">
              <p role="alert" className="text-sm font-bold">{state.message}</p>
              <RouteNotices notices={state.notices} />
              {state.retry ? (
                <button form={RETURN_FORM_ID} type="submit" disabled={festivalLoading} className="rounded-chip bg-brand px-3 py-1.5 text-xs font-bold text-surface disabled:opacity-60">
                  다시 시도
                </button>
              ) : null}
            </div>
          ) : null}
          {!(pending && state.fromLink) ? <FestivalMapPreview festival={festival} /> : null}
        </div>
      )}

      {showMockTools ? (
        <label className="mx-4 mt-3 flex items-center justify-between gap-2 rounded-card border border-line-light bg-surface px-3 py-2 text-xs font-semibold text-muted">
          시나리오
          <select
            value={scenario}
            disabled={pending}
            onChange={(event) => setScenario(MOCK_SCENARIOS.find(({ value }) => value === event.target.value)?.value ?? "")}
            className="rounded-lg border border-line-light bg-bg px-2 py-1 text-ink focus-visible:outline-accent"
          >
            {MOCK_SCENARIOS.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
      ) : null}
    </div>
  );
}

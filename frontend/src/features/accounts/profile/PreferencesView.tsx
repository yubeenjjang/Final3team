"use client";

import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { Camera, Check, Heart, PawPrint, RotateCcw, Sparkles, UsersRound, UserRound } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { BrandLogo } from "@/components/BrandLogo";
import { handleAuthError, RequireAuth } from "@/components/RequireAuth";
import { ApiError } from "@/lib/api/client";
import {
  getFestivalPreferences,
  saveFestivalPreferences,
  SCENARIO_OPTIONS,
  type OnboardingStatus,
  type Scenario,
} from "./api";

export function PreferencesSection({
  embedded = false,
  onSaved,
}: {
  embedded?: boolean;
  onSaved?: (status: OnboardingStatus) => void;
}) {
  const [selected, setSelected] = useState<Scenario[]>([]);
  const [status, setStatus] = useState<OnboardingStatus>("pending");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const carouselRef = useRef<HTMLUListElement>(null);
  const dragStartX = useRef(0);
  const dragStartScrollLeft = useRef(0);
  const dragged = useRef(false);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await getFestivalPreferences(controller.signal);
        if (controller.signal.aborted) return;
        setSelected(Array.isArray(res.scenarios) ? res.scenarios : []);
        setStatus(
          res.onboarding_status === "completed" ||
            res.onboarding_status === "skipped"
            ? res.onboarding_status
            : "pending",
        );
      } catch (cause) {
        if (controller.signal.aborted) return;
        if (handleAuthError(cause)) return;
        setError(
          cause instanceof ApiError
            ? cause.message
            : "취향 정보를 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [reloadTick]);

  function toggleScenario(value: Scenario) {
    setNotice(null);
    setSelected((prev) => {
      if (prev.includes(value)) return prev.filter((item) => item !== value);
      if (prev.length >= 5) return prev;
      return [...prev, value];
    });
  }

  function startDrag(event: ReactPointerEvent<HTMLUListElement>) {
    if (event.pointerType !== "mouse" || event.button !== 0) return;
    const carousel = carouselRef.current;
    if (!carousel) return;
    dragStartX.current = event.clientX;
    dragStartScrollLeft.current = carousel.scrollLeft;
    dragged.current = false;
    setDragging(true);
  }

  function moveDrag(event: ReactPointerEvent<HTMLUListElement>) {
    if (!dragging || event.pointerType !== "mouse") return;
    const carousel = carouselRef.current;
    if (!carousel) return;
    const distance = event.clientX - dragStartX.current;
    if (Math.abs(distance) > 4 && !dragged.current) {
      dragged.current = true;
      event.currentTarget.setPointerCapture?.(event.pointerId);
    }
    if (!dragged.current) return;
    carousel.scrollLeft = dragStartScrollLeft.current - distance;
    event.preventDefault();
  }

  function finishDrag(event: ReactPointerEvent<HTMLUListElement>) {
    if (!dragging) return;
    setDragging(false);
    if (dragged.current) {
      event.currentTarget.releasePointerCapture?.(event.pointerId);
    }
  }

  async function submitPreferences(skip: boolean) {
    if (saving) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await saveFestivalPreferences({
        scenarios: skip ? [] : selected,
        skip,
      });
      setSelected(updated.scenarios);
      setStatus(updated.onboarding_status);
      setNotice(
        skip
          ? "취향 선택을 건너뛰었어요."
          : "축제 취향을 저장했어요!",
      );
      onSaved?.(updated.onboarding_status);
    } catch (cause) {
      if (handleAuthError(cause)) return;
      setError(
        cause instanceof ApiError
          ? cause.message
          : "취향을 저장하지 못했어요.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (!embedded) {
    const scenarioIcons = {
      family_relaxed: UsersRound,
      friends_activity: Sparkles,
      couple_photo: Camera,
      pet: PawPrint,
      solo: UserRound,
    } as const;

    return (
      <section className="min-h-dvh bg-screen-dark px-0 pb-10 pt-5 text-surface md:pt-7">
        <div className="px-6">
          <BrandLogo priority className="h-9 w-auto brightness-0 invert" />
          <h1 className="mt-8 text-center text-[32px] font-black leading-tight tracking-tight md:mt-10">
            어떤 <span className="text-brand">축제</span>를 좋아하시나요?
          </h1>
          <p className="mt-4 text-center text-base text-surface/80">마음에 드는 축제 스타일을 선택해 주세요.</p>
          <p className="mt-5 rounded-chip border-2 border-brand px-5 py-3 text-center text-sm font-semibold text-surface/90">
            ♡ 하트를 눌러 선택하면, 나만의 축제를 추천해드려요!
          </p>
        </div>

        {notice ? <p role="status" className="mx-6 mt-4 rounded-card bg-brand/15 px-4 py-3 text-sm">{notice}</p> : null}
        {error ? <p role="alert" className="mx-6 mt-4 text-sm font-semibold text-brand">{error}</p> : null}

        {loading ? (
          <div role="status" className="mx-6 mt-8 h-[430px] animate-pulse rounded-panel bg-surface/10" />
        ) : (
          <ul
            ref={carouselRef}
            className={`no-scrollbar mt-8 flex touch-pan-x gap-4 overflow-x-auto px-[42px] pb-4 select-none ${dragging ? "cursor-grabbing snap-none" : "cursor-grab snap-x snap-mandatory"}`}
            onPointerDown={startDrag}
            onPointerMove={moveDrag}
            onPointerUp={finishDrag}
            onPointerCancel={finishDrag}
            onDragStart={(event) => event.preventDefault()}
            onClickCapture={(event) => {
              if (!dragged.current) return;
              event.preventDefault();
              event.stopPropagation();
              dragged.current = false;
            }}
          >
            {SCENARIO_OPTIONS.map((option) => {
              const active = selected.includes(option.value);
              const Icon = scenarioIcons[option.value];
              return (
                <li key={option.value} className="w-[300px] shrink-0 snap-center">
                  <button
                    type="button"
                    aria-pressed={active}
                    aria-label={`${option.tag}: ${option.title}`}
                    onClick={() => toggleScenario(option.value)}
                    className={`relative flex h-[430px] w-full flex-col overflow-hidden rounded-[28px] border-[3px] text-left shadow-xl transition-transform ${active ? "scale-[1.01] border-brand" : "border-surface"}`}
                  >
                    <Image
                      src={option.imageSrc}
                      alt={`${option.tag} 취향 이미지`}
                      fill
                      sizes="300px"
                      priority={option.value === "family_relaxed"}
                      draggable={false}
                      className="object-cover object-center"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-screen-dark via-screen-dark/10 to-screen-dark/5" aria-hidden="true" />
                    <span className="absolute left-5 top-5 z-10 inline-flex w-fit items-center gap-2 rounded-chip bg-brand px-4 py-2 text-sm font-extrabold text-surface">
                      <Icon className="h-5 w-5" aria-hidden="true" /> {option.tag}
                    </span>
                    <div className="absolute inset-x-0 bottom-0 z-10 bg-gradient-to-t from-screen-dark via-screen-dark/90 to-transparent px-5 pb-6 pt-28">
                      <p className="max-w-[225px] text-[27px] font-black leading-tight text-surface">
                        {option.titleLines.map((line) => (
                          <span key={line} className="block">{line}</span>
                        ))}
                      </p>
                    </div>
                    <span className={`absolute bottom-5 right-5 z-20 grid h-16 w-16 place-items-center rounded-chip border-[3px] border-surface ${active ? "bg-brand" : "bg-screen-dark/35"}`}>
                      {active ? <Check className="h-8 w-8" aria-hidden="true" /> : <Heart className="h-8 w-8" aria-hidden="true" />}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        <div className="mt-2 flex items-center justify-between px-7">
          <div className="flex gap-2" aria-label={`${selected.length}개 선택됨`}>
            {SCENARIO_OPTIONS.map((item) => <span key={item.value} className={`h-2.5 w-2.5 rounded-chip ${selected.includes(item.value) ? "bg-brand" : "bg-surface/30"}`} />)}
          </div>
          <button type="button" disabled={saving} onClick={() => void submitPreferences(true)} className="min-h-11 px-3 text-base font-bold">건너뛰기 ›</button>
        </div>
        <div className="px-6 pt-5">
          <button type="button" disabled={saving || selected.length === 0} onClick={() => void submitPreferences(false)} className="min-h-14 w-full rounded-card-lg bg-brand text-base font-extrabold disabled:opacity-40">
            {saving ? "저장 중…" : `${selected.length}개 취향 선택 완료`}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-3">
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
            <h2 className="text-base font-extrabold text-ink">
              어떤 축제를 좋아하시나요?
            </h2>
          </div>
          <span className="rounded-chip bg-surface-soft px-2.5 py-0.5 text-[11px] font-bold text-brand">
            {status === "completed"
              ? "설정 완료"
              : status === "skipped"
                ? "건너뜀"
                : "미설정"}
          </span>
        </div>
        <p className="text-xs text-muted">
          마음에 드는 축제 스타일을 골라 주세요. ({selected.length}/5 선택)
        </p>
      </div>

      {notice ? (
        <p role="status" className="rounded-card bg-surface-soft px-3.5 py-2.5 text-xs font-semibold text-ink">
          {notice}
        </p>
      ) : null}

      {loading ? (
        <div role="status" className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-card bg-surface-muted" />
          ))}
        </div>
      ) : error && status === "pending" && selected.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-card border border-line-light bg-surface px-4 py-10 text-center">
          <p role="alert" className="text-sm font-semibold text-ink">
            {error}
          </p>
          <button
            type="button"
            onClick={() => setReloadTick((v) => v + 1)}
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>다시 시도</span>
          </button>
        </div>
      ) : (
        <>
          {error ? (
            <p role="alert" className="text-xs font-semibold text-brand">
              {error}
            </p>
          ) : null}
          <ul className="space-y-2">
            {SCENARIO_OPTIONS.map((option) => {
              const active = selected.includes(option.value);
              return (
                <li key={option.value}>
                  <button
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleScenario(option.value)}
                    className={`flex w-full items-center justify-between gap-3 rounded-card border p-3.5 text-left transition-colors ${
                      active
                        ? "border-brand bg-surface-soft/75 shadow-sm"
                        : "border-line-light bg-surface hover:border-brand/40"
                    }`}
                  >
                    <div className="min-w-0 space-y-0.5">
                      <span className="inline-block rounded-chip bg-brand/15 px-2 py-0.5 text-[10px] font-extrabold text-brand">
                        {option.tag}
                      </span>
                      <p className="text-sm font-extrabold text-ink">
                        {option.title}
                      </p>
                      <p className="text-xs text-muted">{option.description}</p>
                    </div>
                    <span
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-chip ${
                        active
                          ? "bg-brand text-surface"
                          : "border border-line-light bg-surface text-muted"
                      }`}
                    >
                      {active ? (
                        <Check className="h-4 w-4" aria-hidden="true" />
                      ) : (
                        <Heart className="h-4 w-4" aria-hidden="true" />
                      )}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              disabled={saving}
              onClick={() => void submitPreferences(true)}
              className="flex-1 rounded-chip border border-line-light bg-surface py-3 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
            >
              건너뛰기
            </button>
            <button
              type="button"
              disabled={saving}
              onClick={() => void submitPreferences(false)}
              className="flex-1 rounded-chip bg-brand py-3 text-xs font-extrabold text-surface shadow-sm hover:opacity-90 disabled:opacity-60"
            >
              {saving ? "저장 중…" : "취향 저장"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}

export function PreferencesView() {
  const router = useRouter();
  return (
    <RequireAuth nextPath="/onboarding">
      <PreferencesSection
        onSaved={(status) =>
          router.push(status === "completed" ? "/onboarding/complete" : "/")
        }
      />
    </RequireAuth>
  );
}

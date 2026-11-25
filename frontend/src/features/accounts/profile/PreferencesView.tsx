"use client";

import { useEffect, useState } from "react";
import { Check, Heart, RotateCcw } from "lucide-react";
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
    setSelected((prev) =>
      prev.includes(value)
        ? prev.filter((item) => item !== value)
        : [...prev, value],
    );
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

  return (
    <section className={embedded ? "space-y-3" : "space-y-4 px-4 py-4"}>
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
  return (
    <RequireAuth nextPath="/onboarding">
      <PreferencesSection />
    </RequireAuth>
  );
}

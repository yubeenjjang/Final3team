import {
  Accessibility,
  ArrowLeftRight,
  Footprints,
  Sparkles,
  UsersRound,
  Zap,
} from "lucide-react";
import type { RoutePreference } from "./api";

const PREFERENCES = [
  { value: "fastest", label: "가장 빠른", Icon: Zap },
  { value: "min_walk", label: "도보 최소", Icon: Footprints },
  { value: "fewest_transfers", label: "환승 최소", Icon: ArrowLeftRight },
  { value: "less_crowded", label: "혼잡 적은", Icon: UsersRound },
  { value: "accessible", label: "이동 편한", Icon: Accessibility },
] as const;

export function preferenceLabel(value: RoutePreference) {
  return PREFERENCES.find((option) => option.value === value)?.label ?? "가장 빠른";
}

export function RoutePreferences({
  value,
  onChange,
}: {
  value: RoutePreference;
  onChange?: (value: RoutePreference) => void;
}) {
  return (
    <fieldset className="min-w-0 rounded-card border border-brand/25 bg-surface px-3 pb-3 pt-1.5 shadow-sm">
      <legend className="ml-0.5 inline-flex items-center gap-1.5 rounded-chip bg-surface px-2 text-xs font-extrabold text-brand">
        <Sparkles size={14} className="fill-brand text-brand" aria-hidden="true" /> 추천 기준
      </legend>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {onChange ? (
          PREFERENCES.map(({ value: option, label, Icon }) => (
            <label key={option} className="cursor-pointer">
              <input
                type="radio"
                name="route-preference"
                className="peer sr-only"
                value={option}
                checked={value === option}
                onChange={() => onChange(option)}
              />
              <span className="flex min-h-8 items-center justify-center gap-1 whitespace-nowrap rounded-chip border border-line-light bg-surface-muted/70 px-3 text-[11px] font-bold text-ink/80 transition-colors hover:border-brand/40 hover:bg-surface-soft hover:text-brand peer-checked:border-brand peer-checked:bg-brand peer-checked:text-surface peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand">
                <Icon size={13} aria-hidden="true" /> {label}
              </span>
            </label>
          ))
        ) : (
          <span className="inline-flex min-h-8 w-fit items-center rounded-chip bg-surface-soft px-3 text-xs font-bold text-brand">
            {preferenceLabel(value)}
          </span>
        )}
      </div>
    </fieldset>
  );
}

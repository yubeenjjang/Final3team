import { ArrowLeftRight, Footprints, Sparkles, UsersRound, Zap } from "lucide-react";
import type { RoutePreference } from "./api";

const PREFERENCES = [
  { value: "fastest", label: "가장 빠른 길", Icon: Zap },
  { value: "min_walk", label: "도보 최소", Icon: Footprints },
  { value: "fewest_transfers", label: "환승 최소", Icon: ArrowLeftRight },
  { value: "less_crowded", label: "혼잡 회피", Icon: UsersRound },
] as const;

export function preferenceLabel(value: RoutePreference) {
  return PREFERENCES.find((option) => option.value === value)?.label ?? "이동 편의";
}

export function RoutePreferences({
  value,
  onChange,
}: {
  value: RoutePreference;
  onChange?: (value: RoutePreference) => void;
}) {
  return (
    <fieldset className="min-w-0 rounded-input border border-accent/45 bg-accent/5 px-3 pb-2.5 shadow-sm">
      <legend className="ml-0.5 inline-flex items-center gap-1.5 rounded-chip bg-bg px-2 text-xs font-extrabold text-accent">
        <Sparkles size={16} aria-hidden="true" /> 추천 기준
      </legend>
      <div className="mt-0.5 grid grid-cols-2 gap-1.5 min-[396px]:flex min-[396px]:flex-wrap">
        {onChange ? PREFERENCES.map(({ value: option, label, Icon }) => (
          <label key={option} className="cursor-pointer">
            <input
              type="radio"
              name="route-preference"
              className="peer sr-only"
              value={option}
              checked={value === option}
              onChange={() => onChange(option)}
            />
            <span className="flex min-h-8 items-center justify-center gap-1 whitespace-nowrap rounded-chip bg-accent/10 px-2 text-[11px] font-bold text-accent peer-checked:bg-accent peer-checked:text-surface peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent">
              <Icon size={13} aria-hidden="true" /> {label}
            </span>
          </label>
        )) : (
          <span className="inline-flex min-h-8 w-fit items-center rounded-chip bg-accent/10 px-3 text-xs font-bold text-accent">
            {preferenceLabel(value)}
          </span>
        )}
      </div>
    </fieldset>
  );
}

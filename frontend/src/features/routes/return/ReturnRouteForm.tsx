import type { FormEvent } from "react";
import { ChevronDown, Clock, House, MapPin, Route } from "lucide-react";
import { FestivalPicker, type SelectedFestival } from "./FestivalPicker";
import { RoutePreferences } from "./RoutePreferences";
import type { RoutePreference } from "./api";

export const RETURN_FORM_ID = "return-route-form";

export interface RouteInputs {
  originType: "festival" | "place";
  originText: string;
  destination: string;
  preference: RoutePreference;
}

interface ReturnRouteFormProps {
  inputs: RouteInputs;
  onInputChange: (patch: Partial<RouteInputs>) => void;
  festival: SelectedFestival | null;
  festivalLoading: boolean;
  festivalError: string | null;
  onFestivalChange: (festival: SelectedFestival) => void;
  pending: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

const PLACE_INPUT_CLASS = "w-full bg-transparent py-0.5 text-base font-bold outline-none placeholder:font-medium placeholder:text-muted focus-visible:underline focus-visible:decoration-accent focus-visible:underline-offset-4";

export function ReturnRouteForm({
  inputs,
  onInputChange,
  festival,
  festivalLoading,
  festivalError,
  onFestivalChange,
  pending,
  onSubmit,
}: ReturnRouteFormProps) {
  return (
    <form id={RETURN_FORM_ID} onSubmit={onSubmit} className="space-y-3">
      <fieldset disabled={pending} className="min-w-0 space-y-3">
        <RoutePreferences value={inputs.preference} onChange={(preference) => onInputChange({ preference })} />
        <div className="divide-y divide-line-light rounded-card border border-line-light bg-surface px-3 shadow-sm">
          <FestivalPicker festival={festival} loading={festivalLoading} error={festivalError} onChange={onFestivalChange} />
          <div className="flex items-center gap-3 py-2">
            <MapPin size={21} className="ml-1 shrink-0 text-brand" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <label htmlFor="return-origin-type" className="block text-xs text-muted">출발지</label>
              <div className="relative">
                <select
                  id="return-origin-type"
                  value={inputs.originType}
                  onChange={(event) => onInputChange({ originType: event.target.value === "place" ? "place" : "festival" })}
                  className="w-full appearance-none bg-transparent py-0.5 pr-7 text-sm font-extrabold focus-visible:outline-accent"
                >
                  <option value="festival">축제 장소</option>
                  <option value="place">직접 입력</option>
                </select>
                <ChevronDown size={18} className="pointer-events-none absolute right-0 top-0.5 text-muted" aria-hidden="true" />
              </div>
              {inputs.originType === "place" ? (
                <input
                  type="text"
                  aria-label="출발 장소"
                  placeholder="출발할 장소 입력"
                  value={inputs.originText}
                  onChange={(event) => onInputChange({ originText: event.target.value })}
                  maxLength={100}
                  required
                  className={PLACE_INPUT_CLASS}
                />
              ) : festival?.venue_name ? (
                <p className="truncate text-xs text-muted">{festival.venue_name}</p>
              ) : null}
            </div>
          </div>
          <div className="flex items-center gap-3 py-2">
            <House size={21} className="ml-1 shrink-0 text-accent" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <label htmlFor="return-destination" className="block text-xs text-muted">도착지</label>
              <input
                id="return-destination"
                type="text"
                placeholder="집 또는 목적지 입력"
                value={inputs.destination}
                onChange={(event) => onInputChange({ destination: event.target.value })}
                maxLength={100}
                required
                className={PLACE_INPUT_CLASS}
              />
            </div>
          </div>
          <div className="flex min-h-9 items-center gap-3 py-2 text-sm font-bold">
            <Clock size={20} className="ml-1 shrink-0 text-accent" aria-hidden="true" />
            지금 출발
          </div>
        </div>
        <button
          type="submit"
          disabled={festivalLoading}
          className="flex min-h-10 w-full items-center justify-center gap-2 rounded-card bg-brand px-4 py-2 text-base font-extrabold text-surface shadow-sm hover:bg-brand/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:opacity-60"
        >
          <Route size={21} aria-hidden="true" /> 집으로 가는 길 찾기
        </button>
      </fieldset>
    </form>
  );
}

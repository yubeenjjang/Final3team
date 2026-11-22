import { useEffect, useState } from "react";
import { ChevronDown, Search, Ticket } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { listFestivals, type FestivalListItem } from "@/features/festivals/explore/api";

export type SelectedFestival = Pick<FestivalListItem, "festival_id" | "name" | "venue_name" | "lat" | "lng">;

interface FestivalPickerProps {
  festival: SelectedFestival | null;
  loading: boolean;
  error: string | null;
  onChange: (festival: SelectedFestival) => void;
}

type SearchResult = { query: string; items: FestivalListItem[]; error?: string };

function FestivalSearch({ onSelect }: { onSelect: (festival: SelectedFestival) => void }) {
  const [search, setSearch] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const query = search.trim();
  const visible = result?.query === query ? result : null;

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    const timer = setTimeout(async () => {
      try {
        const page = await listFestivals({ q: query, sort: "name", page_size: 20 }, signal);
        if (!signal.aborted) {
          setResult({ query, items: page.items });
        }
      } catch (error) {
        if (!signal.aborted) {
          setResult({
            query,
            items: [],
            error: error instanceof ApiError ? error.message : "축제를 검색하지 못했어요.",
          });
        }
      }
    }, query ? 250 : 0);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  return (
    <div id="return-festival-search" className="space-y-2 pb-3">
      <label className="flex items-center gap-2 rounded-input border border-line-light bg-bg px-3 py-2 focus-within:border-accent">
        <Search size={16} className="shrink-0 text-muted" aria-hidden="true" />
        <input
          type="search"
          aria-label="축제 검색"
          placeholder="축제 이름 또는 장소"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") event.preventDefault();
          }}
          maxLength={100}
          className="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted"
        />
      </label>
      {!visible ? <p role="status" className="px-2 text-xs text-muted">축제를 찾고 있어요.</p> : null}
      {visible?.error ? <p role="alert" className="px-2 text-xs text-brand">{visible.error}</p> : null}
      {visible && !visible.error && !visible.items.length ? (
        <p role="status" className="px-2 text-xs text-muted">검색 결과가 없어요.</p>
      ) : null}
      {visible?.items.length ? (
        <ul aria-label="축제 검색 결과" className="max-h-44 divide-y divide-line-light overflow-y-auto rounded-card border border-line-light">
          {visible.items.map((festival) => (
            <li key={festival.festival_id}>
              <button
                type="button"
                onClick={() => onSelect(festival)}
                className="block w-full px-3 py-2 text-left text-sm font-bold hover:bg-accent/5 focus-visible:bg-accent/10"
              >
                {festival.name}
                {festival.venue_name ? (
                  <span className="block text-xs font-medium text-muted">{festival.venue_name}</span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function FestivalPicker({ festival, loading, error, onChange }: FestivalPickerProps) {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        id="return-festival-picker"
        type="button"
        aria-expanded={open}
        aria-controls={open ? "return-festival-search" : undefined}
        className="flex min-h-11 w-full items-center gap-3 py-2 text-left"
        onClick={() => setOpen(!open)}
      >
        <Ticket size={21} className="ml-1 shrink-0 text-accent" aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="block text-xs text-muted">축제</span>
          <span className="block truncate text-sm font-extrabold">
            {loading ? "선택한 축제를 불러오는 중…" : festival?.name ?? "축제 검색 및 선택"}
          </span>
        </span>
        <ChevronDown size={18} className={`shrink-0 text-muted ${open ? "rotate-180" : ""}`} aria-hidden="true" />
      </button>
      {error ? <p role="alert" className="pb-2 pl-10 text-xs text-brand">{error}</p> : null}
      {open ? (
        <FestivalSearch onSelect={(selection) => {
          onChange(selection);
          setOpen(false);
        }} />
      ) : null}
    </div>
  );
}

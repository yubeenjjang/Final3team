"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { RotateCcw, Search, X } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { listFestivals, type FestivalListItem } from "./api";
import { FestivalCard } from "./FestivalCard";
import {
  REGION_OPTIONS,
  STATUS_OPTIONS,
  type RegionFilter,
  type StatusFilter,
} from "./regions";

const PAGE_SIZE = 20;

export function FestivalExploreView() {
  const [searchInput, setSearchInput] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [region, setRegion] = useState<RegionFilter>("ALL");
  const [status, setStatus] = useState<StatusFilter>("");

  const [items, setItems] = useState<FestivalListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const moreRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    async function fetchFirstPage() {
      setLoading(true);
      setErrorMessage(null);
      try {
        const res = await listFestivals(
          {
            region,
            q: appliedQuery || undefined,
            status: status || undefined,
            page: 1,
            page_size: PAGE_SIZE,
          },
          controller.signal,
        );
        if (!active) {
          return;
        }
        setItems(res.items);
        setTotal(res.total);
        setPage(res.page);
      } catch (error) {
        if (!active || (error instanceof Error && error.name === "AbortError")) {
          return;
        }
        setItems([]);
        setTotal(0);
        setErrorMessage(
          error instanceof ApiError
            ? error.message
            : "축제 목록을 불러오지 못했어요",
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    fetchFirstPage();

    return () => {
      active = false;
      controller.abort();
      moreRequest.current?.abort();
      moreRequest.current = null;
    };
  }, [region, status, appliedQuery, reloadTick]);

  const cancelLoadMore = useCallback(() => {
    moreRequest.current?.abort();
    moreRequest.current = null;
    setLoadingMore(false);
  }, []);

  const handleSearchSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const nextQuery = searchInput.trim();
      if (nextQuery !== appliedQuery) {
        cancelLoadMore();
        setAppliedQuery(nextQuery);
      }
    },
    [appliedQuery, cancelLoadMore, searchInput],
  );

  const handleClearSearch = useCallback(() => {
    setSearchInput("");
    if (appliedQuery) cancelLoadMore();
    setAppliedQuery("");
  }, [appliedQuery, cancelLoadMore]);

  const handleLoadMore = useCallback(async () => {
    if (moreRequest.current) {
      return;
    }
    const controller = new AbortController();
    moreRequest.current = controller;
    const nextPage = page + 1;
    setLoadingMore(true);
    setErrorMessage(null);
    try {
      const res = await listFestivals({
        region,
        q: appliedQuery || undefined,
        status: status || undefined,
        page: nextPage,
        page_size: PAGE_SIZE,
      }, controller.signal);
      if (controller.signal.aborted) return;
      setItems((prev) => [...prev, ...res.items]);
      setTotal(res.total);
      setPage(res.page);
    } catch (error) {
      if (controller.signal.aborted) return;
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "추가 축제를 불러오지 못했어요",
      );
    } finally {
      if (moreRequest.current === controller) {
        moreRequest.current = null;
        setLoadingMore(false);
      }
    }
  }, [page, region, appliedQuery, status]);

  const hasMore = items.length < total;

  return (
    <div className="space-y-4 px-4 py-4">
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
            <h1 className="text-lg font-extrabold text-ink">전국 축제</h1>
          </div>
          {!loading && !errorMessage ? (
            <span className="text-xs font-semibold text-muted">
              총 {total}개
            </span>
          ) : null}
        </div>

        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search
              className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
              aria-hidden="true"
            />
            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="축제 이름, 장소 검색"
              aria-label="축제 검색"
              className="h-11 w-full rounded-input border border-line-light bg-surface pl-10 pr-9 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none"
            />
            {searchInput ? (
              <button
                type="button"
                onClick={handleClearSearch}
                aria-label="검색어 지우기"
                className="absolute right-2.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-chip text-muted hover:bg-surface-soft hover:text-ink"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            ) : null}
          </div>
          <button
            type="submit"
            className="h-11 shrink-0 rounded-input bg-brand px-4 text-sm font-bold text-surface transition-opacity hover:opacity-90"
          >
            검색
          </button>
        </form>

        <div className="flex items-center gap-2">
          <label htmlFor="festival-region-select" className="sr-only">
            지역 선택
          </label>
          <select
            id="festival-region-select"
            aria-label="지역 선택"
            value={region}
            onChange={(event) => {
              const nextRegion = event.target.value as RegionFilter;
              if (nextRegion !== region) {
                cancelLoadMore();
                setRegion(nextRegion);
              }
            }}
            className="h-9 shrink-0 rounded-chip border border-line-light bg-surface px-3 text-xs font-semibold text-ink focus:border-accent focus:outline-none"
          >
            {REGION_OPTIONS.map((option) => (
              <option key={option.code} value={option.code}>
                {option.label}
              </option>
            ))}
          </select>

          <div
            role="group"
            aria-label="축제 상태"
            className="flex flex-1 items-center gap-1.5 overflow-x-auto py-0.5"
          >
            {STATUS_OPTIONS.map((option) => {
              const active = status === option.value;
              return (
                <button
                  key={option.label}
                  type="button"
                  aria-pressed={active}
                  onClick={() => {
                    if (option.value !== status) {
                      cancelLoadMore();
                      setStatus(option.value);
                    }
                  }}
                  className={
                    active
                      ? "shrink-0 rounded-chip bg-brand px-3 py-1.5 text-xs font-bold text-surface"
                      : "shrink-0 rounded-chip border border-line-light bg-surface px-3 py-1.5 text-xs font-semibold text-muted transition-colors hover:text-ink"
                  }
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {loading ? (
        <div
          aria-label="축제 목록 불러오는 중"
          className="space-y-3"
        >
          {[0, 1, 2].map((skeleton) => (
            <div
              key={skeleton}
              className="h-64 animate-pulse rounded-card border border-line-light bg-surface"
            />
          ))}
        </div>
      ) : errorMessage && items.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-card border border-line-light bg-surface px-4 py-12 text-center">
          <p className="text-sm font-semibold text-ink">{errorMessage}</p>
          <button
            type="button"
            onClick={() => setReloadTick((prev) => prev + 1)}
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>다시 시도</span>
          </button>
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-card border border-line-light bg-surface px-4 py-12 text-center">
          <p className="text-sm font-semibold text-muted">
            조건에 맞는 축제가 없어요
          </p>
        </div>
      ) : (
        <section className="space-y-3">
          <div className="grid grid-cols-1 gap-3">
            {items.map((item) => (
              <FestivalCard key={item.festival_id} item={item} />
            ))}
          </div>

          {errorMessage ? (
            <p className="text-center text-xs font-medium text-brand">
              {errorMessage}
            </p>
          ) : null}

          {hasMore ? (
            <div className="pt-1 text-center">
              <button
                type="button"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="w-full rounded-card border border-line-light bg-surface py-3 text-sm font-bold text-ink transition-colors hover:bg-surface-soft disabled:opacity-60"
              >
                {loadingMore ? "불러오는 중…" : "더 보기"}
              </button>
            </div>
          ) : null}
        </section>
      )}
    </div>
  );
}

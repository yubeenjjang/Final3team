"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { RotateCcw, Search, X } from "lucide-react";
import Image from "next/image";
import { TabPageHero } from "@/components/TabPageHero";
import { ApiError } from "@/lib/api/client";
import { listFestivals, type FestivalListItem } from "./api";
import { FestivalCarousel } from "./FestivalCarousel";
import { FestivalCard } from "./FestivalCard";
import { PreferenceSetupCta } from "@/features/accounts/profile/PreferenceSetupCta";
import { useFestivalPreferenceStatus } from "@/features/accounts/profile/useFestivalPreferenceStatus";
import {
  FESTIVAL_SECTION_CONFIG,
  FESTIVAL_SECTION_ORDER,
} from "./sectionConfig";
import {
  REGION_OPTIONS,
  STATUS_OPTIONS,
  type RegionFilter,
  type StatusFilter,
} from "./regions";

const PAGE_SIZE = 20;

export function FestivalExploreView({
  mode = "sections",
  listTitle = "전체 축제",
}: {
  mode?: "sections" | "list";
  listTitle?: string;
} = {}) {
  const [region, setRegion] = useState<RegionFilter>("ALL");
  const [status, setStatus] = useState<StatusFilter>("");
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const [items, setItems] = useState<FestivalListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const preferenceStatus = useFestivalPreferenceStatus();
  const hasPersonalRecommendations = preferenceStatus === "completed";

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
            q: searchQuery || undefined,
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
  }, [region, status, searchQuery, reloadTick]);

  const cancelLoadMore = useCallback(() => {
    moreRequest.current?.abort();
    moreRequest.current = null;
    setLoadingMore(false);
  }, []);

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
        q: searchQuery || undefined,
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
  }, [page, region, searchQuery, status]);

  const handleSearch = useCallback((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextQuery = searchInput.trim();
    cancelLoadMore();
    setSearchQuery(nextQuery);
  }, [cancelLoadMore, searchInput]);

  const clearSearch = useCallback(() => {
    cancelLoadMore();
    setSearchInput("");
    setSearchQuery("");
  }, [cancelLoadMore]);

  const hasMore = items.length < total;
  const festivalSections = FESTIVAL_SECTION_ORDER
    .map((key, index) => ({
      key,
      ...FESTIVAL_SECTION_CONFIG[key],
      items: key === "all"
        ? items.slice(0, 4)
        : items.slice(index * 4, index * 4 + 4),
    }))
    .filter((section) => section.items.length > 0)
    .filter((section) => hasPersonalRecommendations || section.key !== "personal");

  return (
    <div className="space-y-4 px-4 py-4 md:space-y-7 md:px-8 md:py-8">
      <TabPageHero
        title={
          mode === "list" ? (
            listTitle
          ) : (
            <>
              축제 <span className="text-brand">즐겨봐!</span>
            </>
          )
        }
        subtitle={
          mode === "list"
            ? "원하는 조건으로 축제를 살펴보세요!"
            : "지금 열리는 축제부터, 나에게 딱 맞는 축제까지!"
        }
        aside={
          <div className="relative h-14 w-[104px]">
            <Image
              src="/brand/festival-hero-compact.png"
              alt=""
              fill
              sizes="104px"
              className="object-contain object-right"
            />
          </div>
        }
      />

      <form
        role="search"
        aria-label="축제 검색"
        onSubmit={handleSearch}
        className="flex items-center gap-2"
      >
        <label className="relative min-w-0 flex-1">
          <span className="sr-only">축제명 또는 장소 검색</span>
          <Search
            className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
            aria-hidden="true"
          />
          <input
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="축제명·장소 검색"
            aria-label="축제명 또는 장소 검색"
            className="h-11 w-full rounded-input border border-line-light bg-surface pl-10 pr-9 text-sm text-ink shadow-sm outline-none placeholder:text-muted focus:border-brand"
          />
          {searchInput ? (
            <button
              type="button"
              onClick={clearSearch}
              aria-label="검색어 지우기"
              className="absolute right-2.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full text-muted hover:bg-surface-soft hover:text-ink"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          ) : null}
        </label>
        <button
          type="submit"
          className="h-11 shrink-0 rounded-chip bg-brand px-4 text-sm font-extrabold text-surface shadow-sm"
        >
          검색
        </button>
      </form>

      {mode === "list" ? (
        <section aria-label="축제 필터" className="flex items-center gap-2">
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
            className="h-9 shrink-0 rounded-chip border border-line-light bg-surface px-3 text-xs font-semibold text-ink focus:border-brand focus:outline-none"
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
            className="no-scrollbar flex flex-1 items-center gap-1.5 overflow-x-auto py-0.5"
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
        </section>
      ) : null}

      {loading ? (
        <div
          aria-label="축제 목록 불러오는 중"
          className={mode === "list" ? "grid grid-cols-2 gap-2" : "space-y-3"}
        >
          {[0, 1, 2, 3].map((skeleton) => (
            <div
              key={skeleton}
              className={`${mode === "list" ? "aspect-[3/2]" : "h-64"} animate-pulse rounded-card border border-line-light bg-surface`}
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
            {searchQuery ? `‘${searchQuery}’ 검색 결과가 없어요` : "조건에 맞는 축제가 없어요"}
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {mode === "list" || searchQuery ? (
            <section
              aria-label={searchQuery ? "축제 검색 결과" : `${listTitle} 목록`}
              className="space-y-3"
            >
              {searchQuery ? (
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-base font-extrabold text-ink">
                    ‘{searchQuery}’ 검색 결과
                  </h2>
                  <span className="text-xs font-semibold text-muted">총 {total}개</span>
                </div>
              ) : null}
              <div className="grid grid-cols-2 gap-x-2 gap-y-4 md:grid-cols-3 md:gap-5 lg:grid-cols-4">
              {items.map((item) => (
                <FestivalCard key={item.festival_id} item={item} />
              ))}
              </div>
            </section>
          ) : (
            festivalSections.map((section) => (
              <section key={section.key} className="space-y-3">
                <div className="flex items-end justify-between gap-3">
                  <div>
                    <h2 className="flex items-center gap-2 text-base font-extrabold tracking-tight text-ink">
                      <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
                      {section.title}
                    </h2>
                    {section.description ? (
                      <p className="ml-3.5 mt-1 text-xs text-muted">{section.description}</p>
                    ) : null}
                  </div>
                  <Link
                    href={`/festivals/all?section=${section.key}`}
                    className="shrink-0 text-xs font-bold text-muted hover:text-brand"
                  >
                    전체보기 ›
                  </Link>
                </div>
                <FestivalCarousel items={section.items} ariaLabel={section.title} />
              </section>
            ))
          )}

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
        </div>
      )}

      {mode === "sections" && preferenceStatus !== "completed" && preferenceStatus !== "loading" ? (
        <PreferenceSetupCta />
      ) : null}

    </div>
  );
}

"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  CalendarDays,
  MapPin,
  MessageCircle,
  Plus,
  RotateCcw,
  Search,
  Users,
  X,
} from "lucide-react";
import { LoginPromptSheet } from "@/components/LoginPromptSheet";
import { FestivalImagePlaceholder } from "@/components/FestivalImagePlaceholder";
import { TabPageHero } from "@/components/TabPageHero";
import { handleAuthError, useIsSignedIn } from "@/components/RequireAuth";
import { listFestivals, type FestivalListItem } from "@/features/festivals/explore/api";
import {
  getRegionLabel,
  REGION_OPTIONS,
  type RegionFilter,
} from "@/features/festivals/explore/regions";
import { ApiError } from "@/lib/api/client";
import {
  createCompanionPost,
  decideCompanionApplication,
  getCompanionPost,
  listCompanionFeed,
  listCompanionPosts,
  listMyCompanionApplications,
  listMyCompanionPosts,
  type AgePreference,
  type CompanionFeedPostItem,
  type CompanionPostDetail,
  type GenderPreference,
  type MyCompanionApplicationItem,
  type MyCompanionPostItem,
  type PostStatus,
} from "./api";
import {
  AGE_PREF_OPTIONS,
  APPLICATION_STATUS_LABEL,
  formatKstDateTime,
  GENDER_PREF_OPTIONS,
  getAgePrefLabel,
  getGenderPrefLabel,
  POST_STATUS_META,
  toKstIsoString,
} from "./format";

type StatusFilter = PostStatus | "all";
type PeriodFilter = "all" | "today" | "week" | "month";
type ConditionFilter = "all" | "age_any" | "gender_any" | "female" | "male";
type SortFilter = "latest" | "meet_soon" | "meet_late" | "vacancy";

const STATUS_TABS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "open", label: "모집 중" },
  { value: "full", label: "정원 마감" },
  { value: "ended", label: "종료" },
  { value: "cancelled", label: "취소" },
];

const DEFAULT_MEETING_TIME = "18:00";
const LEGACY_POST_STATUSES: PostStatus[] = ["open", "full", "ended", "cancelled"];

async function listLegacyCompanionFeed(
  festivals: FestivalListItem[],
  statusFilter: StatusFilter,
  signal: AbortSignal,
) {
  const statuses = statusFilter === "all" ? LEGACY_POST_STATUSES : [statusFilter];
  const tasks = festivals.flatMap((festival) =>
    statuses.map((status) => ({ festival, status })),
  );
  const items: CompanionFeedPostItem[] = [];
  let cursor = 0;

  async function worker() {
    while (cursor < tasks.length && !signal.aborted) {
      const task = tasks[cursor];
      cursor += 1;
      const response = await listCompanionPosts(
        task.festival.festival_id,
        { status: task.status, page: 1 },
        signal,
      );
      response.items.forEach((post) => {
        items.push({
          ...post,
          festival_id: task.festival.festival_id,
          festival_name: task.festival.name,
          festival_thumbnail_url: task.festival.thumbnail_url,
          festival_venue_name: task.festival.venue_name,
          festival_region_code: task.festival.region_code,
        });
      });
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(6, tasks.length) }, () => worker()),
  );
  return items;
}

function getKstDateString(date: Date, dayOffset = 0) {
  const kstTime = date.getTime() + 9 * 60 * 60 * 1000 + dayOffset * 24 * 60 * 60 * 1000;
  return new Date(kstTime).toISOString().slice(0, 10);
}

export function getDefaultCompanionMeetAt(
  festival: Pick<FestivalListItem, "event_status" | "start_date" | "end_date">,
  now = new Date(),
) {
  const today = getKstDateString(now);
  const tomorrow = getKstDateString(now, 1);
  const startDate = festival.start_date ?? tomorrow;
  const endDate = festival.end_date ?? startDate;
  let meetingDate = festival.event_status === "ongoing" ? tomorrow : startDate;

  // 축제가 오늘 끝나는 경우처럼 내일이 기간 밖이면 종료일 안으로 맞춘다.
  if (meetingDate > endDate) meetingDate = endDate;
  if (meetingDate < today) meetingDate = today;

  return `${meetingDate}T${DEFAULT_MEETING_TIME}`;
}

export interface CompanionsViewProps {
  initialFestivalId?: string;
  initialTab?: "browse" | "mine";
  initialWriteOpen?: boolean;
}

export function CompanionsView({
  initialFestivalId,
  initialTab = "browse",
  initialWriteOpen = false,
}: CompanionsViewProps) {
  const router = useRouter();
  const routerRef = useRef(router);
  const feedApiSupportedRef = useRef<boolean | null>(null);
  useEffect(() => {
    routerRef.current = router;
  }, [router]);
  const signedIn = useIsSignedIn();

  const [tab, setTab] = useState<"browse" | "mine">(initialTab);
  const [festivals, setFestivals] = useState<FestivalListItem[]>([]);
  const [festivalsLoading, setFestivalsLoading] = useState(true);
  const [festivalsError, setFestivalsError] = useState<string | null>(null);
  const [selectedFestivalId, setSelectedFestivalId] = useState(initialFestivalId ?? "");
  const [browseFestivalSearch, setBrowseFestivalSearch] = useState("");

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("open");
  const [regionFilter, setRegionFilter] = useState<RegionFilter>("ALL");
  const [periodFilter, setPeriodFilter] = useState<PeriodFilter>("all");
  const [conditionFilter, setConditionFilter] = useState<ConditionFilter>("all");
  const [sortFilter, setSortFilter] = useState<SortFilter>("latest");
  const [filterNow] = useState(() => Date.now());
  const [posts, setPosts] = useState<CompanionFeedPostItem[]>([]);
  const [postsTotal, setPostsTotal] = useState(0);
  const [postsLoading, setPostsLoading] = useState(false);
  const [postsError, setPostsError] = useState<string | null>(null);
  const [postsTick, setPostsTick] = useState(0);

  const [mineSubTab, setMineSubTab] = useState<"posts" | "applications">("posts");
  const [myPosts, setMyPosts] = useState<MyCompanionPostItem[]>([]);
  const [myApps, setMyApps] = useState<MyCompanionApplicationItem[]>([]);
  const [myAppPosts, setMyAppPosts] = useState<Record<string, CompanionPostDetail>>({});
  const [myAppFeedPosts, setMyAppFeedPosts] = useState<Record<string, CompanionFeedPostItem>>({});
  const [mineLoading, setMineLoading] = useState(false);
  const [mineError, setMineError] = useState<string | null>(null);
  const [mineTick, setMineTick] = useState(0);
  const [cancellingAppId, setCancellingAppId] = useState<string | null>(null);

  const [writeOpen, setWriteOpen] = useState(false);
  const initialWriteHandledRef = useRef(false);
  const [loginPromptOpen, setLoginPromptOpen] = useState(false);
  const [loginPromptDesc, setLoginPromptDesc] = useState(
    "동행 모집 글을 작성하거나 신청하려면 로그인해 주세요.",
  );

  // Write form states
  const [formFestivalId, setFormFestivalId] = useState(initialFestivalId ?? "");
  const [festivalSearch, setFestivalSearch] = useState("");
  const [meetAt, setMeetAt] = useState("");
  const [capacity, setCapacity] = useState(3);
  const [agePref, setAgePref] = useState<AgePreference>("any");
  const [genderPref, setGenderPref] = useState<GenderPreference>("any");
  const [memo, setMemo] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [festivalsTick, setFestivalsTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setFestivalsLoading(true);
      setFestivalsError(null);
      try {
        const res = await listFestivals(
          { page: 1, page_size: 100 },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setFestivals(res.items);
        setSelectedFestivalId((prev) => {
          if (prev && res.items.some((item) => item.festival_id === prev)) {
            return prev;
          }
          return "";
        });
        setFormFestivalId((prev) => {
          if (prev && res.items.some((item) => item.festival_id === prev)) {
            return prev;
          }
          return res.items[0]?.festival_id ?? "";
        });
      } catch (error) {
        if (controller.signal.aborted) return;
        setFestivalsError(
          error instanceof ApiError
            ? error.message
            : "축제 목록을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setFestivalsLoading(false);
        }
      }
    }
    void load();
    return () => controller.abort();
  }, [festivalsTick]);

  useEffect(() => {
    if (!initialWriteOpen || initialWriteHandledRef.current || festivalsLoading) {
      return;
    }
    initialWriteHandledRef.current = true;
    let cancelled = false;

    queueMicrotask(() => {
      if (cancelled) return;
      if (!signedIn) {
        setLoginPromptDesc("동행 모집 글을 작성하려면 로그인해 주세요.");
        setLoginPromptOpen(true);
        return;
      }

      const requestedFestival = festivals.find(
        (festival) => festival.festival_id === initialFestivalId,
      );
      const nextFestival = requestedFestival ?? festivals[0];
      if (!nextFestival) return;

      setSelectedFestivalId(nextFestival.festival_id);
      setFormFestivalId(nextFestival.festival_id);
      setFestivalSearch(nextFestival.name);
      setMeetAt(getDefaultCompanionMeetAt(nextFestival));
      setFormError(null);
      setWriteOpen(true);
    });

    return () => {
      cancelled = true;
    };
  }, [festivals, festivalsLoading, initialFestivalId, initialWriteOpen, signedIn]);

  useEffect(() => {
    if (tab !== "browse") {
      return;
    }
    const controller = new AbortController();
    async function load() {
      setPostsLoading(true);
      setPostsError(null);
      try {
        let items: CompanionFeedPostItem[];
        let total: number;
        if (feedApiSupportedRef.current !== false) {
          try {
            const res = await listCompanionFeed(
              {
                festival_id: selectedFestivalId || undefined,
                q: browseFestivalSearch.trim() || undefined,
                status: statusFilter === "all" ? undefined : statusFilter,
                page: 1,
                page_size: 50,
              },
              controller.signal,
            );
            feedApiSupportedRef.current = true;
            items = res.items;
            total = res.total;
          } catch (error) {
            if (!(error instanceof ApiError) || ![404, 405].includes(error.status)) {
              throw error;
            }
            feedApiSupportedRef.current = false;
            const query = browseFestivalSearch.trim().toLocaleLowerCase("ko-KR");
            const candidates = festivals.filter((festival) => {
              if (selectedFestivalId && festival.festival_id !== selectedFestivalId) return false;
              if (!query) return true;
              return [festival.name, festival.venue_name]
                .filter(Boolean)
                .some((value) => value!.toLocaleLowerCase("ko-KR").includes(query));
            });
            items = await listLegacyCompanionFeed(candidates, statusFilter, controller.signal);
            total = items.length;
          }
        } else {
          const query = browseFestivalSearch.trim().toLocaleLowerCase("ko-KR");
          const candidates = festivals.filter((festival) => {
            if (selectedFestivalId && festival.festival_id !== selectedFestivalId) return false;
            if (!query) return true;
            return [festival.name, festival.venue_name]
              .filter(Boolean)
              .some((value) => value!.toLocaleLowerCase("ko-KR").includes(query));
          });
          items = await listLegacyCompanionFeed(candidates, statusFilter, controller.signal);
          total = items.length;
        }
        if (!controller.signal.aborted) {
          setPosts(items);
          setPostsTotal(total);
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        setPosts([]);
        setPostsError(
          error instanceof ApiError
            ? error.message
            : "동행 모집 글을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setPostsLoading(false);
        }
      }
    }
    void load();
    return () => controller.abort();
  }, [tab, selectedFestivalId, browseFestivalSearch, statusFilter, postsTick, festivals]);

  useEffect(() => {
    if (tab !== "mine" || !signedIn) {
      return;
    }
    const controller = new AbortController();
    async function load() {
      setMineLoading(true);
      setMineError(null);
      try {
        if (mineSubTab === "posts") {
          const res = await listMyCompanionPosts(controller.signal);
          if (!controller.signal.aborted) setMyPosts(res.items);
        } else {
          const res = await listMyCompanionApplications(controller.signal);
          if (controller.signal.aborted) return;
          setMyApps(res.items);

          const detailResults = await Promise.allSettled(
            res.items.map((item) => getCompanionPost(item.post_id, controller.signal)),
          );
          if (controller.signal.aborted) return;
          const nextPosts: Record<string, CompanionPostDetail> = {};
          detailResults.forEach((result, index) => {
            if (result.status === "fulfilled") {
              nextPosts[res.items[index].post_id] = result.value;
            }
          });
          setMyAppPosts(nextPosts);

          // The feed adds festival metadata that the current activity response
          // does not include. Keep this best-effort so older API environments
          // still show the post memo, author and meeting time from detail.
          try {
            const feed = await listCompanionFeed({ page: 1, page_size: 50 }, controller.signal);
            if (!controller.signal.aborted) {
              setMyAppFeedPosts(
                Object.fromEntries(feed.items.map((item) => [item.post_id, item])),
              );
            }
          } catch {
            if (!controller.signal.aborted) setMyAppFeedPosts({});
          }
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        if (handleAuthError(error)) {
          routerRef.current.replace(
            `/auth/login?next=${encodeURIComponent("/companions?tab=mine")}`,
          );
          return;
        }
        setMineError(
          error instanceof ApiError
            ? error.message
            : "내 동행 내역을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setMineLoading(false);
        }
      }
    }
    void load();
    return () => controller.abort();
  }, [tab, signedIn, mineSubTab, mineTick]);

  function selectFormFestival(festivalId: string) {
    setFormFestivalId(festivalId);
    const festival = festivals.find((item) => item.festival_id === festivalId);
    setMeetAt(festival ? getDefaultCompanionMeetAt(festival) : "");
  }

  async function handleCreatePost(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    if (!formFestivalId || !meetAt) {
      setFormError("축제와 만남 일시를 선택해 주세요.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      const created = await createCompanionPost({
        festival_id: formFestivalId,
        meet_at: toKstIsoString(meetAt),
        capacity,
        age_pref: agePref,
        gender_pref: genderPref,
        memo: memo.trim() || null,
      });
      setWriteOpen(false);
      router.push(`/companions/${encodeURIComponent(created.post_id)}`);
    } catch (error) {
      if (handleAuthError(error)) {
        router.replace(`/auth/login?next=${encodeURIComponent("/companions")}`);
        return;
      }
      setFormError(
        error instanceof ApiError
          ? error.message
          : "모집 글을 등록하지 못했어요.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancelMyApplication(applicationId: string) {
    if (cancellingAppId) return;
    setCancellingAppId(applicationId);
    setMineError(null);
    try {
      await decideCompanionApplication(applicationId, "cancel");
      setMineTick((v) => v + 1);
    } catch (error) {
      if (handleAuthError(error)) {
        router.replace(`/auth/login?next=${encodeURIComponent("/companions?tab=mine")}`);
        return;
      }
      setMineError(
        error instanceof ApiError
          ? error.message
          : "신청을 취소하지 못했어요.",
      );
    } finally {
      setCancellingAppId(null);
    }
  }

  const selectedFestival = festivals.find((f) => f.festival_id === selectedFestivalId);
  const normalizedBrowseFestivalSearch = browseFestivalSearch
    .trim()
    .toLocaleLowerCase("ko-KR");
  const matchingBrowseFestivals = normalizedBrowseFestivalSearch
    ? festivals.filter((festival) =>
        [festival.name, festival.venue_name]
          .filter(Boolean)
          .some((value) =>
            value!.toLocaleLowerCase("ko-KR").includes(normalizedBrowseFestivalSearch),
          ),
      )
    : festivals;
  const browseFestivalOptions =
    selectedFestival &&
    !matchingBrowseFestivals.some(
      (festival) => festival.festival_id === selectedFestival.festival_id,
    )
      ? [selectedFestival, ...matchingBrowseFestivals]
      : matchingBrowseFestivals;
  const selectedFormFestival = festivals.find((f) => f.festival_id === formFestivalId);
  const normalizedFestivalSearch = festivalSearch.trim().toLocaleLowerCase("ko-KR");
  const matchingFormFestivals = normalizedFestivalSearch
    ? festivals.filter((festival) =>
        [festival.name, festival.venue_name]
          .filter(Boolean)
          .some((value) =>
            value!.toLocaleLowerCase("ko-KR").includes(normalizedFestivalSearch),
          ),
      )
    : festivals;
  const isFormFestivalSelectionCurrent = Boolean(
    selectedFormFestival &&
      selectedFormFestival.name.toLocaleLowerCase("ko-KR") === normalizedFestivalSearch,
  );
  const visibleFormFestivalResults =
    normalizedFestivalSearch && !isFormFestivalSelectionCurrent
      ? matchingFormFestivals.slice(0, 8)
      : [];
  const displayedPosts = posts
    .filter((post) => {
      if (regionFilter !== "ALL" && post.festival_region_code !== regionFilter) {
        return false;
      }
      const meetAtTime = new Date(post.meet_at).getTime();
      const now = filterNow;
      if (periodFilter === "today") {
        if (getKstDateString(new Date(post.meet_at)) !== getKstDateString(new Date(filterNow))) {
          return false;
        }
      } else if (periodFilter === "week") {
        if (meetAtTime < now || meetAtTime > now + 7 * 24 * 60 * 60 * 1000) return false;
      } else if (periodFilter === "month") {
        if (meetAtTime < now || meetAtTime > now + 30 * 24 * 60 * 60 * 1000) return false;
      }
      if (conditionFilter === "age_any" && ![null, "any"].includes(post.age_pref)) {
        return false;
      }
      if (conditionFilter === "gender_any" && post.gender_pref !== "any") return false;
      if (conditionFilter === "female" && post.gender_pref !== "female") return false;
      if (conditionFilter === "male" && post.gender_pref !== "male") return false;
      return true;
    })
    .sort((a, b) => {
      if (sortFilter === "meet_soon") {
        return new Date(a.meet_at).getTime() - new Date(b.meet_at).getTime();
      }
      if (sortFilter === "meet_late") {
        return new Date(b.meet_at).getTime() - new Date(a.meet_at).getTime();
      }
      if (sortFilter === "vacancy") {
        return (b.capacity - b.approved_count) - (a.capacity - a.approved_count);
      }
      return 0;
    });
  const hasLocalFilters =
    regionFilter !== "ALL" || periodFilter !== "all" || conditionFilter !== "all";
  const displayedPostCount = hasLocalFilters ? displayedPosts.length : postsTotal;

  return (
    <div className="space-y-4 px-4 py-4">
      {/* 히어로 */}
      <TabPageHero
        title={
          <>
            같이 <span className="text-brand">놀다가!</span>
          </>
        }
        subtitle="같은 축제를 즐길 동행을 찾아보세요."
        aside={
          <div className="flex items-center gap-1.5">
          <Link
            href="/chats"
            className="inline-flex items-center gap-1 rounded-chip border border-line-light bg-surface px-3 py-2 text-xs font-bold text-ink shadow-sm hover:border-brand/40 hover:text-brand"
          >
            <MessageCircle className="h-3.5 w-3.5 text-brand" aria-hidden="true" />
            <span>채팅</span>
          </Link>
          <button
            type="button"
            onClick={() => {
              if (!signedIn) {
                setLoginPromptDesc("동행 모집 글을 작성하려면 로그인해 주세요.");
                setLoginPromptOpen(true);
                return;
              }
              const nextFestivalId = selectedFestivalId || festivals[0]?.festival_id || "";
              const nextFestival = festivals.find(
                (festival) => festival.festival_id === nextFestivalId,
              );
              selectFormFestival(nextFestivalId);
              setFestivalSearch(nextFestival?.name ?? "");
              setFormError(null);
              setWriteOpen(true);
            }}
            className="inline-flex items-center gap-1 rounded-chip bg-brand px-3.5 py-2 text-xs font-extrabold text-surface shadow-sm hover:opacity-90"
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            <span>모집 글쓰기</span>
          </button>
          </div>
        }
      />

      {/* 세그먼트 탭 */}
      <div
        role="tablist"
        aria-label="동행 메뉴"
        className="grid grid-cols-2 rounded-chip border border-line-light bg-surface p-1 shadow-sm"
      >
        <button
          type="button"
          role="tab"
          aria-selected={tab === "browse"}
          onClick={() => setTab("browse")}
          className={`flex items-center justify-center gap-1.5 rounded-chip py-2.5 text-sm font-extrabold transition-colors ${
            tab === "browse"
              ? "bg-brand text-surface shadow-sm"
              : "text-ink/75 hover:text-brand"
          }`}
        >
          <Users className="h-4 w-4" aria-hidden="true" />
          <span>동행 모집 찾기</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "mine"}
          onClick={() => setTab("mine")}
          className={`flex items-center justify-center gap-1.5 rounded-chip py-2.5 text-sm font-extrabold transition-colors ${
            tab === "mine"
              ? "bg-brand text-surface shadow-sm"
              : "text-ink/75 hover:text-brand"
          }`}
        >
          <MessageCircle className="h-4 w-4" aria-hidden="true" />
          <span>내 동행</span>
        </button>
      </div>

      {tab === "browse" ? (
        <section className="space-y-3">
          {/* 축제 선택 & 상태 필터 */}
          {festivalsLoading ? (
            <div role="status" className="h-11 animate-pulse rounded-input bg-surface-muted" />
          ) : festivalsError ? (
            <div className="flex items-center justify-between gap-2 rounded-card border border-line-light bg-surface px-4 py-3 text-xs">
              <p role="alert" className="font-semibold text-ink">
                {festivalsError}
              </p>
              <button
                type="button"
                onClick={() => setFestivalsTick((v) => v + 1)}
                className="shrink-0 rounded-chip bg-brand px-3 py-1.5 font-bold text-surface"
              >
                다시 시도
              </button>
            </div>
          ) : festivals.length === 0 ? (
            <div className="rounded-card border border-line-light bg-surface px-4 py-8 text-center text-sm text-muted">
              선택할 수 있는 축제가 없어요.
            </div>
          ) : (
            <>
              <div>
                <label
                  htmlFor="companion-festival-search"
                  className="mb-1.5 block text-xs font-bold text-muted"
                >
                  축제 검색
                </label>
                <div className="relative mb-2">
                  <Search
                    className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
                    aria-hidden="true"
                  />
                  <input
                    id="companion-festival-search"
                    type="search"
                    value={browseFestivalSearch}
                    onChange={(event) => {
                      setBrowseFestivalSearch(event.target.value);
                      setSelectedFestivalId("");
                    }}
                    placeholder="축제명·장소 검색"
                    className="h-11 w-full rounded-input border border-line-light bg-surface py-2 pl-11 pr-4 text-sm text-ink shadow-sm placeholder:text-muted focus:border-brand focus:outline-none"
                  />
                </div>
                <label
                  htmlFor="companion-festival-select"
                  className="mb-1.5 block text-xs font-bold text-muted"
                >
                  축제 선택
                </label>
                <select
                  id="companion-festival-select"
                  value={selectedFestivalId}
                  onChange={(event) => {
                    setSelectedFestivalId(event.target.value);
                    setBrowseFestivalSearch("");
                  }}
                  className="h-11 w-full rounded-input border border-line-light bg-surface px-4 text-sm font-semibold text-ink shadow-sm focus:border-brand focus:outline-none"
                >
                  <option value="">전체 축제</option>
                  {browseFestivalOptions.map((festival) => (
                    <option key={festival.festival_id} value={festival.festival_id}>
                      {festival.name}{festival.venue_name ? ` · ${festival.venue_name}` : ""}
                    </option>
                  ))}
                </select>
                {normalizedBrowseFestivalSearch && matchingBrowseFestivals.length === 0 ? (
                  <p className="mt-1.5 text-xs text-muted">
                    검색 결과가 없어요. 현재 선택한 축제는 유지됩니다.
                  </p>
                ) : null}
              </div>

              <div className="space-y-2 py-1 sm:flex sm:items-center sm:gap-1.5 sm:space-y-0">
                <div
                  role="group"
                  aria-label="모집 상태"
                  className="grid w-full grid-cols-5 gap-1 sm:flex sm:w-auto sm:items-center sm:gap-1.5"
                >
                  {STATUS_TABS.map((item) => {
                    const active = statusFilter === item.value;
                    return (
                      <button
                        key={item.value}
                        type="button"
                        aria-pressed={active}
                        onClick={() => setStatusFilter(item.value)}
                        className={
                          active
                            ? "min-w-0 rounded-chip bg-brand px-1.5 py-1.5 text-[11px] font-bold text-surface sm:shrink-0 sm:px-3.5 sm:text-xs"
                            : "min-w-0 rounded-chip border border-line-light bg-surface px-1.5 py-1.5 text-[11px] font-semibold text-muted hover:text-ink sm:shrink-0 sm:px-3.5 sm:text-xs"
                        }
                      >
                        {item.label}
                      </button>
                    );
                  })}
                </div>
                <span
                  className="mx-1 hidden h-5 w-px shrink-0 bg-line-light sm:block"
                  aria-hidden="true"
                />
                <div className="grid w-full grid-cols-4 gap-1 sm:flex sm:w-auto sm:items-center sm:gap-1.5">
                  <label className="sr-only" htmlFor="companion-region-filter">지역</label>
                  <select
                    id="companion-region-filter"
                    value={regionFilter}
                    onChange={(event) => setRegionFilter(event.target.value as RegionFilter)}
                    className="h-8 min-w-0 w-full rounded-chip border border-brand/20 bg-brand/5 px-1.5 text-[11px] font-semibold text-ink focus:border-brand focus:outline-none sm:w-auto sm:shrink-0 sm:px-3 sm:text-xs"
                  >
                    {REGION_OPTIONS.map((option) => (
                      <option key={option.code} value={option.code}>
                        {option.code === "ALL" ? "지역별" : getRegionLabel(option.code)}
                      </option>
                    ))}
                  </select>
                  <label className="sr-only" htmlFor="companion-period-filter">기간</label>
                  <select
                    id="companion-period-filter"
                    value={periodFilter}
                    onChange={(event) => setPeriodFilter(event.target.value as PeriodFilter)}
                    className="h-8 min-w-0 w-full rounded-chip border border-brand/20 bg-brand/5 px-1 text-[11px] font-semibold text-ink focus:border-brand focus:outline-none sm:w-auto sm:shrink-0 sm:px-3 sm:text-xs"
                  >
                    <option value="all">기간별</option>
                    <option value="today">오늘</option>
                    <option value="week">7일 이내</option>
                    <option value="month">30일 이내</option>
                  </select>
                  <label className="sr-only" htmlFor="companion-condition-filter">모집 조건</label>
                  <select
                    id="companion-condition-filter"
                    value={conditionFilter}
                    onChange={(event) => setConditionFilter(event.target.value as ConditionFilter)}
                    className="h-8 min-w-0 w-full rounded-chip border border-brand/20 bg-brand/5 px-1.5 text-[11px] font-semibold text-ink focus:border-brand focus:outline-none sm:w-auto sm:shrink-0 sm:px-3 sm:text-xs"
                  >
                    <option value="all">조건별</option>
                    <option value="age_any">연령 무관</option>
                    <option value="gender_any">성별 무관</option>
                    <option value="female">여성 선호</option>
                    <option value="male">남성 선호</option>
                  </select>
                  <label className="sr-only" htmlFor="companion-sort-filter">정렬</label>
                  <select
                    id="companion-sort-filter"
                    value={sortFilter}
                    onChange={(event) => setSortFilter(event.target.value as SortFilter)}
                    className="h-8 min-w-0 w-full rounded-chip border border-brand/20 bg-brand/5 px-1 text-[11px] font-semibold text-ink focus:border-brand focus:outline-none sm:w-auto sm:shrink-0 sm:px-3 sm:text-xs"
                  >
                    <option value="latest">최신순</option>
                    <option value="meet_soon">만남 임박순</option>
                    <option value="meet_late">만남 날짜순</option>
                    <option value="vacancy">남은 자리순</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <h2 className="flex items-center gap-2 text-base font-extrabold text-ink">
                  <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
                  <span>
                    {selectedFestival
                      ? `${selectedFestival.name} 동행`
                      : statusFilter === "open"
                        ? "지금 모집 중인 동행"
                        : "동행 모집글"}
                  </span>
                </h2>
                {!postsLoading && !postsError ? (
                  <span className="text-xs font-semibold text-muted">
                    총 {displayedPostCount}개의 모집글
                  </span>
                ) : null}
              </div>

              {postsLoading ? (
                <div aria-label="동행 모집 글 불러오는 중" className="space-y-2.5">
                  {[0, 1, 2].map((idx) => (
                    <div
                      key={idx}
                      className="h-32 animate-pulse rounded-card border border-line-light bg-surface-muted/60"
                    />
                  ))}
                </div>
              ) : postsError ? (
                <div className="flex flex-col items-center justify-center gap-3 rounded-card border border-line-light bg-surface px-4 py-10 text-center">
                  <p role="alert" className="text-sm font-semibold text-ink">
                    {postsError}
                  </p>
                  <button
                    type="button"
                    onClick={() => setPostsTick((v) => v + 1)}
                    className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
                  >
                    <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>다시 시도</span>
                  </button>
                </div>
              ) : displayedPosts.length === 0 ? (
                <div className="rounded-card border border-line-light bg-surface px-4 py-10 text-center">
                  <p className="text-sm font-bold text-ink">
                    아직 등록된 동행 모집 글이 없어요
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    먼저 모집 글을 올려 함께 즐길 동행을 찾아보세요.
                  </p>
                </div>
              ) : (
                <ul className="grid gap-3 lg:grid-cols-2">
                  {displayedPosts.map((post) => {
                    const statusMeta = POST_STATUS_META[post.status];
                    const isFull =
                      post.status === "full" || post.approved_count >= post.capacity;
                    return (
                      <li
                        key={post.post_id}
                        className="overflow-hidden rounded-card-lg border border-line-light bg-surface p-3 shadow-card transition-shadow hover:shadow-md"
                      >
                        <div className="flex min-w-0 gap-3">
                          <Link
                            href={`/festivals/${encodeURIComponent(post.festival_id)}`}
                            className="relative h-32 w-28 shrink-0 overflow-hidden rounded-card bg-surface-soft sm:h-36 sm:w-36"
                            aria-label={`${post.festival_name} 축제 상세보기`}
                          >
                            {post.festival_thumbnail_url ? (
                              <Image
                                src={post.festival_thumbnail_url}
                                alt={post.festival_name}
                                fill
                                sizes="(max-width: 639px) 112px, 144px"
                                unoptimized
                                className="object-cover"
                              />
                            ) : (
                              <FestivalImagePlaceholder />
                            )}
                          </Link>

                          <div className="min-w-0 flex-1">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <Link
                                  href={`/festivals/${encodeURIComponent(post.festival_id)}`}
                                  className="block truncate text-sm font-black text-brand hover:underline"
                                >
                                  {post.festival_name}
                                </Link>
                                <span className="mt-1 inline-flex rounded-chip bg-brand/10 px-2 py-0.5 text-[10px] font-extrabold text-brand">
                                  {statusMeta.label}
                                </span>
                              </div>
                              <span className="shrink-0 text-[10px] font-semibold text-muted">
                                {post.author_display_name ?? "익명"}
                              </span>
                            </div>

                            <p className="mt-2 line-clamp-2 text-sm font-extrabold leading-snug text-ink">
                              {post.memo || "함께 축제를 즐길 동행을 구해요!"}
                            </p>

                            <div className="mt-2 space-y-1 text-[11px] font-semibold text-muted">
                              <span className="flex items-center gap-1">
                                <CalendarDays className="h-3.5 w-3.5 text-ink" aria-hidden="true" />
                                {formatKstDateTime(post.meet_at)}
                              </span>
                              <span className="flex min-w-0 items-center gap-1">
                                <MapPin className="h-3.5 w-3.5 shrink-0 text-ink" aria-hidden="true" />
                                <span className="truncate">
                                  {post.festival_venue_name ?? "장소 미정"}
                                </span>
                              </span>
                            </div>

                            <div className="mt-2 flex flex-wrap items-center gap-1.5">
                              <span
                                className={`inline-flex items-center gap-1 text-xs font-extrabold ${
                                  isFull ? "text-muted" : "text-brand"
                                }`}
                              >
                                <Users className="h-3.5 w-3.5" aria-hidden="true" />
                                <span>{post.approved_count} / {post.capacity}명</span>
                              </span>
                              <span className="rounded-chip bg-surface-soft px-2 py-0.5 text-[10px] font-semibold text-ink">
                                {getAgePrefLabel(post.age_pref)} · {getGenderPrefLabel(post.gender_pref)}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="mt-3 flex justify-end">
                          <Link
                            href={`/companions/${encodeURIComponent(post.post_id)}`}
                            className={`rounded-chip px-4 py-1.5 text-xs font-extrabold shadow-sm transition-opacity hover:opacity-90 ${
                              post.status === "open"
                                ? "bg-brand text-surface"
                                : "border border-line-light bg-surface text-ink"
                            }`}
                          >
                            {post.status === "open" ? "참여 신청" : "자세히 보기"}
                          </Link>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </>
          )}
        </section>
      ) : !signedIn ? (
        <section className="rounded-card border border-line-light bg-surface px-4 py-10 text-center">
          <p className="text-sm font-bold text-ink">
            내 동행 내역을 보려면 로그인이 필요해요
          </p>
          <p className="mt-1 text-xs text-muted">
            내가 작성한 모집 글과 신청 상태를 한눈에 확인할 수 있어요.
          </p>
          <Link
            href="/auth/login?next=%2Fcompanions%3Ftab%3Dmine"
            className="mt-4 inline-flex rounded-chip bg-brand px-5 py-2.5 text-xs font-extrabold text-surface shadow-sm"
          >
            로그인하기
          </Link>
        </section>
      ) : (
        <section className="space-y-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              aria-pressed={mineSubTab === "posts"}
              onClick={() => setMineSubTab("posts")}
              className={
                mineSubTab === "posts"
                  ? "rounded-chip bg-brand px-3.5 py-1.5 text-xs font-bold text-surface"
                  : "rounded-chip border border-line-light bg-surface px-3.5 py-1.5 text-xs font-semibold text-muted"
              }
            >
              내가 쓴 글
            </button>
            <button
              type="button"
              aria-pressed={mineSubTab === "applications"}
              onClick={() => setMineSubTab("applications")}
              className={
                mineSubTab === "applications"
                  ? "rounded-chip bg-brand px-3.5 py-1.5 text-xs font-bold text-surface"
                  : "rounded-chip border border-line-light bg-surface px-3.5 py-1.5 text-xs font-semibold text-muted"
              }
            >
              보낸 신청
            </button>
          </div>

          {mineLoading ? (
            <div role="status" className="h-28 animate-pulse rounded-card bg-surface-muted" />
          ) : mineError ? (
            <div className="flex flex-col items-center gap-3 rounded-card border border-line-light bg-surface px-4 py-8 text-center">
              <p role="alert" className="text-sm font-semibold text-ink">
                {mineError}
              </p>
              <button
                type="button"
                onClick={() => setMineTick((v) => v + 1)}
                className="rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
              >
                다시 시도
              </button>
            </div>
          ) : mineSubTab === "posts" ? (
            myPosts.length === 0 ? (
              <div className="rounded-card border border-line-light bg-surface px-4 py-10 text-center text-sm text-muted">
                작성한 동행 모집 글이 없어요.
              </div>
            ) : (
              <ul className="space-y-2.5">
                {myPosts.map((post) => {
                  const statusMeta = POST_STATUS_META[post.status];
                  const postFestival = festivals.find(
                    (festival) => festival.festival_id === post.festival_id,
                  );
                  return (
                    <li
                      key={post.post_id}
                      className="rounded-card border border-line-light bg-surface p-4 shadow-sm"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={`rounded-chip px-2.5 py-0.5 text-[11px] font-extrabold ${statusMeta.className}`}
                        >
                          {statusMeta.label}
                        </span>
                        <span className="text-xs font-extrabold text-brand">
                          {post.approved_count} / {post.capacity}명
                        </span>
                      </div>
                      <Link
                        href={`/festivals/${encodeURIComponent(post.festival_id)}`}
                        className="mt-2 inline-flex max-w-full items-center gap-1.5 text-sm font-extrabold text-brand hover:underline"
                      >
                        <CalendarDays className="h-4 w-4 shrink-0" aria-hidden="true" />
                        <span className="truncate">
                          {postFestival?.name ?? "선택한 축제"}
                        </span>
                      </Link>
                      <p className="mt-1.5 line-clamp-2 text-sm font-bold text-ink">
                        {post.memo || "내용 없음"}
                      </p>
                      <div className="mt-2 flex items-center justify-between text-xs text-muted">
                        <span>{formatKstDateTime(post.meet_at)}</span>
                        <Link
                          href={`/companions/${encodeURIComponent(post.post_id)}`}
                          className="font-bold text-brand hover:underline"
                        >
                          관리하기
                        </Link>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )
          ) : myApps.length === 0 ? (
            <div className="rounded-card border border-line-light bg-surface px-4 py-10 text-center text-sm text-muted">
              신청한 동행 내역이 없어요.
            </div>
          ) : (
            <ul className="space-y-2.5">
              {myApps.map((app) => {
                const post = myAppPosts[app.post_id];
                const feedPost = myAppFeedPosts[app.post_id];
                return (
                  <li
                    key={app.application_id}
                    className="rounded-card border border-line-light bg-surface p-4 shadow-sm"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="rounded-chip bg-surface-soft px-2.5 py-0.5 text-[11px] font-extrabold text-brand">
                        {APPLICATION_STATUS_LABEL[app.status]}
                      </span>
                      <span className="text-[11px] text-muted">
                        신청 {formatKstDateTime(app.created_at)}
                      </span>
                    </div>

                    {feedPost ? (
                      <Link
                        href={`/festivals/${encodeURIComponent(feedPost.festival_id)}`}
                        className="mt-2 inline-flex max-w-full items-center gap-1.5 text-sm font-extrabold text-brand hover:underline"
                      >
                        <CalendarDays className="h-4 w-4 shrink-0" aria-hidden="true" />
                        <span className="truncate">{feedPost.festival_name}</span>
                      </Link>
                    ) : null}

                    <p className="mt-1.5 line-clamp-2 text-sm font-bold text-ink">
                      {post?.memo || feedPost?.memo || "모집 내용을 확인해 주세요."}
                    </p>
                    {post ? (
                      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                        <span>작성자 {post.author_display_name ?? "동행 모집자"}</span>
                        <span>만남 {formatKstDateTime(post.meet_at)}</span>
                      </div>
                    ) : null}
                    {app.message ? (
                      <p className="mt-2 rounded-xl bg-surface-soft px-3 py-2 text-xs text-ink">
                        <span className="font-bold text-muted">내 신청 메시지 · </span>
                        {app.message}
                      </p>
                    ) : null}
                    <div className="mt-3 flex items-center justify-end gap-2">
                      {app.status === "pending" ? (
                        <button
                          type="button"
                          disabled={cancellingAppId === app.application_id}
                          onClick={() => void handleCancelMyApplication(app.application_id)}
                          className="rounded-chip border border-line-light px-3 py-1.5 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
                        >
                          {cancellingAppId === app.application_id ? "취소 중…" : "신청 취소"}
                        </button>
                      ) : null}
                      <Link
                        href={`/companions/${encodeURIComponent(app.post_id)}`}
                        className="rounded-chip bg-brand px-3.5 py-1.5 text-xs font-extrabold text-surface"
                      >
                        글 보기
                      </Link>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}

      {/* 동행 모집 글 작성 모달 */}
      {writeOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-ink/45 backdrop-blur-[1px]"
          onClick={() => setWriteOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="write-companion-title"
            className="max-h-[90dvh] w-full max-w-[480px] overflow-y-auto rounded-t-[24px] bg-surface px-5 pb-7 pt-4 shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 id="write-companion-title" className="text-base font-black text-ink">
                동행 모집 글 작성
              </h2>
              <button
                type="button"
                onClick={() => setWriteOpen(false)}
                aria-label="닫기"
                className="flex h-8 w-8 items-center justify-center rounded-chip text-muted hover:bg-surface-muted"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <form onSubmit={handleCreatePost} className="space-y-3.5">
              <div>
                <label
                  htmlFor="write-festival-search"
                  className="mb-1 block text-xs font-bold text-ink"
                >
                  축제 검색
                </label>
                <div className="relative">
                  <Search
                    className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
                    aria-hidden="true"
                  />
                  <input
                    id="write-festival-search"
                    type="search"
                    value={festivalSearch}
                    role="combobox"
                    aria-autocomplete="list"
                    aria-controls="write-festival-results"
                    aria-expanded={visibleFormFestivalResults.length > 0}
                    aria-invalid={!formFestivalId && festivalSearch.length > 0}
                    required
                    onFocus={(event) => event.currentTarget.select()}
                    onChange={(event) => {
                      setFestivalSearch(event.target.value);
                      setFormFestivalId("");
                      setMeetAt("");
                      setFormError(null);
                    }}
                    placeholder="축제명·장소 검색"
                    className="h-11 w-full rounded-input border border-line-light bg-surface py-2 pl-10 pr-3.5 text-sm text-ink placeholder:text-muted focus:border-brand focus:outline-none"
                  />
                  {normalizedFestivalSearch && !isFormFestivalSelectionCurrent ? (
                    <div
                      id="write-festival-results"
                      role="listbox"
                      aria-label="축제 검색 결과"
                      className="absolute left-0 right-0 top-[calc(100%+6px)] z-20 max-h-56 overflow-y-auto rounded-card border border-line-light bg-surface py-1.5 shadow-lg"
                    >
                      {visibleFormFestivalResults.length > 0 ? (
                        visibleFormFestivalResults.map((festival) => (
                          <button
                            key={festival.festival_id}
                            type="button"
                            role="option"
                            aria-selected="false"
                            onClick={() => {
                              selectFormFestival(festival.festival_id);
                              setFestivalSearch(festival.name);
                              setFormError(null);
                            }}
                            className="flex w-full items-start gap-2.5 px-3.5 py-2.5 text-left hover:bg-surface-muted focus:bg-surface-muted focus:outline-none"
                          >
                            <MapPin
                              className="mt-0.5 h-4 w-4 shrink-0 text-brand"
                              aria-hidden="true"
                            />
                            <span className="min-w-0">
                              <span className="block truncate text-sm font-extrabold text-ink">
                                {festival.name}
                              </span>
                              <span className="mt-0.5 block truncate text-xs text-muted">
                                {getRegionLabel(festival.region_code)}
                                {festival.venue_name ? ` · ${festival.venue_name}` : " · 장소 미정"}
                              </span>
                            </span>
                          </button>
                        ))
                      ) : (
                        <p className="px-3.5 py-4 text-center text-xs text-muted">
                          검색 결과가 없어요.
                        </p>
                      )}
                    </div>
                  ) : null}
                </div>
                {selectedFormFestival && isFormFestivalSelectionCurrent ? (
                  <p className="mt-1.5 flex items-center gap-1 text-xs text-muted">
                    <MapPin className="h-3.5 w-3.5 text-brand" aria-hidden="true" />
                    <span className="truncate">
                      선택됨 · {selectedFormFestival.venue_name || "장소 정보 없음"}
                    </span>
                  </p>
                ) : null}
              </div>

              <div>
                <label
                  htmlFor="write-meet-at"
                  className="mb-1 block text-xs font-bold text-ink"
                >
                  만남 일시 (축제 기간 내 미래 시각)
                </label>
                <input
                  id="write-meet-at"
                  type="datetime-local"
                  required
                  value={meetAt}
                  onChange={(e) => setMeetAt(e.target.value)}
                  min={selectedFormFestival?.start_date ? `${selectedFormFestival.start_date}T00:00` : undefined}
                  max={selectedFormFestival?.end_date ? `${selectedFormFestival.end_date}T23:59` : undefined}
                  className="h-11 w-full rounded-input border border-line-light bg-surface px-3.5 text-sm text-ink focus:border-brand focus:outline-none"
                />
                {selectedFormFestival ? (
                  <p className="mt-1.5 text-xs text-muted">
                    {selectedFormFestival.event_status === "ongoing"
                      ? "진행 중인 축제라 내일 오후 6시로 자동 설정했어요."
                      : "예정된 축제라 시작일 오후 6시로 자동 설정했어요."}
                    {" "}필요하면 축제 기간 안에서 변경할 수 있어요.
                  </p>
                ) : null}
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label
                    htmlFor="write-capacity"
                    className="mb-1 block text-xs font-bold text-ink"
                  >
                    정원 (본인 제외)
                  </label>
                  <input
                    id="write-capacity"
                    type="number"
                    min={1}
                    max={10}
                    required
                    value={capacity}
                    onChange={(e) => setCapacity(Number(e.target.value))}
                    className="h-10 w-full rounded-input border border-line-light bg-surface px-3 text-sm text-ink focus:border-brand focus:outline-none"
                  />
                </div>
                <div>
                  <label
                    htmlFor="write-age-pref"
                    className="mb-1 block text-xs font-bold text-ink"
                  >
                    선호 연령
                  </label>
                  <select
                    id="write-age-pref"
                    value={agePref}
                    onChange={(e) => setAgePref(e.target.value as AgePreference)}
                    className="h-10 w-full rounded-input border border-line-light bg-surface px-2.5 text-xs font-semibold text-ink focus:border-brand focus:outline-none"
                  >
                    {AGE_PREF_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label
                    htmlFor="write-gender-pref"
                    className="mb-1 block text-xs font-bold text-ink"
                  >
                    선호 성별
                  </label>
                  <select
                    id="write-gender-pref"
                    value={genderPref}
                    onChange={(e) => setGenderPref(e.target.value as GenderPreference)}
                    className="h-10 w-full rounded-input border border-line-light bg-surface px-2.5 text-xs font-semibold text-ink focus:border-brand focus:outline-none"
                  >
                    {GENDER_PREF_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label
                  htmlFor="write-memo"
                  className="mb-1 block text-xs font-bold text-ink"
                >
                  모집 안내 (선택, 500자 이내)
                </label>
                <textarea
                  id="write-memo"
                  rows={3}
                  maxLength={500}
                  value={memo}
                  onChange={(e) => setMemo(e.target.value)}
                  placeholder="함께 즐길 계획이나 간단한 소개를 적어 주세요."
                  className="w-full rounded-card border border-line-light bg-surface p-3 text-sm text-ink placeholder:text-muted focus:border-brand focus:outline-none"
                />
              </div>

              {formError ? (
                <p role="alert" className="text-xs font-semibold text-brand">
                  {formError}
                </p>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-chip bg-brand py-3 text-sm font-extrabold text-surface shadow-sm transition-opacity hover:opacity-90 disabled:opacity-60"
              >
                {submitting ? "등록 중…" : "동행 모집 등록"}
              </button>
            </form>
          </div>
        </div>
      ) : null}

      <LoginPromptSheet
        open={loginPromptOpen}
        onClose={() => setLoginPromptOpen(false)}
        nextPath="/companions"
        description={loginPromptDesc}
      />
    </div>
  );
}

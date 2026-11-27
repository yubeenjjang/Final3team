"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  CalendarDays,
  MessageCircle,
  Plus,
  RotateCcw,
  Search,
  Users,
  X,
} from "lucide-react";
import { LoginPromptSheet } from "@/components/LoginPromptSheet";
import { TabPageHero } from "@/components/TabPageHero";
import { handleAuthError, useIsSignedIn } from "@/components/RequireAuth";
import { listFestivals, type FestivalListItem } from "@/features/festivals/explore/api";
import { ApiError } from "@/lib/api/client";
import {
  createCompanionPost,
  decideCompanionApplication,
  listCompanionPosts,
  listMyCompanionApplications,
  listMyCompanionPosts,
  type AgePreference,
  type CompanionPostItem,
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

const STATUS_TABS: { value: PostStatus; label: string }[] = [
  { value: "open", label: "모집 중" },
  { value: "full", label: "정원 마감" },
  { value: "ended", label: "종료" },
  { value: "cancelled", label: "취소" },
];

const DEFAULT_MEETING_TIME = "18:00";

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
  let meetingDate = festival.event_status === "ongoing" ? tomorrow : festival.start_date;

  // 축제가 오늘 끝나는 경우처럼 내일이 기간 밖이면 종료일 안으로 맞춘다.
  if (meetingDate > festival.end_date) meetingDate = festival.end_date;
  if (meetingDate < today) meetingDate = today;

  return `${meetingDate}T${DEFAULT_MEETING_TIME}`;
}

export interface CompanionsViewProps {
  initialFestivalId?: string;
  initialTab?: "browse" | "mine";
}

export function CompanionsView({
  initialFestivalId,
  initialTab = "browse",
}: CompanionsViewProps) {
  const router = useRouter();
  const routerRef = useRef(router);
  useEffect(() => {
    routerRef.current = router;
  }, [router]);
  const signedIn = useIsSignedIn();

  const [tab, setTab] = useState<"browse" | "mine">(initialTab);
  const [festivals, setFestivals] = useState<FestivalListItem[]>([]);
  const [festivalsLoading, setFestivalsLoading] = useState(true);
  const [festivalsError, setFestivalsError] = useState<string | null>(null);
  const [selectedFestivalId, setSelectedFestivalId] = useState(initialFestivalId ?? "");

  const [statusFilter, setStatusFilter] = useState<PostStatus>("open");
  const [posts, setPosts] = useState<CompanionPostItem[]>([]);
  const [postsLoading, setPostsLoading] = useState(false);
  const [postsError, setPostsError] = useState<string | null>(null);
  const [postsTick, setPostsTick] = useState(0);

  const [mineSubTab, setMineSubTab] = useState<"posts" | "applications">("posts");
  const [myPosts, setMyPosts] = useState<MyCompanionPostItem[]>([]);
  const [myApps, setMyApps] = useState<MyCompanionApplicationItem[]>([]);
  const [mineLoading, setMineLoading] = useState(false);
  const [mineError, setMineError] = useState<string | null>(null);
  const [mineTick, setMineTick] = useState(0);
  const [cancellingAppId, setCancellingAppId] = useState<string | null>(null);

  const [writeOpen, setWriteOpen] = useState(false);
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
          return res.items[0]?.festival_id ?? "";
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
    if (!writeOpen) return;
    const festival = festivals.find((item) => item.festival_id === formFestivalId);
    if (festival) {
      setMeetAt(getDefaultCompanionMeetAt(festival));
    }
  }, [festivals, formFestivalId, writeOpen]);

  useEffect(() => {
    if (tab !== "browse" || !selectedFestivalId) {
      return;
    }
    const controller = new AbortController();
    async function load() {
      setPostsLoading(true);
      setPostsError(null);
      try {
        const res = await listCompanionPosts(
          selectedFestivalId,
          { status: statusFilter, page: 1 },
          controller.signal,
        );
        if (!controller.signal.aborted) {
          setPosts(res.items);
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
  }, [tab, selectedFestivalId, statusFilter, postsTick]);

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
          if (!controller.signal.aborted) setMyApps(res.items);
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
  const formFestivalOptions =
    selectedFormFestival &&
    !matchingFormFestivals.some((festival) => festival.festival_id === selectedFormFestival.festival_id)
      ? [selectedFormFestival, ...matchingFormFestivals]
      : matchingFormFestivals;

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
              setFormFestivalId(selectedFestivalId || festivals[0]?.festival_id || "");
              setFestivalSearch("");
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
                  htmlFor="companion-festival-select"
                  className="mb-1.5 block text-xs font-bold text-muted"
                >
                  축제 선택
                </label>
                <select
                  id="companion-festival-select"
                  value={selectedFestivalId}
                  onChange={(event) => setSelectedFestivalId(event.target.value)}
                  className="h-11 w-full rounded-input border border-line-light bg-surface px-4 text-sm font-semibold text-ink shadow-sm focus:border-brand focus:outline-none"
                >
                  {festivals.map((festival) => (
                    <option key={festival.festival_id} value={festival.festival_id}>
                      {festival.name}
                    </option>
                  ))}
                </select>
              </div>

              <div
                role="group"
                aria-label="모집 상태"
                className="flex items-center gap-1.5 overflow-x-auto py-0.5"
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
                          ? "shrink-0 rounded-chip bg-brand px-3.5 py-1.5 text-xs font-bold text-surface"
                          : "shrink-0 rounded-chip border border-line-light bg-surface px-3.5 py-1.5 text-xs font-semibold text-muted hover:text-ink"
                      }
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>

              <div className="flex items-center justify-between pt-1">
                <h2 className="flex items-center gap-2 text-base font-extrabold text-ink">
                  <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
                  <span>{selectedFestival?.name ?? "동행 모집 글"}</span>
                </h2>
                {!postsLoading && !postsError ? (
                  <span className="text-xs font-semibold text-muted">
                    {posts.length}건
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
              ) : posts.length === 0 ? (
                <div className="rounded-card border border-line-light bg-surface px-4 py-10 text-center">
                  <p className="text-sm font-bold text-ink">
                    아직 등록된 동행 모집 글이 없어요
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    먼저 모집 글을 올려 함께 즐길 동행을 찾아보세요.
                  </p>
                </div>
              ) : (
                <ul className="space-y-3">
                  {posts.map((post) => {
                    const statusMeta = POST_STATUS_META[post.status];
                    const isFull =
                      post.status === "full" || post.approved_count >= post.capacity;
                    return (
                      <li
                        key={post.post_id}
                        className="rounded-card border border-line-light bg-surface p-4 shadow-sm transition-shadow hover:shadow-md"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span
                              className={`rounded-chip px-2.5 py-0.5 text-[11px] font-extrabold ${statusMeta.className}`}
                            >
                              {statusMeta.label}
                            </span>
                            <span className="text-xs font-bold text-ink">
                              {post.author_display_name ?? "알 수 없음"}
                            </span>
                          </div>
                          <span
                            className={`inline-flex items-center gap-1 text-xs font-extrabold ${
                              isFull ? "text-muted" : "text-brand"
                            }`}
                          >
                            <Users className="h-3.5 w-3.5" aria-hidden="true" />
                            <span>
                              {post.approved_count} / {post.capacity}명
                            </span>
                          </span>
                        </div>

                        <p className="mt-2 line-clamp-2 text-sm font-bold leading-snug text-ink">
                          {post.memo || "함께 축제를 즐길 동행을 구해요!"}
                        </p>

                        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
                          <span className="inline-flex items-center gap-1">
                            <CalendarDays
                              className="h-3.5 w-3.5 text-brand"
                              aria-hidden="true"
                            />
                            {formatKstDateTime(post.meet_at)}
                          </span>
                          <span className="rounded-chip bg-surface-soft/80 px-2.5 py-0.5 text-[11px] font-semibold text-ink">
                            {getAgePrefLabel(post.age_pref)} ·{" "}
                            {getGenderPrefLabel(post.gender_pref)}
                          </span>
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
                            {post.status === "open" ? "상세 · 참여 신청" : "자세히 보기"}
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
                      <p className="mt-2 line-clamp-2 text-sm font-bold text-ink">
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
              {myApps.map((app) => (
                <li
                  key={app.application_id}
                  className="rounded-card border border-line-light bg-surface p-4 shadow-sm"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded-chip bg-surface-soft px-2.5 py-0.5 text-[11px] font-extrabold text-brand">
                      {APPLICATION_STATUS_LABEL[app.status]}
                    </span>
                    <span className="text-[11px] text-muted">
                      {formatKstDateTime(app.created_at)}
                    </span>
                  </div>
                  {app.message ? (
                    <p className="mt-2 text-xs text-ink">{app.message}</p>
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
              ))}
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
                <div className="relative mb-2">
                  <Search
                    className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
                    aria-hidden="true"
                  />
                  <input
                    id="write-festival-search"
                    type="search"
                    value={festivalSearch}
                    onChange={(event) => setFestivalSearch(event.target.value)}
                    placeholder="축제명·장소 검색"
                    className="h-11 w-full rounded-input border border-line-light bg-surface py-2 pl-10 pr-3.5 text-sm text-ink placeholder:text-muted focus:border-brand focus:outline-none"
                  />
                </div>
                <label
                  htmlFor="write-festival"
                  className="mb-1 block text-xs font-bold text-ink"
                >
                  축제
                </label>
                <select
                  id="write-festival"
                  required
                  value={formFestivalId}
                  onChange={(e) => {
                    setFormFestivalId(e.target.value);
                    setFestivalSearch("");
                  }}
                  className="h-11 w-full rounded-input border border-line-light bg-surface px-3.5 text-sm text-ink focus:border-brand focus:outline-none"
                >
                  {formFestivalOptions.map((f) => (
                    <option key={f.festival_id} value={f.festival_id}>
                      {f.name}{f.venue_name ? ` · ${f.venue_name}` : ""}
                    </option>
                  ))}
                </select>
                {normalizedFestivalSearch && matchingFormFestivals.length === 0 ? (
                  <p className="mt-1.5 text-xs text-muted">
                    검색 결과가 없어요. 현재 선택한 축제는 유지됩니다.
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
                  min={selectedFormFestival ? `${selectedFormFestival.start_date}T00:00` : undefined}
                  max={selectedFormFestival ? `${selectedFormFestival.end_date}T23:59` : undefined}
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

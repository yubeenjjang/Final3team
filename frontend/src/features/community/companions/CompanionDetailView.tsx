"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowLeft,
  CalendarDays,
  Check,
  Lock,
  MapPin,
  MessageCircle,
  RotateCcw,
  Users,
  X,
} from "lucide-react";
import { KakaoMap } from "@/components/KakaoMap";
import { LoginPromptSheet } from "@/components/LoginPromptSheet";
import { handleAuthError, useIsSignedIn } from "@/components/RequireAuth";
import { ApiError } from "@/lib/api/client";
import { listChatRooms } from "@/features/community/chats/api";
import {
  applyToCompanionPost,
  changeCompanionPost,
  decideCompanionApplication,
  getCompanionPost,
  getMeetingPlace,
  isMeetingPlaceUndecided,
  listCompanionApplications,
  listMyCompanionApplications,
  listMyCompanionPosts,
  setMeetingPlace,
  type CompanionApplicationItem,
  type CompanionPostDetail,
  type MeetingPlaceResponse,
  type PostAction,
  type VisibleApplicationStatus,
} from "./api";
import {
  APPLICATION_STATUS_LABEL,
  formatKstDateTime,
  getAgePrefLabel,
  getGenderPrefLabel,
  POST_STATUS_META,
} from "./format";

export interface CompanionDetailViewProps {
  postId: string;
}

export function CompanionDetailView({ postId }: CompanionDetailViewProps) {
  const router = useRouter();
  const routerRef = useRef(router);
  useEffect(() => {
    routerRef.current = router;
  }, [router]);
  const signedIn = useIsSignedIn();

  const [post, setPost] = useState<CompanionPostDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const [isAuthor, setIsAuthor] = useState(false);
  const [myApplicationId, setMyApplicationId] = useState<string | null>(null);

  // Applicant apply form
  const [applyMessage, setApplyMessage] = useState("");
  const [applyBusy, setApplyBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [loginPromptOpen, setLoginPromptOpen] = useState(false);

  // Meeting place
  const [meetingPlace, setMeetingPlaceState] = useState<MeetingPlaceResponse | null>(null);
  const [meetingLoading, setMeetingLoading] = useState(false);
  const [meetingError, setMeetingError] = useState<string | null>(null);
  const [editPlaceOpen, setEditPlaceOpen] = useState(false);
  const [placeName, setPlaceName] = useState("");
  const [placeAddress, setPlaceAddress] = useState("");
  const [placeGuide, setPlaceGuide] = useState("");
  const [placeSaving, setPlaceSaving] = useState(false);

  // Author applications management
  const [applications, setApplications] = useState<CompanionApplicationItem[]>([]);
  const [appFilter, setAppFilter] = useState<VisibleApplicationStatus | "all">("all");
  const [appsLoading, setAppsLoading] = useState(false);
  const [appsError, setAppsError] = useState<string | null>(null);
  const [decidingId, setDecidingId] = useState<string | null>(null);
  const [postActionBusy, setPostActionBusy] = useState<PostAction | null>(null);
  const [chatOpening, setChatOpening] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setErrorMessage(null);
      try {
        const detail = await getCompanionPost(postId, controller.signal);
        if (!controller.signal.aborted) {
          setPost(detail);
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        setPost(null);
        setErrorMessage(
          error instanceof ApiError
            ? error.message
            : "동행 모집 글을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => controller.abort();
  }, [postId, reloadTick]);

  // Check author ownership & pending application ID when signed in
  useEffect(() => {
    if (!signedIn || !post) {
      return;
    }
    const controller = new AbortController();
    async function loadOwnership() {
      const [myPostsRes, myAppsRes] = await Promise.all([
        listMyCompanionPosts(controller.signal).catch(() => ({ items: [] })),
        listMyCompanionApplications(controller.signal).catch(() => ({ items: [] })),
      ]);
      if (controller.signal.aborted) return;
      const owns = myPostsRes.items.some((item) => item.post_id === post?.post_id);
      setIsAuthor(owns);
      const pendingApp = myAppsRes.items.find(
        (item) => item.post_id === post?.post_id && item.status === "pending",
      );
      setMyApplicationId(pendingApp?.application_id ?? null);
    }
    void loadOwnership();
    return () => controller.abort();
  }, [signedIn, post, reloadTick]);

  const effectiveIsAuthor = signedIn && Boolean(post) && isAuthor;
  const canSeeMeetingPlace =
    signedIn && (effectiveIsAuthor || post?.my_application_status === "approved");

  // Load meeting place only for author or approved participants
  useEffect(() => {
    if (!canSeeMeetingPlace || !post) {
      return;
    }
    const controller = new AbortController();
    async function loadMeetingPlace() {
      setMeetingLoading(true);
      setMeetingError(null);
      try {
        const res = await getMeetingPlace(post!.post_id, controller.signal);
        if (controller.signal.aborted) return;
        setMeetingPlaceState(res);
        if (!isMeetingPlaceUndecided(res)) {
          setPlaceName(res.name);
          setPlaceAddress(res.address ?? "");
          setPlaceGuide(res.guide ?? "");
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        if (handleAuthError(error)) {
          routerRef.current.replace(`/auth/login?next=${encodeURIComponent(`/companions/${postId}`)}`);
          return;
        }
        setMeetingError(
          error instanceof ApiError
            ? error.message
            : "만남 장소를 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setMeetingLoading(false);
        }
      }
    }
    void loadMeetingPlace();
    return () => controller.abort();
  }, [canSeeMeetingPlace, post, postId, reloadTick]);

  // Load applications for author
  useEffect(() => {
    if (!effectiveIsAuthor || !post) {
      return;
    }
    const controller = new AbortController();
    async function loadApplications() {
      setAppsLoading(true);
      setAppsError(null);
      try {
        const res = await listCompanionApplications(
          post!.post_id,
          appFilter === "all" ? undefined : appFilter,
          controller.signal,
        );
        if (!controller.signal.aborted) {
          setApplications(res.items);
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        if (handleAuthError(error)) {
          routerRef.current.replace(`/auth/login?next=${encodeURIComponent(`/companions/${postId}`)}`);
          return;
        }
        setAppsError(
          error instanceof ApiError
            ? error.message
            : "신청자 목록을 불러오지 못했어요.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setAppsLoading(false);
        }
      }
    }
    void loadApplications();
    return () => controller.abort();
  }, [effectiveIsAuthor, post, appFilter, postId, reloadTick]);

  async function handleApply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!signedIn) {
      setLoginPromptOpen(true);
      return;
    }
    if (applyBusy || !post) return;
    setApplyBusy(true);
    setActionError(null);
    setActionNotice(null);
    try {
      const created = await applyToCompanionPost(post.post_id, {
        message: applyMessage.trim() || null,
      });
      setMyApplicationId(created.application_id);
      setApplyMessage("");
      setActionNotice("동행 신청을 보냈어요. 작성자 승인을 기다려 주세요.");
      setReloadTick((v) => v + 1);
    } catch (error) {
      if (handleAuthError(error)) {
        router.replace(`/auth/login?next=${encodeURIComponent(`/companions/${postId}`)}`);
        return;
      }
      setActionError(
        error instanceof ApiError ? error.message : "동행 신청에 실패했어요.",
      );
    } finally {
      setApplyBusy(false);
    }
  }

  async function handleCancelOwnApplication() {
    if (!myApplicationId || applyBusy) return;
    setApplyBusy(true);
    setActionError(null);
    setActionNotice(null);
    try {
      await decideCompanionApplication(myApplicationId, "cancel");
      setMyApplicationId(null);
      setActionNotice("동행 신청을 취소했어요.");
      setReloadTick((v) => v + 1);
    } catch (error) {
      if (handleAuthError(error)) {
        router.replace(`/auth/login?next=${encodeURIComponent(`/companions/${postId}`)}`);
        return;
      }
      setActionError(
        error instanceof ApiError ? error.message : "신청 취소에 실패했어요.",
      );
    } finally {
      setApplyBusy(false);
    }
  }

  async function handleDecide(applicationId: string, action: "approve" | "reject") {
    if (decidingId) return;
    setDecidingId(applicationId);
    setAppsError(null);
    try {
      await decideCompanionApplication(applicationId, action);
      setActionNotice(
        action === "approve"
          ? "신청을 승인했어요. 동행 채팅방에 참여자가 합류해요."
          : "신청을 거절했어요.",
      );
      setReloadTick((v) => v + 1);
    } catch (error) {
      if (handleAuthError(error)) {
        router.replace(`/auth/login?next=${encodeURIComponent(`/companions/${postId}`)}`);
        return;
      }
      setAppsError(
        error instanceof ApiError ? error.message : "신청 처리에 실패했어요.",
      );
    } finally {
      setDecidingId(null);
    }
  }

  async function handleSaveMeetingPlace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!post || placeSaving || !placeName.trim()) return;
    setPlaceSaving(true);
    setMeetingError(null);
    try {
      await setMeetingPlace(post.post_id, {
        name: placeName.trim(),
        address: placeAddress.trim() || null,
        guide: placeGuide.trim() || null,
      });
      setEditPlaceOpen(false);
      setActionNotice("만남 장소를 저장했어요.");
      setReloadTick((v) => v + 1);
    } catch (error) {
      if (handleAuthError(error)) {
        router.replace(`/auth/login?next=${encodeURIComponent(`/companions/${postId}`)}`);
        return;
      }
      setMeetingError(
        error instanceof ApiError ? error.message : "만남 장소를 저장하지 못했어요.",
      );
    } finally {
      setPlaceSaving(false);
    }
  }

  async function handlePostAction(action: PostAction) {
    if (!post || postActionBusy) return;
    setPostActionBusy(action);
    setActionError(null);
    try {
      await changeCompanionPost(post.post_id, action);
      setActionNotice(
        action === "close"
          ? "모집을 마감했어요."
          : action === "end"
            ? "동행을 종료했어요."
            : "동행을 취소했어요.",
      );
      setReloadTick((v) => v + 1);
    } catch (error) {
      if (handleAuthError(error)) {
        router.replace(`/auth/login?next=${encodeURIComponent(`/companions/${postId}`)}`);
        return;
      }
      setActionError(
        error instanceof ApiError ? error.message : "모집 상태를 변경하지 못했어요.",
      );
    } finally {
      setPostActionBusy(null);
    }
  }

  async function handleOpenCompanionChat() {
    if (!post || chatOpening) return;
    setChatOpening(true);
    setActionError(null);
    setActionNotice(null);

    try {
      // Prefer the room ID supplied by the post detail API. Until every backend
      // environment exposes it, resolve the user's joined companion room by the
      // post's exact meeting time instead of fabricating an ID from post_id.
      let roomId = post.room_id ?? null;
      if (!roomId) {
        const response = await listChatRooms("companion");
        const meetAt = Date.parse(post.meet_at);
        const matches = response.items.filter(
          (room) =>
            room.room_type === "companion" &&
            room.my_status === "joined" &&
            room.meet_at != null &&
            Date.parse(room.meet_at) === meetAt,
        );
        if (matches.length === 1) {
          roomId = matches[0].room_id;
        }
      }

      if (roomId) {
        router.push(`/chats/${encodeURIComponent(roomId)}`);
        return;
      }

      setActionNotice(
        "이 모집글의 채팅방을 정확히 찾지 못해 동행 채팅 목록으로 이동해요.",
      );
      router.push("/chats");
    } catch (error) {
      if (handleAuthError(error)) {
        router.replace(
          `/auth/login?next=${encodeURIComponent(`/companions/${postId}`)}`,
        );
        return;
      }
      setActionError(
        error instanceof ApiError
          ? error.message
          : "동행 채팅방을 불러오지 못했어요.",
      );
    } finally {
      setChatOpening(false);
    }
  }

  if (loading) {
    return (
      <div role="status" className="space-y-4 px-4 py-4">
        <div className="h-6 w-28 animate-pulse rounded-card bg-surface-muted" />
        <div className="h-44 animate-pulse rounded-card bg-surface-muted" />
        <div className="h-32 animate-pulse rounded-card bg-surface-muted" />
      </div>
    );
  }

  if (errorMessage || !post) {
    return (
      <div className="flex min-h-[55vh] flex-col items-center justify-center gap-3 px-4 py-12 text-center">
        <p role="alert" className="text-sm font-semibold text-ink">
          {errorMessage ?? "동행 모집 글을 찾을 수 없어요."}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setReloadTick((v) => v + 1)}
            className="inline-flex items-center gap-1.5 rounded-chip bg-brand px-4 py-2 text-xs font-bold text-surface"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>다시 시도</span>
          </button>
          <Link
            href="/companions"
            className="rounded-chip border border-line-light bg-surface px-4 py-2 text-xs font-bold text-ink"
          >
            목록으로
          </Link>
        </div>
      </div>
    );
  }

  const statusMeta = POST_STATUS_META[post.status];
  const isActive = post.status === "open" || post.status === "full";
  return (
    <div className="space-y-5 px-4 py-4">
      <div className="flex items-center">
        <Link
          href="/companions?tab=mine"
          className="inline-flex items-center gap-1.5 text-sm font-bold text-ink hover:text-brand"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          <span>동행 상세</span>
        </Link>
      </div>

      {actionNotice ? (
        <p
          role="status"
          className="rounded-card bg-surface-soft px-3.5 py-2.5 text-xs font-semibold text-ink"
        >
          {actionNotice}
        </p>
      ) : null}
      {actionError ? (
        <p
          role="alert"
          className="rounded-card border border-brand/30 bg-surface-soft/50 px-3.5 py-2.5 text-xs font-semibold text-brand"
        >
          {actionError}
        </p>
      ) : null}

      {/* 모집 글 카드 */}
      <section className="space-y-3 rounded-card border border-line-light bg-surface p-4 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-chip px-2.5 py-0.5 text-xs font-extrabold ${statusMeta.className}`}
            >
              {statusMeta.label}
            </span>
            <span className="text-sm font-extrabold text-ink">
              {post.author_display_name ?? "알 수 없음"}
            </span>
            {isAuthor ? (
              <span className="rounded-chip bg-surface-muted px-2 py-0.5 text-[10px] font-bold text-muted">
                내 글
              </span>
            ) : null}
          </div>
          <span className="inline-flex items-center gap-1 text-sm font-extrabold text-brand">
            <Users className="h-4 w-4" aria-hidden="true" />
            <span>
              {post.approved_count} / {post.capacity}명
            </span>
          </span>
        </div>

        <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
          {post.memo || "함께 축제를 즐길 동행을 모집해요!"}
        </p>

        <div className="grid grid-cols-2 gap-2 pt-1 text-xs">
          <div className="flex items-center gap-1.5 rounded-xl bg-surface-muted px-3 py-2 font-semibold text-ink">
            <CalendarDays className="h-3.5 w-3.5 shrink-0 text-brand" aria-hidden="true" />
            <span>{formatKstDateTime(post.meet_at)}</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-xl bg-surface-muted px-3 py-2 font-semibold text-ink">
            <Users className="h-3.5 w-3.5 shrink-0 text-brand" aria-hidden="true" />
            <span>
              {getAgePrefLabel(post.age_pref)} · {getGenderPrefLabel(post.gender_pref)}
            </span>
          </div>
        </div>
      </section>

      {/* 만남 장소 (승인된 사람 & 작성자만) */}
      <section className="space-y-2.5">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-base font-extrabold text-ink">
            <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
            <span>만남 장소</span>
          </h2>
          {isAuthor && isActive ? (
            <button
              type="button"
              onClick={() => setEditPlaceOpen((v) => !v)}
              className="text-xs font-bold text-brand hover:underline"
            >
              {editPlaceOpen ? "닫기" : "장소 설정"}
            </button>
          ) : null}
        </div>

        {!canSeeMeetingPlace ? (
          <div className="flex items-center gap-2.5 rounded-card border border-line-light bg-surface-muted/60 px-4 py-4 text-xs font-medium text-muted">
            <Lock className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
            <span>승인된 참여자만 만남 장소를 볼 수 있어요.</span>
          </div>
        ) : meetingLoading ? (
          <div role="status" className="h-24 animate-pulse rounded-card bg-surface-muted" />
        ) : meetingError ? (
          <p role="alert" className="text-xs font-semibold text-brand">
            {meetingError}
          </p>
        ) : meetingPlace && !isMeetingPlaceUndecided(meetingPlace) ? (
          <div className="space-y-2.5 rounded-card border border-line-light bg-surface-soft/50 p-4 text-xs text-ink">
            <div className="flex items-start gap-2">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-hidden="true" />
              <div className="space-y-1">
                <p className="text-sm font-extrabold text-ink">{meetingPlace.name}</p>
                {meetingPlace.address ? (
                  <p className="text-muted">{meetingPlace.address}</p>
                ) : null}
                {meetingPlace.guide ? (
                  <p className="leading-relaxed text-ink">{meetingPlace.guide}</p>
                ) : null}
              </div>
            </div>
            {meetingPlace.lat != null && meetingPlace.lng != null ? (
              <KakaoMap
                center={{ lat: meetingPlace.lat, lng: meetingPlace.lng }}
                markers={[
                  {
                    lat: meetingPlace.lat,
                    lng: meetingPlace.lng,
                    title: meetingPlace.name,
                  },
                ]}
                className="h-36 w-full"
              />
            ) : null}
          </div>
        ) : (
          <div className="rounded-card border border-line-light bg-surface px-4 py-4 text-xs text-muted">
            아직 만남 장소가 정해지지 않았어요.
          </div>
        )}

        {isAuthor && editPlaceOpen ? (
          <form
            onSubmit={handleSaveMeetingPlace}
            className="space-y-2.5 rounded-card border border-line-light bg-surface p-4 shadow-sm"
          >
            <input
              type="text"
              required
              maxLength={60}
              value={placeName}
              onChange={(e) => setPlaceName(e.target.value)}
              placeholder="만남 장소 이름 (예: 여의나루역 2번 출구)"
              aria-label="만남 장소 이름"
              className="h-10 w-full rounded-input border border-line-light px-3.5 text-sm focus:border-brand focus:outline-none"
            />
            <input
              type="text"
              value={placeAddress}
              onChange={(e) => setPlaceAddress(e.target.value)}
              placeholder="주소 (선택)"
              aria-label="만남 장소 주소"
              className="h-10 w-full rounded-input border border-line-light px-3.5 text-sm focus:border-brand focus:outline-none"
            />
            <textarea
              rows={2}
              maxLength={300}
              value={placeGuide}
              onChange={(e) => setPlaceGuide(e.target.value)}
              placeholder="만남 안내 문구 (선택, 300자 이내)"
              aria-label="만남 안내"
              className="w-full rounded-card border border-line-light p-3 text-sm focus:border-brand focus:outline-none"
            />
            <button
              type="submit"
              disabled={placeSaving}
              className="w-full rounded-chip bg-brand py-2.5 text-xs font-extrabold text-surface disabled:opacity-60"
            >
              {placeSaving ? "저장 중…" : "만남 장소 저장"}
            </button>
          </form>
        ) : null}
      </section>

      {/* 신청자 영역 (작성자가 아닐 때) */}
      {!isAuthor ? (
        <section className="space-y-3 rounded-card border border-line-light bg-surface p-4 shadow-sm">
          <h2 className="text-sm font-extrabold text-ink">동행 참여 신청</h2>

          {post.my_application_status === "pending" ? (
            <div className="space-y-3">
              <p className="text-xs font-semibold text-brand">
                상태: {APPLICATION_STATUS_LABEL.pending}
              </p>
              <button
                type="button"
                disabled={applyBusy || !myApplicationId}
                onClick={() => void handleCancelOwnApplication()}
                className="w-full rounded-chip border border-line-light py-2.5 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
              >
                {applyBusy ? "취소 중…" : "신청 취소"}
              </button>
            </div>
          ) : post.my_application_status === "approved" ? (
            <p className="text-xs font-bold text-brand">
              승인 완료! 아래 동행 채팅방에서 일정을 맞춰 보세요.
            </p>
          ) : post.my_application_status === "rejected" ? (
            <p className="text-xs font-semibold text-muted">
              거절된 신청은 다시 신청할 수 없어요.
            </p>
          ) : post.status !== "open" ? (
            <p className="text-xs font-semibold text-muted">
              현재 모집이 마감되었거나 종료된 글이에요.
            </p>
          ) : (
            <form onSubmit={handleApply} className="space-y-2.5">
              <p className="text-[11px] text-muted">
                신청 시 내 닉네임·나이·성별이 모집 글 작성자에게 보여요.
              </p>
              <textarea
                rows={2}
                maxLength={200}
                value={applyMessage}
                onChange={(e) => setApplyMessage(e.target.value)}
                placeholder="간단한 인사를 남겨 보세요 (선택, 200자 이내)"
                aria-label="신청 메시지"
                className="w-full rounded-card border border-line-light p-3 text-sm text-ink placeholder:text-muted focus:border-brand focus:outline-none"
              />
              <button
                type="submit"
                disabled={applyBusy}
                className="w-full rounded-chip bg-brand py-2.5 text-sm font-extrabold text-surface shadow-sm transition-opacity hover:opacity-90 disabled:opacity-60"
              >
                {applyBusy ? "신청 중…" : "동행 신청하기"}
              </button>
            </form>
          )}
        </section>
      ) : null}

      {/* 작성자 관리 영역 */}
      {isAuthor ? (
        <section className="space-y-3">
          {isActive ? (
            <div className="flex flex-wrap gap-2">
              {post.status === "open" ? (
                <button
                  type="button"
                  disabled={postActionBusy !== null}
                  onClick={() => void handlePostAction("close")}
                  className="rounded-chip border border-line-light bg-surface px-3.5 py-2 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
                >
                  모집 마감
                </button>
              ) : null}
              <button
                type="button"
                disabled={postActionBusy !== null}
                onClick={() => void handlePostAction("end")}
                className="rounded-chip border border-line-light bg-surface px-3.5 py-2 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
              >
                동행 종료
              </button>
              <button
                type="button"
                disabled={postActionBusy !== null}
                onClick={() => void handlePostAction("cancel")}
                className="rounded-chip border border-brand/40 bg-surface-soft px-3.5 py-2 text-xs font-bold text-brand hover:bg-brand/15 disabled:opacity-60"
              >
                모집 취소
              </button>
            </div>
          ) : null}

          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-base font-extrabold text-ink">
              <span className="h-4 w-1 rounded-chip bg-brand" aria-hidden="true" />
              <span>신청자 관리</span>
            </h2>
            <div className="flex items-center gap-1">
              {(["all", "pending", "approved"] as const).map((filterValue) => (
                <button
                  key={filterValue}
                  type="button"
                  aria-pressed={appFilter === filterValue}
                  onClick={() => setAppFilter(filterValue)}
                  className={
                    appFilter === filterValue
                      ? "rounded-chip bg-brand px-2.5 py-1 text-[11px] font-bold text-surface"
                      : "rounded-chip border border-line-light bg-surface px-2.5 py-1 text-[11px] font-semibold text-muted"
                  }
                >
                  {filterValue === "all"
                    ? "전체"
                    : filterValue === "pending"
                      ? "대기 중"
                      : "승인됨"}
                </button>
              ))}
            </div>
          </div>

          {appsLoading ? (
            <div role="status" className="h-24 animate-pulse rounded-card bg-surface-muted" />
          ) : appsError ? (
            <p role="alert" className="text-xs font-semibold text-brand">
              {appsError}
            </p>
          ) : applications.length === 0 ? (
            <div className="rounded-card border border-line-light bg-surface px-4 py-8 text-center text-xs text-muted">
              아직 신청한 사람이 없어요.
            </div>
          ) : (
            <ul className="space-y-2.5">
              {applications.map((item) => (
                <li
                  key={item.application_id}
                  className="rounded-card border border-line-light bg-surface p-3.5 shadow-sm"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-extrabold text-ink">
                        {item.applicant_display_name ?? "알 수 없음"}
                      </span>
                      {item.applicant_age !== null ? (
                        <span className="text-muted">{item.applicant_age}세</span>
                      ) : null}
                      {item.applicant_gender ? (
                        <span className="text-muted">
                          {item.applicant_gender === "male" ? "남성" : "여성"}
                        </span>
                      ) : null}
                    </div>
                    <span className="rounded-chip bg-surface-soft px-2 py-0.5 text-[11px] font-bold text-brand">
                      {APPLICATION_STATUS_LABEL[item.status]}
                    </span>
                  </div>

                  {item.message ? (
                    <p className="mt-2 text-xs text-ink">{item.message}</p>
                  ) : null}

                  {item.status === "pending" ? (
                    <div className="mt-3 flex justify-end gap-2">
                      <button
                        type="button"
                        disabled={decidingId === item.application_id}
                        onClick={() => void handleDecide(item.application_id, "reject")}
                        className="inline-flex items-center gap-1 rounded-chip border border-line-light px-3 py-1.5 text-xs font-bold text-ink hover:bg-surface-muted disabled:opacity-60"
                      >
                        <X className="h-3.5 w-3.5" aria-hidden="true" />
                        <span>거절</span>
                      </button>
                      <button
                        type="button"
                        disabled={
                          decidingId === item.application_id ||
                          post.approved_count >= post.capacity
                        }
                        onClick={() => void handleDecide(item.application_id, "approve")}
                        className="inline-flex items-center gap-1 rounded-chip bg-brand px-3.5 py-1.5 text-xs font-extrabold text-surface disabled:opacity-60"
                      >
                        <Check className="h-3.5 w-3.5" aria-hidden="true" />
                        <span>승인</span>
                      </button>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      <nav
        aria-label="동행 상세 바로가기"
        className={`grid gap-2 pt-1 ${canSeeMeetingPlace ? "grid-cols-2" : "grid-cols-1"}`}
      >
        {canSeeMeetingPlace ? (
          <button
            type="button"
            onClick={() => void handleOpenCompanionChat()}
            disabled={chatOpening}
            className="flex min-h-11 items-center justify-center gap-1.5 rounded-chip bg-brand px-3 py-2.5 text-xs font-extrabold text-surface shadow-sm transition-opacity hover:opacity-90"
          >
            <MessageCircle className="h-4 w-4" aria-hidden="true" />
            <span>{chatOpening ? "채팅방 찾는 중..." : "동행 채팅방"}</span>
          </button>
        ) : null}
        <Link
          href="/companions"
          className="flex min-h-11 items-center justify-center gap-1.5 rounded-chip border border-brand/30 bg-surface px-3 py-2.5 text-xs font-extrabold text-brand shadow-sm hover:bg-surface-soft"
        >
          <Users className="h-4 w-4" aria-hidden="true" />
          <span>동행 리스트 가기</span>
        </Link>
      </nav>

      <LoginPromptSheet
        open={loginPromptOpen}
        onClose={() => setLoginPromptOpen(false)}
        nextPath={`/companions/${postId}`}
        description="동행에 참여 신청하려면 로그인해 주세요."
      />
    </div>
  );
}

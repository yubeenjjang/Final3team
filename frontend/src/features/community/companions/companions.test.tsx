import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetAuthStateForTest, setAuthSession } from "@/lib/api/auth";
import { CompanionDetailView } from "./CompanionDetailView";
import { CompanionsView, getDefaultCompanionMeetAt } from "./CompanionsView";

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
  usePathname: () => "/companions",
}));

const sampleFestival = {
  festival_id: "fst_000001",
  name: "서울 불꽃 축제",
  region_code: "SEOUL",
  venue_name: "여의도 한강공원",
  lat: 37.528,
  lng: 126.932,
  start_date: "2026-12-05",
  end_date: "2026-12-07",
  event_status: "upcoming" as const,
  thumbnail_url: null,
  image_credit: null,
  source: "tourapi",
  last_synced_at: "2026-11-24T00:00:00Z",
};

const samplePost = {
  post_id: "cpo_01JD8Q3K2M",
  author_display_name: "축제러버",
  meet_at: "2026-12-05T18:00:00+09:00",
  capacity: 4,
  approved_count: 2,
  age_pref: "20s",
  gender_pref: "any",
  memo: "불꽃놀이 같이 보고 사진 찍어요!",
  status: "open",
};

const sampleFeedPost = {
  ...samplePost,
  festival_id: sampleFestival.festival_id,
  festival_name: sampleFestival.name,
  festival_thumbnail_url: sampleFestival.thumbnail_url,
  festival_venue_name: sampleFestival.venue_name,
  festival_region_code: sampleFestival.region_code,
};

const ongoingFestival = {
  ...sampleFestival,
  festival_id: "fst_000002",
  name: "운정호수공원 불꽃축제",
  venue_name: "운정호수공원",
  start_date: "2026-11-20",
  end_date: "2026-11-30",
  event_status: "ongoing" as const,
};

describe("Companions screens", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    pushMock.mockReset();
    replaceMock.mockReset();
    resetAuthStateForTest();
  });

  afterEach(() => {
    cleanup();
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("searches festivals in the write form and presets the festival meeting date", async () => {
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "usr_member", displayName: "축제친구" },
    });
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/festivals")) {
        return Response.json({
          items: [sampleFestival, ongoingFestival],
          total: 2,
          page: 1,
          page_size: 100,
        });
      }
      if (url.pathname.endsWith("/companion-posts")) {
        return Response.json({ items: [], total: 0, page: 1, page_size: 50 });
      }
      return Response.json({ items: [] });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<CompanionsView />);

    await waitFor(() => {
      expect(screen.getByText("아직 등록된 동행 모집 글이 없어요")).toBeInTheDocument();
    });

    const browseSearch = screen.getByLabelText("축제 검색");
    fireEvent.change(browseSearch, { target: { value: "서울" } });
    const browseSelect = screen.getByLabelText("축제 선택");
    expect(within(browseSelect).getByRole("option", { name: /서울 불꽃 축제/ })).toBeInTheDocument();
    expect(within(browseSelect).queryByRole("option", { name: /운정호수공원/ })).not.toBeInTheDocument();
    fireEvent.change(browseSearch, { target: { value: "" } });

    fireEvent.click(screen.getByRole("button", { name: "모집 글쓰기" }));

    const meetAtInput = screen.getByLabelText(/만남 일시/) as HTMLInputElement;
    await waitFor(() => {
      expect(meetAtInput.value).toBe("2026-12-05T18:00");
    });

    const writeDialog = screen.getByRole("dialog", { name: "동행 모집 글 작성" });
    fireEvent.change(within(writeDialog).getByLabelText("축제 검색"), {
      target: { value: "운정호수" },
    });
    const searchResult = within(writeDialog).getByRole("option", {
      name: /운정호수공원 불꽃축제/,
    });
    expect(searchResult).toBeInTheDocument();
    expect(within(writeDialog).queryByRole("option", { name: /서울 불꽃 축제/ })).not.toBeInTheDocument();

    fireEvent.click(searchResult);
    expect(within(writeDialog).getByLabelText("축제 검색")).toHaveValue(
      "운정호수공원 불꽃축제",
    );
    expect(within(writeDialog).queryByRole("listbox", { name: "축제 검색 결과" })).not.toBeInTheDocument();
    expect(meetAtInput.value).not.toBe("");
  });

  it("sets tomorrow for an ongoing festival and its start date for an upcoming festival", () => {
    const now = new Date("2026-11-27T01:00:00.000Z");
    expect(getDefaultCompanionMeetAt(ongoingFestival, now)).toBe("2026-11-28T18:00");
    expect(getDefaultCompanionMeetAt(sampleFestival, now)).toBe("2026-12-05T18:00");
  });

  it("opens the write form with the linked festival selected", async () => {
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "usr_member", displayName: "축제친구" },
    });
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/festivals")) {
        return Response.json({ items: [sampleFestival], total: 1, page: 1, page_size: 100 });
      }
      if (url.pathname.endsWith("/companion-posts")) {
        return Response.json({ items: [], total: 0, page: 1, page_size: 50 });
      }
      return Response.json({ items: [] });
    }) as unknown as typeof fetch;

    render(
      <CompanionsView
        initialFestivalId={sampleFestival.festival_id}
        initialWriteOpen
      />,
    );

    const writeDialog = await screen.findByRole("dialog", {
      name: "동행 모집 글 작성",
    });
    expect(within(writeDialog).getByLabelText("축제 검색")).toHaveValue(
      sampleFestival.name,
    );
    expect(within(writeDialog).getByLabelText(/만남 일시/)).toHaveValue(
      "2026-12-05T18:00",
    );
  });

  it("shows the festival name on my companion post", async () => {
    setAuthSession({
      accessToken: "token-owner",
      refreshToken: "token-r",
      user: { userId: "usr_owner", displayName: "축제러버" },
    });
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/festivals")) {
        return Response.json({ items: [sampleFestival], total: 1, page: 1, page_size: 100 });
      }
      if (url.pathname.endsWith("/me/companion-activity")) {
        return Response.json({ items: [{ ...samplePost, festival_id: sampleFestival.festival_id }] });
      }
      return Response.json({ items: [] });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<CompanionsView initialTab="mine" />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /서울 불꽃 축제/ })).toHaveAttribute(
        "href",
        "/festivals/fst_000001",
      );
    });
  });

  it("renders companion posts, empty state, and error state", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/festivals")) {
        return Response.json({ items: [sampleFestival], total: 1, page: 1, page_size: 50 });
      }
      if (url.pathname.endsWith("/companion-posts")) {
        const status = url.searchParams.get("status");
        if (status === "full") {
          return Response.json({ items: [], total: 0, page: 1, page_size: 50 });
        }
        if (status === "ended") {
          return Response.json(
            { error: { code: "HTTP_ERROR", message: "목록 조회 오류" } },
            { status: 500 },
          );
        }
        return Response.json({ items: [sampleFeedPost], total: 1, page: 1, page_size: 50 });
      }
      return Response.json({ items: [] });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<CompanionsView />);

    await waitFor(() => {
      expect(screen.getByText("불꽃놀이 같이 보고 사진 찍어요!")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(document.body).toHaveTextContent(/2\s*\/\s*4명/);
    });
    expect(screen.getByRole("button", { name: "전체" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "정원 마감" }));
    await waitFor(() => {
      expect(screen.getByText("아직 등록된 동행 모집 글이 없어요")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "종료" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("목록 조회 오류");
    });
  });

  it("shows every recruitment status when the all filter is selected", async () => {
    const fullPost = {
      ...sampleFeedPost,
      post_id: "cpo_full",
      memo: "정원이 마감된 동행 글",
      status: "full",
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/festivals")) {
        return Response.json({ items: [sampleFestival], total: 1, page: 1, page_size: 100 });
      }
      if (url.pathname.endsWith("/companion-posts")) {
        const status = url.searchParams.get("status");
        if (status === "open") {
          return Response.json({ items: [sampleFeedPost], total: 1, page: 1, page_size: 50 });
        }
        if (status === null) {
          return Response.json({
            items: [sampleFeedPost, fullPost],
            total: 2,
            page: 1,
            page_size: 50,
          });
        }
        return Response.json({ items: [], total: 0, page: 1, page_size: 50 });
      }
      return Response.json({ items: [] });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<CompanionsView />);
    await waitFor(() => {
      expect(screen.getByText("불꽃놀이 같이 보고 사진 찍어요!")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "전체" }));

    await waitFor(() => {
      expect(screen.getByText("정원이 마감된 동행 글")).toBeInTheDocument();
    });
    expect(screen.getByText("불꽃놀이 같이 보고 사진 찍어요!")).toBeInTheDocument();
  });

  it("falls back to festival post lists when the global feed endpoint is unavailable", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/festivals")) {
        return Response.json({ items: [sampleFestival], total: 1, page: 1, page_size: 100 });
      }
      if (url.pathname.endsWith("/api/v1/companion-posts")) {
        return Response.json(
          { error: { code: "METHOD_NOT_ALLOWED", message: "지원하지 않는 요청 방식입니다." } },
          { status: 405 },
        );
      }
      if (url.pathname.endsWith("/festivals/fst_000001/companion-posts")) {
        return Response.json({ items: [samplePost] });
      }
      return Response.json({ items: [] });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<CompanionsView />);

    await waitFor(() => {
      expect(screen.getByText("불꽃놀이 같이 보고 사진 찍어요!")).toBeInTheDocument();
    });
    expect(screen.queryByText("지원하지 않는 요청 방식입니다.")).not.toBeInTheDocument();
    expect(screen.getByLabelText("지역")).toBeInTheDocument();
    expect(screen.getByLabelText("기간")).toBeInTheDocument();
    expect(screen.getByLabelText("모집 조건")).toBeInTheDocument();
    expect(screen.getByLabelText("정렬")).toBeInTheDocument();
  });

  it("locks meeting place for unapproved users and shows it for approved users", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/companion-posts/cpo_01JD8Q3K2M")) {
        return Response.json({ ...samplePost, my_application_status: null });
      }
      return Response.json({ items: [] });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<CompanionDetailView postId="cpo_01JD8Q3K2M" />);

    await waitFor(() => {
      expect(screen.getByText("승인된 참여자만 만남 장소를 볼 수 있어요.")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "동행 리스트 가기" })).toHaveAttribute(
      "href",
      "/companions",
    );
    expect(screen.queryByRole("link", { name: "동행 채팅방" })).not.toBeInTheDocument();

    cleanup();
    setAuthSession({
      accessToken: "token-a",
      refreshToken: "token-r",
      user: { userId: "usr_member", displayName: "승인멤버" },
    });

    const approvedFetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/companion-posts/cpo_01JD8Q3K2M")) {
        return Response.json({ ...samplePost, my_application_status: "approved" });
      }
      if (url.pathname.endsWith("/meeting-place")) {
        return Response.json({
          name: "여의나루역 2번 출구",
          address: "서울 영등포구 여의동로",
          lat: null,
          lng: null,
          guide: "출구 앞 벤치에서 만나요",
          updated_at: "2026-11-24T12:00:00+09:00",
        });
      }
      return Response.json({ items: [] });
    });
    globalThis.fetch = approvedFetch as unknown as typeof fetch;

    render(<CompanionDetailView postId="cpo_01JD8Q3K2M" />);

    await waitFor(() => {
      expect(screen.getByText("여의나루역 2번 출구")).toBeInTheDocument();
    });
    expect(screen.getByText("출구 앞 벤치에서 만나요")).toBeInTheDocument();
    const chatLink = screen.getByRole("link", { name: "동행 채팅방" });
    expect(chatLink).toHaveAttribute("href", "/chats/crm_01JD8Q3K2M");
    expect(screen.getByRole("link", { name: "동행 리스트 가기" })).toHaveAttribute(
      "href",
      "/companions",
    );
    expect(
      screen.getByText("출구 앞 벤치에서 만나요").compareDocumentPosition(chatLink) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("lets author approve an applicant", async () => {
    setAuthSession({
      accessToken: "token-owner",
      refreshToken: "token-r",
      user: { userId: "usr_owner", displayName: "축제러버" },
    });
    let approved = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input));
      if (url.pathname.endsWith("/companion-posts/cpo_01JD8Q3K2M")) {
        return Response.json({
          ...samplePost,
          approved_count: approved ? 3 : 2,
          my_application_status: null,
        });
      }
      if (url.pathname.endsWith("/me/companion-activity")) {
        if (url.searchParams.get("type") === "posts") {
          return Response.json({ items: [{ ...samplePost, festival_id: "fst_000001" }] });
        }
        return Response.json({ items: [] });
      }
      if (url.pathname.endsWith("/meeting-place")) {
        return Response.json({ status: "undecided" });
      }
      if (url.pathname.endsWith("/applications")) {
        return Response.json({
          items: [
            {
              application_id: "cap_01JD8Q3K2M",
              applicant_display_name: "새신청자",
              applicant_age: 26,
              applicant_gender: "female",
              message: "같이 가고 싶어요!",
              status: approved ? "approved" : "pending",
              created_at: "2026-11-24T10:00:00+09:00",
            },
          ],
        });
      }
      if (url.pathname.endsWith("/companion-applications/cap_01JD8Q3K2M/approve") && init?.method === "POST") {
        approved = true;
        return Response.json({
          application_id: "cap_01JD8Q3K2M",
          status: "approved",
          post_status: "open",
        });
      }
      return Response.json({ items: [] });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<CompanionDetailView postId="cpo_01JD8Q3K2M" />);

    await waitFor(() => {
      expect(screen.getByText("새신청자")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "승인" }));
    await waitFor(() => {
      expect(screen.getByText("3 / 4명")).toBeInTheDocument();
    });
  });
});

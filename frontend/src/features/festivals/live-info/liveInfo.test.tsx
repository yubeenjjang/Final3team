import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import tailwindConfig from "../../../../tailwind.config";
import { LiveInfoSection } from "./LiveInfoSection";
import {
  formatDateTimeShort,
  getCrowdColorClass,
  getPrecipitationLabel,
} from "./liveInfoUtils";

describe("F7 live info", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
    globalThis.fetch = originalFetch;
  });

  it("F7 maps precipitation types and crowd color tokens", () => {
    expect(getPrecipitationLabel("none")).toBe("강수 없음");
    expect(getPrecipitationLabel("rain")).toBe("비");
    expect(getPrecipitationLabel("snow")).toBe("눈");
    expect(getCrowdColorClass("yellow")).toContain("bg-crowd-yellow");
    expect(getCrowdColorClass("red")).toContain("bg-crowd-red");
  });

  it("F7 crowd badges and stale warning meet the 4.5:1 text contrast threshold", () => {
    const colors = tailwindConfig.theme?.extend?.colors as Record<string, string>;
    function luminance(hex: string) {
      const [red, green, blue] = hex.slice(1).match(/../g)!.map((channel) => {
        const unit = Number.parseInt(channel, 16) / 255;
        return unit <= 0.04045 ? unit / 12.92 : ((unit + 0.055) / 1.055) ** 2.4;
      });
      return red * 0.2126 + green * 0.7152 + blue * 0.0722;
    }

    for (const color of ["green", "yellow", "orange", "red"] as const) {
      const [background, text] = getCrowdColorClass(color).split(" ");
      const ratio = (luminance(colors[background.slice(3)]) + 0.05) / (luminance(colors[text.slice(5)]) + 0.05);
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    }
    expect((luminance(colors.surface) + 0.05) / (luminance(colors.ink) + 0.05)).toBeGreaterThanOrEqual(4.5);
  });

  it("F7 formats ISO timestamps in Asia/Seoul timezone", () => {
    expect(formatDateTimeShort("2026-11-22T11:00:00+09:00")).toBe("11.22 11:00");
    expect(formatDateTimeShort("2026-11-20T18:00:00+09:00")).toBe("11.20 18:00");
    expect(formatDateTimeShort("2026-11-22T02:00:00Z")).toBe("11.22 11:00");
    expect(formatDateTimeShort("2026-11-21T15:00:00Z")).toBe("11.22 00:00");
  });

  it("F7 renders crowd, weather, and notices independently when all succeed", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/crowd")) {
        return new Response(
          JSON.stringify({
            is_mock: true,
            festival_id: "fst_000001",
            status: "ok",
            coverage: { scope: "seoul_only", region_code: "SEOUL", supported: true },
            source: "seoul_citydata",
            areas: [
              {
                area_code: "POI001",
                area_name: "광화문·덕수궁",
                relation_type: "contains",
                congest_level: "보통",
                congest_color: "yellow",
                congest_message: "보통 수준",
                population_min: 12000,
                population_max: 14000,
                observed_at: "2026-11-22T14:00:00+09:00",
                forecast: [],
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/weather")) {
        return new Response(
          JSON.stringify({
            is_mock: true,
            festival_id: "fst_000001",
            status: "ok",
            coverage: { scope: "national", region_code: "SEOUL", supported: true },
            source: "kma",
            observed_at: "2026-11-22T14:00:00+09:00",
            data: {
              observed_at: "2026-11-22T14:00:00+09:00",
              temperature_c: 8,
              precipitation_mm: 0,
              precipitation_type: "none",
              grid: { nx: 60, ny: 127 },
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          is_mock: true,
          festival_id: "fst_000001",
          status: "ok",
          coverage: { scope: "seoul_only", region_code: "SEOUL", supported: true },
          source: "seoul_topis",
          items: [
            {
              notice_id: "ntc_1",
              type: "traffic_control",
              title: "차량 통제 안내",
              content: "일부 구간 통제",
              effective_from: "2026-11-22T12:00:00+09:00",
              effective_to: "2026-11-22T22:00:00+09:00",
              source: "seoul_topis",
              published_at: "2026-11-22T10:00:00+09:00",
            },
            {
              notice_id: "ntc_2",
              type: "operation",
              title: "야간 연장 운영",
              content: "22시까지 운영",
              effective_from: "2026-11-22T18:00:00+09:00",
              effective_to: "2026-11-22T22:00:00+09:00",
              source: "operator",
              published_at: "2026-11-22T10:00:00+09:00",
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<LiveInfoSection festivalId="fst_000001" />);

    await waitFor(() => {
      expect(screen.getByText("광화문·덕수궁")).toBeInTheDocument();
      expect(screen.getByText("보통")).toBeInTheDocument();
      expect(screen.getByText("8°C")).toBeInTheDocument();
      expect(screen.getByText("강수 없음")).toBeInTheDocument();
      expect(screen.getByText("차량 통제 안내")).toBeInTheDocument();
      expect(screen.getByText("야간 연장 운영")).toBeInTheDocument();
    });
  });

  it("F7 isolates card failures and shows unsupported/stale/empty states", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/crowd")) {
        return new Response(
          JSON.stringify({
            is_mock: true,
            festival_id: "fst_000003",
            status: "unsupported",
            coverage: { scope: "seoul_only", region_code: "BUSAN", supported: false },
            source: "seoul_citydata",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/weather")) {
        return new Response(
          JSON.stringify({
            is_mock: true,
            festival_id: "fst_000003",
            status: "stale",
            coverage: { scope: "national", region_code: "BUSAN", supported: true },
            source: "kma",
            data: {
              observed_at: "2026-11-22T10:00:00+09:00",
              temperature_c: 12,
              precipitation_mm: 3.5,
              precipitation_type: "rain",
              grid: { nx: 98, ny: 76 },
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          is_mock: true,
          festival_id: "fst_000003",
          status: "ok",
          coverage: { scope: "seoul_only", region_code: "BUSAN", supported: true },
          source: "seoul_topis",
          items: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<LiveInfoSection festivalId="fst_000003" />);

    await waitFor(() => {
      expect(
        screen.getByText("이 지역은 아직 지원하지 않아요"),
      ).toBeInTheDocument();
      expect(screen.getByText("정보가 오래됐어요")).toHaveClass("text-ink");
      expect(screen.getByText("12°C")).toBeInTheDocument();
      expect(screen.getByText("비 (3.5mm)")).toBeInTheDocument();
      expect(
        screen.getByText("확인할 수 있는 공지 자료가 없어요"),
      ).toBeInTheDocument();
    });
  });

  it("F7 keeps weather and notices visible even when crowd request fails", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/crowd")) {
        throw new TypeError("Network error");
      }
      if (url.endsWith("/weather")) {
        return new Response(
          JSON.stringify({
            is_mock: true,
            festival_id: "fst_000001",
            status: "ok",
            coverage: { scope: "national", region_code: "SEOUL", supported: true },
            source: "kma",
            data: {
              observed_at: "2026-11-22T14:00:00+09:00",
              temperature_c: 4,
              precipitation_mm: 1,
              precipitation_type: "snow",
              grid: { nx: 60, ny: 127 },
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          is_mock: true,
          festival_id: "fst_000001",
          status: "ok",
          coverage: { scope: "seoul_only", region_code: "SEOUL", supported: true },
          source: "operator",
          items: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<LiveInfoSection festivalId="fst_000001" />);

    await waitFor(() => {
      expect(screen.getByText("서버에 연결할 수 없어요")).toBeInTheDocument();
      expect(screen.getByText("4°C")).toBeInTheDocument();
      expect(screen.getByText("눈 (1mm)")).toBeInTheDocument();
      expect(
        screen.getByText("확인할 수 있는 공지 자료가 없어요"),
      ).toBeInTheDocument();
    });
  });

  it("F7 renders multiple nearby_areas lines under 주변 지역 혼잡 without percentages", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/crowd")) {
        return new Response(
          JSON.stringify({
            is_mock: false,
            festival_id: "fst_000001",
            status: "ok",
            coverage: { scope: "seoul_only", region_code: "SEOUL", supported: true },
            source: "seoul_citydata",
            areas: [],
            nearby_areas: [
              {
                area_code: "POI009",
                area_name: "광화문·덕수궁",
                distance_m: 0,
                status: "ok",
                data: {
                  area_code: "POI009",
                  area_name: "광화문·덕수궁",
                  relation_type: "contains",
                  congest_level: "여유",
                  congest_color: "green",
                  congest_message: "여유",
                  population_min: 10000,
                  population_max: 12000,
                  observed_at: "2026-11-24T14:00:00+09:00",
                  forecast: [],
                },
              },
              {
                area_code: "POI130",
                area_name: "시의회 앞",
                distance_m: 280.4,
                status: "ok",
                data: {
                  area_code: "POI130",
                  area_name: "시의회 앞",
                  relation_type: "adjacent",
                  congest_level: "약간 붐빔",
                  congest_color: "orange",
                  congest_message: "약간 붐빔",
                  population_min: 18000,
                  population_max: 20000,
                  observed_at: "2026-11-24T14:00:00+09:00",
                  forecast: [],
                },
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          is_mock: true,
          festival_id: "fst_000001",
          status: "ok",
          coverage: { scope: "seoul_only", region_code: "SEOUL", supported: true },
          source: "operator",
          items: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    render(<LiveInfoSection festivalId="fst_000001" />);

    await waitFor(() => {
      expect(screen.getByText("주변 지역 혼잡")).toBeInTheDocument();
      expect(screen.getByText("광화문·덕수궁")).toBeInTheDocument();
      expect(screen.getByText("시의회 앞")).toBeInTheDocument();
      expect(screen.getByText("여유")).toHaveClass("bg-crowd-green");
      expect(screen.getByText("약간 붐빔")).toHaveClass("bg-crowd-orange");
    });
    expect(screen.getByTestId("live-info-crowd").textContent).not.toContain("%");
  });
});

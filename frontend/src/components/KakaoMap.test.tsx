import "@testing-library/jest-dom/vitest";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { loadKakaoMaps, resetKakaoLoaderForTest } from "@/lib/kakao";
import { KakaoMap } from "./KakaoMap";

vi.mock("./OpenStreetMap", () => ({
  OpenStreetMap: () => <div data-testid="openstreet-map-fallback">OpenStreetMap 지도</div>,
}));

describe("F11 KakaoMap", () => {
  const originalKakaoKey = process.env.NEXT_PUBLIC_KAKAO_JS_KEY;

  beforeEach(() => {
    resetKakaoLoaderForTest();
    delete window.kakao;
    document
      .querySelectorAll('script[data-kakao-maps-sdk="true"]')
      .forEach((node) => node.remove());
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    if (originalKakaoKey === undefined) {
      delete process.env.NEXT_PUBLIC_KAKAO_JS_KEY;
    } else {
      process.env.NEXT_PUBLIC_KAKAO_JS_KEY = originalKakaoKey;
    }
  });

  it("F11 shows OpenStreetMap when NEXT_PUBLIC_KAKAO_JS_KEY is empty", () => {
    process.env.NEXT_PUBLIC_KAKAO_JS_KEY = "";

    render(<KakaoMap center={{ lat: 37.5759, lng: 126.9768 }} />);

    expect(screen.getByTestId("openstreet-map-fallback")).toBeInTheDocument();
  });

  it("F11 removes an invalid SDK script and allows the next load to succeed", async () => {
    const first = loadKakaoMaps("test-placeholder-key");
    const script = document.querySelector<HTMLScriptElement>("script[data-kakao-maps-sdk]")!;
    script.dispatchEvent(new Event("load"));
    await expect(first).rejects.toThrow("KAKAO_SDK_INVALID");
    expect(script).not.toBeInTheDocument();

    const retry = loadKakaoMaps("test-placeholder-key");
    const loaded = { Map: vi.fn(), load: (ready: () => void) => ready() } as unknown as NonNullable<NonNullable<Window["kakao"]>["maps"]>;
    window.kakao = { maps: loaded };
    const newScript = document.querySelector<HTMLScriptElement>("script[data-kakao-maps-sdk]")!;
    expect(newScript).not.toBe(script);
    newScript.dispatchEvent(new Event("load"));
    await expect(retry).resolves.toBe(loaded);
  });

  it("F11 times out an SDK that never calls maps.load back and shows the fallback", async () => {
    vi.useFakeTimers();
    process.env.NEXT_PUBLIC_KAKAO_JS_KEY = "test-placeholder-key";
    render(<KakaoMap center={{ lat: 37.5759, lng: 126.9768 }} />);
    const script = document.querySelector<HTMLScriptElement>("script[data-kakao-maps-sdk]")!;
    const load = vi.fn();
    window.kakao = { maps: { load } as unknown as NonNullable<NonNullable<Window["kakao"]>["maps"]> };
    script.dispatchEvent(new Event("load"));
    expect(load).toHaveBeenCalledOnce();

    await act(async () => vi.advanceTimersByTimeAsync(10_000));
    expect(screen.getByTestId("openstreet-map-fallback")).toBeInTheDocument();
    expect(script).not.toBeInTheDocument();
  });

  it("F11 loads Kakao SDK script only once and shows fallback on script error", async () => {
    process.env.NEXT_PUBLIC_KAKAO_JS_KEY = "test-placeholder-key";

    const first = loadKakaoMaps();
    const second = loadKakaoMaps();

    const scripts = document.querySelectorAll<HTMLScriptElement>(
      'script[data-kakao-maps-sdk="true"]',
    );
    expect(scripts).toHaveLength(1);
    expect(scripts[0].getAttribute("src")).toBe(
      "//dapi.kakao.com/v2/maps/sdk.js?appkey=test-placeholder-key&autoload=false",
    );

    scripts[0].onerror?.(new Event("error"));

    await expect(first).rejects.toThrow("KAKAO_SDK_LOAD_FAILED");
    await expect(second).rejects.toThrow("KAKAO_SDK_LOAD_FAILED");

    render(<KakaoMap center={{ lat: 37.5759, lng: 126.9768 }} />);
    const injected = document.querySelector<HTMLScriptElement>(
      'script[data-kakao-maps-sdk="true"]',
    );
    expect(injected).not.toBeNull();
    injected?.onerror?.(new Event("error"));

    await waitFor(() => {
      expect(screen.getByTestId("openstreet-map-fallback")).toBeInTheDocument();
    });
  });
});

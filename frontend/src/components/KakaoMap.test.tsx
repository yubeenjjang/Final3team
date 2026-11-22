import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { loadKakaoMaps, resetKakaoLoaderForTest } from "@/lib/kakao";
import { KakaoMap } from "./KakaoMap";

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
    if (originalKakaoKey === undefined) {
      delete process.env.NEXT_PUBLIC_KAKAO_JS_KEY;
    } else {
      process.env.NEXT_PUBLIC_KAKAO_JS_KEY = originalKakaoKey;
    }
  });

  it("F11 shows fallback message when NEXT_PUBLIC_KAKAO_JS_KEY is empty", () => {
    process.env.NEXT_PUBLIC_KAKAO_JS_KEY = "";

    render(<KakaoMap center={{ lat: 37.5759, lng: 126.9768 }} />);

    expect(
      screen.getByText("지도를 불러올 수 없어요(지도 키 확인)"),
    ).toBeInTheDocument();
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
      expect(
        screen.getByText("지도를 불러올 수 없어요(지도 키 확인)"),
      ).toBeInTheDocument();
    });
  });
});

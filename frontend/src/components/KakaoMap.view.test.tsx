import "@testing-library/jest-dom/vitest";
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { KakaoMapsNamespace } from "@/lib/kakao";

const map = { setCenter: vi.fn(), setLevel: vi.fn(), setBounds: vi.fn() };
const maps = {
  LatLng: vi.fn(function (this: object, lat: number, lng: number) {
    Object.assign(this, { lat, lng });
  }),
  LatLngBounds: vi.fn(function (this: { extend: () => void }) {
    this.extend = vi.fn();
  }),
  Map: vi.fn(function () {
    return map;
  }),
  Marker: vi.fn(function (this: { setMap: () => void }) {
    this.setMap = vi.fn();
  }),
  Polyline: vi.fn(function (this: { setMap: () => void }) {
    this.setMap = vi.fn();
  }),
} as unknown as KakaoMapsNamespace;

vi.mock("@/lib/kakao", () => ({
  getKakaoJsKey: () => "test-key",
  loadKakaoMaps: () => Promise.resolve(maps),
}));

import { KakaoMap } from "./KakaoMap";

describe("KakaoMap view range", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("fits bounds once per center and does not refit when only markers change", async () => {
    const center = { lat: 37.57, lng: 126.98 };
    const two = [
      { lat: 37.57, lng: 126.98 },
      { lat: 35.16, lng: 129.16 },
    ];
    const { rerender } = render(<KakaoMap center={center} markers={two} />);
    await waitFor(() => expect(map.setBounds).toHaveBeenCalledTimes(1));

    rerender(<KakaoMap center={center} markers={[...two, { lat: 36.35, lng: 127.38 }]} />);
    await waitFor(() => expect(maps.Marker).toHaveBeenCalledTimes(5));
    expect(map.setBounds).toHaveBeenCalledTimes(1);
    expect(map.setCenter).not.toHaveBeenCalled();

    rerender(<KakaoMap center={{ lat: 35.16, lng: 129.16 }} markers={two} />);
    await waitFor(() => expect(map.setBounds).toHaveBeenCalledTimes(2));
    expect(map.setCenter).toHaveBeenCalledTimes(1);
  });
});

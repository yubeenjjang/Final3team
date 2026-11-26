import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  buildOpenStreetMapLink,
  OpenStreetMap,
} from "./OpenStreetMap";

const leafletMocks = vi.hoisted(() => ({
  polygon: vi.fn(() => ({
    remove: vi.fn(),
    bindTooltip: vi.fn().mockReturnThis(),
    addTo: vi.fn().mockReturnThis(),
  })),
}));

vi.mock("leaflet", () => ({
  map: vi.fn(() => ({ remove: vi.fn(), setView: vi.fn(), getZoom: () => 14 })),
  tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
  divIcon: vi.fn(() => ({})),
  marker: vi.fn(() => ({ bindTooltip: vi.fn().mockReturnThis(), addTo: vi.fn().mockReturnThis() })),
  polygon: leafletMocks.polygon,
}));

describe("OpenStreetMap", () => {
  it("builds an external map URL for the selected position", () => {
    const url = new URL(buildOpenStreetMapLink({ lat: 37.5759, lng: 126.9768 }));
    expect(url.hostname).toBe("www.openstreetmap.org");
    expect(url.searchParams.get("mlat")).toBe("37.5759");
    expect(url.searchParams.get("mlon")).toBe("126.9768");
  });

  it("renders an interactive map container", () => {
    render(
      <OpenStreetMap
        center={{ lat: 37.5759, lng: 126.9768 }}
        title="광화문 겨울빛 축제"
      />,
    );
    expect(screen.getByRole("application", { name: "광화문 겨울빛 축제 지도" })).toBeInTheDocument();
  });

  it("draws crowd boundary polygons", async () => {
    render(
      <OpenStreetMap
        center={{ lat: 37.5759, lng: 126.9768 }}
        title="광화문 겨울빛 축제"
        areas={[{
          id: "crowd-1",
          label: "혼잡도 보통",
          fillColor: "#facc15",
          strokeColor: "#facc15",
          paths: [[
            { lat: 37.57, lng: 126.97 },
            { lat: 37.58, lng: 126.97 },
            { lat: 37.58, lng: 126.98 },
          ]],
        }]}
      />,
    );
    await waitFor(() => expect(leafletMocks.polygon).toHaveBeenCalled());
  });

});

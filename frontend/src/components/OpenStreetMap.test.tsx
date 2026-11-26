import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  buildOpenStreetMapLink,
  OpenStreetMap,
} from "./OpenStreetMap";

vi.mock("leaflet", () => ({
  map: vi.fn(() => ({ remove: vi.fn(), setView: vi.fn(), getZoom: () => 14 })),
  tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
  divIcon: vi.fn(() => ({})),
  marker: vi.fn(() => ({ bindTooltip: vi.fn().mockReturnThis(), addTo: vi.fn().mockReturnThis() })),
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

});

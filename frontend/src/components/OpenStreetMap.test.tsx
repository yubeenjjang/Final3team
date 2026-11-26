import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  buildOpenStreetMapEmbedUrl,
  OpenStreetMap,
} from "./OpenStreetMap";

describe("OpenStreetMap", () => {
  it("builds an embedded map URL with a marker", () => {
    const url = new URL(buildOpenStreetMapEmbedUrl({ lat: 37.5759, lng: 126.9768 }));
    expect(url.hostname).toBe("www.openstreetmap.org");
    expect(url.pathname).toBe("/export/embed.html");
    expect(url.searchParams.get("marker")).toBe("37.5759,126.9768");
    expect(url.searchParams.get("bbox")?.split(",")).toHaveLength(4);
  });

  it("renders the selected place in an iframe", () => {
    render(
      <OpenStreetMap
        center={{ lat: 37.5759, lng: 126.9768 }}
        title="광화문 겨울빛 축제"
      />,
    );
    expect(screen.getByTitle("광화문 겨울빛 축제 지도")).toHaveAttribute(
      "src",
      expect.stringContaining("marker=37.5759%2C126.9768"),
    );
  });
});

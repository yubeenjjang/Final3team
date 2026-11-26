"use client";

import { useEffect, useRef, useState } from "react";
import { ExternalLink } from "lucide-react";
import type { Map as LeafletMap, Marker as LeafletMarker } from "leaflet";
import type { KakaoMapPoint } from "./KakaoMap";

export function buildOpenStreetMapLink(point: KakaoMapPoint): string {
  return `https://www.openstreetmap.org/?mlat=${point.lat}&mlon=${point.lng}#map=14/${point.lat}/${point.lng}`;
}

export function OpenStreetMap({ center, title, markers = [], className = "h-80 w-full" }: {
  center: KakaoMapPoint;
  title: string;
  markers?: Array<KakaoMapPoint & { title: string; label: string }>;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const markersRef = useRef<LeafletMarker[]>([]);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void import("leaflet").then((leaflet) => {
      if (cancelled || !containerRef.current || mapRef.current) return;
      const map = leaflet.map(containerRef.current, {
        center: [center.lat, center.lng],
        zoom: 14,
        zoomControl: true,
        attributionControl: true,
      });
      leaflet.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 19,
      }).addTo(map);
      mapRef.current = map;
      setMapReady(true);
    });
    return () => {
      cancelled = true;
      markersRef.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // 지도 인스턴스는 한 번만 만들고 중심과 마커는 아래 effect에서 갱신합니다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const moveMap = () => mapRef.current?.setView(
      [center.lat, center.lng],
      mapRef.current.getZoom(),
      { animate: true },
    );
    if (mapRef.current) moveMap();
    else {
      const timer = window.setTimeout(moveMap, 0);
      return () => window.clearTimeout(timer);
    }
  }, [center.lat, center.lng, mapReady]);

  useEffect(() => {
    let cancelled = false;
    void import("leaflet").then((leaflet) => {
      const map = mapRef.current;
      if (cancelled || !map) return;
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = markers.map((point) => {
        const icon = leaflet.divIcon({
          className: "",
          html: `<span class="festival-map-marker" aria-hidden="true">${point.label}</span>`,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
        });
        return leaflet.marker([point.lat, point.lng], { icon, title: point.title })
          .bindTooltip(point.title, { direction: "top", offset: [0, -14] })
          .addTo(map);
      });
    });
    return () => { cancelled = true; };
  }, [mapReady, markers]);

  return (
    <div className="overflow-hidden rounded-card-lg border border-line-light bg-surface shadow-card">
      <div ref={containerRef} role="application" aria-label={`${title} 지도`} data-testid="openstreet-map-container" className={`relative z-0 ${className}`} />
      <div className="flex items-center justify-end px-3 py-2 text-[10px] text-muted">
        <a href={buildOpenStreetMapLink(center)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-bold text-ink hover:text-brand">
          크게 보기 <ExternalLink className="h-3 w-3" aria-hidden="true" />
        </a>
      </div>
    </div>
  );
}

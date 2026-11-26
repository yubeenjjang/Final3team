"use client";

import { useEffect, useRef, useState } from "react";
import { MapPinOff } from "lucide-react";
import {
  getKakaoJsKey,
  loadKakaoMaps,
  type KakaoMapInstance,
  type KakaoMarkerInstance,
  type KakaoPolylineInstance,
} from "@/lib/kakao";

export interface KakaoMapPoint {
  lat: number;
  lng: number;
}

export interface KakaoMapMarker extends KakaoMapPoint {
  title?: string;
}

export type KakaoMapPolyline = Array<[number, number]>;

export interface KakaoMapProps {
  center: KakaoMapPoint;
  markers?: KakaoMapMarker[];
  polylines?: KakaoMapPolyline[];
  level?: number;
  className?: string;
}

const FALLBACK_MESSAGE = "지도를 불러올 수 없어요(지도 키 확인)";

function resolveAccentStrokeColor(): string {
  if (typeof window === "undefined") {
    return "currentColor";
  }
  const value = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue("--color-brand")
    .trim();
  return value || "currentColor";
}

export function KakaoMap({
  center,
  markers = [],
  polylines = [],
  level = 4,
  className = "h-56 w-full",
}: KakaoMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<KakaoMapInstance | null>(null);
  const overlaysRef = useRef<{
    markers: KakaoMarkerInstance[];
    polylines: KakaoPolylineInstance[];
  }>({ markers: [], polylines: [] });
  // 마지막으로 화면 범위를 맞춘 기준(중심·확대 수준·경로). 마커만 바뀔 때는 범위를 다시 맞추지 않는다.
  const viewRef = useRef<{ key: string; fitted: boolean } | null>(null);

  const apiKey = getKakaoJsKey();
  const [failedKey, setFailedKey] = useState<string | null>(null);
  const loadFailed = !apiKey || failedKey === apiKey;

  useEffect(() => {
    if (!apiKey) {
      return;
    }

    let cancelled = false;

    loadKakaoMaps(apiKey)
      .then((maps) => {
        if (cancelled || !containerRef.current) {
          return;
        }

        const centerLatLng = new maps.LatLng(center.lat, center.lng);
        const viewKey = [
          center.lat,
          center.lng,
          level,
          polylines.map((path) => path.length).join("."),
        ].join("|");
        const viewChanged = viewRef.current?.key !== viewKey;
        if (!mapRef.current) {
          mapRef.current = new maps.Map(containerRef.current, {
            center: centerLatLng,
            level,
          });
        } else if (viewChanged) {
          mapRef.current.setCenter(centerLatLng);
          mapRef.current.setLevel(level);
        }
        if (viewChanged) {
          viewRef.current = { key: viewKey, fitted: false };
        }

        const map = mapRef.current;

        overlaysRef.current.markers.forEach((m) => m.setMap(null));
        overlaysRef.current.polylines.forEach((p) => p.setMap(null));

        const nextMarkers: KakaoMarkerInstance[] = [];
        const nextPolylines: KakaoPolylineInstance[] = [];
        const bounds = new maps.LatLngBounds();
        let pointCount = 0;

        for (const item of markers) {
          const position = new maps.LatLng(item.lat, item.lng);
          const marker = new maps.Marker({
            position,
            map,
            title: item.title,
          });
          nextMarkers.push(marker);
          bounds.extend(position);
          pointCount += 1;
        }

        const strokeColor = resolveAccentStrokeColor();
        for (const pathCoords of polylines) {
          if (pathCoords.length < 2) {
            continue;
          }
          const path = pathCoords.map(([lat, lng]) => {
            const point = new maps.LatLng(lat, lng);
            bounds.extend(point);
            pointCount += 1;
            return point;
          });
          const polyline = new maps.Polyline({
            path,
            map,
            strokeWeight: 5,
            strokeColor,
            strokeOpacity: 0.9,
            strokeStyle: "solid",
          });
          nextPolylines.push(polyline);
        }

        overlaysRef.current = {
          markers: nextMarkers,
          polylines: nextPolylines,
        };

        // 검색어 입력 등으로 마커 수만 바뀔 때 매번 setBounds하면 지도가 갑자기 확대·축소된다.
        // 중심·경로가 바뀐 뒤 처음 한 번만 범위를 맞춘다.
        if (pointCount >= 2 && viewRef.current && !viewRef.current.fitted) {
          map.setBounds(bounds);
          viewRef.current.fitted = true;
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFailedKey(apiKey);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [apiKey, center.lat, center.lng, level, markers, polylines]);

  if (loadFailed) {
    return (
      <div
        role="img"
        aria-label={FALLBACK_MESSAGE}
        className={`flex flex-col items-center justify-center gap-2 rounded-card border border-line-light bg-muted/15 px-4 text-center text-sm font-medium text-muted ${className}`}
      >
        <MapPinOff className="h-5 w-5 text-muted" aria-hidden="true" />
        <span>{FALLBACK_MESSAGE}</span>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      data-testid="kakao-map-container"
      className={`overflow-hidden rounded-card border border-line-light bg-surface ${className}`}
    />
  );
}

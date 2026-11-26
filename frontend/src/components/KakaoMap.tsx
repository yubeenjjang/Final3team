"use client";

import { useEffect, useRef, useState } from "react";
import {
  getKakaoJsKey,
  loadKakaoMaps,
  type KakaoMapInstance,
  type KakaoCustomOverlayInstance,
  type KakaoMarkerInstance,
  type KakaoPolygonInstance,
  type KakaoPolylineInstance,
} from "@/lib/kakao";
import { OpenStreetMap } from "./OpenStreetMap";
import { getMapMarkerIconMarkup, type MapMarkerIcon } from "./mapMarkerIcons";

export interface KakaoMapPoint {
  lat: number;
  lng: number;
}

export interface KakaoMapMarker extends KakaoMapPoint {
  id?: string;
  title?: string;
  label?: string;
  icon?: MapMarkerIcon;
  variant?: "festival" | "transport" | "food" | "safety";
  selected?: boolean;
}

export type KakaoMapPolyline = Array<[number, number]>;

export interface KakaoMapArea {
  id: string;
  label: string;
  paths: KakaoMapPoint[][];
  fillColor: string;
  strokeColor: string;
  fillOpacity?: number;
  strokeOpacity?: number;
  strokeWeight?: number;
}

export interface KakaoMapProps {
  center: KakaoMapPoint;
  markers?: KakaoMapMarker[];
  polylines?: KakaoMapPolyline[];
  areas?: KakaoMapArea[];
  level?: number;
  className?: string;
  onMarkerClick?: (marker: KakaoMapMarker) => void;
}

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
  areas = [],
  level = 4,
  className = "h-56 w-full",
  onMarkerClick,
}: KakaoMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<KakaoMapInstance | null>(null);
  const overlaysRef = useRef<{
    markers: Array<KakaoMarkerInstance | KakaoCustomOverlayInstance>;
    polylines: KakaoPolylineInstance[];
    areas: KakaoPolygonInstance[];
  }>({ markers: [], polylines: [], areas: [] });
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
        overlaysRef.current.areas.forEach((area) => area.setMap(null));

        const nextMarkers: Array<KakaoMarkerInstance | KakaoCustomOverlayInstance> = [];
        const nextPolylines: KakaoPolylineInstance[] = [];
        const nextAreas: KakaoPolygonInstance[] = [];
        const bounds = new maps.LatLngBounds();
        let pointCount = 0;

        for (const area of areas) {
          const paths = area.paths
            .filter((ring) => ring.length >= 3)
            .map((ring) => ring.map((point) => new maps.LatLng(point.lat, point.lng)));
          if (!paths.length) continue;
          const polygon = new maps.Polygon({
            path: paths,
            map,
            strokeWeight: area.strokeWeight ?? 2,
            strokeColor: area.strokeColor,
            strokeOpacity: area.strokeOpacity ?? 0.9,
            strokeStyle: "solid",
            fillColor: area.fillColor,
            fillOpacity: area.fillOpacity ?? 0.28,
          });
          nextAreas.push(polygon);
        }

        for (const item of markers) {
          const position = new maps.LatLng(item.lat, item.lng);
          const marker = item.variant && maps.CustomOverlay
            ? new maps.CustomOverlay({
                position,
                map,
                content: createMarkerElement(item, onMarkerClick),
                xAnchor: 0.5,
                yAnchor: 1,
                zIndex: item.variant === "festival" ? 20 : item.selected ? 15 : 10,
              })
            : new maps.Marker({
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
          areas: nextAreas,
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
  }, [apiKey, areas, center.lat, center.lng, level, markers, onMarkerClick, polylines]);

  if (loadFailed) {
    return (
      <OpenStreetMap
        center={center}
        title="축제 위치"
        markers={markers.map((marker) => ({
          ...marker,
          title: marker.title ?? "축제 위치",
          label: marker.label ?? "📍",
        }))}
        areas={areas}
        onMarkerClick={onMarkerClick}
        className={className}
      />
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

function createMarkerElement(
  marker: KakaoMapMarker,
  onMarkerClick?: (marker: KakaoMapMarker) => void,
): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = [
    "festival-map-marker",
    `festival-map-marker--${marker.variant}`,
    marker.selected ? "festival-map-marker--selected" : "",
  ].filter(Boolean).join(" ");
  const symbol = document.createElement("span");
  symbol.className = "festival-map-marker__symbol";
  const iconMarkup = getMapMarkerIconMarkup(marker.icon);
  if (iconMarkup) symbol.innerHTML = iconMarkup;
  else symbol.textContent = marker.label ?? "●";
  symbol.setAttribute("aria-hidden", "true");
  button.appendChild(symbol);
  button.title = marker.title ?? "지도 위치";
  button.setAttribute("aria-label", marker.title ?? "지도 위치");
  if (onMarkerClick) button.addEventListener("click", () => onMarkerClick(marker));
  return button;
}

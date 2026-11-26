import { apiGet } from "@/lib/api/client";
import { getFestivalCrowd } from "@/features/festivals/live-info/api";

export type FacilityCategory =
  | "toilet"
  | "parking"
  | "hospital"
  | "emergency"
  | "subway_station"
  | "bus_stop"
  | "bike_zone"
  | "taxi_stand"
  | "food"
  | "attraction";

export interface MapFacility {
  facility_id: string;
  category: FacilityCategory;
  name: string;
  lat: number;
  lng: number;
  distance_m: number;
  address?: string | null;
  source?: string | null;
  ref_code?: string | null;
  extra?: Record<string, string | number | boolean | null>;
}

export interface AvailableMapCrowd {
  available: true;
  level: "여유" | "보통" | "약간 붐빔" | "붐빔";
  color: "green" | "yellow" | "orange" | "red";
  areaName: string;
  message?: string | null;
  populationMin?: number | null;
  populationMax?: number | null;
  observedAt?: string | null;
  isEstimate?: boolean | null;
  stale?: boolean;
  center?: { lat: number; lng: number } | null;
  boundary: Array<Array<{ lat: number; lng: number }>>;
}

export interface UnavailableMapCrowd {
  available: false;
  reason: string;
  message?: string | null;
}

export type MapCrowd = AvailableMapCrowd | UnavailableMapCrowd;

interface FacilitiesResponse {
  items: MapFacility[];
}

export const FACILITY_GROUPS = {
  transport: ["subway_station", "bus_stop", "bike_zone", "taxi_stand"],
  food: ["food", "attraction"],
  safety: ["toilet", "parking", "hospital", "emergency"],
} as const satisfies Record<string, readonly FacilityCategory[]>;

export type FacilityGroup = keyof typeof FACILITY_GROUPS;

function mockFacilities(
  lat: number,
  lng: number,
  categories: readonly FacilityCategory[],
): MapFacility[] {
  const names: Record<FacilityCategory, readonly string[]> = {
    toilet: ["축제장 공중화장실", "한강공원 공중화장실"], parking: ["축제장 공영주차장", "인근 노상주차장"],
    hospital: ["지역 종합병원", "가까운 내과의원"], emergency: ["지역 응급의료센터", "24시간 응급실"],
    subway_station: ["주변 지하철역", "인근 환승역"], bus_stop: ["축제장 버스정류장", "인근 버스정류장"],
    bike_zone: ["공공자전거 대여소", "자전거 주차장"], taxi_stand: ["택시 승강장", "인근 택시 승강장"],
    food: ["축제장 맛집", "한강뷰 카페"], attraction: ["주변 전망 명소", "인근 문화공간"],
  };
  return categories.flatMap((category, categoryIndex) => names[category].map((name, itemIndex) => {
    const index = categoryIndex * 2 + itemIndex;
    const angle = (index / (categories.length * 2)) * Math.PI * 2 - Math.PI / 2;
    const radius = 0.004 + (index % 3) * 0.002;
    return { facility_id: `mock_${category}_${itemIndex}`, category, name,
      lat: lat + Math.sin(angle) * radius, lng: lng + Math.cos(angle) * radius,
      distance_m: 220 + index * 130 };
  }));
}

export async function listMapFacilities({
  festivalId,
  lat,
  lng,
  group,
  signal,
}: {
  festivalId: string;
  lat: number;
  lng: number;
  group: FacilityGroup;
  signal?: AbortSignal;
}): Promise<MapFacility[]> {
  const categories = FACILITY_GROUPS[group];
  if (
    process.env.NODE_ENV === "development" &&
    process.env.NEXT_PUBLIC_USE_MOCK_FESTIVALS === "1"
  ) {
    return mockFacilities(lat, lng, categories);
  }
  const response = await apiGet<FacilitiesResponse>(
    `/festivals/${encodeURIComponent(festivalId)}/facilities`,
    {
      query: {
        categories: categories.join(","),
        radius_m: 1500,
        limit_per_category: 10,
      },
      signal,
      timeoutMs: 12_000,
    },
  );
  return response.items;
}

export async function getMapCrowd(
  festivalId: string,
  signal?: AbortSignal,
): Promise<MapCrowd | null> {
  if (
    process.env.NODE_ENV === "development" &&
    process.env.NEXT_PUBLIC_USE_MOCK_FESTIVALS === "1"
  ) {
    return {
      available: true,
      level: "붐빔",
      color: "red",
      areaName: "축제장 주변",
      message: "축제장 주변이 붐비고 있어요.",
      populationMin: 4200,
      populationMax: 5600,
      observedAt: new Date().toISOString(),
      isEstimate: true,
        center: null,
      boundary: [],
    };
  }
  const response = await getFestivalCrowd(festivalId, signal);
  const nearby = response.nearby_areas
    ?.filter((item) => item.data)
    .sort((left, right) => left.distance_m - right.distance_m)[0];
  const area = nearby?.data ?? response.areas?.[0];
  return area
    ? {
        available: true,
        level: area.congest_level,
        color: area.congest_color,
        areaName: nearby?.area_name ?? area.area_name,
        message: area.congest_message,
        populationMin: area.population_min,
        populationMax: area.population_max,
        observedAt: area.observed_at,
        isEstimate: nearby?.is_estimate ?? response.is_estimate,
        stale: nearby?.status === "stale" || response.status === "stale",
        center: area.center ?? nearby?.center ?? null,
        boundary: area.boundary ?? nearby?.boundary ?? [],
      }
    : {
        available: false,
        reason: response.unsupported_reason === "outside_seoul"
          ? "서울 외 미지원"
          : response.unsupported_reason === "missing_coordinates"
            ? "위치 확인 필요"
            : response.unsupported_reason === "no_approved_mapping"
              ? "혼잡 연결 대기"
              : response.unsupported_reason === "no_nearby_areas"
                ? "주변 구역 없음"
                : "정보 없음",
        message: response.error?.message ?? response.notices?.[0] ?? null,
      };
}

export const FACILITY_LABELS: Record<FacilityCategory, string> = {
  toilet: "화장실",
  parking: "주차장",
  hospital: "병원",
  emergency: "응급실",
  subway_station: "지하철역",
  bus_stop: "버스정류장",
  bike_zone: "자전거주차장",
  taxi_stand: "택시승강장",
  food: "맛집·카페",
  attraction: "관광지",
};

export const FACILITY_SYMBOLS: Record<FacilityCategory, string> = {
  toilet: "🚻",
  parking: "P",
  hospital: "H",
  emergency: "+",
  subway_station: "🚇",
  bus_stop: "🚌",
  bike_zone: "🚲",
  taxi_stand: "🚕",
  food: "🍴",
  attraction: "★",
};

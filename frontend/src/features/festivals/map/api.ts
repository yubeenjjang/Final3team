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
  extra?: Record<string, string | number | boolean | null>;
}

export interface MapCrowd {
  level: "여유" | "보통" | "약간 붐빔" | "붐빔";
  color: "green" | "yellow" | "orange" | "red";
}

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
  return categories.map((category, index) => {
    const angle = (index / categories.length) * Math.PI * 2 - Math.PI / 2;
    const radius = 0.006 + (index % 2) * 0.002;
    return {
      facility_id: `mock_${category}_${index}`,
      category,
      name: `주변 ${FACILITY_LABELS[category]}`,
      lat: lat + Math.sin(angle) * radius,
      lng: lng + Math.cos(angle) * radius,
      distance_m: 300 + index * 140,
    };
  });
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
    return { level: "붐빔", color: "red" };
  }
  const response = await getFestivalCrowd(festivalId, signal);
  const area = response.nearby_areas?.find((item) => item.data)?.data ?? response.areas?.[0];
  return area
    ? { level: area.congest_level, color: area.congest_color }
    : null;
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

import type { FestivalListItem, FestivalPage, ListFestivalsQuery } from "./api";

const LAST_SYNCED_AT = "2026-11-25T09:00:00+09:00";

export const MOCK_FESTIVALS: FestivalListItem[] = [
  {
    festival_id: "fst_design_001",
    name: "운정호수공원 불꽃축제",
    region_code: "GYEONGGI",
    venue_name: "운정호수공원",
    lat: 37.7168,
    lng: 126.7518,
    start_date: "2026-11-20",
    end_date: "2026-11-30",
    event_status: "ongoing",
    thumbnail_url: "/mock/festivals/night.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_002",
    name: "해운대 빛축제",
    region_code: "BUSAN",
    venue_name: "해운대해수욕장",
    lat: 35.1587,
    lng: 129.1604,
    start_date: "2026-11-25",
    end_date: "2026-12-28",
    event_status: "ongoing",
    thumbnail_url: "/mock/festivals/lights.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_003",
    name: "포천빛스타",
    region_code: "GYEONGGI",
    venue_name: "포천 아트밸리",
    lat: 37.9235,
    lng: 127.2366,
    start_date: "2026-11-22",
    end_date: "2026-12-14",
    event_status: "ongoing",
    thumbnail_url: "/mock/festivals/lights.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_004",
    name: "라코니 뮤직쇼 앤 스트릿 페스티벌",
    region_code: "BUSAN",
    venue_name: "부산시민공원",
    lat: 35.1686,
    lng: 129.0571,
    start_date: "2026-11-18",
    end_date: "2026-12-05",
    event_status: "ongoing",
    thumbnail_url: "/mock/festivals/night.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_005",
    name: "양평빙송어축제",
    region_code: "GYEONGGI",
    venue_name: "수미마을",
    lat: 37.4724,
    lng: 127.6391,
    start_date: "2026-12-05",
    end_date: "2027-01-18",
    event_status: "upcoming",
    thumbnail_url: "/mock/festivals/snow.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_006",
    name: "논산 양촌곶감축제",
    region_code: "CHUNGNAM",
    venue_name: "양촌면 체육공원",
    lat: 36.1389,
    lng: 127.2332,
    start_date: "2026-12-11",
    end_date: "2026-12-13",
    event_status: "upcoming",
    thumbnail_url: "/mock/festivals/flowers.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_007",
    name: "서울빛초롱축제",
    region_code: "SEOUL",
    venue_name: "청계천 일대",
    lat: 37.5692,
    lng: 126.9784,
    start_date: "2026-12-11",
    end_date: "2027-01-03",
    event_status: "upcoming",
    thumbnail_url: "/mock/festivals/lights.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_008",
    name: "청계천의 빛",
    region_code: "SEOUL",
    venue_name: "청계광장",
    lat: 37.5698,
    lng: 126.9775,
    start_date: "2026-12-11",
    end_date: "2026-12-31",
    event_status: "upcoming",
    thumbnail_url: "/mock/festivals/night.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_009",
    name: "평창 대관령 눈꽃축제",
    region_code: "GANGWON",
    venue_name: "대관령 송천 일원",
    lat: 37.6869,
    lng: 128.7584,
    start_date: "2026-12-18",
    end_date: "2027-01-10",
    event_status: "upcoming",
    thumbnail_url: "/mock/festivals/snow.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_010",
    name: "제주 동백꽃 겨울정원",
    region_code: "JEJU",
    venue_name: "휴애리 자연생활공원",
    lat: 33.3085,
    lng: 126.6344,
    start_date: "2026-12-20",
    end_date: "2027-02-08",
    event_status: "upcoming",
    thumbnail_url: "/mock/festivals/flowers.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_011",
    name: "인천 개항장 야행",
    region_code: "INCHEON",
    venue_name: "인천 개항장 문화지구",
    lat: 37.4737,
    lng: 126.6214,
    start_date: "2026-12-24",
    end_date: "2026-12-27",
    event_status: "upcoming",
    thumbnail_url: "/mock/festivals/night.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
  {
    festival_id: "fst_design_012",
    name: "전주 한옥마을 겨울마실",
    region_code: "JEONBUK",
    venue_name: "전주 한옥마을",
    lat: 35.8149,
    lng: 127.1513,
    start_date: "2026-12-26",
    end_date: "2027-01-17",
    event_status: "upcoming",
    thumbnail_url: "/mock/festivals/flowers.svg",
    image_credit: "놀다가 디자인 mock",
    source: "tourapi",
    last_synced_at: LAST_SYNCED_AT,
  },
];

export function listMockFestivals(query: ListFestivalsQuery): FestivalPage {
  const statuses = String(query.status ?? "ongoing,upcoming").split(",");
  const search = query.q?.trim().toLocaleLowerCase("ko-KR");

  const filtered = MOCK_FESTIVALS.filter((festival) => {
    if (query.region && query.region !== "ALL" && festival.region_code !== query.region) return false;
    if (!statuses.includes(festival.event_status)) return false;
    if (!search) return true;
    return `${festival.name} ${festival.venue_name ?? ""}`.toLocaleLowerCase("ko-KR").includes(search);
  });

  filtered.sort((left, right) => {
    if (query.sort === "name") return left.name.localeCompare(right.name, "ko-KR");
    const direction = query.sort === "-start_date" ? -1 : 1;
    return (left.start_date ?? "9999-12-31").localeCompare(right.start_date ?? "9999-12-31") * direction;
  });

  const page = query.page ?? 1;
  const pageSize = query.page_size ?? 20;
  const start = (page - 1) * pageSize;

  return {
    is_mock: true,
    items: filtered.slice(start, start + pageSize),
    total: filtered.length,
    page,
    page_size: pageSize,
  };
}

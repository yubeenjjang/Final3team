export interface KakaoLatLng {
  getLat(): number;
  getLng(): number;
}

export interface KakaoLatLngBounds {
  extend(latlng: KakaoLatLng): void;
}

export interface KakaoMapInstance {
  setCenter(latlng: KakaoLatLng): void;
  setLevel(level: number): void;
  setBounds(bounds: KakaoLatLngBounds): void;
}

export interface KakaoMarkerInstance {
  setMap(map: KakaoMapInstance | null): void;
}

export interface KakaoCustomOverlayInstance {
  setMap(map: KakaoMapInstance | null): void;
}

export interface KakaoPolylineInstance {
  setMap(map: KakaoMapInstance | null): void;
}

export interface KakaoMapsNamespace {
  load(callback: () => void): void;
  LatLng: new (lat: number, lng: number) => KakaoLatLng;
  LatLngBounds: new () => KakaoLatLngBounds;
  Map: new (
    container: HTMLElement,
    options: { center: KakaoLatLng; level?: number },
  ) => KakaoMapInstance;
  Marker: new (options: {
    position: KakaoLatLng;
    map?: KakaoMapInstance;
    title?: string;
  }) => KakaoMarkerInstance;
  CustomOverlay: new (options: {
    position: KakaoLatLng;
    map?: KakaoMapInstance;
    content: HTMLElement;
    xAnchor?: number;
    yAnchor?: number;
    zIndex?: number;
  }) => KakaoCustomOverlayInstance;
  Polyline: new (options: {
    path: KakaoLatLng[];
    map?: KakaoMapInstance;
    strokeWeight?: number;
    strokeColor?: string;
    strokeOpacity?: number;
    strokeStyle?: string;
  }) => KakaoPolylineInstance;
}

export interface KakaoSDK {
  maps?: KakaoMapsNamespace;
}

declare global {
  interface Window {
    kakao?: KakaoSDK;
  }
}

const KAKAO_SDK_ATTR = "data-kakao-maps-sdk";

let kakaoMapsPromise: Promise<KakaoMapsNamespace> | null = null;

export function getKakaoJsKey(): string {
  return (process.env.NEXT_PUBLIC_KAKAO_JS_KEY ?? "").trim();
}

export function buildKakaoSdkUrl(appKey: string): string {
  return `//dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(appKey)}&autoload=false`;
}

export function loadKakaoMaps(
  explicitKey?: string,
): Promise<KakaoMapsNamespace> {
  const key = (explicitKey ?? getKakaoJsKey()).trim();
  if (!key) {
    return Promise.reject(new Error("KAKAO_KEY_MISSING"));
  }

  if (typeof window === "undefined" || typeof document === "undefined") {
    return Promise.reject(new Error("KAKAO_BROWSER_ONLY"));
  }

  if (kakaoMapsPromise) return kakaoMapsPromise;
  if (window.kakao?.maps?.Map) return Promise.resolve(window.kakao.maps);

  const existingScript = document.querySelector<HTMLScriptElement>(
    `script[${KAKAO_SDK_ATTR}="true"]`,
  );
  const script = existingScript ?? document.createElement("script");

  kakaoMapsPromise = new Promise<KakaoMapsNamespace>((resolve, reject) => {
    let settled = false;
    const timeout = setTimeout(() => fail("KAKAO_SDK_TIMEOUT"), 10_000);

    function cleanup() {
      settled = true;
      clearTimeout(timeout);
      script.onload = null;
      script.onerror = null;
    }

    function fail(code: string) {
      if (settled) return;
      cleanup();
      script.remove();
      delete window.kakao;
      reject(new Error(code));
    }

    function finishLoad() {
      const maps = window.kakao?.maps;
      if (!maps || typeof maps.load !== "function") {
        fail("KAKAO_SDK_INVALID");
        return;
      }

      try {
        maps.load(() => {
          if (settled) return;
          const loaded = window.kakao?.maps;
          if (!loaded?.Map) {
            fail("KAKAO_SDK_INVALID");
            return;
          }
          cleanup();
          resolve(loaded);
        });
      } catch {
        fail("KAKAO_SDK_INVALID");
      }
    }

    script.onload = finishLoad;
    script.onerror = () => fail("KAKAO_SDK_LOAD_FAILED");
    if (!existingScript) {
      script.src = buildKakaoSdkUrl(key);
      script.async = true;
      script.setAttribute(KAKAO_SDK_ATTR, "true");
      document.head.appendChild(script);
    } else if (window.kakao?.maps) {
      finishLoad();
    }
  }).catch((error: unknown) => {
    kakaoMapsPromise = null;
    throw error;
  });

  return kakaoMapsPromise;
}

export function resetKakaoLoaderForTest(): void {
  kakaoMapsPromise = null;
}

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

  if (window.kakao?.maps?.Map) {
    return Promise.resolve(window.kakao.maps);
  }

  if (kakaoMapsPromise) {
    return kakaoMapsPromise;
  }

  kakaoMapsPromise = new Promise<KakaoMapsNamespace>((resolve, reject) => {
    const finishLoad = () => {
      const maps = window.kakao?.maps;
      if (!maps || typeof maps.load !== "function") {
        kakaoMapsPromise = null;
        reject(new Error("KAKAO_SDK_INVALID"));
        return;
      }
      maps.load(() => {
        if (window.kakao?.maps) {
          resolve(window.kakao.maps);
        } else {
          kakaoMapsPromise = null;
          reject(new Error("KAKAO_SDK_INVALID"));
        }
      });
    };

    const existingScript = document.querySelector<HTMLScriptElement>(
      `script[${KAKAO_SDK_ATTR}="true"]`,
    );

    if (existingScript) {
      if (window.kakao?.maps) {
        finishLoad();
        return;
      }
      existingScript.addEventListener("load", finishLoad, { once: true });
      existingScript.addEventListener(
        "error",
        () => {
          kakaoMapsPromise = null;
          reject(new Error("KAKAO_SDK_LOAD_FAILED"));
        },
        { once: true },
      );
      return;
    }

    const script = document.createElement("script");
    script.src = buildKakaoSdkUrl(key);
    script.async = true;
    script.setAttribute(KAKAO_SDK_ATTR, "true");
    script.onload = finishLoad;
    script.onerror = () => {
      script.remove();
      kakaoMapsPromise = null;
      reject(new Error("KAKAO_SDK_LOAD_FAILED"));
    };
    document.head.appendChild(script);
  });

  return kakaoMapsPromise;
}

export function resetKakaoLoaderForTest(): void {
  kakaoMapsPromise = null;
}

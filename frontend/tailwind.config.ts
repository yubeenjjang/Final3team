import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#F6F6F7",
        bg: "#FFFFFF",
        surface: "#FFFFFF",
        "surface-soft": "#FFF0F5",
        "surface-muted": "#F5F6F8",
        "banner-dark": "#343536",
        "screen-dark": "#292A2D",
        ink: "#343536",
        muted: "#6B7078",
        brand: "#F74F85",
        "brand-soft": "#FFE8F0",
        "line-light": "#E7E8EC",
        "line-strong": "#D9DBE1",
        "crowd-green": "#8FDCBE",
        "crowd-yellow": "#F5D778",
        "crowd-orange": "#F6B978",
        "crowd-red": "#F19AA1",
      },
      fontFamily: {
        sans: [
          "Pretendard Variable",
          "-apple-system",
          "BlinkMacSystemFont",
          "system-ui",
          "sans-serif",
        ],
        display: ["var(--font-outfit)", "Outfit", "Pretendard Variable", "sans-serif"],
      },
      borderRadius: {
        control: "12px",
        card: "14px",
        "card-lg": "20px",
        panel: "24px",
        nav: "28px",
        input: "25px",
        chip: "9999px",
      },
      maxWidth: {
        mobile: "390px",
      },
      boxShadow: {
        shell: "0 18px 54px rgba(52, 53, 54, 0.12)",
        card: "0 8px 24px rgba(52, 53, 54, 0.08)",
        nav: "0 -8px 28px rgba(52, 53, 54, 0.07)",
      },
    },
  },
  plugins: [],
};

export default config;

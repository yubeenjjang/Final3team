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
        bg: "#FFFFFF",
        surface: "#FFFFFF",
        "surface-soft": "#FFF0F5",
        "surface-muted": "#F5F6F8",
        "banner-dark": "#343536",
        ink: "#343536",
        muted: "#6B7078",
        brand: "#F74F85",
        "line-light": "#E7E8EC",
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
        card: "14px",
        input: "25px",
        chip: "9999px",
      },
    },
  },
  plugins: [],
};

export default config;

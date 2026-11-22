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
        bg: "#FCFCFF",
        surface: "#FFFFFF",
        "surface-soft": "#FEEEF2",
        ink: "#0A101F",
        muted: "#6B7280",
        brand: "#F0145F",
        accent: "#7C36FC",
        neon: "#C8FF2F",
        "dark-bg": "#0D0D0C",
        "dark-surface": "#1E1D1C",
        "dark-muted": "#A9A9A9",
        "line-light": "#E5E7EB",
        "line-dark": "#2E2D2C",
        "crowd-green": "#22C55E",
        "crowd-yellow": "#EAB308",
        "crowd-orange": "#F97316",
        "crowd-red": "#EF4444",
      },
      fontFamily: {
        sans: [
          "Pretendard",
          "-apple-system",
          "BlinkMacSystemFont",
          "system-ui",
          "sans-serif",
        ],
        display: ["var(--font-outfit)", "Outfit", "Pretendard", "sans-serif"],
      },
      borderRadius: {
        card: "18px",
        input: "25px",
        chip: "9999px",
      },
    },
  },
  plugins: [],
};

export default config;

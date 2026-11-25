import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  use: {
    baseURL: "http://localhost:3000",
    viewport: { width: 402, height: 874 },
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: [
    {
      command: "cd ../backend && uv run --with-requirements api/requirements.txt uvicorn api.main:app --port 8000",
      url: "http://localhost:8000/api/v1/health",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_API_BASE: "http://localhost:8000/api/v1",
        NEXT_PUBLIC_SHOW_MOCK_TOOLS: "1",
      },
    },
  ],
});

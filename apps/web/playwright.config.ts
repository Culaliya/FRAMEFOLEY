import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video:
      process.env.CAPTURE_EVIDENCE === "1"
        ? { mode: "on", size: { width: 1280, height: 720 } }
        : "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], browserName: "chromium" } },
    { name: "tablet", use: { ...devices["iPad Pro 11"], browserName: "chromium" } },
    { name: "mobile", use: { ...devices["iPhone 14"], browserName: "chromium" } },
  ],
  webServer: [
    {
      command:
        "cd ../.. && GENERATION_MODE=demo FRAMEFOLEY_DATA_DIR=.data/e2e FRONTEND_ORIGIN=http://127.0.0.1:3000 .venv/bin/uvicorn framefoley_api.main:app --host 127.0.0.1 --port 8000 --no-access-log",
      url: "http://127.0.0.1:8000/readyz",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "pnpm dev",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: true,
      timeout: 120_000,
    }
  ],
});

import { defineConfig, devices } from "@playwright/test";

const publicBaseUrl = process.env.PUBLIC_BASE_URL;
const publicVerification = process.env.PUBLIC_SUBMISSION_VERIFY === "1";
const phase2MasterCapture = process.env.CAPTURE_PHASE2_MASTER === "1";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: publicBaseUrl ?? "http://127.0.0.1:3000",
    trace: publicVerification ? "off" : "retain-on-failure",
    screenshot: "only-on-failure",
    video:
      phase2MasterCapture
        ? { mode: "on", size: { width: 1920, height: 1080 } }
        : process.env.CAPTURE_EVIDENCE === "1"
          ? { mode: "on", size: { width: 1280, height: 720 } }
        : "retain-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        browserName: "chromium",
        viewport: phase2MasterCapture ? { width: 1920, height: 1080 } : undefined,
      },
    },
    { name: "tablet", use: { ...devices["iPad Pro 11"], browserName: "chromium" } },
    { name: "mobile", use: { ...devices["iPhone 14"], browserName: "chromium" } },
  ],
  webServer: publicBaseUrl ? undefined : [
    {
      command:
        "cd ../.. && .venv/bin/python scripts/build_test_live_proof_fixture.py --output .data/e2e/objects && GENERATION_MODE=demo FRAMEFOLEY_DATA_DIR=.data/e2e FRONTEND_ORIGIN=http://127.0.0.1:3000 .venv/bin/uvicorn framefoley_api.main:app --host 127.0.0.1 --port 8000 --no-access-log",
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

import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const ENABLED = process.env.PUBLIC_SUBMISSION_VERIFY === "1";
const CAPTURE = process.env.CAPTURE_PHASE2_PUBLIC === "1";
const SCREENSHOTS = resolve(process.cwd(), "../../evidence/phase2/screenshots");

function failOnConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

async function capture(page: Page, name: string, fullPage = false) {
  if (!CAPTURE) return;
  mkdirSync(SCREENSHOTS, { recursive: true });
  await page.screenshot({
    path: resolve(SCREENSHOTS, name),
    fullPage,
    animations: "disabled",
  });
}

async function openLiveProof(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByTestId("open-live-proof").click();
  await expect(page).toHaveURL(/\/projects\/prj_[a-z0-9]+\/generate/, { timeout: 110_000 });
  await expect(page.getByTestId("live-proof-banner")).toBeVisible();
  await expect(page.getByText("0 PROVIDER CALLS", { exact: true })).toBeVisible();
}

async function completeLiveProof(page: Page): Promise<void> {
  await page.getByTestId("open-audition").click();
  const event = page.locator(".audition-event").first();
  await expect(event.locator(".candidate-card")).toHaveCount(2);
  await event.locator(".candidate-card").first().getByRole("button", { name: "SOLO" }).click();
  await page.getByRole("button", { name: "STOP ALL" }).click();
  await event.locator(".candidate-card").first().getByRole("button", { name: "APPROVE" }).click();
  await page.getByTestId("open-mix").click();
  await page.getByTestId("render-mix").click();
  await expect(page.getByTestId("open-export")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("open-export").click();
  await page.getByTestId("export-kit").click();
  await expect(page.getByTestId("download-kit")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("link", { name: /INSPECT PROVENANCE/ }).click();
  await expect(page.locator(".provenance-record")).toHaveCount(2);
  await expect(page.getByText("Manifest.verify(): TRUE").first()).toBeVisible();
}

test("public Phase 2 landing and LIVE replay pass on every judge viewport", async ({
  page,
}, testInfo) => {
  test.skip(!ENABLED, "Public submission verification is explicit.");
  test.setTimeout(240_000);
  const consoleErrors = failOnConsoleErrors(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /YOUR GAME/ })).toBeVisible();
  await expect(page.locator(".instant-comparison")).toBeVisible();
  await expect(page.getByText("UPLOAD MY CLIP", { exact: true })).toHaveCount(0);
  await page.getByTestId("comparison-mix").click();
  await expect(page.getByTestId("comparison-mix")).toHaveAttribute("aria-pressed", "true");
  await page.getByTestId("comparison-silent").click();
  await capture(page, `01-landing-${testInfo.project.name}.png`);

  await page.goto("/projects/new");
  await expect(page.getByTestId("custom-upload-info")).toBeVisible();
  await expect(page.getByTestId("custom-upload")).toHaveCount(0);

  await openLiveProof(page);
  await capture(page, `02-live-proof-${testInfo.project.name}.png`, true);
  await completeLiveProof(page);
  await capture(page, `03-provenance-${testInfo.project.name}.png`, true);
  expect(consoleErrors).toEqual([]);
});

test("public CACHED DEMO remains complete", async ({ page }, testInfo) => {
  test.skip(!ENABLED || testInfo.project.name !== "desktop", "The three-cue public flow runs once.");
  test.setTimeout(240_000);
  const consoleErrors = failOnConsoleErrors(page);
  await page.goto("/projects/new");
  await page.getByTestId("start-demo").click();
  await expect(page).toHaveURL(/\/cue/);
  await page.getByTestId("lock-cues").click();
  await page.getByTestId("generate-candidates").click();
  await expect(page.getByTestId("open-audition")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("open-audition").click();
  const events = page.locator(".audition-event");
  await expect(events).toHaveCount(3);
  for (let index = 0; index < 3; index += 1) {
    await events.nth(index).locator(".candidate-card").first().getByRole("button", { name: "APPROVE" }).click();
  }
  await page.getByTestId("open-mix").click();
  await page.getByTestId("render-mix").click();
  await expect(page.getByTestId("open-export")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("open-export").click();
  await page.getByTestId("export-kit").click();
  await expect(page.getByTestId("download-kit")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("link", { name: /INSPECT PROVENANCE/ }).click();
  await expect(page.locator(".provenance-record")).toHaveCount(6);
  await capture(page, "04-cached-demo-provenance-desktop.png", true);
  expect(consoleErrors).toEqual([]);
});

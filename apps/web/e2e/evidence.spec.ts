import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const CAPTURE = process.env.CAPTURE_EVIDENCE === "1";
const EVIDENCE_ROOT = resolve(process.cwd(), "../../evidence/final");
const SCREENSHOTS = resolve(EVIDENCE_ROOT, "screenshots");
const VIDEO = resolve(EVIDENCE_ROOT, "video");

function prepareDirectories() {
  mkdirSync(SCREENSHOTS, { recursive: true });
  mkdirSync(VIDEO, { recursive: true });
}

async function shot(page: Page, name: string, fullPage = false) {
  await page.screenshot({
    path: resolve(SCREENSHOTS, name),
    fullPage,
    animations: "disabled",
  });
}

async function hold(milliseconds: number) {
  await new Promise((resolveHold) => setTimeout(resolveHold, milliseconds));
}

test("capture the complete narrated-demo visual spine", async ({ page }, testInfo) => {
  test.skip(!CAPTURE || testInfo.project.name !== "desktop", "Evidence capture is explicit.");
  test.setTimeout(300_000);
  prepareDirectories();

  await page.goto("/");
  await expect(page.getByRole("heading", { name: /YOUR GAME/ })).toBeVisible();
  await shot(page, "01-landing-desktop.png");
  await hold(10_000);

  await page.goto("/projects/new");
  await shot(page, "02-source-desktop.png");
  await hold(10_000);

  await page.getByTestId("start-demo").click();
  await expect(page).toHaveURL(/\/cue/);
  await shot(page, "03-cue-desktop.png");
  await hold(18_000);

  await page.getByTestId("lock-cues").click();
  await expect(page).toHaveURL(/\/generate/);
  await shot(page, "04-generation-locked-desktop.png");
  await hold(8_000);
  await page.getByTestId("generate-candidates").click();
  await expect(page.getByTestId("open-audition")).toBeVisible({ timeout: 30_000 });
  await shot(page, "05-generation-complete-desktop.png", true);
  await hold(12_000);

  await page.getByTestId("open-audition").click();
  await expect(page.getByRole("heading", { name: /A sound can be valid/ })).toBeVisible();
  await shot(page, "06-audition-desktop.png", true);
  await hold(15_000);
  const events = page.locator(".audition-event");
  await events.first().locator(".candidate-card").first().getByRole("button", { name: "SOLO" }).click();
  await hold(4_000);
  await events.first().locator(".candidate-card").nth(1).getByRole("button", { name: "IN FRAME" }).click();
  await hold(14_000);
  await page.getByRole("button", { name: "STOP ALL" }).click();
  for (let index = 0; index < 3; index += 1) {
    await events
      .nth(index)
      .locator(".candidate-card")
      .first()
      .getByRole("button", { name: "APPROVE" })
      .click();
  }
  await shot(page, "07-audition-approved-desktop.png", true);
  await hold(10_000);

  await page.getByTestId("open-mix").click();
  await shot(page, "08-mix-before-desktop.png", true);
  await hold(12_000);
  await page.getByTestId("render-mix").click();
  await expect(page.getByTestId("open-export")).toBeVisible({ timeout: 30_000 });
  await shot(page, "09-mix-rendered-desktop.png", true);
  await hold(15_000);

  await page.getByTestId("open-export").click();
  await shot(page, "10-export-ready-to-pack-desktop.png", true);
  await hold(10_000);
  await page.getByTestId("export-kit").click();
  await expect(page.getByTestId("download-kit")).toBeVisible({ timeout: 30_000 });
  await shot(page, "11-export-complete-desktop.png", true);
  await hold(12_000);

  await page.getByRole("link", { name: /INSPECT PROVENANCE/ }).click();
  await expect(page.locator(".provenance-record")).toHaveCount(6);
  await shot(page, "12-provenance-desktop.png", true);
  await hold(18_000);

  const recording = page.video();
  await page.close();
  if (!recording) throw new Error("Playwright did not start the evidence recording.");
  await recording.saveAs(resolve(VIDEO, "framefoley-demo-raw.webm"));
});

test("capture the tablet editorial layout", async ({ page }, testInfo) => {
  test.skip(!CAPTURE || testInfo.project.name !== "tablet", "Evidence capture is explicit.");
  prepareDirectories();
  await page.goto("/");
  await shot(page, "13-landing-tablet.png");
  await page.goto("/projects/new");
  await page.getByTestId("start-demo").click();
  await expect(page).toHaveURL(/\/cue/);
  await shot(page, "14-cue-tablet.png", true);
});

test("capture the phone cue contract", async ({ page }, testInfo) => {
  test.skip(!CAPTURE || testInfo.project.name !== "mobile", "Evidence capture is explicit.");
  prepareDirectories();
  await page.goto("/projects/new");
  await page.getByTestId("start-demo").click();
  await expect(page).toHaveURL(/\/cue/);
  await shot(page, "15-cue-phone.png", true);
});

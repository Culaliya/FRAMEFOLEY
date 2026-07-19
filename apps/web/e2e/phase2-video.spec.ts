import { expect, test, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const CAPTURE = process.env.CAPTURE_PHASE2_MASTER === "1";
const PUBLIC = Boolean(process.env.PUBLIC_BASE_URL);
const VIDEO_DIR = resolve(process.cwd(), "../../evidence/phase2/video");

async function hold(milliseconds: number) {
  await new Promise((resolveHold) => setTimeout(resolveHold, milliseconds));
}

function runtimeErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

test("capture the fresh public Phase 2 competition master spine", async ({ page }, testInfo) => {
  test.skip(!CAPTURE || !PUBLIC || testInfo.project.name !== "desktop", "Public master capture is explicit.");
  test.setTimeout(600_000);
  mkdirSync(VIDEO_DIR, { recursive: true });
  const errors = runtimeErrors(page);
  const startedAt = Date.now();
  const marks: Array<{ name: string; seconds: number }> = [];
  const mark = (name: string) => marks.push({ name, seconds: (Date.now() - startedAt) / 1000 });

  mark("comparison");
  await page.goto("/");
  await expect(page.locator(".instant-comparison")).toBeVisible();
  await page.getByTestId("comparison-silent").click();
  await page.getByRole("button", { name: "REPLAY" }).click();
  await hold(3_600);
  await page.getByTestId("comparison-mix").click();
  await page.getByRole("button", { name: "REPLAY" }).click();
  await hold(4_000);

  mark("problem");
  await page.locator(".hero-copy").hover();
  await hold(9_000);

  mark("cues");
  await page.getByRole("link", { name: /BUILD THE 3-CUE DEMO/ }).click();
  await expect(page.getByTestId("start-demo")).toBeVisible();
  await hold(2_000);
  await page.getByTestId("start-demo").click();
  await expect(page).toHaveURL(/\/cue/, { timeout: 110_000 });
  await expect(page.locator(".event-tabs button")).toHaveCount(3, { timeout: 110_000 });
  await page.locator(".event-inspector").scrollIntoViewIfNeeded();
  await hold(14_000);

  mark("cached_pipeline");
  await page.getByTestId("lock-cues").click();
  await expect(page).toHaveURL(/\/generate/, { timeout: 110_000 });
  await page.getByTestId("generate-candidates").click();
  await expect(page.getByTestId("open-audition")).toBeVisible({ timeout: 110_000 });
  await page.locator(".demo-disclosure").first().scrollIntoViewIfNeeded();
  await hold(15_000);

  mark("audition");
  await page.getByTestId("open-audition").click();
  const cachedEvents = page.locator(".audition-event");
  await expect(cachedEvents).toHaveCount(3, { timeout: 110_000 });
  const firstCached = cachedEvents.first();
  await firstCached.locator(".candidate-card").first().getByRole("button", { name: "SOLO" }).click();
  await hold(2_500);
  await page.getByRole("button", { name: "STOP ALL" }).click();
  await firstCached.locator(".candidate-card").nth(1).getByRole("button", { name: "IN FRAME" }).click();
  await hold(4_000);
  await page.getByRole("button", { name: "STOP ALL" }).click();
  for (let index = 0; index < 3; index += 1) {
    const card = cachedEvents.nth(index).locator(".candidate-card").first();
    await card.getByRole("button", { name: "APPROVE" }).click();
    await expect(card.locator(".approve-button")).toHaveText("APPROVED", { timeout: 30_000 });
  }
  await hold(4_000);

  mark("mix");
  await page.getByTestId("open-mix").click();
  await page.getByTestId("render-mix").click();
  await expect(page.getByTestId("open-export")).toBeVisible({ timeout: 110_000 });
  await page.locator(".render-comparison").scrollIntoViewIfNeeded();
  await hold(9_000);

  mark("live_proof");
  await page.goto("/");
  await page.getByTestId("open-live-proof").click();
  await expect(page.getByTestId("live-proof-banner")).toBeVisible({ timeout: 110_000 });
  await hold(5_000);
  await page.getByTestId("open-audition").click();
  const proofEvent = page.locator(".audition-event").first();
  await expect(proofEvent.locator(".candidate-card")).toHaveCount(2, { timeout: 110_000 });
  await proofEvent.locator(".candidate-card").first().getByRole("button", { name: "SOLO" }).click();
  await hold(2_500);
  await page.getByRole("button", { name: "STOP ALL" }).click();
  await proofEvent.locator(".candidate-card").nth(1).getByRole("button", { name: "SOLO" }).click();
  await hold(2_500);
  await page.getByRole("button", { name: "STOP ALL" }).click();
  await proofEvent.locator(".candidate-card").first().getByRole("button", { name: "APPROVE" }).click();
  await hold(3_000);

  mark("export_provenance");
  await page.getByTestId("open-mix").click();
  await page.getByTestId("render-mix").click();
  await expect(page.getByTestId("open-export")).toBeVisible({ timeout: 110_000 });
  await page.getByTestId("open-export").click();
  await page.getByTestId("export-kit").click();
  await expect(page.getByTestId("download-kit")).toBeVisible({ timeout: 110_000 });
  await hold(4_000);
  await page.getByRole("link", { name: /INSPECT PROVENANCE/ }).click();
  await expect(page.locator(".provenance-record")).toHaveCount(2, { timeout: 110_000 });
  await page.locator(".provenance-record").first().scrollIntoViewIfNeeded();
  await expect(page.getByText("Manifest.verify(): TRUE").first()).toBeVisible();
  await hold(9_000);

  mark("close");
  await page.locator(".provenance-hero").scrollIntoViewIfNeeded();
  await hold(6_000);
  mark("end");
  expect(errors).toEqual([]);

  const recording = page.video();
  await page.close();
  if (!recording) throw new Error("Playwright did not start the Phase 2 recording.");
  const rawVideo = resolve(VIDEO_DIR, "framefoley-phase2-public-raw.webm");
  await recording.saveAs(rawVideo);
  const recordedDuration = Number(
    execFileSync(
      "ffprobe",
      [
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        rawVideo,
      ],
      { encoding: "utf8" },
    ).trim(),
  );
  const finalMark = marks.at(-1)?.seconds ?? 0;
  expect(recordedDuration).toBeGreaterThanOrEqual(finalMark - 1);
  writeFileSync(
    resolve(VIDEO_DIR, "framefoley-phase2-capture-timings.json"),
    `${JSON.stringify({ schemaVersion: 1, marks }, null, 2)}\n`,
    "utf8",
  );
});

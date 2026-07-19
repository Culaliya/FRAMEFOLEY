import { expect, test, type Page } from "@playwright/test";

function failOnConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

async function createDemoAndLockCues(page: Page): Promise<void> {
  await page.goto("/projects/new");
  await page.getByTestId("start-demo").click();
  await expect(page).toHaveURL(/\/projects\/prj_[a-z0-9]+\/cue/);
  await expect(page.getByRole("heading", { name: /Mark the frame/ })).toBeVisible();
  await page.getByTestId("lock-cues").click();
  await expect(page).toHaveURL(/\/generate/);
}

test("desktop demo completes audition, mix, export, and provenance", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "The full spine runs once on desktop.");
  const consoleErrors = failOnConsoleErrors(page);
  await createDemoAndLockCues(page);

  await page.getByTestId("generate-candidates").click();
  await expect(page.getByTestId("open-audition")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("open-audition").click();
  await expect(page.getByRole("heading", { name: /A sound can be valid/ })).toBeVisible();

  const firstEvent = page.locator(".audition-event").first();
  await firstEvent.locator(".candidate-card").first().getByRole("button", { name: "SOLO" }).click();
  await firstEvent.locator(".candidate-card").nth(1).getByRole("button", { name: "IN FRAME" }).click();
  await page.getByRole("button", { name: "STOP ALL" }).click();

  const events = page.locator(".audition-event");
  await expect(events).toHaveCount(3);
  for (let index = 0; index < 3; index += 1) {
    await events
      .nth(index)
      .locator(".candidate-card")
      .first()
      .getByRole("button", { name: "APPROVE" })
      .click();
  }
  await expect(page.getByTestId("open-mix")).toBeEnabled();
  await page.getByTestId("open-mix").click();

  await page.getByTestId("render-mix").click();
  await expect(page.getByTestId("open-export")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("open-export").click();
  await page.getByTestId("export-kit").click();
  await expect(page.getByTestId("download-kit")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("LOCAL OBJECT / MOCKED")).toBeVisible();
  await page.getByRole("link", { name: /INSPECT PROVENANCE/ }).click();
  await expect(page.getByRole("heading", { name: /EVERY SOUND/ })).toBeVisible();
  await expect(page.locator(".provenance-record")).toHaveCount(6);
  expect(consoleErrors).toEqual([]);
});

test("public demo explains custom upload without exposing a dead-end control", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Capability-gated upload is exercised once.");
  const consoleErrors = failOnConsoleErrors(page);
  await page.goto("/projects/new");
  await expect(page.getByTestId("custom-upload-info")).toBeVisible();
  await expect(page.getByText("Available in a self-hosted LIVE build.")).toBeVisible();
  await expect(page.getByTestId("custom-upload")).toHaveCount(0);
  await expect(page.locator('input[type="file"]')).toHaveCount(0);
  expect(consoleErrors).toEqual([]);
});

test("landing comparison requires a gesture for sound and keeps one timeline", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Audio comparison behavior runs once.");
  const consoleErrors = failOnConsoleErrors(page);
  await page.goto("/");
  const video = page.locator(".comparison-stage video");
  await expect(video).toBeVisible();
  await expect.poll(() => video.evaluate((element: HTMLVideoElement) => element.muted)).toBe(true);
  const before = await video.evaluate((element: HTMLVideoElement) => element.currentTime);
  await page.getByTestId("comparison-mix").click();
  await expect.poll(() => video.evaluate((element: HTMLVideoElement) => element.muted)).toBe(false);
  const after = await video.evaluate((element: HTMLVideoElement) => element.currentTime);
  expect(Math.abs(after - before)).toBeLessThan(0.75);
  await page.getByTestId("comparison-silent").click();
  await expect.poll(() => video.evaluate((element: HTMLVideoElement) => element.muted)).toBe(true);
  await page.getByTestId("comparison-mix").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("comparison-mix")).toHaveAttribute("aria-pressed", "true");
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, value: true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect.poll(() => video.evaluate((element: HTMLVideoElement) => element.paused && element.muted)).toBe(true);
  expect(consoleErrors).toEqual([]);
});

test("LIVE evidence replay completes with zero provider calls", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "The complete replay spine runs once.");
  const consoleErrors = failOnConsoleErrors(page);
  await page.goto("/");
  await page.getByTestId("open-live-proof").click();
  await expect(page).toHaveURL(/\/projects\/prj_[a-z0-9]+\/generate/, { timeout: 30_000 });
  await expect(page.getByTestId("live-proof-banner")).toBeVisible();
  await expect(page.getByText("2 / 2 VERIFIED")).toBeVisible();
  await expect(page.getByText("0 PROVIDER CALLS", { exact: true })).toBeVisible();
  await page.getByTestId("open-audition").click();
  const event = page.locator(".audition-event").first();
  await expect(event.locator(".candidate-card")).toHaveCount(2);
  await event.locator(".candidate-card").first().getByRole("button", { name: "SOLO" }).click();
  await event.locator(".candidate-card").nth(1).getByRole("button", { name: "IN FRAME" }).click();
  await page.getByRole("button", { name: "STOP ALL" }).click();
  await event.locator(".candidate-card").first().getByRole("button", { name: "APPROVE" }).click();
  await page.getByTestId("open-mix").click();
  await page.getByTestId("render-mix").click();
  await expect(page.getByTestId("open-export")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("open-export").click();
  await page.getByTestId("export-kit").click();
  await expect(page.getByTestId("download-kit")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("link", { name: /INSPECT PROVENANCE/ }).click();
  await expect(page.getByText("THE PROVIDER CALLS HAPPENED DURING THE RECORDED LIVE GATE — NOT NOW.")).toBeVisible();
  await expect(page.getByText("Manifest.verify(): TRUE").first()).toBeVisible();
  await expect(page.locator(".provenance-record")).toHaveCount(2);
  expect(consoleErrors).toEqual([]);
});

test("mobile cue markers are keyboard adjustable and actions remain reachable", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "Mobile-specific cue contract.");
  const consoleErrors = failOnConsoleErrors(page);
  await page.goto("/projects/new");
  await page.getByTestId("start-demo").click();
  await expect(page).toHaveURL(/\/cue/);
  const marker = page.locator(".event-marker").first();
  await marker.focus();
  const before = await marker.getAttribute("aria-label");
  await page.keyboard.press("ArrowRight");
  const after = await marker.getAttribute("aria-label");
  expect(after).not.toBe(before);
  await expect(page.getByTestId("lock-cues")).toBeInViewport();
  const target = await page.getByTestId("lock-cues").boundingBox();
  expect(target?.height).toBeGreaterThanOrEqual(44);
  expect(consoleErrors).toEqual([]);
});

test("tablet keeps the editorial monitor and phase rail visible", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "tablet", "Tablet layout contract.");
  const consoleErrors = failOnConsoleErrors(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /YOUR GAME/ })).toBeVisible();
  await expect(page.locator(".instant-comparison")).toBeVisible();
  await expect(page.getByTestId("open-live-proof")).toBeVisible();
  await page.goto("/projects/new");
  await expect(page.getByText("JELLY RELAY")).toBeVisible();
  expect(consoleErrors).toEqual([]);
});

test("reduced motion disables decorative loops", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Reduced-motion audit runs once.");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const paused = await page
    .locator(".comparison-stage video")
    .evaluate((element: HTMLVideoElement) => element.paused);
  expect(paused).toBe(true);
});

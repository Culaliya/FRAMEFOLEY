import { describe, expect, it, vi } from "vitest";

import { SoundLabUnavailableError, waitForSoundLab, type ReadinessStage } from "./readiness";

const READY = {
  status: "ready" as const,
  generationMode: "demo" as const,
  storage: "BACKBLAZE B2" as const,
  mediaTools: { ffmpeg: true, ffprobe: true },
  storageReady: true,
};

describe("bounded sound-lab readiness", () => {
  it("survives a simulated thirty-second cold start and then succeeds", async () => {
    let clock = 0;
    const stages: ReadinessStage[] = [];
    const result = await waitForSoundLab({
      fetchReadiness: vi.fn(async () =>
        clock >= 30_000 ? READY : { status: "not_ready" as const },
      ),
      now: () => clock,
      sleep: async (milliseconds) => {
        clock += milliseconds;
      },
      maxWaitMs: 90_000,
      onUpdate: (update) => stages.push(update.stage),
    });
    expect(result).toEqual(READY);
    expect(clock).toBeGreaterThanOrEqual(30_000);
    expect(clock).toBeLessThan(40_000);
    expect(stages.at(-1)).toBe("ready");
  });

  it("stops at the bounded timeout without looping forever", async () => {
    let clock = 0;
    const stages: ReadinessStage[] = [];
    const failure = await waitForSoundLab({
      fetchReadiness: async () => ({ status: "not_ready" }),
      now: () => clock,
      sleep: async (milliseconds) => {
        clock += milliseconds;
      },
      maxWaitMs: 30_000,
      onUpdate: (update) => stages.push(update.stage),
    }).catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(SoundLabUnavailableError);
    expect(clock).toBe(30_000);
    expect(stages.at(-1)).toBe("timed_out");
  });

  it("does not expose a raw network exception", async () => {
    let clock = 0;
    const failure = await waitForSoundLab({
      fetchReadiness: async () => {
        throw new Error("Authorization: Bearer secret-stack-detail");
      },
      now: () => clock,
      sleep: async (milliseconds) => {
        clock += milliseconds;
      },
      maxWaitMs: 1_000,
    }).catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(SoundLabUnavailableError);
    expect(String(failure)).not.toContain("Bearer");
    expect(String(failure)).not.toContain("stack");
  });
});

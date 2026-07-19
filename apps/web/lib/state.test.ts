import type { SseEvent } from "@framefoley/contracts";
import { beforeEach, describe, expect, it } from "vitest";

import { initialProgress, progressReducer } from "./progress";
import { stylePreset } from "./style-presets";
import { readProjectToken, removeProjectToken, storeProjectToken } from "./token-store";

describe("browser-local project state", () => {
  beforeEach(() => window.sessionStorage.clear());

  it("stores project tokens only in the current browser session", () => {
    storeProjectToken("prj_123", "signed-token");
    expect(readProjectToken("prj_123")).toBe("signed-token");
    removeProjectToken("prj_123");
    expect(readProjectToken("prj_123")).toBeNull();
  });

  it("reduces real SSE state without discarding candidate identity", () => {
    const event: SseEvent = {
      type: "candidate.status",
      projectId: "prj_123",
      eventId: "evt_123",
      candidateId: "cand_123",
      at: "2026-07-19T00:00:00Z",
      payload: { status: "stored" },
    };
    const next = progressReducer(initialProgress, event);
    expect(next.events).toEqual([event]);
    expect(next.latestByCandidate.cand_123).toEqual(event);
  });

  it("selects only a declared style preset", () => {
    expect(stylePreset("paper_signal")?.title).toBe("PAPER SIGNAL");
    expect(stylePreset("custom")).toBeUndefined();
  });
});

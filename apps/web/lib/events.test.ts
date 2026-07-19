import type { SoundEvent } from "@framefoley/contracts";
import { describe, expect, it } from "vitest";

import { canAddEvent, clampTimestamp, eventSlug, orderEvents } from "./events";

function soundEvent(id: string, timestampSeconds: number): SoundEvent {
  return {
    id,
    slug: id,
    title: id,
    type: "impact",
    timestampSeconds,
    targetDurationSeconds: 0.5,
    intensity: "medium",
    candidates: [],
  };
}

describe("event rail rules", () => {
  it("orders markers without mutating the source list", () => {
    const source = [soundEvent("late", 8), soundEvent("early", 1)];
    expect(orderEvents(source).map((event) => event.id)).toEqual(["early", "late"]);
    expect(source[0].id).toBe("late");
  });

  it("enforces the three-event limit and source bounds", () => {
    expect(canAddEvent([soundEvent("one", 1), soundEvent("two", 2)])).toBe(true);
    expect(
      canAddEvent([soundEvent("one", 1), soundEvent("two", 2), soundEvent("three", 3)]),
    ).toBe(false);
    expect(clampTimestamp(-4, 12)).toBe(0);
    expect(clampTimestamp(18, 12)).toBe(11.99);
  });

  it("creates deterministic safe slugs from cue titles", () => {
    expect(eventSlug("Glass lands!", 1)).toBe("glass-lands");
    expect(eventSlug("月亮", 2)).toBe("sound-event-2");
  });
});

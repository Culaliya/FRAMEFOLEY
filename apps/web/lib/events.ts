import type { SoundEvent } from "@framefoley/contracts";

export const MAX_EVENTS = 3;

export function orderEvents(events: SoundEvent[]): SoundEvent[] {
  return [...events].sort((left, right) => left.timestampSeconds - right.timestampSeconds);
}

export function canAddEvent(events: SoundEvent[]): boolean {
  return events.length < MAX_EVENTS;
}

export function clampTimestamp(value: number, duration: number): number {
  return Math.min(Math.max(value, 0), Math.max(0, duration - 0.01));
}

export function eventId(): string {
  const bytes = new Uint8Array(6);
  crypto.getRandomValues(bytes);
  return `evt_${Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("")}`;
}

export function eventSlug(title: string, fallback: number): string {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
  return slug || `sound-event-${fallback}`;
}

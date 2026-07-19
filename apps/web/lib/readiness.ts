export interface ReadinessPayload {
  status: "ready" | "not_ready";
  generationMode?: "live" | "demo" | "disabled";
  storage?: "BACKBLAZE B2" | "MOCKED LOCAL STORAGE";
  mediaTools?: { ffmpeg: boolean; ffprobe: boolean };
  storageReady?: boolean;
}

export type ReadinessStage =
  | "idle"
  | "contacting"
  | "checking_media"
  | "connecting_storage"
  | "ready"
  | "timed_out";

export interface ReadinessUpdate {
  stage: ReadinessStage;
  attempt: number;
  payload?: ReadinessPayload;
}

export class SoundLabUnavailableError extends Error {
  constructor() {
    super("The interactive sound lab is temporarily unavailable.");
    this.name = "SoundLabUnavailableError";
  }
}

interface WaitOptions {
  fetchReadiness: () => Promise<ReadinessPayload>;
  onUpdate?: (update: ReadinessUpdate) => void;
  maxWaitMs?: number;
  sleep?: (milliseconds: number) => Promise<void>;
  now?: () => number;
}

const defaultSleep = (milliseconds: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

export async function waitForSoundLab({
  fetchReadiness,
  onUpdate,
  maxWaitMs = 90_000,
  sleep = defaultSleep,
  now = Date.now,
}: WaitOptions): Promise<ReadinessPayload> {
  const startedAt = now();
  let delayMs = 1_000;
  let attempt = 0;
  while (now() - startedAt <= maxWaitMs) {
    attempt += 1;
    onUpdate?.({ stage: "contacting", attempt });
    try {
      const payload = await fetchReadiness();
      if (payload.mediaTools?.ffmpeg && payload.mediaTools.ffprobe) {
        onUpdate?.({ stage: "checking_media", attempt, payload });
      }
      if (payload.storageReady && payload.storage) {
        onUpdate?.({ stage: "connecting_storage", attempt, payload });
      }
      if (
        payload.status === "ready" &&
        payload.mediaTools?.ffmpeg === true &&
        payload.mediaTools.ffprobe === true &&
        payload.storageReady === true
      ) {
        onUpdate?.({ stage: "ready", attempt, payload });
        return payload;
      }
    } catch {
      // Network and cold-start details are intentionally not exposed to the browser UI.
    }
    const remaining = maxWaitMs - (now() - startedAt);
    if (remaining <= 0) break;
    await sleep(Math.min(delayMs, remaining));
    delayMs = Math.min(delayMs * 2, 10_000);
  }
  onUpdate?.({ stage: "timed_out", attempt });
  throw new SoundLabUnavailableError();
}

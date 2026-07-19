"use client";

import { useCallback, useState } from "react";

import { api, type ReadinessContract } from "@/lib/api";
import {
  SoundLabUnavailableError,
  waitForSoundLab,
  type ReadinessStage,
} from "@/lib/readiness";

export function useSoundLabReadiness() {
  const [stage, setStage] = useState<ReadinessStage>("idle");
  const [payload, setPayload] = useState<ReadinessContract | null>(null);

  const ensureReady = useCallback(async (): Promise<boolean> => {
    try {
      const result = await waitForSoundLab({
        fetchReadiness: api.readiness,
        onUpdate: (update) => {
          setStage(update.stage);
          if (update.payload) setPayload(update.payload);
        },
      });
      setPayload(result);
      return true;
    } catch (caught) {
      setStage("timed_out");
      if (!(caught instanceof SoundLabUnavailableError)) return false;
      return false;
    }
  }, []);

  const reset = useCallback(() => {
    setStage("idle");
    setPayload(null);
  }, []);

  return { stage, payload, ensureReady, reset };
}

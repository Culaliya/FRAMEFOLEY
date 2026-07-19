"use client";

import { Database, ExternalLink, RefreshCw, ServerCog, Wrench } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef } from "react";

import type { ReadinessContract } from "@/lib/api";
import type { ReadinessStage } from "@/lib/readiness";

const VIDEO_URL =
  "https://raw.githubusercontent.com/Culaliya/FRAMEFOLEY/main/evidence/phase2/video/framefoley-phase2-demo.mp4";
const REPOSITORY_URL = "https://github.com/Culaliya/FRAMEFOLEY";

export function ReadinessGate({
  stage,
  payload,
  onRetry,
}: {
  stage: ReadinessStage;
  payload: ReadinessContract | null;
  onRetry: () => void;
}) {
  const retryRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (stage === "timed_out") retryRef.current?.focus();
  }, [stage]);

  if (stage === "idle" || stage === "ready") return null;
  const timedOut = stage === "timed_out";
  return (
    <section className={`readiness-gate ${timedOut ? "is-timeout" : ""}`} aria-live="polite">
      <div className="readiness-orbit" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div>
        <p className="eyebrow">{timedOut ? "INTERACTIVE APP TEMPORARILY UNAVAILABLE" : "RENDER FREE COLD START"}</p>
        <h2>{timedOut ? "The proof is still public." : "WAKING THE SOUND LAB…"}</h2>
        <p>
          {timedOut
            ? "The API did not become ready within ninety seconds. No raw server error or credential was exposed."
            : "The private media service may need a moment after inactivity. This check stops automatically."}
        </p>
      </div>
      {!timedOut ? (
        <ol className="readiness-steps">
          <li data-state={stage === "contacting" ? "active" : "done"}>
            <ServerCog aria-hidden="true" /> CONTACTING API
          </li>
          {payload?.mediaTools ? (
            <li data-state={payload.mediaTools.ffmpeg && payload.mediaTools.ffprobe ? "done" : "wait"}>
              <Wrench aria-hidden="true" /> CHECKING MEDIA TOOLS
            </li>
          ) : null}
          {payload?.storageReady && payload.storage ? (
            <li data-state="done">
              <Database aria-hidden="true" /> {payload.storage === "BACKBLAZE B2"
                ? "CONNECTING PRIVATE B2 STORAGE"
                : "CONNECTING LOCAL TEST STORAGE"}
            </li>
          ) : null}
        </ol>
      ) : (
        <div className="readiness-fallbacks">
          <button ref={retryRef} type="button" className="button button-primary" onClick={onRetry}>
            <RefreshCw size={17} /> RETRY INTERACTIVE APP
          </button>
          <Link href={VIDEO_URL} className="button button-secondary" target="_blank">
            WATCH PUBLIC DEMO <ExternalLink size={15} />
          </Link>
          <Link href={REPOSITORY_URL} className="button button-ghost" target="_blank">
            OPEN SOURCE <ExternalLink size={15} />
          </Link>
        </div>
      )}
    </section>
  );
}

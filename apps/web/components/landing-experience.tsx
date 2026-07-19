"use client";

import {
  ArrowRight,
  Database,
  Fingerprint,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Volume2,
  VolumeX,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ReadinessGate } from "@/components/readiness-gate";
import { useSoundLabReadiness } from "@/hooks/use-readiness";
import { api, type CapabilityContract } from "@/lib/api";
import { storeProjectToken } from "@/lib/token-store";

const CUES = [
  { label: "GLASS LANDING", at: 1.6 },
  { label: "BUBBLE POP", at: 5.2 },
  { label: "ROUTE CONFIRM", at: 8.85 },
] as const;

export function LandingExperience() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [capabilities, setCapabilities] = useState<CapabilityContract | null>(null);
  const [mode, setMode] = useState<"silent" | "mix">("silent");
  const [playing, setPlaying] = useState(false);
  const [status, setStatus] = useState("Silent source. Approved Foley is off.");
  const [proofBusy, setProofBusy] = useState(false);
  const [proofError, setProofError] = useState<string | null>(null);
  const readiness = useSoundLabReadiness();

  useEffect(() => {
    let active = true;
    void api
      .capabilities()
      .then((value) => {
        if (active) setCapabilities(value);
      })
      .catch(() => {
        if (active) setCapabilities(null);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.muted = true;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reducedMotion) {
      void video.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
    }
    const stop = () => {
      video.muted = true;
      video.pause();
      setMode("silent");
      setPlaying(false);
      setStatus("Playback stopped. Approved Foley is off.");
    };
    const onVisibility = () => {
      if (document.hidden) stop();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      stop();
      video.removeAttribute("src");
      video.load();
    };
  }, []);

  async function chooseMode(next: "silent" | "mix") {
    const video = videoRef.current;
    if (!video) return;
    if (next === "silent") {
      video.muted = true;
      setMode("silent");
      setStatus("Silent source. Every audio output is muted.");
      return;
    }
    video.volume = 0.9;
    video.muted = false;
    setMode("mix");
    setStatus("Approved Foley mix playing on the same video timeline.");
    if (video.paused) {
      await video.play();
      setPlaying(true);
    }
  }

  async function togglePlayback() {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      await video.play();
      setPlaying(true);
    } else {
      video.pause();
      setPlaying(false);
    }
  }

  async function replay() {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = 0;
    await video.play();
    setPlaying(true);
    setStatus(
      mode === "mix"
        ? "Replaying all three approved Foley cues."
        : "Replaying the same twelve seconds silently.",
    );
  }

  async function openLiveProof() {
    if (proofBusy) return;
    setProofBusy(true);
    setProofError(null);
    const ready = await readiness.ensureReady();
    if (!ready) {
      setProofBusy(false);
      return;
    }
    try {
      const project = await api.createLiveProof();
      storeProjectToken(project.projectId, project.projectToken);
      router.push(`/projects/${project.projectId}/generate`);
    } catch {
      setProofError("The private LIVE evidence bundle is not ready to replay yet.");
      setProofBusy(false);
    }
  }

  return (
    <>
      <main>
        <section className="landing-hero phase2-hero">
          <div className="hero-copy">
            <p className="eyebrow">PROVENANCE-BACKED GAMEPLAY SOUND</p>
            <h1>
              YOUR GAME
              <br />
              ALREADY <span>MOVES.</span>
              <br />
              LET IT HIT.
            </h1>
            <p className="hero-deck">
              Mark the moments that matter. Compare two bounded candidates. Approve by ear, then
              export a provenance-backed sound kit.
            </p>
            <div className="hero-actions">
              <Link href="/projects/new?source=demo" className="button button-primary">
                BUILD THE 3-CUE DEMO <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <button
                type="button"
                className="button button-ghost"
                onClick={() => void openLiveProof()}
                disabled={proofBusy || capabilities?.liveProofReplayAvailable === false}
                data-testid="open-live-proof"
              >
                {proofBusy ? <span className="button-loader" /> : <ShieldCheck size={17} />}
                OPEN A VERIFIED LIVE RUN
              </button>
            </div>
            {capabilities?.customUploadCanComplete ? (
              <Link href="/projects/new?source=upload" className="self-hosted-upload-link">
                SELF-HOSTED LIVE BUILD: UPLOAD MY CLIP ↗
              </Link>
            ) : (
              <p className="microcopy">
                PUBLIC ZERO-SPEND DEMO · 3 EVENTS · 2 CANDIDATES EACH · PRIVATE B2 STORAGE
              </p>
            )}
            {proofError ? <p className="landing-proof-error" role="alert">{proofError}</p> : null}
          </div>

          <section className="instant-comparison" aria-labelledby="comparison-title">
            <div className="comparison-head">
              <div>
                <p className="eyebrow">HEAR THE DECISION</p>
                <h2 id="comparison-title">Same twelve seconds. Three approved sounds.</h2>
              </div>
              <span className={`truth-pill ${mode === "mix" ? "is-mix" : ""}`}>
                {mode === "mix" ? <Volume2 size={14} /> : <VolumeX size={14} />}
                {mode === "mix" ? "APPROVED MIX" : "SILENT"}
              </span>
            </div>
            <div className="comparison-stage">
              <video
                ref={videoRef}
                src="/jelly-relay-approved-mix.mp4"
                playsInline
                loop
                muted
                preload="metadata"
                poster="/jelly-relay-thumbnail.webp"
                aria-label="JELLY RELAY silent versus approved Foley comparison"
                onPlay={() => setPlaying(true)}
                onPause={() => setPlaying(false)}
              />
              <div className="comparison-timecode" aria-hidden="true">JELLY_RELAY / 00:12</div>
            </div>
            <div className="comparison-timeline" aria-label="Three Foley cue positions">
              {CUES.map((cue, index) => (
                <span
                  key={cue.label}
                  className="comparison-cue"
                  style={{ left: `${(cue.at / 12) * 100}%` }}
                  title={`${cue.label} at ${cue.at.toFixed(2)} seconds`}
                >
                  <i />
                  <small>{String(index + 1).padStart(2, "0")}</small>
                </span>
              ))}
            </div>
            <div className="comparison-cue-list" aria-hidden="true">
              {CUES.map((cue) => <span key={cue.label}>{cue.label}</span>)}
            </div>
            <div className="comparison-controls">
              <div className="comparison-toggle" role="group" aria-label="Comparison audio">
                <button
                  type="button"
                  aria-pressed={mode === "silent"}
                  onClick={() => void chooseMode("silent")}
                  data-testid="comparison-silent"
                >
                  <VolumeX size={15} /> SILENT SOURCE
                </button>
                <button
                  type="button"
                  aria-pressed={mode === "mix"}
                  onClick={() => void chooseMode("mix")}
                  data-testid="comparison-mix"
                >
                  <Volume2 size={15} /> APPROVED FOLEY MIX
                </button>
              </div>
              <button type="button" className="comparison-utility" onClick={() => void togglePlayback()}>
                {playing ? <Pause size={15} /> : <Play size={15} />} {playing ? "PAUSE" : "PLAY"}
              </button>
              <button type="button" className="comparison-utility" onClick={() => void replay()}>
                <RotateCcw size={15} /> REPLAY
              </button>
            </div>
            <p className="sr-only" aria-live="polite">{status}</p>
            <details className="production-disclosure">
              <summary>HOW THIS WAS PRODUCED</summary>
              <p>
                This landing preview uses the original JELLY RELAY motion and approved CACHED DEMO
                Foley. It demonstrates the creative decision; it is not a provider call made now.
              </p>
            </details>
          </section>
        </section>

        <ReadinessGate
          stage={readiness.stage}
          payload={readiness.payload}
          onRetry={() => void openLiveProof()}
        />

        <section className="trust-strip" aria-label="Production infrastructure">
          <article><Sparkles size={22} /><span>ORCHESTRATED WITH</span><strong>GENBLAZE</strong></article>
          <article><Database size={22} /><span>SYSTEM OF RECORD</span><strong>BACKBLAZE B2</strong></article>
          <article><Fingerprint size={22} /><span>CREATIVE AUTHORITY</span><strong>HUMAN APPROVAL</strong></article>
        </section>
      </main>
      <footer className="landing-footer">
        <span>FRAMEFOLEY / COMPETITION BUILD</span>
        <span>HUMAN APPROVAL REMAINS AUTHORITATIVE</span>
      </footer>
    </>
  );
}

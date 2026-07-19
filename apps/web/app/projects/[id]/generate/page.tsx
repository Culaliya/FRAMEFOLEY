"use client";

import type { GenerationCandidate, SseEvent } from "@framefoley/contracts";
import { ArrowRight, Check, CircleDashed, Database, Fingerprint, Sparkles } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useReducer, useRef, useState } from "react";

import {
  ProjectChrome,
  ProjectError,
  ProjectLoading,
} from "@/components/project-chrome";
import { InlineError, PageIntro, StatusStamp } from "@/components/ui";
import { useProject } from "@/hooks/use-project";
import { api, FrameFoleyApiError } from "@/lib/api";
import { initialProgress, progressReducer } from "@/lib/progress";

const PIPELINE = [
  "PROMPT LOCKED",
  "GENBLAZE RUN STARTED",
  "PROVIDER RESPONDED",
  "ASSET STORED",
  "MANIFEST CHECKED",
  "AUDIO INSPECTED",
  "REPAIR / RETRY / PASS",
] as const;

function stage(candidate: GenerationCandidate | undefined, index: number): "done" | "active" | "wait" {
  if (!candidate) return index === 0 ? "done" : "wait";
  const completed = [
    true,
    candidate.status !== "queued",
    Boolean(candidate.rawAssetKey),
    Boolean(candidate.rawAssetKey),
    Boolean(candidate.manifestUri),
    Boolean(candidate.qcBefore),
    candidate.status === "ready" || candidate.status === "failed",
  ];
  if (completed[index]) return "done";
  if (index === completed.findIndex((value) => !value)) return "active";
  return "wait";
}

function CandidatePipeline({
  candidate,
  variant,
}: {
  candidate?: GenerationCandidate;
  variant: "clean" | "character";
}) {
  return (
    <article className={`pipeline-candidate ${candidate?.status === "failed" ? "failed" : ""}`}>
      <header>
        <span className="candidate-letter">{variant === "clean" ? "A" : "B"}</span>
        <div>
          <strong>{variant === "clean" ? "CLEAN / COMPACT" : "CHARACTER / TEXTURE"}</strong>
          <small>{candidate?.sourceLabel ?? "AWAITING GENERATION"}</small>
        </div>
        <span className="candidate-status">{candidate?.status.toUpperCase() ?? "LOCKED"}</span>
      </header>
      <ol>
        {PIPELINE.map((label, index) => {
          const state = stage(candidate, index);
          const displayLabel =
            label === "GENBLAZE RUN STARTED" && candidate?.sourceLabel === "CACHED DEMO"
              ? "DEMO CACHE LOCATED"
              : label === "PROVIDER RESPONDED" && candidate?.sourceLabel === "CACHED DEMO"
                ? "ORIGINAL CACHE LOADED"
                : label === "MANIFEST CHECKED" && candidate?.sourceLabel === "CACHED DEMO"
                  ? "CACHE RECORD LABELED"
                  : label;
          return (
            <li key={label} data-state={state}>
              {state === "done" ? (
                <Check size={14} aria-hidden="true" />
              ) : (
                <CircleDashed size={14} aria-hidden="true" />
              )}
              <span>{displayLabel}</span>
            </li>
          );
        })}
      </ol>
      {candidate?.error ? (
        <p className="candidate-error">{candidate.error.code}: {candidate.error.message}</p>
      ) : null}
    </article>
  );
}

export default function GeneratePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const state = useProject(id);
  const abortRef = useRef<AbortController | null>(null);
  const [progress, dispatch] = useReducer(progressReducer, initialProgress);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (state.loading) return <ProjectLoading />;
  if (!state.project || state.error) return <ProjectError message={state.error ?? "Unknown project."} />;
  const project = state.project;
  const ready = ["audition_ready", "generation_partial"].includes(project.state);

  async function generate() {
    if (!state.token) return;
    setBusy(true);
    setError(null);
    const controller = new AbortController();
    abortRef.current = controller;
    void api.stream(id, state.token, controller.signal, (event: SseEvent) => dispatch(event)).catch(
      (caught: unknown) => {
        if (!(caught instanceof DOMException && caught.name === "AbortError")) return;
      },
    );
    try {
      const envelope = await api.generate(id, state.token, crypto.randomUUID());
      state.apply(envelope);
    } catch (caught) {
      setError(
        caught instanceof FrameFoleyApiError
          ? `${caught.message} · ${caught.requestId}`
          : "Candidate generation stopped.",
      );
    } finally {
      controller.abort();
      setBusy(false);
    }
  }

  return (
    <ProjectChrome project={project} active="generate">
      <PageIntro
        step="PIPELINE / SIX BOUNDED CANDIDATES"
        title="Every sound earns its place on the rail."
        copy="Status only advances after the actual provider, storage, manifest, and deterministic audio checks complete."
      />
      <InlineError message={error} />

      <section className="generation-summary">
        <div>
          <Sparkles aria-hidden="true" />
          <span>GENERATION MODE</span>
          <strong>{project.generationMode.toUpperCase()}</strong>
        </div>
        <div>
          <Database aria-hidden="true" />
          <span>DURABLE TARGET</span>
          <strong>{state.storageLabel ?? "STORAGE UNAVAILABLE"}</strong>
        </div>
        <div>
          <Fingerprint aria-hidden="true" />
          <span>TECHNICAL GATE</span>
          <strong>QC + SHA-256</strong>
        </div>
        <div className="quota-block">
          <span>LIVE GENERATION</span>
          <strong>6 CANDIDATES MAX</strong>
          <small>1 controlled retry per candidate · project budget {project.retryBudgetRemaining}</small>
        </div>
      </section>

      {project.generationMode === "demo" ? (
        <div className="demo-disclosure">
          <StatusStamp label="CACHED DEMO" tone="cyan" icon="storage" />
          <p>
            These six original bundled sounds exercise the real QC, repair, storage, render, and
            export path. They are never represented as live provider calls or canonical manifests.
          </p>
        </div>
      ) : null}

      {state.storageLabel === "MOCKED LOCAL STORAGE" ? (
        <div className="demo-disclosure">
          <StatusStamp label="MOCKED STORAGE" tone="steel" icon="storage" />
          <p>
            This local run stores project objects on disk for reproducible development. It is not
            evidence that these objects reached Backblaze B2.
          </p>
        </div>
      ) : null}

      <section className="pipeline-console" aria-live="polite">
        <div className="console-head">
          <span>EVENT / VARIANT</span>
          <span>VERIFIED EXECUTION LOG</span>
        </div>
        {project.events.map((soundEvent, eventIndex) => (
          <div className="pipeline-event" key={soundEvent.id}>
            <header>
              <span>{String(eventIndex + 1).padStart(2, "0")}</span>
              <div>
                <h2>{soundEvent.title}</h2>
                <p>{soundEvent.timestampSeconds.toFixed(2)} SEC · {soundEvent.type.toUpperCase()} · {soundEvent.targetDurationSeconds.toFixed(2)} SEC TARGET</p>
              </div>
            </header>
            <div className="pipeline-pair">
              <CandidatePipeline
                variant="clean"
                candidate={soundEvent.candidates.find((candidate) => candidate.variant === "clean")}
              />
              <CandidatePipeline
                variant="character"
                candidate={soundEvent.candidates.find(
                  (candidate) => candidate.variant === "character",
                )}
              />
            </div>
          </div>
        ))}
      </section>

      {progress.events.length > 0 ? (
        <aside className="live-log" aria-label="Recent pipeline messages">
          <span className="eyebrow">LIVE EVENT LOG</span>
          {progress.events.slice(-6).map((event, index) => (
            <code key={`${event.at}-${index}`}>
              {event.type} / {event.candidateId ?? event.projectId} / {String(event.payload.status ?? event.payload.state ?? "updated")}
            </code>
          ))}
        </aside>
      ) : null}

      <div className="sticky-action">
        <div>
          <span className="eyebrow">{ready ? "PIPELINE COMPLETE" : "READY TO GENERATE"}</span>
          <strong>{ready ? "CHOOSE BY EAR, NOT BY SCORE" : `${project.events.length * 2} BOUNDED CANDIDATES`}</strong>
        </div>
        {ready ? (
          <button
            type="button"
            className="button button-primary"
            onClick={() => router.push(`/projects/${id}/audition`)}
            data-testid="open-audition"
          >
            OPEN THE AUDITION <ArrowRight size={18} />
          </button>
        ) : (
          <button
            type="button"
            className="button button-primary"
            disabled={busy || project.generationMode === "disabled"}
            onClick={generate}
            data-testid="generate-candidates"
          >
            {busy ? <span className="button-loader dark" /> : <Sparkles size={18} />}
            {busy ? "RUNNING VERIFIED PIPELINE" : "GENERATE SIX CANDIDATES"}
          </button>
        )}
      </div>
    </ProjectChrome>
  );
}

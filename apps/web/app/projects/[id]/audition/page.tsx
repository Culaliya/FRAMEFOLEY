"use client";

import type { GenerationCandidate } from "@framefoley/contracts";
import { Check, Pause, Play, SlidersHorizontal, Volume2, VolumeX } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  ProjectChrome,
  ProjectError,
  ProjectLoading,
} from "@/components/project-chrome";
import { HashValue, InlineError, PageIntro, StatusStamp } from "@/components/ui";
import { useProject } from "@/hooks/use-project";
import { api, FrameFoleyApiError } from "@/lib/api";
import { AuditionEngine } from "@/lib/audition-engine";
import { formatTime } from "@/lib/format";

function CandidateCard({
  candidate,
  audioUrl,
  waveformUrl,
  selected,
  approved,
  busy,
  onSelect,
  onSolo,
  onContext,
  onApprove,
}: {
  candidate: GenerationCandidate;
  audioUrl?: string;
  waveformUrl?: string;
  selected: boolean;
  approved: boolean;
  busy: boolean;
  onSelect: () => void;
  onSolo: () => void;
  onContext: () => void;
  onApprove: () => void;
}) {
  const qc = candidate.qcAfter ?? candidate.qcBefore;
  return (
    <article className={`candidate-card ${selected ? "selected" : ""} ${approved ? "approved" : ""}`}>
      <button type="button" className="candidate-select" onClick={onSelect} aria-pressed={selected}>
        <span className="candidate-letter">{candidate.variant === "clean" ? "A" : "B"}</span>
        <span>
          <strong>{candidate.variant === "clean" ? "CLEAN / COMPACT" : "CHARACTER / TEXTURE"}</strong>
          <small>{candidate.sourceLabel}</small>
        </span>
        {approved ? <StatusStamp label="APPROVED" tone="lime" /> : null}
      </button>

      <div className="waveform-frame">
        {waveformUrl ? (
          // Waveforms are generated from the approved audio derivative, not decorative art.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={waveformUrl} alt={`Waveform for ${candidate.variant} candidate`} />
        ) : (
          <span>WAVEFORM UNAVAILABLE</span>
        )}
        <code>{qc ? `${qc.durationSeconds.toFixed(3)} SEC` : "—"}</code>
      </div>

      <div className="candidate-badges">
        <StatusStamp label={qc?.verdict.toUpperCase() ?? "UNCHECKED"} tone="lime" />
        {candidate.repairs.length ? <StatusStamp label="REPAIRED" tone="coral" /> : null}
        <StatusStamp
          label={candidate.manifestVerified ? "MANIFEST VERIFIED" : "CACHE RECORD"}
          tone={candidate.manifestVerified ? "cyan" : "steel"}
          icon="shield"
        />
      </div>

      {candidate.repairs.length ? (
        <p className="repair-note">
          <strong>TECHNICAL REPAIR</strong> Trim / gain / format was corrected. Generated content
          was not replaced.
        </p>
      ) : null}

      <dl className="candidate-metrics">
        <div><dt>PEAK</dt><dd>{qc?.peakDbfs.toFixed(2) ?? "—"} dBFS</dd></div>
        <div><dt>RMS</dt><dd>{qc?.rmsDbfs.toFixed(2) ?? "—"} dBFS</dd></div>
        <div><dt>FORMAT</dt><dd>{qc ? `${qc.sampleRateHz / 1000}K / ${qc.channels}CH` : "—"}</dd></div>
      </dl>

      <div className="candidate-provenance">
        <span>{candidate.provider}</span>
        <span>{candidate.model}</span>
        <HashValue value={candidate.assetSha256} label="ASSET" />
      </div>

      <div className="candidate-actions">
        <button type="button" onClick={onSolo} disabled={!audioUrl || busy}>
          <Play size={15} fill="currentColor" /> SOLO
        </button>
        <button type="button" onClick={onContext} disabled={!audioUrl || busy}>
          <Play size={15} /> IN FRAME
        </button>
        <button type="button" className="approve-button" onClick={onApprove} disabled={busy}>
          <Check size={16} /> {approved ? "APPROVED" : "APPROVE"}
        </button>
      </div>
    </article>
  );
}

export default function AuditionPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const state = useProject(id);
  const videoRef = useRef<HTMLVideoElement>(null);
  const engineRef = useRef<AuditionEngine | null>(null);
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.9);
  const [error, setError] = useState<string | null>(null);

  function engine(): AuditionEngine {
    engineRef.current ??= new AuditionEngine();
    return engineRef.current;
  }

  useEffect(() => {
    const activeEngine = new AuditionEngine();
    engineRef.current = activeEngine;
    const video = videoRef.current;
    return () => {
      void activeEngine?.dispose(video ?? undefined);
      engineRef.current = null;
    };
  }, []);

  if (state.loading) return <ProjectLoading />;
  if (!state.project || state.error) return <ProjectError message={state.error ?? "Unknown project."} />;
  const project = state.project;
  if (!project.source) return <ProjectError message="The source clip is missing." />;
  const allApproved = project.events.every((event) => event.approvedCandidateId);

  async function play(
    eventId: string,
    candidate: GenerationCandidate,
    context: boolean,
    timestamp: number,
  ) {
    if (!candidate.approvedWavKey) return;
    const url = state.assetUrls[candidate.approvedWavKey];
    if (!url) return;
    setBusyKey(`${eventId}:${candidate.id}`);
    setError(null);
    try {
      engine().setMuted(muted);
      engine().setVolume(volume);
      if (context && videoRef.current) await engine().playInContext(url, timestamp, videoRef.current);
      else await engine().playSolo(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Audio playback stopped.");
    } finally {
      setBusyKey(null);
    }
  }

  async function approve(eventId: string, candidateId: string) {
    if (!state.token) return;
    setBusyKey(`${eventId}:${candidateId}`);
    setError(null);
    try {
      const envelope = await api.approve(id, state.token, eventId, candidateId);
      state.apply(envelope);
    } catch (caught) {
      setError(
        caught instanceof FrameFoleyApiError
          ? `${caught.message} · ${caught.requestId}`
          : "Approval could not be stored.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <ProjectChrome project={project} active="audition">
      <PageIntro
        step="03 / AUDITION"
        title="A sound can be valid and still be wrong for the frame. Choose by ear."
        copy="Technical QC keeps broken files out. Creative approval stays with you. Nothing plays until you ask."
      />
      <InlineError message={error} />

      <section className="audition-monitor panel-rule">
        <div className="panel-topline">
          <span>IN-CONTEXT MONITOR</span>
          <span>NO AUTOPLAY</span>
        </div>
        <div className="audition-video-wrap">
          <video
            ref={videoRef}
            src={state.assetUrls[project.source.previewKey]}
            playsInline
            preload="metadata"
            aria-label={`${project.title} in-context audition monitor`}
          />
          <button
            type="button"
            className="monitor-stop"
            onClick={() => engineRef.current?.stop(videoRef.current ?? undefined)}
          >
            <Pause size={15} /> STOP ALL
          </button>
        </div>
        <div className="master-controls">
          <SlidersHorizontal size={18} aria-hidden="true" />
          <span>MASTER AUDITION LEVEL</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={volume}
            onChange={(event) => {
              const value = Number(event.target.value);
              setVolume(value);
              engineRef.current?.setVolume(value);
            }}
            aria-label="Master audition volume"
          />
          <button
            type="button"
            aria-pressed={muted}
            onClick={() => {
              const next = !muted;
              setMuted(next);
              engineRef.current?.setMuted(next);
            }}
          >
            {muted ? <VolumeX /> : <Volume2 />} {muted ? "MUTED" : `${Math.round(volume * 100)}%`}
          </button>
        </div>
      </section>

      <section className="audition-events">
        {project.events.map((soundEvent, eventIndex) => (
          <article className="audition-event" key={soundEvent.id}>
            <header className="audition-event-head">
              <span>{String(eventIndex + 1).padStart(2, "0")}</span>
              <div>
                <h2>{soundEvent.title}</h2>
                <p>{formatTime(soundEvent.timestampSeconds)} · {soundEvent.type.toUpperCase()} · EXACT FRAME PLACEMENT</p>
              </div>
              {soundEvent.approvedCandidateId ? <StatusStamp label="HUMAN APPROVED" /> : null}
            </header>
            <div className="candidate-pair">
              {soundEvent.candidates.map((candidate) => {
                const candidateKey = `${soundEvent.id}:${candidate.id}`;
                return (
                  <CandidateCard
                    key={candidate.id}
                    candidate={candidate}
                    audioUrl={
                      candidate.approvedWavKey
                        ? state.assetUrls[candidate.approvedWavKey]
                        : undefined
                    }
                    waveformUrl={
                      candidate.waveformKey ? state.assetUrls[candidate.waveformKey] : undefined
                    }
                    selected={(selected[soundEvent.id] ?? soundEvent.candidates[0]?.id) === candidate.id}
                    approved={soundEvent.approvedCandidateId === candidate.id}
                    busy={busyKey === candidateKey}
                    onSelect={() =>
                      setSelected((current) => ({ ...current, [soundEvent.id]: candidate.id }))
                    }
                    onSolo={() => void play(soundEvent.id, candidate, false, soundEvent.timestampSeconds)}
                    onContext={() => void play(soundEvent.id, candidate, true, soundEvent.timestampSeconds)}
                    onApprove={() => void approve(soundEvent.id, candidate.id)}
                  />
                );
              })}
            </div>
          </article>
        ))}
      </section>

      <div className="sticky-action">
        <div>
          <span className="eyebrow">HUMAN APPROVAL GATE</span>
          <strong>{project.events.filter((event) => event.approvedCandidateId).length} / {project.events.length} EVENTS APPROVED</strong>
        </div>
        <button
          type="button"
          className="button button-primary"
          disabled={!allApproved}
          onClick={() => router.push(`/projects/${id}/render`)}
          data-testid="open-mix"
        >
          BUILD THE MIX <SlidersHorizontal size={18} />
        </button>
      </div>
    </ProjectChrome>
  );
}

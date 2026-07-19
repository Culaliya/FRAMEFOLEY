"use client";

import { ArrowRight, Film, SlidersHorizontal } from "lucide-react";
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
import { formatTime } from "@/lib/format";

export default function RenderPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const state = useProject(id);
  const initialized = useRef(false);
  const [gains, setGains] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!state.project || initialized.current) return;
    initialized.current = true;
    setGains(
      Object.fromEntries(
        state.project.events.map((event) => [event.id, state.project?.render?.gainsDb[event.id] ?? 0]),
      ),
    );
  }, [state.project]);

  if (state.loading) return <ProjectLoading />;
  if (!state.project || state.error) return <ProjectError message={state.error ?? "Unknown project."} />;
  const project = state.project;
  if (!project.source) return <ProjectError message="The source clip is missing." />;
  const rendered = project.render?.status === "ready" && project.render.previewKey;

  async function render() {
    if (!state.token) return;
    setBusy(true);
    setError(null);
    try {
      const envelope = await api.render(id, state.token, gains);
      state.apply(envelope);
    } catch (caught) {
      setError(
        caught instanceof FrameFoleyApiError
          ? `${caught.message} · ${caught.requestId}`
          : "The authoritative render stopped.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <ProjectChrome project={project} active="render">
      <PageIntro
        step="04 / MIX"
        title="Three approved sounds. One playable moment."
        copy="Trim only the event level. FRAMEFOLEY owns the exact delay, limiter, encoding, mix map, and final SHA-256."
      />
      <InlineError message={error} />

      <div className="mix-workspace">
        <section className="mix-console panel-rule">
          <div className="panel-topline">
            <span>APPROVED EVENT STRIPS</span>
            <span>−12 dB / +6 dB</span>
          </div>
          {project.events.map((soundEvent, index) => {
            const candidate = soundEvent.candidates.find(
              (item) => item.id === soundEvent.approvedCandidateId,
            );
            const value = gains[soundEvent.id] ?? 0;
            return (
              <article className="mix-strip" key={soundEvent.id}>
                <span className="mix-number">{String(index + 1).padStart(2, "0")}</span>
                <div className="mix-event-copy">
                  <strong>{soundEvent.title}</strong>
                  <small>{formatTime(soundEvent.timestampSeconds)} · {candidate?.variant.toUpperCase()} APPROVED</small>
                </div>
                <div className="mix-gain">
                  <label htmlFor={`gain-${soundEvent.id}`}>EVENT GAIN</label>
                  <input
                    id={`gain-${soundEvent.id}`}
                    type="range"
                    min="-12"
                    max="6"
                    step="0.5"
                    value={value}
                    onChange={(event) =>
                      setGains((current) => ({
                        ...current,
                        [soundEvent.id]: Number(event.target.value),
                      }))
                    }
                    disabled={Boolean(rendered)}
                  />
                  <output>{value > 0 ? "+" : ""}{value.toFixed(1)} dB</output>
                </div>
                <HashValue value={candidate?.assetSha256} label="ASSET" />
              </article>
            );
          })}
        </section>

        <section className="render-comparison">
          <article className="render-monitor panel-rule">
            <div className="panel-topline"><span>BEFORE / SILENT SOURCE</span><span>ORIGINAL</span></div>
            <video
              controls
              playsInline
              preload="metadata"
              src={state.assetUrls[project.source.previewKey]}
              aria-label="Silent source preview"
            />
          </article>
          <article className={`render-monitor panel-rule ${rendered ? "rendered" : "awaiting"}`}>
            <div className="panel-topline">
              <span>AFTER / AUTHORITATIVE MIX</span>
              {rendered ? (
                <StatusStamp
                  label={state.storageLabel === "BACKBLAZE B2" ? "B2 STORED" : "LOCAL / MOCKED"}
                  tone={state.storageLabel === "BACKBLAZE B2" ? "cyan" : "steel"}
                  icon="storage"
                />
              ) : <span>PENDING</span>}
            </div>
            {rendered && project.render?.previewKey ? (
              <video
                controls
                playsInline
                preload="metadata"
                src={state.assetUrls[project.render.previewKey]}
                aria-label="Authoritative mixed preview"
              />
            ) : (
              <div className="render-placeholder">
                <Film aria-hidden="true" />
                <strong>THE MIX HAS NOT BEEN PRINTED</strong>
                <span>Approved WAV → fixed delay → limiter → H.264 / AAC</span>
              </div>
            )}
          </article>
        </section>

        <section className="render-proof panel-rule">
          <div>
            <span className="eyebrow">SERVER-SIDE AUTHORITY</span>
            <strong>FIXED-ARRAY FFMPEG</strong>
            <small>No user text enters a command, path, filter, or filename.</small>
          </div>
          <div>
            <span className="eyebrow">MIX PLACEMENT</span>
            <strong>EXACT TIMESTAMPS</strong>
            <small>Each approved WAV is delayed to its marked gameplay frame.</small>
          </div>
          <div>
            <span className="eyebrow">RENDER IDENTITY</span>
            <HashValue value={project.render?.sha256} label="MIX SHA-256" />
          </div>
        </section>
      </div>

      <div className="sticky-action">
        <div>
          <span className="eyebrow">{rendered ? "AUTHORITATIVE MIX READY" : "READY TO PRINT"}</span>
          <strong>{rendered ? "MIX MAP + HASH STORED" : "H.264 VIDEO / AAC AUDIO"}</strong>
        </div>
        {rendered ? (
          <button
            type="button"
            className="button button-primary"
            onClick={() => router.push(`/projects/${id}/export`)}
            data-testid="open-export"
          >
            PACKAGE THE SOUND KIT <ArrowRight size={18} />
          </button>
        ) : (
          <button
            type="button"
            className="button button-primary"
            onClick={render}
            disabled={busy}
            data-testid="render-mix"
          >
            {busy ? <span className="button-loader dark" /> : <SlidersHorizontal size={18} />}
            {busy ? "PRINTING THE MIX" : "RENDER APPROVED MIX"}
          </button>
        )}
      </div>
    </ProjectChrome>
  );
}

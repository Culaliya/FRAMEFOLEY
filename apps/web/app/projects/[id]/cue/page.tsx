"use client";

import type { SoundEvent, StyleProfile } from "@framefoley/contracts";
import { ChevronLeft, ChevronRight, Pause, Play, Plus, Save, Trash2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { PointerEvent, useEffect, useRef, useState } from "react";

import {
  ProjectChrome,
  ProjectError,
  ProjectLoading,
} from "@/components/project-chrome";
import { HashValue, InlineError, PageIntro, StatusStamp } from "@/components/ui";
import { useProject } from "@/hooks/use-project";
import { api, FrameFoleyApiError } from "@/lib/api";
import {
  canAddEvent,
  clampTimestamp,
  eventId,
  eventSlug,
  orderEvents,
} from "@/lib/events";
import { formatTime } from "@/lib/format";
import { STYLE_PRESETS } from "@/lib/style-presets";

function blankEvent(timestampSeconds: number, index: number): SoundEvent {
  return {
    id: eventId(),
    slug: `sound-event-${index + 1}`,
    title: `Sound event ${index + 1}`,
    type: "impact",
    timestampSeconds,
    targetDurationSeconds: 0.7,
    intensity: "medium",
    materialNote: "",
    candidates: [],
  };
}

export default function CuePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const state = useProject(id);
  const videoRef = useRef<HTMLVideoElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);
  const [events, setEvents] = useState<SoundEvent[]>([]);
  const [style, setStyle] = useState<StyleProfile>(STYLE_PRESETS[0]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!state.project || initialized.current) return;
    initialized.current = true;
    const initialEvents = orderEvents(state.project.events);
    setEvents(initialEvents);
    setStyle(state.project.style);
    setSelectedId(initialEvents[0]?.id ?? null);
  }, [state.project]);

  if (state.loading) return <ProjectLoading />;
  if (!state.project || state.error) return <ProjectError message={state.error ?? "Unknown project."} />;
  const project = state.project;
  const source = project.source;
  if (!source) return <ProjectError message="The source clip is missing." />;
  const duration = source.durationSeconds;
  const sourceUrl = state.assetUrls[source.previewKey];
  const selected = events.find((event) => event.id === selectedId) ?? events[0];

  function updateEvent(idToUpdate: string, update: Partial<SoundEvent>) {
    setEvents((current) =>
      orderEvents(
        current.map((event) => (event.id === idToUpdate ? { ...event, ...update } : event)),
      ),
    );
  }

  function seek(value: number) {
    const bounded = clampTimestamp(value, duration);
    setCurrentTime(bounded);
    if (videoRef.current) videoRef.current.currentTime = bounded;
  }

  function markerPointer(event: PointerEvent<HTMLButtonElement>, markerId: string) {
    if (!timelineRef.current) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const bounds = timelineRef.current.getBoundingClientRect();
    const value = ((event.clientX - bounds.left) / bounds.width) * duration;
    updateEvent(markerId, { timestampSeconds: clampTimestamp(value, duration) });
    setSelectedId(markerId);
    seek(value);
  }

  function addMarker() {
    if (!canAddEvent(events)) return;
    const created = blankEvent(currentTime, events.length);
    setEvents((current) => orderEvents([...current, created]));
    setSelectedId(created.id);
  }

  async function togglePlayback() {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) await video.play();
    else video.pause();
  }

  async function saveCues() {
    if (!state.token || events.length === 0) return;
    setSaving(true);
    setError(null);
    const normalized = orderEvents(events).map((event, index) => ({
      ...event,
      slug: event.slug || `${eventSlug(event.title, index + 1)}-${index + 1}`,
      candidates: [],
      approvedCandidateId: undefined,
    }));
    try {
      const envelope = await api.updateEvents(id, state.token, style, normalized);
      state.apply(envelope);
      router.push(`/projects/${id}/generate`);
    } catch (caught) {
      setError(
        caught instanceof FrameFoleyApiError
          ? `${caught.message} · ${caught.requestId}`
          : "The cue sheet could not be saved.",
      );
      setSaving(false);
    }
  }

  return (
    <ProjectChrome project={project} active="cue">
      <PageIntro
        step="02 / CUE"
        title="Mark the frame where silence stops being useful."
        copy="Place up to three moments. The frame decides when; your notes decide what the moment should feel like."
      />
      <InlineError message={error} />

      <div className="cue-workspace">
        <section className="cue-monitor panel-rule">
          <div className="panel-topline">
            <span>SOURCE MONITOR</span>
            <HashValue value={source.sha256} label="SOURCE" />
          </div>
          <div className="video-shell">
            <video
              ref={videoRef}
              src={sourceUrl}
              playsInline
              preload="metadata"
              aria-label={`${project.title} silent gameplay source`}
              onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onEnded={() => setPlaying(false)}
            >
              <track kind="captions" srcLang="en" label="No dialogue — silent gameplay clip" />
            </video>
            <span className="monitor-timecode">{formatTime(currentTime)}</span>
            <StatusStamp label="SOURCE AUDIO STRIPPED" tone="steel" icon="shield" />
          </div>
          <div className="transport">
            <button type="button" onClick={() => seek(currentTime - 1 / source.fps)} aria-label="Back one frame">
              <ChevronLeft />
            </button>
            <button className="transport-play" type="button" onClick={togglePlayback} aria-label={playing ? "Pause" : "Play"}>
              {playing ? <Pause fill="currentColor" /> : <Play fill="currentColor" />}
            </button>
            <button type="button" onClick={() => seek(currentTime + 1 / source.fps)} aria-label="Forward one frame">
              <ChevronRight />
            </button>
            <input
              type="range"
              min="0"
              max={duration}
              step={1 / source.fps}
              value={currentTime}
              onChange={(event) => seek(Number(event.target.value))}
              aria-label="Video playhead"
            />
            <span>{formatTime(duration)}</span>
          </div>
        </section>

        <section className="cue-timeline panel-rule" aria-label="Sound event timeline">
          <div className="panel-topline">
            <span>EVENT RAIL / {source.fps} FPS</span>
            <button type="button" className="text-action" onClick={addMarker} disabled={!canAddEvent(events)}>
              <Plus size={16} /> ADD AT PLAYHEAD
            </button>
          </div>
          <div
            className="timeline-track"
            ref={timelineRef}
            onPointerMove={(pointer) => {
              if (pointer.buttons !== 1 || !selectedId) return;
              markerPointer(pointer as unknown as PointerEvent<HTMLButtonElement>, selectedId);
            }}
          >
            <div className="timeline-ticks" aria-hidden="true">
              {Array.from({ length: 13 }, (_, index) => (
                <span key={index} style={{ left: `${(index / 12) * 100}%` }}>
                  {index}s
                </span>
              ))}
            </div>
            <span className="timeline-playhead" style={{ left: `${(currentTime / duration) * 100}%` }} />
            {events.map((soundEvent, index) => (
              <button
                type="button"
                key={soundEvent.id}
                className={`event-marker ${selectedId === soundEvent.id ? "selected" : ""}`}
                style={{ left: `${(soundEvent.timestampSeconds / duration) * 100}%` }}
                onPointerDown={(pointer) => markerPointer(pointer, soundEvent.id)}
                onClick={() => {
                  setSelectedId(soundEvent.id);
                  seek(soundEvent.timestampSeconds);
                }}
                onKeyDown={(keyboard) => {
                  if (!["ArrowLeft", "ArrowRight"].includes(keyboard.key)) return;
                  keyboard.preventDefault();
                  const direction = keyboard.key === "ArrowLeft" ? -1 : 1;
                  const step = keyboard.shiftKey ? 0.1 : 1 / source.fps;
                  const next = clampTimestamp(soundEvent.timestampSeconds + direction * step, duration);
                  updateEvent(soundEvent.id, { timestampSeconds: next });
                  seek(next);
                }}
                aria-label={`Event ${index + 1}, ${soundEvent.title}, at ${soundEvent.timestampSeconds.toFixed(2)} seconds. Drag or use arrow keys.`}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                <i />
              </button>
            ))}
          </div>
          <div className="event-tabs">
            {events.map((soundEvent, index) => (
              <button
                type="button"
                key={soundEvent.id}
                className={selectedId === soundEvent.id ? "active" : ""}
                onClick={() => {
                  setSelectedId(soundEvent.id);
                  seek(soundEvent.timestampSeconds);
                }}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{soundEvent.title}</strong>
                <code>{formatTime(soundEvent.timestampSeconds)}</code>
              </button>
            ))}
          </div>
        </section>

        <section className="event-inspector panel-rule">
          <div className="panel-topline">
            <span>EVENT INSPECTOR</span>
            <span>{events.length} / 3 MOMENTS</span>
          </div>
          {selected ? (
            <div className="inspector-form">
              <label className="field field-wide">
                <span>EVENT DESCRIPTION</span>
                <input
                  value={selected.title}
                  maxLength={80}
                  onChange={(event) => updateEvent(selected.id, { title: event.target.value })}
                />
              </label>
              <label className="field">
                <span>TYPE</span>
                <select
                  value={selected.type}
                  onChange={(event) =>
                    updateEvent(selected.id, {
                      type: event.target.value as SoundEvent["type"],
                    })
                  }
                >
                  <option value="impact">Impact</option>
                  <option value="creature">Creature</option>
                  <option value="ui">UI</option>
                  <option value="ambience">Ambience</option>
                </select>
              </label>
              <label className="field">
                <span>INTENSITY</span>
                <select
                  value={selected.intensity}
                  onChange={(event) =>
                    updateEvent(selected.id, {
                      intensity: event.target.value as SoundEvent["intensity"],
                    })
                  }
                >
                  <option value="soft">Soft</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </label>
              <label className="field">
                <span>TARGET LENGTH</span>
                <input
                  type="number"
                  min="0.08"
                  max="8"
                  step="0.01"
                  value={selected.targetDurationSeconds}
                  onChange={(event) =>
                    updateEvent(selected.id, { targetDurationSeconds: Number(event.target.value) })
                  }
                />
              </label>
              <label className="field">
                <span>FRAME TIME</span>
                <input
                  type="number"
                  min="0"
                  max={duration}
                  step={1 / source.fps}
                  value={selected.timestampSeconds}
                  onChange={(event) => {
                    const value = clampTimestamp(Number(event.target.value), duration);
                    updateEvent(selected.id, { timestampSeconds: value });
                    seek(value);
                  }}
                />
              </label>
              <label className="field field-wide">
                <span>MATERIAL / MOTION NOTE</span>
                <textarea
                  value={selected.materialNote ?? ""}
                  maxLength={180}
                  onChange={(event) =>
                    updateEvent(selected.id, { materialNote: event.target.value })
                  }
                />
              </label>
              <button
                type="button"
                className="delete-event"
                onClick={() => {
                  const remaining = events.filter((event) => event.id !== selected.id);
                  setEvents(remaining);
                  setSelectedId(remaining[0]?.id ?? null);
                }}
              >
                <Trash2 size={15} /> REMOVE EVENT
              </button>
            </div>
          ) : (
            <button type="button" className="empty-inspector" onClick={addMarker}>
              <Plus /> ADD THE FIRST MOMENT AT {formatTime(currentTime)}
            </button>
          )}
        </section>

        <section className="style-console panel-rule">
          <div className="panel-topline">
            <span>PROJECT STYLE</span>
            <span>ONE STYLE / SIX PROMPTS</span>
          </div>
          <div className="style-grid">
            {STYLE_PRESETS.map((preset, index) => (
              <button
                type="button"
                key={preset.id}
                className={style.id === preset.id ? "active" : ""}
                onClick={() => setStyle(preset)}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{preset.title}</strong>
                <small>{preset.promptPrefix}</small>
              </button>
            ))}
          </div>
        </section>
      </div>

      <div className="sticky-action">
        <div>
          <span className="eyebrow">READY TO LOCK</span>
          <strong>{events.length} EVENTS × 2 CANDIDATES</strong>
        </div>
        <button
          type="button"
          className="button button-primary"
          onClick={saveCues}
          disabled={saving || events.length === 0}
          data-testid="lock-cues"
        >
          {saving ? <span className="button-loader dark" /> : <Save size={18} />}
          LOCK CUES + BUILD PROMPTS
        </button>
      </div>
    </ProjectChrome>
  );
}

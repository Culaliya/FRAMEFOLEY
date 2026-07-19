"use client";

import { ArrowRight, FileVideo, LockKeyhole, Play, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";

import { ReadinessGate } from "@/components/readiness-gate";
import { SiteHeader } from "@/components/site-header";
import { InlineError } from "@/components/ui";
import { useSoundLabReadiness } from "@/hooks/use-readiness";
import { api, type CapabilityContract, FrameFoleyApiError } from "@/lib/api";
import { storeProjectToken } from "@/lib/token-store";

const MAX_BYTES = 30 * 1024 * 1024;

async function validateFile(file: File): Promise<void> {
  if (!["video/mp4", "video/webm"].includes(file.type)) {
    throw new Error("Use an MP4 or WebM clip.");
  }
  if (file.size > MAX_BYTES) throw new Error("Keep the clip at or below 30 MB.");
  const url = URL.createObjectURL(file);
  try {
    const duration = await new Promise<number>((resolve, reject) => {
      const video = document.createElement("video");
      video.preload = "metadata";
      video.onloadedmetadata = () => resolve(video.duration);
      video.onerror = () => reject(new Error("The browser could not inspect this clip."));
      video.src = url;
    });
    if (duration < 8 || duration > 15) throw new Error("Use a clip between 8 and 15 seconds.");
  } finally {
    URL.revokeObjectURL(url);
  }
}

export default function NewProjectPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<"demo" | "upload" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [capabilities, setCapabilities] = useState<CapabilityContract | null>(null);
  const readiness = useSoundLabReadiness();

  useEffect(() => {
    let active = true;
    void api.capabilities().then((value) => {
      if (active) setCapabilities(value);
    }).catch(() => {
      if (active) setCapabilities(null);
    });
    return () => {
      active = false;
    };
  }, []);

  async function startDemo() {
    setBusy("demo");
    setError(null);
    if (!(await readiness.ensureReady())) {
      setBusy(null);
      return;
    }
    try {
      const project = await api.createDemo();
      storeProjectToken(project.projectId, project.projectToken);
      router.push(`/projects/${project.projectId}/cue`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The demo project could not be created.");
      setBusy(null);
    }
  }

  async function startUpload(file: File) {
    setBusy("upload");
    setError(null);
    try {
      if (!capabilities?.customUploadCanComplete) {
        throw new Error("Custom clip mode is available in a self-hosted LIVE build.");
      }
      if (!(await readiness.ensureReady())) {
        setBusy(null);
        return;
      }
      await validateFile(file);
      const project = await api.uploadSource(file);
      storeProjectToken(project.projectId, project.projectToken);
      router.push(`/projects/${project.projectId}/cue`);
    } catch (caught) {
      setError(
        caught instanceof FrameFoleyApiError
          ? `${caught.message} · ${caught.requestId}`
          : caught instanceof Error
            ? caught.message
            : "The source upload stopped.",
      );
      setBusy(null);
    }
  }

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void startUpload(file);
  }

  function onDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) void startUpload(file);
  }

  return (
    <div className="source-page">
      <SiteHeader />
      <main className="source-main">
        <header className="source-intro">
          <p className="eyebrow">01 / SOURCE</p>
          <h1>
            Give us motion.
            <br />
            <span>Keep the sound for later.</span>
          </h1>
          <p>One silent gameplay clip. Eight to fifteen seconds. We strip any source audio.</p>
        </header>

        <InlineError message={error} />
        <ReadinessGate
          stage={readiness.stage}
          payload={readiness.payload}
          onRetry={() => void readiness.ensureReady()}
        />

        <div className="source-choices">
          <article className="demo-source-card">
            <div className="source-card-label">
              <span className="eyebrow">BUILT-IN / ORIGINAL</span>
              <span>12.00 SEC</span>
            </div>
            <div className="demo-mini-stage" aria-hidden="true">
              <span className="mini-moon" />
              <span className="mini-platform" />
              <span className="mini-jelly" />
              <span className="mini-crystal" />
              <span className="mini-timecode">00:08:25</span>
            </div>
            <div className="source-card-copy">
              <div>
                <h2>JELLY RELAY</h2>
                <p>A tiny lunar courier. Three clear moments. Six cached demo candidates.</p>
              </div>
              <button
                type="button"
                className="round-action"
                onClick={startDemo}
                disabled={busy !== null}
                aria-label="Sound the JELLY RELAY demo clip"
                data-testid="start-demo"
              >
                {busy === "demo" ? <span className="button-loader" /> : <Play fill="currentColor" />}
              </button>
            </div>
          </article>

          {capabilities?.customUploadCanComplete ? (
            <button
              type="button"
              className={`upload-source-card ${dragging ? "is-dragging" : ""}`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              disabled={busy !== null}
              data-testid="custom-upload"
            >
              <input
                ref={inputRef}
                type="file"
                accept="video/mp4,video/webm"
                onChange={onFile}
                hidden
              />
              <span className="upload-icon">
                {busy === "upload" ? <span className="button-loader" /> : <Upload />}
              </span>
              <span>
                <strong>{busy === "upload" ? "VALIDATING + STORING" : "DROP YOUR GAMEPLAY CLIP"}</strong>
                <small>or choose an MP4 / WebM</small>
              </span>
              <ArrowRight aria-hidden="true" />
            </button>
          ) : (
            <article className="upload-source-card upload-source-info" data-testid="custom-upload-info">
              <span className="upload-icon"><Upload /></span>
              <span>
                <strong>CUSTOM CLIP MODE</strong>
                <small>Available in a self-hosted LIVE build.</small>
                <small>The public competition demo cannot spend provider credit.</small>
                <a
                  href="https://github.com/Culaliya/FRAMEFOLEY#clean-local-setup"
                  target="_blank"
                  rel="noreferrer"
                >
                  OPEN SELF-HOSTED SETUP ↗
                </a>
              </span>
            </article>
          )}
        </div>

        <aside className="source-requirements">
          <div>
            <FileVideo aria-hidden="true" />
            <span>MP4 / WEBM</span>
            <strong>8–15 SEC · ≤ 30 MB · 480P–1080P</strong>
          </div>
          <div>
            <LockKeyhole aria-hidden="true" />
            <span>PRIVATE PROJECT STORAGE</span>
            <strong>HMAC ACCESS · SOURCE AUDIO REMOVED</strong>
          </div>
        </aside>
      </main>
    </div>
  );
}

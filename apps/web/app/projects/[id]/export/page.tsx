"use client";

import { Archive, Download, ExternalLink, FileAudio, FileJson, Film, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import {
  ProjectChrome,
  ProjectError,
  ProjectLoading,
} from "@/components/project-chrome";
import { HashValue, InlineError, StatusStamp } from "@/components/ui";
import { useProject } from "@/hooks/use-project";
import { api, FrameFoleyApiError } from "@/lib/api";
import { formatBytes } from "@/lib/format";

function InventoryIcon({ path }: { path: string }) {
  if (path.endsWith(".mp4")) return <Film size={16} />;
  if (path.endsWith(".wav") || path.endsWith(".ogg")) return <FileAudio size={16} />;
  return <FileJson size={16} />;
}

export default function ExportPage() {
  const { id } = useParams<{ id: string }>();
  const state = useProject(id);
  const [busy, setBusy] = useState<"export" | "download" | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (state.loading) return <ProjectLoading />;
  if (!state.project || state.error) return <ProjectError message={state.error ?? "Unknown project."} />;
  const project = state.project;
  const bundle = project.export;
  const ready = bundle?.status === "ready";

  async function packageBundle() {
    if (!state.token) return;
    setBusy("export");
    setError(null);
    try {
      const envelope = await api.export(id, state.token);
      state.apply(envelope);
    } catch (caught) {
      setError(
        caught instanceof FrameFoleyApiError
          ? `${caught.message} · ${caught.requestId}`
          : "The deterministic export stopped.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function download() {
    if (!state.token) return;
    setBusy("download");
    setError(null);
    try {
      const blob = await api.download(id, state.token);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `framefoley-${project.slug}.zip`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The bundle could not be downloaded.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <ProjectChrome project={project} active="export">
      <header className="export-hero">
        <p className="eyebrow">05 / EXPORT</p>
        <h1>
          THE SOUND MAY BE SYNTHETIC.
          <br />
          <span>THE HISTORY IS NOT.</span>
        </h1>
        <p>
          One deterministic kit: approved audio, playable preview, QC, waveforms, manifests,
          full prompts, and a human-readable provenance index.
        </p>
      </header>
      <InlineError message={error} />

      <div className="export-workspace">
        <section className="bundle-visual panel-rule">
          <div className="bundle-spine">
            <span>FRAMEFOLEY / SOUND KIT</span>
            <strong>{project.title}</strong>
            <code>{project.id}</code>
          </div>
          <div className="bundle-face">
            <Archive size={54} strokeWidth={1.2} aria-hidden="true" />
            <span className="eyebrow">DETERMINISTIC ZIP</span>
            <h2>{project.slug.toUpperCase()}</h2>
            <div>
              {ready ? (
                <StatusStamp
                  label={state.storageLabel === "BACKBLAZE B2" ? "B2 OBJECT READY" : "LOCAL OBJECT / MOCKED"}
                  tone={state.storageLabel === "BACKBLAZE B2" ? "cyan" : "steel"}
                  icon="storage"
                />
              ) : <StatusStamp label="AWAITING PACK" tone="steel" />}
              <HashValue value={bundle?.sha256} label="ZIP" />
            </div>
          </div>
        </section>

        <section className="inventory panel-rule">
          <div className="panel-topline">
            <span>EXPORT INVENTORY</span>
            <span>{bundle?.inventory.length ?? 0} FILES · {formatBytes(bundle?.sizeBytes)}</span>
          </div>
          {ready ? (
            <ol>
              {bundle.inventory.map((path, index) => (
                <li key={path}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <InventoryIcon path={path} />
                  <code>{path}</code>
                </li>
              ))}
            </ol>
          ) : (
            <div className="inventory-empty">
              <Archive aria-hidden="true" />
              <strong>READY TO PACK THE VERIFIED EDIT</strong>
              <span>Stable order · stable timestamps · explicit source labels</span>
            </div>
          )}
        </section>

        <section className="export-actions-grid">
          <button
            type="button"
            className="export-action primary"
            onClick={ready ? download : packageBundle}
            disabled={busy !== null}
            data-testid={ready ? "download-kit" : "export-kit"}
          >
            {busy ? <span className="button-loader dark" /> : ready ? <Download /> : <Archive />}
            <span>
              <strong>{ready ? "DOWNLOAD SOUND KIT" : "BUILD SOUND KIT"}</strong>
              <small>{ready ? formatBytes(bundle.sizeBytes) : "WAV / OGG / MP4 / JSON / PNG"}</small>
            </span>
          </button>
          <Link href={`/projects/${id}/provenance`} className={`export-action ${ready ? "" : "disabled"}`} aria-disabled={!ready}>
            <ExternalLink />
            <span><strong>INSPECT PROVENANCE</strong><small>Every candidate, prompt, hash, and decision</small></span>
          </Link>
          <Link href="/projects/new" className="export-action">
            <RotateCcw />
            <span><strong>START ANOTHER PROJECT</strong><small>A fresh private storage prefix</small></span>
          </Link>
        </section>
      </div>

      {ready ? (
        <footer className="export-seal">
          <StatusStamp label="HUMAN APPROVAL RECORDED" tone="lime" />
          <StatusStamp label="DETERMINISTIC QC RECORDED" tone="lime" />
          <StatusStamp
            label={state.storageLabel === "BACKBLAZE B2" ? "B2 OBJECT STORED" : "LOCAL STORAGE / MOCKED"}
            tone={state.storageLabel === "BACKBLAZE B2" ? "cyan" : "steel"}
            icon="storage"
          />
          <HashValue value={bundle.sha256} label="FINAL ZIP SHA-256" />
        </footer>
      ) : null}
    </ProjectChrome>
  );
}

"use client";

import type { GenerationCandidate } from "@framefoley/contracts";
import { ArrowLeft, Check, Copy, Database, Download, Fingerprint } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  ProjectChrome,
  ProjectError,
  ProjectLoading,
} from "@/components/project-chrome";
import { HashValue, StatusStamp } from "@/components/ui";
import { useProject } from "@/hooks/use-project";
import { api } from "@/lib/api";
import { copySafeProvenanceJson, formatParameters } from "@/lib/provenance";

interface ProvenanceRecord {
  event: { id: string; title: string; timestampSeconds: number };
  candidate: GenerationCandidate;
  approvalStatus: boolean;
}

interface ProvenanceDocument {
  schemaVersion: 1;
  projectId: string;
  generatedAt: string;
  candidates: ProvenanceRecord[];
}

export default function ProvenancePage() {
  const { id } = useParams<{ id: string }>();
  const state = useProject(id);
  const [document, setDocument] = useState<ProvenanceDocument | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (!state.token || !state.project || document) return;
    void api
      .provenance(id, state.token)
      .then((value) => setDocument(value as unknown as ProvenanceDocument));
  }, [document, id, state.project, state.token]);

  if (state.loading || (state.project && !document)) return <ProjectLoading />;
  if (!state.project || state.error || !document) {
    return <ProjectError message={state.error ?? "The provenance document is unavailable."} />;
  }
  const project = state.project;
  const proofReplay = project.evidenceLabel === "LIVE EVIDENCE REPLAY";

  async function copy(value: string, key: string) {
    await navigator.clipboard.writeText(value);
    setCopied(key);
    window.setTimeout(() => setCopied(null), 1200);
  }

  function downloadJson() {
    if (!document) return;
    const blob = new Blob([copySafeProvenanceJson(document)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url;
    anchor.download = `framefoley-${document.projectId}-provenance.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <ProjectChrome project={project} active="export">
      <header className="provenance-hero">
        <Link href={`/projects/${id}/export`} className="back-link"><ArrowLeft size={16} /> BACK TO KIT</Link>
        <p className="eyebrow">PROVENANCE / SCHEMA 1</p>
        <h1>EVERY SOUND<br /><span>LEAVES A PAPER TRAIL.</span></h1>
        <p>Verified facts, explicit source labels, deterministic QC, and human decisions. Assumptions do not get promoted to evidence.</p>
        <button type="button" className="button button-secondary" onClick={downloadJson}>
          <Download size={16} /> DOWNLOAD COPY-SAFE JSON
        </button>
      </header>

      {proofReplay ? (
        <section className="provenance-replay-note">
          <StatusStamp label="LIVE EVIDENCE REPLAY" tone="lime" icon="shield" />
          <div>
            <strong>THE PROVIDER CALLS HAPPENED DURING THE RECORDED LIVE GATE — NOT NOW.</strong>
            <p>
              Two real Genblaze / ElevenLabs outputs were loaded from private B2, re-hashed, and
              re-verified before this isolated project opened. Replay provider calls: 0.
            </p>
          </div>
        </section>
      ) : null}

      <section className="provenance-overview">
        <div><Fingerprint /><span>PROJECT ID</span><code>{document.projectId}</code></div>
        <div><Database /><span>STORAGE RECORD</span><strong>{state.storageLabel ?? "UNAVAILABLE"}</strong></div>
        <div><Check /><span>GENERATED AT</span><strong>{new Date(document.generatedAt).toLocaleString()}</strong></div>
      </section>

      <section className="provenance-records">
        {document.candidates.map((record, index) => {
          const candidate = record.candidate;
          const key = `${record.event.id}:${candidate.id}`;
          return (
            <article className="provenance-record panel-rule" key={key}>
              <header>
                <span className="record-index">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <p className="eyebrow">{record.event.timestampSeconds.toFixed(2)} SEC / {candidate.variant.toUpperCase()}</p>
                  <h2>{record.event.title}</h2>
                </div>
                <div className="record-stamps">
                  {proofReplay ? <StatusStamp label="LIVE EVIDENCE REPLAY" tone="lime" icon="shield" /> : null}
                  <StatusStamp label={candidate.sourceLabel} tone={candidate.sourceLabel === "LIVE" ? "lime" : "cyan"} />
                  {record.approvalStatus ? <StatusStamp label="APPROVED" tone="lime" /> : null}
                </div>
              </header>
              <dl className="record-grid">
                <div><dt>PROVIDER</dt><dd>{candidate.provider}</dd></div>
                <div><dt>MODEL</dt><dd>{candidate.model}</dd></div>
                <div>
                  <dt>GENBLAZE RUN</dt>
                  <dd className="copy-run">
                    {candidate.genblazeRunId ? `${candidate.genblazeRunId.slice(0, 8)}…${candidate.genblazeRunId.slice(-4)}` : "NOT A LIVE RUN"}
                    {candidate.genblazeRunId ? (
                      <button type="button" onClick={() => void copy(candidate.genblazeRunId ?? "", `${key}:run`)}>
                        <Copy size={12} /> {copied === `${key}:run` ? "COPIED" : "COPY"}
                      </button>
                    ) : null}
                  </dd>
                </div>
                <div><dt>PARENT RUN</dt><dd>{candidate.parentRunId ?? "—"}</dd></div>
                <div><dt>MANIFEST</dt><dd>{candidate.manifestVerified ? "Manifest.verify(): TRUE" : "CACHE RECORD / NON-CANONICAL"}</dd></div>
                <div><dt>QC BEFORE / AFTER</dt><dd>{candidate.qcBefore?.verdict.toUpperCase() ?? "—"} / {candidate.qcAfter?.verdict.toUpperCase() ?? "—"}</dd></div>
                <div><dt>STARTED</dt><dd>{candidate.startedAt ? new Date(candidate.startedAt).toLocaleString() : "—"}</dd></div>
                <div><dt>ENDED</dt><dd>{candidate.endedAt ? new Date(candidate.endedAt).toLocaleString() : "—"}</dd></div>
                <div><dt>LATENCY</dt><dd>{candidate.latencySeconds != null ? `${candidate.latencySeconds.toFixed(3)} SEC` : "—"}</dd></div>
                <div><dt>COST</dt><dd>{candidate.costUsd != null ? `$${candidate.costUsd.toFixed(6)}` : "NOT REPORTED"}</dd></div>
                <div><dt>MANIFEST URI</dt><dd>{candidate.manifestUri ?? "—"}</dd></div>
                <div><dt>STORAGE OBJECT</dt><dd>{candidate.rawAssetKey ?? "—"}</dd></div>
                <div><dt>HUMAN DECISION</dt><dd>{record.approvalStatus ? "APPROVED IN THIS REPLAY" : "AWAITING REPLAY APPROVAL"}</dd></div>
              </dl>
              <div className="prompt-ledger">
                <div className="prompt-label"><span>PARAMETERS</span></div>
                <pre>{formatParameters(candidate.parameters)}</pre>
              </div>
              <div className="prompt-ledger">
                <div className="prompt-label">
                  <span>FULL DETERMINISTIC PROMPT</span>
                  <button type="button" onClick={() => void copy(candidate.prompt, key)}>
                    <Copy size={14} /> {copied === key ? "COPIED" : "COPY"}
                  </button>
                </div>
                <pre>{candidate.prompt}</pre>
              </div>
              <div className="hash-ledger">
                <HashValue value={candidate.assetSha256} label="ASSET SHA-256" />
                <HashValue value={candidate.manifestHash} label="MANIFEST HASH" />
                <span><small>REPAIRS</small><code>{candidate.repairs.join(", ") || "NONE"}</code></span>
              </div>
            </article>
          );
        })}
      </section>

      <footer className="provenance-limit">
        <strong>PROVENANCE IS A HISTORY, NOT A RIGHTS WARRANTY.</strong>
        <p>FRAMEFOLEY records provider/model disclosure, technical checks, hashes, storage references, and human approval. Review the provider plan and terms that apply to your use.</p>
      </footer>
    </ProjectChrome>
  );
}

/* Generated from schemas/framefoley.schema.json. Do not edit by hand. */

export type Sha256 = string;

export type ObjectKey = string;

export interface FrameFoleyProject {
  schemaVersion: 1;
  id: string;
  slug: string;
  title: string;
  state: "created" | "source_uploading" | "source_ready" | "cueing" | "generation_queued" | "generating" | "audition_ready" | "approvals_complete" | "rendering" | "render_ready" | "exporting" | "complete" | "source_failed" | "generation_partial" | "generation_failed" | "render_failed" | "export_failed";
  phase: "source" | "cue" | "generate" | "audition" | "render" | "export" | "complete";
  createdAt: string;
  updatedAt: string;
  expiresAt: string;
  source?: SourceClip | null;
  style: StyleProfile;
  events: Array<SoundEvent>;
  render?: MixRender | null;
  export?: ExportBundle | null;
  generationMode: "live" | "demo" | "disabled";
  liveCallCount: number;
  retryBudgetRemaining: number;
  generationRequestKeys: Array<Sha256>;
  evidenceLabel?: "CACHED DEMO" | "LIVE EVIDENCE REPLAY" | "LIVE";
  proofReplay?: ProofReplayMetadata;
  error?: ApiError | null;
}

export interface SourceClip {
  b2Key: ObjectKey;
  previewKey: ObjectKey;
  mimeType: "video/mp4" | "video/webm";
  durationSeconds: number;
  width: number;
  height: number;
  fps: number;
  sha256: Sha256;
  thumbnailKey: ObjectKey;
  sourceAudioStripped: true;
  origin: "demo" | "upload" | "live_proof";
}

export interface ProofReplayMetadata {
  proofVersion: "live-v1";
  capturedAt: string;
  recordedProviderCallCount: 2;
  replayProviderCallCount: 0;
  b2ObjectCount: number;
  costDisclosure: string;
}

export interface StyleProfile {
  id: "lunar_arcade" | "rubber_dungeon" | "rust_bloom" | "paper_signal" | "custom";
  title: string;
  promptPrefix: string;
  customText?: string;
}

export interface SoundEvent {
  id: string;
  slug: string;
  title: string;
  type: "impact" | "creature" | "ui" | "ambience";
  timestampSeconds: number;
  targetDurationSeconds: number;
  intensity: "soft" | "medium" | "hard";
  materialNote?: string;
  candidates: Array<GenerationCandidate>;
  approvedCandidateId?: string;
}

export interface GenerationCandidate {
  id: string;
  variant: "clean" | "character";
  status: "queued" | "generating" | "stored" | "checking" | "repaired" | "retrying" | "ready" | "failed";
  prompt: string;
  provider: string;
  model: string;
  sourceLabel: "LIVE" | "CACHED DEMO" | "MOCKED";
  parameters?: Record<string, string | number | boolean>;
  startedAt?: string;
  endedAt?: string;
  latencySeconds?: number;
  costUsd?: number;
  genblazeRunId?: string;
  parentRunId?: string;
  manifestUri?: string;
  manifestHash?: Sha256;
  manifestVerified: boolean;
  rawAssetKey?: ObjectKey;
  approvedWavKey?: ObjectKey;
  approvedOggKey?: ObjectKey;
  waveformKey?: ObjectKey;
  assetSha256?: Sha256;
  qcBefore?: QcReport;
  qcAfter?: QcReport;
  repairs: Array<string>;
  retryCount: number;
  retryOfCandidateId?: string;
  error?: ApiError | null;
}

export interface QcReport {
  schemaVersion: 1;
  verdict: "pass" | "repairable" | "regenerate" | "failed";
  durationSeconds: number;
  sampleRateHz: number;
  channels: number;
  peakDbfs: number;
  rmsDbfs: number;
  leadingSilenceMs: number;
  trailingSilenceMs: number;
  reasons: Array<string>;
  repairs: Array<string>;
  sha256: Sha256;
}

export interface MixRender {
  status: "queued" | "rendering" | "ready" | "failed";
  previewKey?: ObjectKey;
  mixMapKey?: ObjectKey;
  durationSeconds?: number;
  sha256?: Sha256;
  gainsDb: Record<string, number>;
  error?: ApiError | null;
}

export interface ExportBundle {
  status: "queued" | "packing" | "ready" | "failed";
  zipKey?: ObjectKey;
  sha256?: Sha256;
  sizeBytes?: number;
  createdAt?: string;
  provenanceIndexKey?: ObjectKey;
  inventory: Array<string>;
  error?: ApiError | null;
}

export interface SseEvent {
  type: "project.state" | "candidate.status" | "candidate.qc" | "render.status" | "export.status" | "heartbeat";
  projectId: string;
  eventId?: string;
  candidateId?: string;
  at: string;
  payload: Record<string, unknown>;
}

export interface ApiError {
  code: string;
  message: string;
  retryable: boolean;
  requestId: string;
}

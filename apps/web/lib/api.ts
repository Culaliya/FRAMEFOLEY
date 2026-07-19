import type {
  ApiError,
  FrameFoleyProject,
  SoundEvent,
  SseEvent,
  StyleProfile,
} from "@framefoley/contracts";

export interface ProjectCreation {
  projectId: string;
  projectToken: string;
  phase: "source" | "generate";
  expiresAt: string;
}

export interface CapabilityContract {
  schemaVersion: 1;
  generationMode: "live" | "demo" | "disabled";
  storage: "BACKBLAZE B2" | "MOCKED LOCAL STORAGE";
  customUploadCanComplete: boolean;
  liveProofReplayAvailable: boolean;
  anonymousProviderSpendEnabled: boolean;
  projectTtlHours: number;
}

export interface ReadinessContract {
  status: "ready" | "not_ready";
  generationMode?: "live" | "demo" | "disabled";
  storage?: "BACKBLAZE B2" | "MOCKED LOCAL STORAGE";
  mediaTools?: { ffmpeg: boolean; ffprobe: boolean };
  storageReady?: boolean;
}

export interface ProjectEnvelope {
  project: FrameFoleyProject;
  assetUrls: Record<string, string>;
  storageLabel: "BACKBLAZE B2" | "MOCKED LOCAL STORAGE";
}

export interface UploadTicket {
  uploadUrl: string;
  method: "PUT";
  objectKey: string;
  expiresAt: string;
}

export class FrameFoleyApiError extends Error {
  readonly code: string;
  readonly retryable: boolean;
  readonly requestId: string;

  constructor(payload: ApiError) {
    super(payload.message);
    this.name = "FrameFoleyApiError";
    this.code = payload.code;
    this.retryable = payload.retryable;
    this.requestId = payload.requestId;
  }
}

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let payload: ApiError;
    try {
      payload = (await response.json()) as ApiError;
    } catch {
      payload = {
        code: "NETWORK_RESPONSE_INVALID",
        message: "FRAMEFOLEY received an unreadable response.",
        retryable: response.status >= 500,
        requestId: response.headers.get("x-request-id") ?? "req_browser0000",
      };
    }
    throw new FrameFoleyApiError(payload);
  }
  return (await response.json()) as T;
}

function auth(token: string, extras: HeadersInit = {}): HeadersInit {
  return { Authorization: `Bearer ${token}`, ...extras };
}

export const api = {
  async readiness(): Promise<ReadinessContract> {
    const response = await fetch(`${API_BASE}/readyz`, { cache: "no-store" });
    try {
      return (await response.json()) as ReadinessContract;
    } catch {
      return { status: "not_ready" };
    }
  },

  capabilities(): Promise<CapabilityContract> {
    return fetch(`${API_BASE}/v1/capabilities`, { cache: "no-store" }).then(
      parseResponse<CapabilityContract>,
    );
  },

  createProject(title: string): Promise<ProjectCreation> {
    return fetch(`${API_BASE}/v1/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }).then(parseResponse<ProjectCreation>);
  },

  createDemo(): Promise<ProjectCreation> {
    return fetch(`${API_BASE}/v1/projects/demo`, { method: "POST" }).then(
      parseResponse<ProjectCreation>,
    );
  },

  createLiveProof(): Promise<ProjectCreation> {
    return fetch(`${API_BASE}/v1/projects/live-proof`, { method: "POST" }).then(
      parseResponse<ProjectCreation>,
    );
  },

  getProject(projectId: string, token: string): Promise<ProjectEnvelope> {
    return fetch(`${API_BASE}/v1/projects/${projectId}`, { headers: auth(token) }).then(
      parseResponse<ProjectEnvelope>,
    );
  },

  updateEvents(
    projectId: string,
    token: string,
    style: StyleProfile,
    events: SoundEvent[],
  ): Promise<ProjectEnvelope> {
    return fetch(`${API_BASE}/v1/projects/${projectId}/events`, {
      method: "PUT",
      headers: auth(token, { "Content-Type": "application/json" }),
      body: JSON.stringify({ style, events }),
    }).then(parseResponse<ProjectEnvelope>);
  },

  async uploadSource(file: File): Promise<ProjectCreation> {
    const creation = await this.createProject(file.name.replace(/\.[^.]+$/, "") || "Sound kit");
    const ticket = await fetch(`${API_BASE}/v1/projects/${creation.projectId}/upload-url`, {
      method: "POST",
      headers: auth(creation.projectToken, { "Content-Type": "application/json" }),
      body: JSON.stringify({ filename: file.name, mimeType: file.type, sizeBytes: file.size }),
    }).then(parseResponse<UploadTicket>);
    const upload = await fetch(ticket.uploadUrl, {
      method: "PUT",
      headers: { "Content-Type": file.type },
      body: file,
    });
    if (!upload.ok) await parseResponse<never>(upload);
    await fetch(`${API_BASE}/v1/projects/${creation.projectId}/source/complete`, {
      method: "POST",
      headers: auth(creation.projectToken, { "Content-Type": "application/json" }),
      body: JSON.stringify({ objectKey: ticket.objectKey }),
    }).then(parseResponse<ProjectEnvelope>);
    return creation;
  },

  generate(projectId: string, token: string, idempotencyKey: string): Promise<ProjectEnvelope> {
    return fetch(`${API_BASE}/v1/projects/${projectId}/generate`, {
      method: "POST",
      headers: auth(token, { "Idempotency-Key": idempotencyKey }),
    }).then(parseResponse<ProjectEnvelope>);
  },

  approve(
    projectId: string,
    token: string,
    eventId: string,
    candidateId: string,
  ): Promise<ProjectEnvelope> {
    return fetch(`${API_BASE}/v1/projects/${projectId}/events/${eventId}/approve`, {
      method: "POST",
      headers: auth(token, { "Content-Type": "application/json" }),
      body: JSON.stringify({ candidateId }),
    }).then(parseResponse<ProjectEnvelope>);
  },

  render(
    projectId: string,
    token: string,
    gainsDb: Record<string, number>,
  ): Promise<ProjectEnvelope> {
    return fetch(`${API_BASE}/v1/projects/${projectId}/render`, {
      method: "POST",
      headers: auth(token, { "Content-Type": "application/json" }),
      body: JSON.stringify({ gainsDb }),
    }).then(parseResponse<ProjectEnvelope>);
  },

  export(projectId: string, token: string): Promise<ProjectEnvelope> {
    return fetch(`${API_BASE}/v1/projects/${projectId}/export`, {
      method: "POST",
      headers: auth(token),
    }).then(parseResponse<ProjectEnvelope>);
  },

  provenance(projectId: string, token: string): Promise<Record<string, unknown>> {
    return fetch(`${API_BASE}/v1/projects/${projectId}/provenance`, {
      headers: auth(token),
    }).then(parseResponse<Record<string, unknown>>);
  },

  async download(projectId: string, token: string): Promise<Blob> {
    const response = await fetch(`${API_BASE}/v1/projects/${projectId}/download`, {
      headers: auth(token),
    });
    if (!response.ok) await parseResponse<never>(response);
    return response.blob();
  },

  async stream(
    projectId: string,
    token: string,
    signal: AbortSignal,
    onEvent: (event: SseEvent) => void,
    onFallback?: () => Promise<void>,
  ): Promise<void> {
    let lastEventId = "0";
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        const response = await fetch(`${API_BASE}/v1/projects/${projectId}/stream`, {
          headers: auth(token, lastEventId === "0" ? {} : { "Last-Event-ID": lastEventId }),
          signal,
        });
        if (!response.ok) await parseResponse<never>(response);
        const reader = response.body?.getReader();
        if (!reader) throw new Error("Event stream is unavailable.");
        const decoder = new TextDecoder();
        let buffer = "";
        while (!signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const records = buffer.split("\n\n");
          buffer = records.pop() ?? "";
          for (const record of records) {
            const lines = record.split("\n");
            const eventId = lines.find((line) => line.startsWith("id: "))?.slice(4);
            if (eventId && /^\d+$/.test(eventId)) lastEventId = eventId;
            const data = lines.find((line) => line.startsWith("data: "))?.slice(6);
            if (data && data !== "{}") onEvent(JSON.parse(data) as SseEvent);
          }
        }
        if (signal.aborted) return;
      } catch (caught) {
        if (signal.aborted) throw caught;
        if (attempt === 0) continue;
      }
    }
    await onFallback?.();
  },
};

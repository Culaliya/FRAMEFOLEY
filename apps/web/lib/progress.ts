import type { SseEvent } from "@framefoley/contracts";

export interface ProgressState {
  events: SseEvent[];
  latestByCandidate: Record<string, SseEvent>;
  projectState?: string;
}

export const initialProgress: ProgressState = { events: [], latestByCandidate: {} };

export function progressReducer(state: ProgressState, event: SseEvent): ProgressState {
  const events = [...state.events, event].slice(-80);
  const candidateKey = event.candidateId;
  return {
    events,
    latestByCandidate: candidateKey
      ? { ...state.latestByCandidate, [candidateKey]: event }
      : state.latestByCandidate,
    projectState:
      event.type === "project.state" && typeof event.payload.state === "string"
        ? event.payload.state
        : state.projectState,
  };
}

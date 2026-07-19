"use client";

import type { FrameFoleyProject } from "@framefoley/contracts";
import { useCallback, useEffect, useState } from "react";

import { api, FrameFoleyApiError, type ProjectEnvelope } from "@/lib/api";
import { readProjectToken } from "@/lib/token-store";

interface ProjectState {
  project: FrameFoleyProject | null;
  assetUrls: Record<string, string>;
  storageLabel: "BACKBLAZE B2" | "MOCKED LOCAL STORAGE" | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<ProjectEnvelope | null>;
  apply: (envelope: ProjectEnvelope) => void;
}

export function useProject(projectId: string): ProjectState {
  const [project, setProject] = useState<FrameFoleyProject | null>(null);
  const [assetUrls, setAssetUrls] = useState<Record<string, string>>({});
  const [storageLabel, setStorageLabel] = useState<ProjectState["storageLabel"]>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apply = useCallback((envelope: ProjectEnvelope) => {
    setProject(envelope.project);
    setAssetUrls(envelope.assetUrls);
    setStorageLabel(envelope.storageLabel);
    setError(null);
  }, []);

  const refresh = useCallback(async () => {
    const activeToken = readProjectToken(projectId);
    setToken(activeToken);
    if (!activeToken) {
      setError("This private project token is not available in this browser session.");
      setLoading(false);
      return null;
    }
    try {
      const envelope = await api.getProject(projectId, activeToken);
      apply(envelope);
      return envelope;
    } catch (caught) {
      setError(
        caught instanceof FrameFoleyApiError
          ? `${caught.message} · ${caught.requestId}`
          : "FRAMEFOLEY could not load this project.",
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, [apply, projectId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  return { project, assetUrls, storageLabel, token, loading, error, refresh, apply };
}

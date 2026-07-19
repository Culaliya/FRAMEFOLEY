import { afterEach, describe, expect, it, vi } from "vitest";

import { api, FrameFoleyApiError } from "./api";

describe("API public error mapping", () => {
  afterEach(() => vi.restoreAllMocks());

  it("maps typed API failures without exposing response internals", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: "GENERATION_BUSY",
          message: "Generation capacity is busy.",
          retryable: true,
          requestId: "req_browser1234",
        }),
        { status: 429, headers: { "Content-Type": "application/json" } },
      ),
    );
    const failure = await api.createDemo().catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(FrameFoleyApiError);
    expect(failure).toMatchObject({
      code: "GENERATION_BUSY",
      retryable: true,
      requestId: "req_browser1234",
    });
  });

  it("reconnects SSE once with Last-Event-ID and then polls authoritative state", async () => {
    const encoder = new TextEncoder();
    const firstStream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            'id: 4\nevent: candidate.status\ndata: {"type":"candidate.status","projectId":"prj_123456789abc","at":"2026-07-19T00:00:00Z","payload":{"status":"ready"}}\n\n',
          ),
        );
        controller.close();
      },
    });
    const secondStream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.close();
      },
    });
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(firstStream, { status: 200 }))
      .mockResolvedValueOnce(new Response(secondStream, { status: 200 }));
    const events: unknown[] = [];
    const fallback = vi.fn(async () => undefined);
    await api.stream(
      "prj_123456789abc",
      "test-token",
      new AbortController().signal,
      (event) => events.push(event),
      fallback,
    );
    expect(events).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const secondOptions = fetchMock.mock.calls[1]?.[1] as RequestInit;
    expect(new Headers(secondOptions.headers).get("Last-Event-ID")).toBe("4");
    expect(fallback).toHaveBeenCalledOnce();
  });
});

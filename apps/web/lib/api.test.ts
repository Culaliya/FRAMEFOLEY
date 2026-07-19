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
});

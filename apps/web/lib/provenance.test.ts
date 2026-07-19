import { describe, expect, it } from "vitest";

import { copySafeProvenanceJson, formatParameters } from "./provenance";

describe("provenance rendering", () => {
  it("sorts parameter fields for stable human-readable output", () => {
    expect(formatParameters({ modality: "audio", durationSeconds: 0.72 })).toBe(
      '{\n  "durationSeconds": 0.72,\n  "modality": "audio"\n}',
    );
  });

  it("removes signed queries and private fields from downloadable JSON", () => {
    const rendered = copySafeProvenanceJson({
      manifestUri: "https://storage.example/object.json?X-Amz-Signature=private",
      projectToken: "private-token",
    });
    expect(rendered).toContain("https://storage.example/object.json");
    expect(rendered).toContain("[REDACTED]");
    expect(rendered).not.toContain("X-Amz-Signature");
    expect(rendered).not.toContain("private-token");
  });
});

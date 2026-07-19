const PRIVATE_KEY = /(authorization|cookie|projecttoken|secret|signedurl)/i;

function cleanValue(value: unknown, key = ""): unknown {
  if (PRIVATE_KEY.test(key)) return "[REDACTED]";
  if (Array.isArray(value)) return value.map((item) => cleanValue(item));
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([childKey, childValue]) => [
        childKey,
        cleanValue(childValue, childKey),
      ]),
    );
  }
  if (typeof value === "string" && /^https?:\/\//i.test(value)) {
    try {
      const url = new URL(value);
      return `${url.origin}${url.pathname}`;
    } catch {
      return value;
    }
  }
  return value;
}

export function copySafeProvenanceJson(document: unknown): string {
  return `${JSON.stringify(cleanValue(document), null, 2)}\n`;
}

export function formatParameters(
  parameters: Record<string, string | number | boolean> | undefined,
): string {
  return JSON.stringify(Object.fromEntries(Object.entries(parameters ?? {}).sort()), null, 2);
}

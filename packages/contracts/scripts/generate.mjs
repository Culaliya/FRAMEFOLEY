import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const schemaPath = join(root, "schemas", "framefoley.schema.json");
const outputPath = join(root, "src", "generated.ts");

const schema = JSON.parse(await readFile(schemaPath, "utf8"));
const definitions = schema.definitions;
if (!definitions || typeof definitions !== "object") {
  throw new Error("framefoley.schema.json must define a definitions object");
}

const refName = (ref) => decodeURIComponent(ref.split("/").at(-1));
const literal = (value) => JSON.stringify(value);

function typeFor(node) {
  if (node.$ref) return refName(node.$ref);
  if (Object.hasOwn(node, "const")) return literal(node.const);
  if (node.enum) return node.enum.map(literal).join(" | ");
  if (node.anyOf) return node.anyOf.map(typeFor).join(" | ");
  if (node.type === "array") return `Array<${typeFor(node.items ?? {})}>`;
  if (node.type === "string") return "string";
  if (node.type === "number" || node.type === "integer") return "number";
  if (node.type === "boolean") return "boolean";
  if (node.type === "null") return "null";
  if (node.type === "object") {
    if (node.additionalProperties && typeof node.additionalProperties === "object") {
      return `Record<string, ${typeFor(node.additionalProperties)}>`;
    }
    return "Record<string, unknown>";
  }
  return "unknown";
}

function renderDefinition(name, node) {
  if (node.type !== "object" || !node.properties) {
    return `export type ${name} = ${typeFor(node)};`;
  }
  const required = new Set(node.required ?? []);
  const properties = Object.entries(node.properties).map(([property, propertySchema]) => {
    const optional = required.has(property) ? "" : "?";
    return `  ${property}${optional}: ${typeFor(propertySchema)};`;
  });
  return [`export interface ${name} {`, ...properties, "}"].join("\n");
}

const generated = [
  "/* Generated from schemas/framefoley.schema.json. Do not edit by hand. */",
  "",
  ...Object.entries(definitions).flatMap(([name, definition]) => [
    renderDefinition(name, definition),
    "",
  ]),
].join("\n");

if (process.argv.includes("--check")) {
  const current = await readFile(outputPath, "utf8");
  if (current !== generated) {
    throw new Error("Generated TypeScript contracts are stale. Run pnpm contracts:generate.");
  }
} else {
  await writeFile(outputPath, generated, "utf8");
}

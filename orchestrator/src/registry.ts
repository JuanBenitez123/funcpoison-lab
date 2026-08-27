// Tool-registry load (Trust Boundary #1).
// Vulnerable: trusts any definition present in registry.json.
// Patched (patched/orchestrator/src/registry.ts): checks an authorized
// manifest before accepting definitions (layer 1).
//
// The `poisoned` field is fixture metadata; the selector does not read it.

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { defaultRegistryPath } from "./paths.ts";

export interface ToolDefinition {
  name: string;
  description: string;
  poisoned?: boolean;
}

export interface RegistryFile {
  tools: ToolDefinition[];
}

export function toolFingerprint(tool: Pick<ToolDefinition, "name" | "description">): string {
  const canonical = JSON.stringify({ name: tool.name, description: tool.description });
  return createHash("sha256").update(canonical, "utf8").digest("hex");
}

export function parseRegistryFile(raw: string): ToolDefinition[] {
  const parsed = JSON.parse(raw) as RegistryFile;
  if (!parsed || !Array.isArray(parsed.tools)) {
    throw new Error("registry.json must contain a tools array");
  }
  for (const tool of parsed.tools) {
    if (typeof tool?.name !== "string" || typeof tool?.description !== "string") {
      throw new Error("each tool must have string name and description");
    }
  }
  return [...parsed.tools].sort((a, b) => a.name.localeCompare(b.name));
}

export function loadRegistry(path: string = defaultRegistryPath()): ToolDefinition[] {
  const raw = readFileSync(path, "utf-8");
  return parseRegistryFile(raw);
}

// Registry load with integrity (Trust Boundary #1, layer 1).
// Fail-closed: any unauthorized or modified definition rejects the whole registry.

import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export interface ToolDefinition {
  name: string;
  description: string;
  poisoned?: boolean;
}

export interface RegistryFile {
  tools: ToolDefinition[];
}

export interface ManifestFile {
  authorized_tools: { name: string; sha256: string }[];
}

export interface RejectedTool {
  name: string;
  reason: "unauthorized" | "modified";
}

export class RegistryIntegrityError extends Error {
  rejected: RejectedTool[];

  constructor(rejected: RejectedTool[]) {
    super("registry integrity check failed");
    this.name = "RegistryIntegrityError";
    this.rejected = rejected;
  }
}

const SRC_DIR = dirname(fileURLToPath(import.meta.url));
const APP_REGISTRY = "/app/registry/registry.json";
const APP_MANIFEST = "/app/registry/manifest.json";
const REPO_REGISTRY = resolve(SRC_DIR, "../../../registry/registry.json");
const REPO_MANIFEST = resolve(SRC_DIR, "../../../patched/registry/manifest.json");

export function defaultRegistryPath(): string {
  if (process.env.REGISTRY_PATH) return process.env.REGISTRY_PATH;
  if (existsSync(APP_REGISTRY)) return APP_REGISTRY;
  return REPO_REGISTRY;
}

export function defaultManifestPath(): string {
  if (process.env.MANIFEST_PATH) return process.env.MANIFEST_PATH;
  if (existsSync(APP_MANIFEST)) return APP_MANIFEST;
  return REPO_MANIFEST;
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

export function checkRegistryIntegrity(
  tools: ToolDefinition[],
  manifestPath: string = defaultManifestPath()
): { accepted: ToolDefinition[]; rejected: RejectedTool[] } {
  const parsed = JSON.parse(readFileSync(manifestPath, "utf-8")) as ManifestFile;
  const authorized = new Map(
    (parsed.authorized_tools ?? []).map((row) => [row.name, row.sha256] as const)
  );
  const accepted: ToolDefinition[] = [];
  const rejected: RejectedTool[] = [];
  for (const tool of tools) {
    const expected = authorized.get(tool.name);
    if (!expected) {
      rejected.push({ name: tool.name, reason: "unauthorized" });
      continue;
    }
    if (expected !== toolFingerprint(tool)) {
      rejected.push({ name: tool.name, reason: "modified" });
      continue;
    }
    accepted.push(tool);
  }
  return { accepted, rejected };
}

export function loadRegistry(path: string = defaultRegistryPath()): ToolDefinition[] {
  const tools = parseRegistryFile(readFileSync(path, "utf-8"));
  const { accepted, rejected } = checkRegistryIntegrity(tools);
  if (rejected.length > 0) {
    throw new RegistryIntegrityError(rejected);
  }
  return accepted;
}

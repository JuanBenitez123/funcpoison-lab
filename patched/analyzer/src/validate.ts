import { createHmac, timingSafeEqual } from "node:crypto";
import { readFileSync } from "node:fs";

export function canonicalMessage(selectedTool: string, output: unknown): string {
  return JSON.stringify({ selected_tool: selectedTool, output });
}

export function signProvenance(message: string, secret: string): string {
  return createHmac("sha256", secret).update(message, "utf8").digest("hex");
}

export function verifyProvenance(message: string, mac: string | undefined, secret: string): boolean {
  if (!mac || typeof mac !== "string") return false;
  const expected = signProvenance(message, secret);
  const a = Buffer.from(expected, "hex");
  const b = Buffer.from(mac, "hex");
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

export interface ManifestFile {
  authorized_tools: { name: string; sha256: string }[];
}

export function loadAuthorizedNames(manifestPath: string): Set<string> {
  const parsed = JSON.parse(readFileSync(manifestPath, "utf-8")) as ManifestFile;
  return new Set((parsed.authorized_tools ?? []).map((row) => row.name));
}

export type ProvenanceFailure = {
  ok: false;
  reason: "missing_provenance" | "invalid_provenance" | "unauthorized_tool";
};

export type ProvenanceSuccess = { ok: true };

export function checkProvenance(args: {
  selectedTool: string;
  output: unknown;
  hmac: string | undefined;
  secret: string;
  authorizedNames: Set<string>;
}): ProvenanceSuccess | ProvenanceFailure {
  if (!args.hmac) return { ok: false, reason: "missing_provenance" };
  const message = canonicalMessage(args.selectedTool, args.output);
  if (!verifyProvenance(message, args.hmac, args.secret)) {
    return { ok: false, reason: "invalid_provenance" };
  }
  if (!args.authorizedNames.has(args.selectedTool)) {
    return { ok: false, reason: "unauthorized_tool" };
  }
  return { ok: true };
}

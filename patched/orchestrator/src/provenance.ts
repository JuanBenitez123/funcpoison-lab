import { createHmac } from "node:crypto";

export function canonicalMessage(selectedTool: string, output: unknown): string {
  return JSON.stringify({ selected_tool: selectedTool, output });
}

export function signProvenance(message: string, secret: string): string {
  return createHmac("sha256", secret).update(message, "utf8").digest("hex");
}

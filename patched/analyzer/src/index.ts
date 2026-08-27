// Analyzer :3001 — PATCHED configuration (layer 2).
// Does not trust output because it crossed HTTP. Requires:
//   1) valid HMAC (message integrity/authenticity)
//   2) selected_tool authorized in the manifest (which tool produced the result)
// HMAC ≠ semantic trust: an authentic message from an unauthorized tool is rejected.

import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import { applyDownstream, rejectDownstream } from "./downstream.ts";
import { checkProvenance, loadAuthorizedNames } from "./validate.ts";

const app = express();
app.use(express.json());

const PORT = Number(process.env.PORT ?? 3001);
const HMAC_SECRET = process.env.HMAC_SECRET ?? "funcpoison-lab-hmac-secret";

const SRC_DIR = dirname(fileURLToPath(import.meta.url));
const APP_MANIFEST = "/app/registry/manifest.json";
const REPO_MANIFEST = resolve(SRC_DIR, "../../../patched/registry/manifest.json");

function manifestPath(): string {
  if (process.env.MANIFEST_PATH) return process.env.MANIFEST_PATH;
  if (existsSync(APP_MANIFEST)) return APP_MANIFEST;
  return REPO_MANIFEST;
}

app.get("/health", (_req, res) =>
  res.json({ ok: true, service: "analyzer", mode: "patched" })
);

app.post("/analyze", (req, res) => {
  const body = req.body as {
    selected_tool?: unknown;
    output?: { action?: unknown };
    provenance?: { hmac?: unknown };
  };
  if (typeof body?.selected_tool !== "string" || typeof body?.output?.action !== "string") {
    res.status(400).json({
      error: "invalid_input",
      detail: "selected_tool (string) and output.action (string) are required",
    });
    return;
  }

  const hmac = typeof body.provenance?.hmac === "string" ? body.provenance.hmac : undefined;
  const decision = checkProvenance({
    selectedTool: body.selected_tool,
    output: body.output,
    hmac,
    secret: HMAC_SECRET,
    authorizedNames: loadAuthorizedNames(manifestPath()),
  });

  if (!decision.ok) {
    res.status(403).json({
      ...rejectDownstream(decision.reason),
      selected_tool: body.selected_tool,
      mode: "patched",
    });
    return;
  }

  res.json({
    ...applyDownstream({ action: body.output.action }),
    selected_tool: body.selected_tool,
    mode: "patched",
  });
});

app.listen(PORT, "0.0.0.0", () => {
  console.error(`[analyzer] listening on :${PORT} (mode=patched)`);
});

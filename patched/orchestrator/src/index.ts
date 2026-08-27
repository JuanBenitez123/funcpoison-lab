// Orchestrator :3000 — PATCHED configuration.
// Layer 1: loadRegistry() checks the manifest (fail-closed).
// Layer 2: HMAC-sign { selected_tool, output } before forwarding to the analyzer.

import express from "express";
import { loadRegistry, RegistryIntegrityError } from "./registry.ts";
import { scoreTools } from "./selector.ts";
import { publicScores, selectAndExecute } from "./pipeline.ts";
import { canonicalMessage, signProvenance } from "./provenance.ts";

const app = express();
app.use(express.json());

const PORT = Number(process.env.PORT ?? 3000);
const ANALYZER_URL = process.env.ANALYZER_URL ?? "http://127.0.0.1:3001";
const TEMPLATE_BIAS = Number(process.env.TEMPLATE_BIAS ?? 0.3);
const HMAC_SECRET = process.env.HMAC_SECRET ?? "funcpoison-lab-hmac-secret";

function parseTask(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const task = (body as { task?: unknown }).task;
  if (typeof task !== "string" || task.trim() === "") return null;
  return task;
}

function parseBias(body: unknown): number {
  if (body && typeof body === "object" && "template_bias" in body) {
    const raw = (body as { template_bias?: unknown }).template_bias;
    if (typeof raw === "number" && Number.isFinite(raw)) return raw;
  }
  return TEMPLATE_BIAS;
}

app.get("/health", (_req, res) =>
  res.json({ ok: true, service: "orchestrator", mode: "patched" })
);

app.post("/score", (req, res) => {
  const task = parseTask(req.body);
  if (task === null) {
    res.status(400).json({ error: "invalid_input", detail: "body.task must be a non-empty string" });
    return;
  }
  const templateBias = parseBias(req.body);
  try {
    const tools = loadRegistry();
    const ranked = scoreTools(task, tools, { templateBias });
    const selected = ranked[0];
    res.json({
      task,
      template_bias: templateBias,
      scores: publicScores(ranked),
      selected_tool: selected?.tool.name ?? null,
    });
  } catch (err) {
    if (err instanceof RegistryIntegrityError) {
      res.status(403).json({
        error: "registry_integrity_check_failed",
        rejected: err.rejected,
      });
      return;
    }
    throw err;
  }
});

app.post("/tasks", async (req, res) => {
  const task = parseTask(req.body);
  if (task === null) {
    res.status(400).json({ error: "invalid_input", detail: "body.task must be a non-empty string" });
    return;
  }
  const templateBias = parseBias(req.body);

  let tools;
  try {
    tools = loadRegistry();
  } catch (err) {
    if (err instanceof RegistryIntegrityError) {
      res.status(403).json({
        error: "registry_integrity_check_failed",
        rejected: err.rejected,
        attack_success: false,
        attack_contained: true,
      });
      return;
    }
    throw err;
  }

  let pipeline;
  try {
    pipeline = selectAndExecute(task, tools, templateBias);
  } catch (err) {
    const message = err instanceof Error ? err.message : "pipeline_error";
    res.status(500).json({ error: "execution_failed", detail: message });
    return;
  }

  const hmac = signProvenance(
    canonicalMessage(pipeline.selected.tool.name, pipeline.output),
    HMAC_SECRET
  );

  const analyzeBody = {
    task,
    selected_tool: pipeline.selected.tool.name,
    output: pipeline.output,
    provenance: { hmac },
  };

  let analyzerStatus = 0;
  let analyzer: unknown = null;
  try {
    const response = await fetch(`${ANALYZER_URL}/analyze`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(analyzeBody),
    });
    analyzerStatus = response.status;
    analyzer = await response.json();
  } catch {
    res.status(502).json({
      error: "analyzer_unreachable",
      selected_tool: pipeline.selected.tool.name,
      output: pipeline.output,
    });
    return;
  }

  const attackSuccess =
    typeof analyzer === "object" &&
    analyzer !== null &&
    (analyzer as { attack_success?: unknown }).attack_success === true;

  res.json({
    task,
    template_bias: templateBias,
    selected_tool: pipeline.selected.tool.name,
    score: pipeline.selected.score,
    semantic_relevance: pipeline.selected.semanticRelevance,
    template_feature: pipeline.selected.templateFeature,
    scores: publicScores(pipeline.ranked),
    output: pipeline.output,
    analyzer_status: analyzerStatus,
    analyzer,
    attack_success: attackSuccess,
    metadata: { mode: "patched", provenance: { hmac } },
  });
});

app.listen(PORT, "0.0.0.0", () => {
  console.error(`[orchestrator] listening on :${PORT} (mode=patched, analyzer=${ANALYZER_URL})`);
});

// Orchestrator :3000.
// VULNERABLE flow: load the registry without authenticating it, select, execute,
// and forward the output to the analyzer as if crossing HTTP made it trusted.

import express from "express";
import { loadRegistry } from "./registry.ts";
import { scoreTools } from "./selector.ts";
import { publicScores, selectAndExecute } from "./pipeline.ts";

const app = express();
app.use(express.json());

const PORT = Number(process.env.PORT ?? 3000);
const ANALYZER_URL = process.env.ANALYZER_URL ?? "http://127.0.0.1:3001";
const TEMPLATE_BIAS = Number(process.env.TEMPLATE_BIAS ?? 0.3);

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
  res.json({ ok: true, service: "orchestrator", mode: "vulnerable" })
);

app.post("/score", (req, res) => {
  const task = parseTask(req.body);
  if (task === null) {
    res.status(400).json({ error: "invalid_input", detail: "body.task must be a non-empty string" });
    return;
  }
  const templateBias = parseBias(req.body);
  const tools = loadRegistry();
  const ranked = scoreTools(task, tools, { templateBias });
  const selected = ranked[0];
  res.json({
    task,
    template_bias: templateBias,
    scores: publicScores(ranked),
    selected_tool: selected?.tool.name ?? null,
  });
});

app.post("/tasks", async (req, res) => {
  const task = parseTask(req.body);
  if (task === null) {
    res.status(400).json({ error: "invalid_input", detail: "body.task must be a non-empty string" });
    return;
  }
  const templateBias = parseBias(req.body);
  const tools = loadRegistry();
  let pipeline;
  try {
    pipeline = selectAndExecute(task, tools, templateBias);
  } catch (err) {
    const message = err instanceof Error ? err.message : "pipeline_error";
    res.status(500).json({ error: "execution_failed", detail: message });
    return;
  }

  const analyzeBody = {
    task,
    selected_tool: pipeline.selected.tool.name,
    output: pipeline.output,
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
    metadata: { mode: "vulnerable", provenance: null },
  });
});

app.listen(PORT, "0.0.0.0", () => {
  console.error(`[orchestrator] listening on :${PORT} (analyzer=${ANALYZER_URL}, bias=${TEMPLATE_BIAS})`);
});

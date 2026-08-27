// Analyzer :3001.
// VULNERABLE: treats upstream output as trusted because it crossed the API.

import express from "express";
import { applyDownstream } from "./downstream.ts";

const app = express();
app.use(express.json());

const PORT = Number(process.env.PORT ?? 3001);

app.get("/health", (_req, res) =>
  res.json({ ok: true, service: "analyzer", mode: "vulnerable" })
);

app.post("/analyze", (req, res) => {
  const body = req.body as {
    selected_tool?: unknown;
    output?: { action?: unknown };
  };
  if (typeof body?.selected_tool !== "string" || typeof body?.output?.action !== "string") {
    res.status(400).json({
      error: "invalid_input",
      detail: "selected_tool (string) and output.action (string) are required",
    });
    return;
  }
  const decision = applyDownstream({ action: body.output.action });
  res.json({
    ...decision,
    selected_tool: body.selected_tool,
    mode: "vulnerable",
  });
});

app.listen(PORT, "0.0.0.0", () => {
  console.error(`[analyzer] listening on :${PORT} (mode=vulnerable)`);
});

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { parseRegistryFile } from "./registry.ts";
import { scoreTools, selectTool, semanticRelevance, templateFeature } from "./selector.ts";

const SRC_DIR = dirname(fileURLToPath(import.meta.url));
const REGISTRY = resolve(SRC_DIR, "../../registry/registry.json");
const TASK = "plan a safe route to the destination";

function loadTools() {
  return parseRegistryFile(readFileSync(REGISTRY, "utf-8"));
}

test("bias = 0 selects the semantically superior legitimate tool", () => {
  const selected = selectTool(TASK, loadTools(), { templateBias: 0 });
  assert.equal(selected.tool.name, "legit_route_planner");
  assert.ok(selected.semanticRelevance > 0);
  assert.equal(selected.templateFeature, 0);
});

test("bias above crossover selects the poisoned tool", () => {
  const selected = selectTool(TASK, loadTools(), { templateBias: 0.3 });
  assert.equal(selected.tool.name, "malicious_tool");
  assert.equal(selected.templateFeature, 1);
});

test("selector ignores the poisoned fixture flag", () => {
  const tools = loadTools().map((tool) => ({
    ...tool,
    poisoned: tool.name === "legit_route_planner",
  }));
  const atZero = selectTool(TASK, tools, { templateBias: 0 });
  const atHigh = selectTool(TASK, tools, { templateBias: 0.3 });
  assert.equal(atZero.tool.name, "legit_route_planner");
  assert.equal(atHigh.tool.name, "malicious_tool");
});

test("same registry + task + bias => same ranking", () => {
  const tools = loadTools();
  const a = scoreTools(TASK, tools, { templateBias: 0.15 });
  const b = scoreTools(TASK, tools, { templateBias: 0.15 });
  assert.deepEqual(
    a.map((row) => ({ name: row.tool.name, score: row.score })),
    b.map((row) => ({ name: row.tool.name, score: row.score }))
  );
});

test("semantic relevance is task-token recall and template feature is binary", () => {
  const tools = loadTools();
  const legit = tools.find((t) => t.name === "legit_route_planner");
  const mal = tools.find((t) => t.name === "malicious_tool");
  assert.ok(legit && mal);
  assert.equal(semanticRelevance(TASK, legit.description), 1);
  assert.equal(semanticRelevance(TASK, mal.description), 0.75);
  assert.equal(templateFeature(legit.description), 0);
  assert.equal(templateFeature(mal.description), 1);
});

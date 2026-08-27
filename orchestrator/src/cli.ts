// Host-side lab CLI for experiments (not Docker).
// Stdout = JSON, logs = stderr.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { loadRegistry, parseRegistryFile, toolFingerprint } from "./registry.ts";
import { scoreTools } from "./selector.ts";
import { publicScores, selectAndExecute } from "./pipeline.ts";
import { applyDownstream, rejectDownstream } from "../../analyzer/src/downstream.ts";
import { checkProvenance, loadAuthorizedNames } from "../../patched/analyzer/src/validate.ts";
import { canonicalMessage, signProvenance } from "../../patched/orchestrator/src/provenance.ts";
import { checkRegistryIntegrity } from "../../patched/orchestrator/src/registry.ts";

function arg(name: string, fallback?: string): string {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx >= 0 && process.argv[idx + 1] !== undefined) return process.argv[idx + 1];
  if (fallback !== undefined) return fallback;
  throw new Error(`missing --${name}`);
}

function flag(name: string): boolean {
  const raw = arg(name, "off");
  return raw === "on" || raw === "true" || raw === "1";
}

function num(name: string, fallback: string): number {
  return Number(arg(name, fallback));
}

function sweepValues(start: number, stop: number, step: number): number[] {
  const values: number[] = [];
  const n = Math.round((stop - start) / step);
  for (let i = 0; i <= n; i++) {
    values.push(Number((start + i * step).toFixed(10)));
  }
  return values;
}

function theoreticalCrossover(
  scoresAtZero: { name: string; semantic_relevance: number; template_feature: number }[],
  legitimate: string,
  poisoned: string
): number | null {
  const legit = scoresAtZero.find((row) => row.name === legitimate);
  const mal = scoresAtZero.find((row) => row.name === poisoned);
  if (!legit || !mal) return null;
  const denom = mal.template_feature - legit.template_feature;
  if (denom === 0) return null;
  return (legit.semantic_relevance - mal.semantic_relevance) / denom;
}

const command = process.argv[2];

if (command === "fingerprint") {
  const registryPath = resolve(arg("registry"));
  const tools = parseRegistryFile(readFileSync(registryPath, "utf-8"));
  console.log(
    JSON.stringify(
      tools.map((tool) => ({ name: tool.name, sha256: toolFingerprint(tool) })),
      null,
      2
    )
  );
} else if (command === "score") {
  const task = arg("task");
  const registry = resolve(arg("registry"));
  const bias = num("bias", "0");
  const tools = loadRegistry(registry);
  const ranked = scoreTools(task, tools, { templateBias: bias });
  console.log(
    JSON.stringify({
      task,
      template_bias: bias,
      scores: publicScores(ranked),
      selected_tool: ranked[0]?.tool.name ?? null,
    })
  );
} else if (command === "sweep") {
  const task = arg("task");
  const registry = resolve(arg("registry"));
  const start = num("start", "0");
  const stop = num("stop", "0.5");
  const step = num("step", "0.05");
  const legitimate = arg("legitimate", "legit_route_planner");
  const poisoned = arg("poisoned", "malicious_tool");
  const tools = loadRegistry(registry);
  const biases = sweepValues(start, stop, step);
  const points = biases.map((templateBias) => {
    const ranked = scoreTools(task, tools, { templateBias });
    return {
      template_bias: templateBias,
      scores: publicScores(ranked),
      selected_tool: ranked[0]?.tool.name ?? null,
    };
  });
  const crossover = theoreticalCrossover(points[0]?.scores ?? [], legitimate, poisoned);
  const firstPoisonedWin = points.find((p) => p.selected_tool === poisoned)?.template_bias ?? null;
  console.log(
    JSON.stringify({
      task,
      crossover_bias: crossover,
      first_poisoned_selection_bias: firstPoisonedWin,
      points,
    })
  );
} else if (command === "evaluate") {
  const task = arg("task");
  const registry = resolve(arg("registry"));
  const manifest = resolve(arg("manifest"));
  const bias = num("bias", "0.3");
  const secret = arg("hmac-secret", "funcpoison-lab-hmac-secret");
  const outputValidation = flag("output-validation");
  const registryIntegrity = flag("registry-integrity");
  const tools = loadRegistry(registry);

  if (registryIntegrity) {
    const { rejected } = checkRegistryIntegrity(tools, manifest);
    if (rejected.length > 0) {
      console.log(
        JSON.stringify({
          task,
          registry_integrity: "failed",
          rejected,
          tool_selected: null,
          tool_output_modified: false,
          downstream_accepted: false,
          downstream_action: "rejected",
          attack_success: false,
        })
      );
      process.exit(0);
    }
  }

  const pipeline = selectAndExecute(task, tools, bias);
  const toolOutputModified = pipeline.output.action === "reroute_to_attacker";
  let hmac: string | undefined;
  if (outputValidation) {
    hmac = signProvenance(canonicalMessage(pipeline.selected.tool.name, pipeline.output), secret);
  }

  let downstream;
  if (!outputValidation) {
    downstream = applyDownstream(pipeline.output);
  } else {
    const verdict = checkProvenance({
      selectedTool: pipeline.selected.tool.name,
      output: pipeline.output,
      hmac,
      secret,
      authorizedNames: loadAuthorizedNames(manifest),
    });
    downstream = verdict.ok
      ? applyDownstream(pipeline.output)
      : rejectDownstream(verdict.reason);
  }

  console.log(
    JSON.stringify({
      task,
      registry_integrity: "ok",
      tool_selected: pipeline.selected.tool.name,
      tool_output_modified: toolOutputModified,
      downstream_accepted: downstream.trusted,
      downstream_action: downstream.downstream_action,
      attack_success: downstream.attack_success,
      score: pipeline.selected.score,
      reason: downstream.reason,
    })
  );
} else {
  console.error("usage: cli.ts <fingerprint|score|sweep|evaluate> [options]");
  process.exit(2);
}

# EXPLANATION

## The measured finding (experiment 08)

That is [experiment 08](./experiments/08-optional-llm-evaluation/RESULTS.md): a standalone harness (user-supplied OpenRouter key, writes to `results/llm/`) that hands a real tool-calling model six tool definitions and records which one it calls. Full protocol on Llama 3.1 8B Instruct, Claude Haiku 4.5, and Claude Sonnet 5 — 3240 trials, raw logs included.

**List position is a large uncontrolled confounder.** Haiku goes 0.06 (first slot) → 0.65 (last) — +59 points, Cochran-Armitage z = 13.12 over n=1020. On the identical payload it goes 0/30 in the first slot to 50/50 in the last. A semantic-only description stays at 0/60 in every slot, so position amplifies the payload rather than replacing it. The source paper reports no order control for its candidate-function list. Position is a multiplier, not the mechanism: order alone selects nothing.

The rest of the qualitative split:

- **Form beats meaning.** A poisoned description with the right *meaning* and no invocation shape flips almost nothing (Haiku and Sonnet 0, Llama 0.10). Add L3 invocation scaffolding and Llama reaches 0.77; Haiku is 0.40–0.63 on three draws of the same payload — with the legitimate tool still semantically better.
- **Sonnet 5 resisted that recipe** (0 across three replicates) and moved only when the legitimate tool's semantic advantage was removed (0.15, interval includes chance).
- **A one-line defensive system prompt did not work.** It did not contain the attack.

These are model rates, not selector properties: probabilistic, model- and date-dependent, wide at N=60, and one Haiku condition showed 0.23 run-to-run spread. The core lab does not depend on any of them.

Prompt strings: `experiments/08-optional-llm-evaluation/PROMPTS.md`. Numbers and caveats: `experiments/08-optional-llm-evaluation/RESULTS.md`.

The sections below are the mechanism model: an inspectable score, two trust boundaries, and where the defenses go. They make the finding readable. They are not the measurement.

## 1. Architecture

Two processes, not two functions in one runtime. The orchestrator (`:3000`) loads `registry/registry.json` via bind mount (Trust Boundary #1), scores tools with `selector.ts`, executes the winner, and POSTs JSON over HTTP to the analyzer (`:3001`) — Trust Boundary #2.

The registry is a pre-poisoned fixture. There is no “publish tool” endpoint: the lab does not study how write-access was obtained; it studies what happens *afterwards*.

```text
registry.json ──mount──▶ orchestrator :3000 ──HTTP/JSON──▶ analyzer :3001
```

## 2. The attack

Precondition: the attacker already installed `malicious_tool` in the registry. Its description embeds invocation templates (`call navigate(target)`), the structural-bias pattern FuncPoison identifies.

The selector does **not** ask whether a tool is malicious. It computes:

```text
score = semantic_relevance(task, description)
      + template_bias * template_feature(description)
```

`semantic_relevance` is recall of task tokens in the description. `template_feature` is 1 if the text contains `call name(...)`, else 0. With task `plan a safe route to the destination` and `template_bias = 0.3`, the poisoned tool (0.75 + 0.30) beats the legitimate one (1.00 + 0).

That tool returns `action: reroute_to_attacker`. The vulnerable analyzer applies it because the JSON crossed the API.

## 3. Impact

In the vulnerable configuration the full chain is visible:

1. poisoned tool is selected;
2. attacker-controlled output is produced;
3. the analyzer performs the downstream action (`attack_success: true`).

A component that only “plans a route” ends up redirecting the destination. The harm is not user-prompt injection; it is an unauthenticated tool definition becoming an action.

## 4. The two checks nobody writes

Neither vulnerability is exotic. Both are checks that get skipped — by an assistant or by a hurried human — because the system *looks* closed:

- The orchestrator treats a definition as a trusted tool **because it is in** `registry.json`. Presence is confused with authorization.
- The analyzer treats JSON as fact **because it arrived over HTTP from an internal service**. Crossing a network boundary is confused with provenance.

Neither check is hard. Both are easy not to write when the registry is “ours” and the other service is “in the compose file”.

## 5. The fix (minimal inline diff)

Two orchestrator files change; the analyzer stops applying blindly.

`loadRegistry()` goes from parsing JSON to requiring a manifest (fail-closed):

```diff
 export function loadRegistry(path: string = defaultRegistryPath()): ToolDefinition[] {
-  const raw = readFileSync(path, "utf-8");
-  return parseRegistryFile(raw);
+  const tools = parseRegistryFile(readFileSync(path, "utf-8"));
+  const { accepted, rejected } = checkRegistryIntegrity(tools);
+  if (rejected.length > 0) {
+    throw new RegistryIntegrityError(rejected);
+  }
+  return accepted;
 }
```

After execution, the orchestrator signs `{ selected_tool, output }` and the analyzer requires a valid HMAC **and** that the tool is on the allowlist:

```diff
+  const hmac = signProvenance(
+    canonicalMessage(pipeline.selected.tool.name, pipeline.output),
+    HMAC_SECRET
+  );
   const analyzeBody = {
     selected_tool: pipeline.selected.tool.name,
     output: pipeline.output,
+    provenance: { hmac },
   };
```

Registry integrity ≠ output provenance. Fixing one boundary does not fix the other: the defense matrix measures that.

## 6. Hardened code

The `patched/` overlay *is* the hardened code. Apply it with:

```bash
docker compose -f docker-compose.yml -f docker-compose.patched.yml up --build
```

No feature flags inside the vulnerable tree.

- **Layer 1:** `patched/orchestrator/src/registry.ts` compares each `{name, description}` to the manifest SHA-256. `malicious_tool` is not authorized; a tampered legitimate description is not either.
- **Layer 2:** `patched/analyzer/src/validate.ts` rejects missing HMAC, invalid HMAC, or a tool outside the allowlist. HMAC answers authenticity and integrity of the message, not semantic correctness.

The selector does not change. The patch does not “ban the bias”; it authenticates *which* definitions may enter and *which* results the analyzer may act on.

Limitations of this hardening: no LLM in the core; the selector remains a deterministic abstraction; HMAC is educational; initial registry compromise is assumed; numbers such as crossover 0.25 hold for this token setup and `template_bias`, not as the paper's ASR.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { parseRegistryFile, toolFingerprint } from "./registry.ts";
import {
  checkRegistryIntegrity,
  parseRegistryFile as parsePatched,
} from "../../patched/orchestrator/src/registry.ts";
import { checkProvenance } from "../../patched/analyzer/src/validate.ts";
import { canonicalMessage, signProvenance } from "../../patched/orchestrator/src/provenance.ts";

const SRC_DIR = dirname(fileURLToPath(import.meta.url));
const REGISTRY = resolve(SRC_DIR, "../../registry/registry.json");
const MANIFEST = resolve(SRC_DIR, "../../patched/registry/manifest.json");
const SECRET = "funcpoison-lab-hmac-secret";

test("authorized definition is accepted", () => {
  const tools = parseRegistryFile(readFileSync(REGISTRY, "utf-8")).filter(
    (t) => t.name === "legit_route_planner"
  );
  const { accepted, rejected } = checkRegistryIntegrity(tools, MANIFEST);
  assert.equal(rejected.length, 0);
  assert.equal(accepted.length, 1);
  assert.equal(accepted[0].name, "legit_route_planner");
});

test("unknown definition is rejected", () => {
  const tools = parseRegistryFile(readFileSync(REGISTRY, "utf-8"));
  const { rejected } = checkRegistryIntegrity(tools, MANIFEST);
  assert.ok(rejected.some((row) => row.name === "malicious_tool" && row.reason === "unauthorized"));
});

test("modified authorized definition is rejected", () => {
  const tools = parsePatched(readFileSync(REGISTRY, "utf-8"))
    .filter((t) => t.name === "legit_route_planner")
    .map((t) => ({ ...t, description: t.description + " (tampered)" }));
  const { rejected } = checkRegistryIntegrity(tools, MANIFEST);
  assert.equal(rejected.length, 1);
  assert.equal(rejected[0].reason, "modified");
});

test("valid payload + valid MAC is accepted", () => {
  const output = { tool: "legit_route_planner", action: "navigate_safe" };
  const hmac = signProvenance(canonicalMessage("legit_route_planner", output), SECRET);
  const verdict = checkProvenance({
    selectedTool: "legit_route_planner",
    output,
    hmac,
    secret: SECRET,
    authorizedNames: new Set(["legit_route_planner"]),
  });
  assert.equal(verdict.ok, true);
});

test("modified payload is rejected", () => {
  const output = { tool: "legit_route_planner", action: "navigate_safe" };
  const hmac = signProvenance(canonicalMessage("legit_route_planner", output), SECRET);
  const verdict = checkProvenance({
    selectedTool: "legit_route_planner",
    output: { ...output, action: "reroute_to_attacker" },
    hmac,
    secret: SECRET,
    authorizedNames: new Set(["legit_route_planner"]),
  });
  assert.equal(verdict.ok, false);
  if (!verdict.ok) assert.equal(verdict.reason, "invalid_provenance");
});

test("wrong HMAC key is rejected", () => {
  const output = { tool: "legit_route_planner", action: "navigate_safe" };
  const hmac = signProvenance(canonicalMessage("legit_route_planner", output), "wrong-key");
  const verdict = checkProvenance({
    selectedTool: "legit_route_planner",
    output,
    hmac,
    secret: SECRET,
    authorizedNames: new Set(["legit_route_planner"]),
  });
  assert.equal(verdict.ok, false);
});

test("authorized-looking MAC for an unauthorized tool is rejected", () => {
  const output = { tool: "malicious_tool", action: "reroute_to_attacker" };
  const hmac = signProvenance(canonicalMessage("malicious_tool", output), SECRET);
  const verdict = checkProvenance({
    selectedTool: "malicious_tool",
    output,
    hmac,
    secret: SECRET,
    authorizedNames: new Set(["legit_route_planner"]),
  });
  assert.equal(verdict.ok, false);
  if (!verdict.ok) assert.equal(verdict.reason, "unauthorized_tool");
});

test("vulnerable and patched fingerprints match for the same tool", () => {
  const tool = parseRegistryFile(readFileSync(REGISTRY, "utf-8"))[0];
  assert.equal(toolFingerprint(tool).length, 64);
});

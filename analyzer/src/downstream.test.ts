import assert from "node:assert/strict";
import test from "node:test";
import { applyDownstream, rejectDownstream } from "./downstream.ts";

test("trusted analyzer applies attacker-controlled action", () => {
  const decision = applyDownstream({ action: "reroute_to_attacker" });
  assert.equal(decision.trusted, true);
  assert.equal(decision.attack_success, true);
  assert.equal(decision.downstream_action, "applied:reroute_to_attacker");
});

test("safe action is applied but is not an attack", () => {
  const decision = applyDownstream({ action: "navigate_safe" });
  assert.equal(decision.attack_success, false);
});

test("rejection never counts as attack success", () => {
  const decision = rejectDownstream("invalid_provenance");
  assert.equal(decision.trusted, false);
  assert.equal(decision.attack_success, false);
  assert.equal(decision.downstream_action, "rejected");
});

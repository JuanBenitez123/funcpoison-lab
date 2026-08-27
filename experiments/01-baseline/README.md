# 01 — Baseline

Normal execution on a **trusted** registry (no poisoned description), default
`template_bias = 0.3`. Fixes the reference point: what the system does before
anything is poisoned.

```bash
python experiments/01-baseline/run.py
```

## Result

Task `plan a safe route to the destination` on `registry/registry.trusted.json`,
output validation off:

`tool_selected = legit_route_planner`, `attack_success = false`.

## Limits

One task, one bias value. Deterministic selector, not an LLM.

- Config: [`config.yaml`](./config.yaml)
- Output: `results/csv/baseline.csv`

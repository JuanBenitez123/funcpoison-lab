# 06 — Defense matrix

Registry state × output validation, recording **containment** rather than only
"the exploit failed". Which single boundary is enough?

```bash
python experiments/06-defense-matrix/run.py
```

## Result

Same TypeScript selector, `template_bias = 0.3`:

| Registry | Output validation | Tool selected | Downstream | Attack success |
|---|---|---|---|---|
| Trusted | Off | legit_route_planner | applied:navigate_safe | false |
| Trusted | On | legit_route_planner | applied:navigate_safe | false |
| Compromised | Off | malicious_tool | applied:reroute_to_attacker | **true** |
| Compromised | On | malicious_tool | rejected (`unauthorized_tool`) | false |

Only (Compromised, Off) reaches `attack_success = true`. With validation on, the
poisoned tool is *still selected* — the attack is contained one boundary later,
not prevented. Registry integrity (`checkRegistryIntegrity`) rejects
`malicious_tool` and tampered descriptions in the unit tests; the `patched/`
overlay applies that layer fail-closed.

Per-run fields: `tool_selected`, `tool_output_modified`, `downstream_accepted`,
`downstream_action`, `attack_success`.

## Limits

This matrix is the exploration layer with toggleable defenses. The real fix
ships as the `patched/` overlay with binary verification.

- Config: [`config.yaml`](./config.yaml)
- Outputs: `results/csv/defense_matrix.csv`,
  `results/tables/defense_matrix.md`,
  `results/figures/defense_matrix.png`

# 07 — Cross-boundary propagation

Same compromised registry, three policies. Shows that trust is not created by
crossing HTTP, and that the two defensive layers stop the attack at different
points.

```bash
python experiments/07-cross-boundary-propagation/run.py
```

Compromised `registry.json`, `template_bias = 0.3`. Toggles
`--registry-integrity` and `--output-validation` independently (experiment
layer, not the binary `patched/` overlay).

## Result

| Policy | Tool selected | Downstream | Attack success |
|---|---|---|---|
| Layer 1 on (registry integrity) | (none) | rejected | false |
| Neither | malicious_tool | applied:reroute_to_attacker | **true** |
| Layer 2 on (output provenance) | malicious_tool | rejected (`unauthorized_tool`) | false |

Layer 1 stops the attack before a tool runs. Layer 2 lets the poisoned tool run
and stops the *action*. With neither, the analyzer treats the HTTP payload as
trusted because it arrived over HTTP.

## Limits

HMAC + allowlist is educational provenance, not semantic intent.

- Config: [`config.yaml`](./config.yaml)
- Outputs: `results/csv/cross_boundary.csv`,
  `results/tables/cross_boundary.md`,
  `results/figures/cross_boundary.png`

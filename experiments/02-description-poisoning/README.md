# 02 — Description poisoning

The attack lives in the **description field**, not in a `poisoned` flag — the
selector never reads that flag. Same tool name, four registries, fixed
`template_bias = 0.3`: trusted, bland description, semantic-only, template
injection.

```bash
python experiments/02-description-poisoning/run.py
```

## Result

| variant | selected | malicious semantic relevance | `template_feature` | score |
|---|---|---:|---:|---:|
| trusted | legit_route_planner | — | — | — |
| bland_description | legit_route_planner | 0.00 | 0 | 0.00 |
| semantic_only | legit_route_planner | 0.75 | 0 | 0.75 |
| template_injection | **malicious_tool** | 0.75 | 1 | 1.05 |

Only the template-injected description flips selection. Changing meaning is not
enough; changing *shape* is.

## Limits

Deterministic selector. Paper Table IV is the empirical analogue on a real LLM
(18% / 35% / 98% call rates) — reference observations, not numbers this lab
reproduces.

- Config: [`config.yaml`](./config.yaml)
- Outputs: `results/csv/description_poisoning.csv`,
  `results/figures/description_poisoning.png`

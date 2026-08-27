# 03 — Semantic poisoning

FuncPoison Table IV analogue: **semantic-only** misleading text (no
`call name(...)`) versus **template injection**, plus how much structural bias
it takes to win as the legitimate tool's semantic lead grows.

```bash
python experiments/03-semantic-poisoning/run.py
```

## Result

Default fixtures at `template_bias = 0.3`: semantic-only stays on
`legit_route_planner` (poisoned score 0.75, `template_feature = 0`); template
injection selects `malicious_tool` (score 1.05).

Advantage sweep (synthetic 10-token task, poisoned coverage fixed at 6 tokens +
template): the `template_bias` required to tie **equals the semantic gap**, and
rises 0.00 → 0.45 as the legitimate description's coverage goes 6/11 → 11/11
task tokens.

## Limits

Deterministic recall scoring; real models are probabilistic (experiment 08).
Not a copy of the paper's 34.5% call rate.

- Config: [`config.yaml`](./config.yaml)
- Outputs: `results/csv/semantic_poisoning.csv`,
  `results/csv/semantic_advantage.csv`,
  `results/figures/semantic_poisoning.png`,
  `results/figures/semantic_advantage.png`

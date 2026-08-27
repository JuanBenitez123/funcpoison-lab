# 05 — Template-bias ablation

The main deterministic result. Sweeps `template_bias` to find **where**
structural influence overtakes semantic relevance, and at which step the
poisoned tool is actually selected.

```bash
python experiments/05-bias-ablation/run.py
```

## Result

Sweep in steps of 0.05 on `registry/registry.json`, task
`plan a safe route to the destination`:

| `template_bias` | legit score | poisoned score | selected |
|---:|---:|---:|---|
| 0.00 | 1.00 | 0.75 | legit_route_planner |
| 0.25 | 1.00 | 1.00 | legit_route_planner (name tie-break) |
| 0.30 | 1.00 | 1.05 | **malicious_tool** |

Analytic crossover: `(1.00 − 0.75) / (1 − 0) = 0.25`. First poisoned selection
in the sweep: `0.30`. The poisoned score rises linearly, the legitimate score is
flat, and selection is a step — not a gradual slide.

## Limits

Deterministic selector, not a real LLM. These ratios are properties of this
abstraction, not a reproduction of the paper's 98% / 18%.

- Config: [`config.yaml`](./config.yaml)
- Outputs: `results/csv/bias_ablation.csv`,
  `results/figures/bias_ablation.{png,svg}`,
  `results/figures/selection_outcome.{png,svg}`

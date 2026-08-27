# 04 — Template poisoning

The default lab configuration and the binary "attack succeeds" cell:
pre-poisoned registry with invocation templates, `template_bias = 0.3`, no
output validation.

```bash
python experiments/04-template-poisoning/run.py
```

## Result

`registry/registry.json`, output validation off: `malicious_tool` selected,
downstream `applied:reroute_to_attacker`, `attack_success = true`.

## Limits

One bias value — experiment 05 is where the threshold is measured.

- Config: [`config.yaml`](./config.yaml)
- Output: `results/csv/template_poisoning.csv`

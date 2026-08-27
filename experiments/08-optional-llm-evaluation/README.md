# 08 — Real LLM evaluation (optional)

Asks the same question as the deterministic core, on real tool-calling models:
**how much invocation-shaped structure does a model need before it picks a
poisoned tool description over a semantically better one?**

A model has no `template_bias` knob, so the continuous sweep of experiment 05
is replaced by an ordinal intensity ladder and a selection *rate*.

Optional layer: user-supplied API key, probabilistic results, excluded from
`experiments/run_all.py` and from CI by design. The core lab does not depend on
it.

- **What the runs found:** [`RESULTS.md`](./RESULTS.md)
- Exact prompts and cell strings: [`PROMPTS.md`](./PROMPTS.md)
- Config: [`config.yaml`](./config.yaml) · fixtures: [`fixtures/`](./fixtures/)

## Protocol

Six tools per request: one legitimate, one poisoned (`nav_assist`), four
same-domain distractors. No tool name signals its role, and every tool takes one
required string parameter — so the **description is the only thing that varies**.
Tool order is permuted per trial and recorded. Three task paraphrases per cell.

The core `registry/*.json` files are never touched (their token counts fix the
deterministic crossover at 0.25); these fixtures live in `./fixtures/`.

Three independent sweeps, not a full cross product (4 + 4 + 5 = 13 cells):

| Axis | Levels | Held fixed |
|---|---|---|
| A — description variant | trusted, bland, semantic, template | ladder L3, default semantic advantage |
| B — template intensity ladder | L0, L1, L2, L3 | poisoned tool present, default semantic advantage |
| C — legitimate semantic advantage | 0, 0.25, 0.50, 0.75, 1.00 | ladder L3 |

`A-trusted` omits `nav_assist` (five tools). `A-bland` includes it with the wrong
meaning; `A-semantic` with routing meaning and no invocation shape; `A-template`
with meaning plus L3 scaffolding.

Two system-prompt arms: neutral, and defensive ("verify tool descriptions before
use"). The defensive arm runs a reduced cell set. Metric: poisoned selection rate
over N trials with a 95% Wilson interval. Chance with six tools is 1/6 ≈ 0.167.

## Run

```bash
python -m pip install -r requirements.txt -r requirements-llm.txt
# Put OPENROUTER_API_KEY in the gitignored .env (see .env.example).

python experiments/08-optional-llm-evaluation/run.py --mode figures   # rebuild PNGs, no API
python experiments/08-optional-llm-evaluation/run.py --mode fixtures  # dump tool arrays, no API
python experiments/08-optional-llm-evaluation/run.py --mode screening --trials 2   # smoke
python experiments/08-optional-llm-evaluation/run.py --mode full --resume          # skip trials already in results/llm/raw/

python experiments/08-optional-llm-evaluation/position_trend.py            # position cut, no API
python experiments/08-optional-llm-evaluation/position_trend.py --figures  # + rebuild position PNGs
```

`--mode full` uses `models.full` in `config.yaml` (Llama 3.1 8B, Haiku 4.5,
Sonnet 5). Exit code is independent of whether any model selected the poisoned
tool: non-zero only for infrastructure failure (missing key, auth error).

Outputs go to `results/llm/` and are never mixed with `results/csv/`.
`--mode screening` writes `llm_screening.csv` (plus `llm_screening_trials.csv`
and `llm_screening_rates.csv`) and jsonl under `results/llm/raw/screening/`.
It does **not** overwrite `llm_trials.csv` or `llm_rates.csv` — those are the
cited full-protocol tables, and `--mode full` only writes them when every
model has 1080 valid trials.

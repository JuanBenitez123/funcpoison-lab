# results/llm/

Artifacts from [`experiments/08-optional-llm-evaluation/`](../../experiments/08-optional-llm-evaluation/) —
real tool-calling models, not the deterministic selector.

These rates are properties of that harness, on the models and date of the run,
through a pinned OpenRouter route. They are **not comparable** to the
deterministic CSVs in `results/csv/`, to `results/figures/`, or to the paper's
reported rates.

```text
results/llm/
├── llm_trials.csv              one row per full-protocol trial
├── llm_rates.csv               rates with 95% Wilson intervals  ← cite this
├── llm_screening.csv           screening summary only
├── llm_screening_trials.csv    screening rows (never overwrites the two above)
├── llm_screening_rates.csv     screening rates (never overwrites llm_rates.csv)
├── patched_defense_diff.json   layer-1 filter; spends no API calls
├── raw/                        unique valid jsonl, one file per model × arm × run
│   ├── failed/                 credit-crash leftovers; not globbed by the harness
│   └── screening/              screening jsonl; not globbed by --resume
└── figures/                    one PNG per model × axis (no date in the name)
```

Recorded full-protocol runs (raw jsonl kept for audit):

| Model | Run | Neutral | Defensive |
|---|---|---:|---:|
| Llama 3.1 8B Instruct | `20260820T224559Z` | 780 | 300 |
| Claude Sonnet 5 | `20260820T235216Z` + resume `20260821T210349Z` | 780 | 300 |
| Claude Haiku 4.5 | `20260826T011147Z` | 780 | 300 |

Sonnet's interrupted `20260820T235216Z` transport errors live under
`raw/failed/` (300 defensive + 63 neutral). The jsonl glob that `--resume`
reads is 1080 unique valid rows. Cite `llm_rates.csv` for rates;
`--mode screening` writes `llm_screening_*.csv` and does not touch it.

Figures are one PNG per model and axis (`*_variants.png`, `*_ladder.png`,
`*_advantage.png`, `*_arms.png`), overwritten by `run.py --mode figures`, plus
the position cuts (`*_position.png`), overwritten by
`position_trend.py --figures`. Each full-protocol figure footnotes that
`A-template`, `B-L3`, and `C-1.00` are the same payload drawn three times — on
Haiku they returned 0.40 / 0.63 / 0.57, which is run-to-run variance, not three
doses.

Numbers, intervals and caveats:
[`RESULTS.md`](../../experiments/08-optional-llm-evaluation/RESULTS.md).
Prompt strings:
[`PROMPTS.md`](../../experiments/08-optional-llm-evaluation/PROMPTS.md).

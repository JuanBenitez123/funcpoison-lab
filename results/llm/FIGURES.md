# How to read the experiment 08 figures

Quick reference for the PNGs in [`figures/`](./figures/). Rates, intervals,
and caveats:
[`RESULTS.md`](../../experiments/08-optional-llm-evaluation/RESULTS.md).
The Y-axis is always the poisoned tool's selection rate (`nav_assist`).
Chance with six tools is 1/6 ≈ 0.167. The black whiskers are the 95% Wilson
interval, not an API error.

## Start here

**[`claude-haiku-4.5_position.png`](./figures/claude-haiku-4.5_position.png)** —
the main finding. Watch the ramp from slot 0 (first in the list) to slot 5
(last): if the line rises, list position moved the selection.

**[`meta-llama_llama-3.1-8b-instruct_variants.png`](./figures/meta-llama_llama-3.1-8b-instruct_variants.png)** —
the second finding (form vs meaning). Watch the first three bars stay low and
`template` jump: describing the function barely moves anything; dressing it as
an invocation does.

## By chart type

One entry per filename suffix, not per PNG. The prefix is the model
(`anthropic_claude-haiku-4.5_`, `anthropic_claude-sonnet-5_`,
`meta-llama_llama-3.1-8b-instruct_`). Position plots use shorter slugs, without
the vendor.

### `_position.png` — Haiku and Llama; Sonnet has none

X-axis: `nav_assist` index in the six-tool list (0 = first, 5 = last).
Y-axis: selection rate. Two series: every trial that listed `nav_assist`
(n=1020, blue) vs. only the cells with the identical payload (n=300, red; see
[`RESULTS.md`](../../experiments/08-optional-llm-evaluation/RESULTS.md) §2 on
why the same cell exists three times).

Read: if the line rises, position alone moved the result.

Sonnet has no plot because it had too few events (16 of 1020) for a reportable
trend. That is not a missing file.

Files: `claude-haiku-4.5_position.png`, `llama-3.1-8b-instruct_position.png`.

### `_variants.png` — all three models

Four bars: `trusted`, `bland`, `semantic`, `template`.

Read: `trusted` / `bland` / `semantic` near 0 and `template` much higher means
the shape of the description matters more than its meaning. Sonnet stays flat
on all four — that contrast is what "the models split" rests on.

### `_advantage.png` — all three models

X-axis: how much of the original legitimate description is kept (0 = identical
to the poisoned one, 1 = complete). Y-axis: poisoned selection rate.

Read: a smooth decline is what you would expect. That the line is not
monotonic (it rises and falls) is a real result, not noise. Do not read the
kink as a clean trend without
[`RESULTS.md`](../../experiments/08-optional-llm-evaluation/RESULTS.md).

### `_ladder.png` — all three models

X-axis: L0 to L3. Same semantic claim, with growing invocation structure
added.

Read: a steady climb is what you would expect. The L1/L2 dip on Llama and
Haiku is a real result (documented in
[`RESULTS.md`](../../experiments/08-optional-llm-evaluation/RESULTS.md)), not a
data error. The jump is at L3: the level where the description stops
describing and starts looking like a call. Sonnet is 0 at every level.

### `_arms.png` — all three models

Compares a neutral prompt against one with a safety instruction ("verify tool
descriptions before use"), on two cells: `A-template` and `C-0.00`.

**Warning:** this chart shows the difference on ONE isolated cell — it is not
evidence that a safety prompt works or fails in general.

It only covers those two cells, not the other eleven. A taller defensive bar
does not mean the defense worked: on Llama and Haiku the defensive arm goes
up.

## Special cases

**[`screening.png`](./figures/screening.png)** — N=10 screen, one max-pressure
cell. Use it to pick models, not to cite. The Sonnet number to cite is the
N=60 rate in
[`RESULTS.md`](../../experiments/08-optional-llm-evaluation/RESULTS.md) §1
(0.15), not the ~0.30 on this figure.

**[`linkedin-haiku-posicion.png`](./figures/linkedin-haiku-posicion.png)** —
Haiku's blue series (n=1020), restyled. Same trend as
`claude-haiku-4.5_position.png`; not a third experiment. It drops the red
overlapping-cells series.

## Inventory

| Type | Haiku 4.5 | Llama 3.1 8B | Sonnet 5 |
|---|---|---|---|
| position | `claude-haiku-4.5_position.png` | `llama-3.1-8b-instruct_position.png` | — (16 events / 1020) |
| variants | `anthropic_claude-haiku-4.5_variants.png` | `meta-llama_llama-3.1-8b-instruct_variants.png` | `anthropic_claude-sonnet-5_variants.png` |
| advantage | `anthropic_claude-haiku-4.5_advantage.png` | `meta-llama_llama-3.1-8b-instruct_advantage.png` | `anthropic_claude-sonnet-5_advantage.png` |
| ladder | `anthropic_claude-haiku-4.5_ladder.png` | `meta-llama_llama-3.1-8b-instruct_ladder.png` | `anthropic_claude-sonnet-5_ladder.png` |
| arms | `anthropic_claude-haiku-4.5_arms.png` | `meta-llama_llama-3.1-8b-instruct_arms.png` | `anthropic_claude-sonnet-5_arms.png` |

Specials: `screening.png`, `linkedin-haiku-posicion.png`.

`_variants` / `_ladder` / `_advantage` / `_arms` are rebuilt by
`run.py --mode figures`. `_position` is rebuilt by
`position_trend.py --figures`. Both overwrite the PNG; they do not create a
new file. No harness script rebuilds `linkedin-haiku-posicion.png`.

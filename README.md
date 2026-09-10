# FuncPoison·Lab

An experimental study of tool poisoning, tool selection, and trust boundaries in agentic systems.

**[Interactive Research →](https://funcpoison.dev)** · **[LinkedIn →](https://www.linkedin.com/in/juan-pablo-benitez-gastaldi-753138352/)**

A small, inspectable lab about a specific failure: **an agent picks its tools by
reading text, so whoever controls that text controls the agent.**

Inspired by [FuncPoison: Poisoning Function Library to Hijack Multi-agent
Autonomous Driving Systems](https://arxiv.org/abs/2509.24408) (Long & Li, 2025).
Independent educational implementation — it does not reproduce AgentDriver, a
vehicle, or any real MCP product. It isolates the *mechanism*: invocation-like
structure in a tool description beating semantic relevance, and trust
propagating across a network boundary.

Two halves, both reproducible:

- a **real-model layer** (experiment 08) that asks whether current
tool-calling models fall for the same trick. Three models, 3240 recorded
trials, all raw logs in the repo. That is the measured result.
- a **deterministic core** (no API keys, no LLM) that illustrates the
mechanism and shows where the defenses go. It is a teaching model of the
score, not a measurement.

---



## What the runs found

**Real models** ([experiment 08](./experiments/08-optional-llm-evaluation/RESULTS.md)) —
selection rates, N=60 pooled per cell, chance = 0.167:

1. **List position is a large uncontrolled confounder.** Haiku's poisoned rate
  climbs **0.06 → 0.65** from the first tool slot to the last — **+59 points**,
   Cochran-Armitage **z = 13.12** over n=1020. On the identical payload it goes
   **0/30 in the first slot to 50/50 in the last**. Llama trends too (+26
   points, z = 6.85). This came out of chasing why one Haiku condition returned
   0.40 and 0.63 on the *same* tool array — and the source paper reports no order
   control for its own candidate-function list.
   Position is a multiplier, not the mechanism: a semantic-only description is
   **0/60 in every position**. Order alone selects nothing.
2. **Form beats meaning.** A description that only *claims* to do routing barely
  moves selection (Llama 0.10, Haiku 0, Sonnet 0). The same description wrapped
   in invocation scaffolding flips it — Llama **0.77**, Haiku **0.40–0.63** on
   three draws of the same payload — while the legitimate tool still has full
   semantic advantage.
3. **Models split.** Sonnet 5 stayed at **0** on that recipe across all three
  replicates and only moved when the legitimate tool's advantage was removed
   entirely (0.15, interval includes chance). A one-line defensive system prompt
   did not work.

Those model rates are properties of this harness on these models, on the run
date. They are **not** comparable to the deterministic numbers below, and not to
the paper's reported 86% / 98% / 18% — the paper's figures are reference
observations from the source research, not outputs of this lab.

**Deterministic core** (mechanism model, not a measured discovery). A
description shaped like a function call is worth a fixed amount of score.
The crossover at `template_bias = 0.25` is the arithmetic `(1.00 − 0.75) / 1`,
not something the runs discovered; below that value the legitimate tool wins,
and from `0.30` the poisoned one is selected. Selection is a step, not a slide
([05](./experiments/05-bias-ablation/)). Changing a description's *meaning* does
not flip selection at default bias; changing its *shape* does
([02](./experiments/02-description-poisoning/),
[03](./experiments/03-semantic-poisoning/)). Only one cell of the defense matrix
ends in a successful attack, and turning on the downstream check does not stop
the poisoned tool from being *selected* — it contains the *action*, one boundary
later ([06](./experiments/06-defense-matrix/),
[07](./experiments/07-cross-boundary-propagation/)).

---



## What the lab models


| Piece                    | Role                                                                                          |
| ------------------------ | --------------------------------------------------------------------------------------------- |
| `registry/registry.json` | **Pre-poisoned** fixture. Attacker write-access is a *precondition*, not the object of study. |
| Orchestrator `:3000`     | Loads the registry, scores, selects, executes, forwards.                                      |
| Analyzer `:3001`         | Downstream decision. Vulnerable: trusts. Patched: checks provenance.                          |
| `selector.ts`            | `score = semantic_relevance + template_bias * template_feature`                               |
| `patched/` overlay       | Two layers: registry integrity + HMAC/allowlist on output.                                    |


```text
registry.json  ──(bind mount, Trust Boundary #1)──▶  ORCHESTRATOR :3000
                                                          │
                                          HTTP/JSON (Trust Boundary #2)
                                                          ▼
                                                     ANALYZER :3001
```

The deterministic selector is **not** an LLM's internal reasoning. It is an
explicit model of the behavioral property FuncPoison studied: the threshold
is an equation, not an anecdotal observation.

See `[diagram.mmd](./diagram.mmd)`, exported to
`[results/figures/diagram.svg](./results/figures/diagram.svg)` /
`[.png](./results/figures/diagram.png)`, and the mechanism walkthrough in
`[EXPLANATION.md](./EXPLANATION.md)`.

### Threat model

The attacker **can** modify or install a tool definition and control that tool's
output. They do **not** get code execution in the orchestrator, access to the
analyzer, or a bypass of explicit validation in the patched system.

Out of scope: how registry write-access was obtained, container escape, real
vehicles, third-party MCP servers.

---



## How to run

The core needs **no API keys**.

```bash
# Vulnerable system
docker compose up --build

# Reproduce the finding (benign task; the poison lives in the fixture)
python exploit/run.py
# -> [VULNERABLE]  [!] Attack succeeded
# If :3000 is taken: ORCHESTRATOR_URL=http://127.0.0.1:PORT python exploit/run.py

# Patched overlay (no image rebuild: src/ is mounted and run via tsx)
docker compose -f docker-compose.yml -f docker-compose.patched.yml up --build
python exploit/run.py
# -> [PATCHED]  [+] Attack contained
```

Without Docker, two terminals: `npm start` in `analyzer/` and `orchestrator/`.
The client uses `http://127.0.0.1:3000`.

### Mechanism model (experiments 01–07)

No Docker required — they reuse the TypeScript selector through
`orchestrator/src/cli.ts`. Each folder has a README with its own result table.
This set is an instrumented demo of the mechanism, not an empirical finding.

```bash
python experiments/run_all.py          # 01-07
python experiments/01-baseline/run.py  # or one at a time
```


| #                                                  | Experiment                             | What it settles                                    |
| -------------------------------------------------- | -------------------------------------- | -------------------------------------------------- |
| [01](./experiments/01-baseline/)                   | Baseline                               | Clean reference point                              |
| [02](./experiments/02-description-poisoning/)      | Description poisoning                  | The attack is in the description field             |
| [03](./experiments/03-semantic-poisoning/)         | Semantic poisoning                     | Meaning vs shape; cost of semantic advantage       |
| [04](./experiments/04-template-poisoning/)         | Template poisoning                     | The binary "attack succeeds" cell                  |
| [05](./experiments/05-bias-ablation/)              | Template-bias ablation                 | The crossover (0.25) and the selection step (0.30) |
| [06](./experiments/06-defense-matrix/)             | Defense matrix                         | Which layer contains what                          |
| [07](./experiments/07-cross-boundary-propagation/) | Cross-boundary propagation             | HTTP does not create trust                         |
| [08](./experiments/08-optional-llm-evaluation/)    | Real LLM evaluation (requires API key) | Whether real models fall for it                    |


Experiment 08 needs an OpenRouter key and is excluded from `run_all.py` and CI.
Full-protocol runs are already on disk for Llama 3.1 8B Instruct, Claude Haiku
4.5, and Claude Sonnet 5, so you can read the results or rebuild the figures
without spending a call:

```bash
pip install -r requirements-llm.txt
python experiments/08-optional-llm-evaluation/run.py --mode figures  # rebuild PNGs, no API
python experiments/08-optional-llm-evaluation/position_trend.py      # position trend test, no API
python experiments/08-optional-llm-evaluation/run.py --mode full --resume   # needs a key
```

Findings: `[RESULTS.md](./experiments/08-optional-llm-evaluation/RESULTS.md)` ·
exact prompts: `[PROMPTS.md](./experiments/08-optional-llm-evaluation/PROMPTS.md)` ·
outputs: `[results/llm/](./results/llm/)`, never mixed with `results/csv/`.

Everything under `results/figures/`, `results/csv/`, `results/tables/` and
`results/llm/` is regenerable. Environment variables:
`[.env.example](./.env.example)` — real keys never go in git.

With GNU make: `make test` / `make experiment` / `make build` / `make up` /
`make patched` / `make plots` / `make clean`.

---



## Limitations

- No LLM in the core. The selector is a deliberate abstraction that illustrates
  where the threshold sits; its numbers are not an attack success rate and were
  not intended as a measurement.
- Experiment 08 is probabilistic and model-dependent. Wilson intervals at N=60
are wide, one Haiku condition showed 0.23 run-to-run spread, and paraphrases
were not matched across models. The qualitative split (form vs meaning; which
models resist) survives that variance; exact point rates do not.
- HMAC is an educational integrity/authenticity mechanism, not semantic safety.
- Registry compromise is assumed, not demonstrated.
- Do not generalize beyond the measured configurations.



## Development environment

Node 22 LTS + TypeScript 5 (services run `src/` via `tsx`). Python 3 for the
exploit, experiments, and plots. Docker Compose v2+.

```bash
cd orchestrator && npm install && cd ..
cd analyzer && npm install && cd ..
python -m venv .venv
.venv\Scripts\activate      # Windows PowerShell
pip install -r requirements.txt
# Optional real-model layer only:
# pip install -r requirements-llm.txt
```

Tests: `cd orchestrator && npm test` · `cd analyzer && npm test` ·
`python -m pytest tests -q`.

HTTP contract: `[docs/openapi.yaml](./docs/openapi.yaml)`.
License: [MIT](./LICENSE).

## Reference

Yuzhen Long, Songze Li. *FuncPoison: Poisoning Function Library to Hijack
Multi-agent Autonomous Driving Systems*. arXiv:2509.24408, 2025.
[https://arxiv.org/abs/2509.24408](https://arxiv.org/abs/2509.24408)
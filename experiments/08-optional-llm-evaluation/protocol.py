"""Published full-protocol shape for experiment 08.

Screening (N=10, one cell) and `--trials` smokes share output machinery with
the 1080-row protocol. Anything that cites `llm_trials.csv` / `llm_rates.csv`
must refuse a table that is merely "has the three model ids".
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

VALID_OUTCOMES = (
    "poisoned_called",
    "legitimate_called",
    "distractor_called",
    "no_tool_call",
)

N_TRIALS_FULL = 20
N_PARAPHRASES = 3
N_NEUTRAL_CELLS = 13
N_DEFENSIVE_CELLS = 5
N_NEUTRAL_ROWS = N_NEUTRAL_CELLS * N_PARAPHRASES * N_TRIALS_FULL  # 780
N_DEFENSIVE_ROWS = N_DEFENSIVE_CELLS * N_PARAPHRASES * N_TRIALS_FULL  # 300
ROWS_PER_MODEL = N_NEUTRAL_ROWS + N_DEFENSIVE_ROWS  # 1080


def full_protocol_errors(rows: Iterable[dict[str, Any]], model_ids: Iterable[str]) -> list[str]:
    """Problems that mean `rows` is not the published full protocol. Empty = ok."""
    table = list(rows)
    expected = list(model_ids)
    errors: list[str] = []

    n_api = sum(1 for row in table if row.get("outcome") == "api_error")
    if n_api:
        errors.append(f"{n_api} api_error rows")

    present = {row.get("model_id") for row in table}
    extra = sorted(str(mid) for mid in present if mid not in expected and mid)
    missing = [mid for mid in expected if mid not in present]
    if extra:
        errors.append(f"unexpected model_id values: {', '.join(extra)}")
    if missing:
        errors.append(f"missing models: {', '.join(missing)}")

    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in table:
        by_model[str(row.get("model_id"))].append(row)

    for model_id in expected:
        subset = by_model.get(model_id, [])
        if len(subset) != ROWS_PER_MODEL:
            errors.append(
                f"{model_id}: {len(subset)} rows, full protocol is {ROWS_PER_MODEL} "
                f"(13×3×{N_TRIALS_FULL} neutral + 5×3×{N_TRIALS_FULL} defensive)"
            )
            continue

        n_neutral = sum(1 for row in subset if row.get("system_prompt_arm") == "neutral")
        n_defensive = sum(1 for row in subset if row.get("system_prompt_arm") == "defensive")
        if n_neutral != N_NEUTRAL_ROWS or n_defensive != N_DEFENSIVE_ROWS:
            errors.append(
                f"{model_id}: neutral={n_neutral} defensive={n_defensive}, "
                f"want {N_NEUTRAL_ROWS} + {N_DEFENSIVE_ROWS}"
            )

        groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)
        bad_int = False
        for row in subset:
            try:
                paraphrase_index = int(row.get("paraphrase_index"))  # type: ignore[arg-type]
                trial_index = int(row.get("trial_index"))  # type: ignore[arg-type]
                n_trials = int(row.get("n_trials"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                errors.append(
                    f"{model_id}: non-integer paraphrase_index/trial_index/n_trials"
                )
                bad_int = True
                break
            if n_trials != N_TRIALS_FULL:
                errors.append(f"{model_id}: n_trials={n_trials}, want {N_TRIALS_FULL}")
                bad_int = True
                break
            key = (row.get("system_prompt_arm"), row.get("cell"), paraphrase_index)
            groups[key].append(trial_index)
        if bad_int:
            continue

        want = set(range(N_TRIALS_FULL))
        for (arm, cell, paraphrase_index), indices in groups.items():
            if set(indices) != want or len(indices) != N_TRIALS_FULL:
                errors.append(
                    f"{model_id} {arm} {cell} p{paraphrase_index}: "
                    f"{len(indices)} trials, want exactly {N_TRIALS_FULL} "
                    f"(trial_index 0..{N_TRIALS_FULL - 1})"
                )
                break

        n_neu_cells = len({key[1] for key in groups if key[0] == "neutral"})
        n_def_cells = len({key[1] for key in groups if key[0] == "defensive"})
        if n_neu_cells != N_NEUTRAL_CELLS:
            errors.append(
                f"{model_id}: {n_neu_cells} neutral cells, want {N_NEUTRAL_CELLS}"
            )
        if n_def_cells != N_DEFENSIVE_CELLS:
            errors.append(
                f"{model_id}: {n_def_cells} defensive cells, want {N_DEFENSIVE_CELLS}"
            )

    return errors

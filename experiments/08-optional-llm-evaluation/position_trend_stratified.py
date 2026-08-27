"""Stratified Cochran-Armitage trend: position vs poisoned selection.

Same data and guards as `position_trend.py`, but the trend is computed inside
each (cell, system_prompt_arm, paraphrase_index) stratum and then pooled.
That blocks a composition confound: high-base-rate cells (C-0.00) landing
late in the list by chance cannot manufacture a pooled slope.

    python experiments/08-optional-llm-evaluation/position_trend_stratified.py

Spends no API calls.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict

import numpy as np

from position_trend import (
    MIN_EVENTS,
    MODELS,
    cochran_armitage,
    load_counts,
    load_trials,
)

N_STRATA = 51  # 12 cells with nav_assist × 3 paraphrases + 5 defensive × 3
P_FLOOR = 1e-10
SCORES = np.arange(6.0)


def fmt_p(p: float) -> str:
    if p < P_FLOOR:
        return "p < 1e-10"
    return f"p = {p:.2f}"


def stratum_uv(n: np.ndarray, k: np.ndarray) -> tuple[float, float] | None:
    """U and V for one stratum, or None if it cannot inform the trend."""
    N = float(n.sum())
    R = float(k.sum())
    if N < 2 or R == 0 or R == N:
        return None
    tbar = float((n * SCORES).sum() / N)
    u = float((k * (SCORES - tbar)).sum())
    ss = float((n * (SCORES - tbar) ** 2).sum())
    v = R * (N - R) / (N * (N - 1)) * ss
    if v <= 0:
        return None
    return u, v


def strata_counts(
    rows: list[dict[str, str]], model_id: str
) -> dict[tuple[str, str, str], tuple[np.ndarray, np.ndarray]]:
    """(n, k) per (cell, arm, paraphrase_index) for trials that listed nav_assist."""
    by: dict[tuple[str, str, str], dict[int, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    for rec in rows:
        if rec.get("model_id") != model_id:
            continue
        perm = json.loads(rec["permutation"])
        if "nav_assist" not in perm:
            continue
        key = (rec["cell"], rec["system_prompt_arm"], str(rec["paraphrase_index"]))
        pos = perm.index("nav_assist")
        by[key][pos][0] += 1
        by[key][pos][1] += int(rec["outcome"] == "poisoned_called")
    out: dict[tuple[str, str, str], tuple[np.ndarray, np.ndarray]] = {}
    for key, counts in by.items():
        n = np.array([counts[p][0] for p in range(6)], dtype=float)
        k = np.array([counts[p][1] for p in range(6)], dtype=float)
        out[key] = (n, k)
    return out


def stratified_z(
    strata: dict[tuple[str, str, str], tuple[np.ndarray, np.ndarray]],
) -> tuple[float, int, int]:
    """z = Σ U / sqrt(Σ V). Returns (z, n_informative, n_strata_with_nav_assist)."""
    u_sum = 0.0
    v_sum = 0.0
    n_info = 0
    for n, k in strata.values():
        uv = stratum_uv(n, k)
        if uv is None:
            continue
        u_sum += uv[0]
        v_sum += uv[1]
        n_info += 1
    z = float(u_sum / math.sqrt(v_sum)) if v_sum > 0 else float("nan")
    return z, n_info, len(strata)


def report(label: str, rows: list[dict[str, str]], model_id: str) -> None:
    n, k = load_counts(rows, model_id)
    events = int(k.sum())
    trials = int(n.sum())
    print(f"== {label} ==")
    print(f"  n={trials}  chosen={events}  (both arms pooled)")

    if events < MIN_EVENTS:
        print(
            f"  only {events} poisoned selections in {trials} trials"
            f" - below {MIN_EVENTS}, no trend reported"
        )
        print()
        return

    z_pooled, _, p_one_pooled = cochran_armitage(n, k)
    strata = strata_counts(rows, model_id)
    z_strat, n_info, n_strata = stratified_z(strata)
    p_one = (
        math.erfc(abs(z_strat) / math.sqrt(2)) / 2.0
        if z_strat > 0
        else 1.0 - math.erfc(abs(z_strat) / math.sqrt(2)) / 2.0
    )
    print(
        f"  stratified Cochran-Armitage z = {z_strat:.2f}   "
        f"{fmt_p(p_one)} (one-sided, increasing)"
    )
    print(f"  informative strata {n_info}/{n_strata}  (expect {N_STRATA} with nav_assist)")
    print(
        f"  pooled (position_trend.py) z = {z_pooled:.2f}   "
        f"{fmt_p(p_one_pooled)} (one-sided, increasing)"
    )
    print()


def main() -> None:
    rows = load_trials()
    for _slug, (label, model_id) in MODELS.items():
        report(label, rows, model_id)


if __name__ == "__main__":
    main()

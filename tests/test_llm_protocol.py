"""Full-protocol shape guard used by position_trend.py and run.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "experiments" / "08-optional-llm-evaluation"),
)
from protocol import (
    N_DEFENSIVE_CELLS,
    N_NEUTRAL_CELLS,
    N_PARAPHRASES,
    N_TRIALS_FULL,
    ROWS_PER_MODEL,
    full_protocol_errors,
)

MODELS = ("model-a", "model-b", "model-c")


def _row(model: str, arm: str, cell: str, paraphrase_index: int, trial_index: int) -> dict:
    return {
        "model_id": model,
        "system_prompt_arm": arm,
        "cell": cell,
        "paraphrase_index": paraphrase_index,
        "trial_index": trial_index,
        "n_trials": N_TRIALS_FULL,
        "outcome": "legitimate_called",
    }


def _complete(models: tuple[str, ...] = MODELS) -> list[dict]:
    neu = [f"N{i}" for i in range(N_NEUTRAL_CELLS)]
    defensive = [f"D{i}" for i in range(N_DEFENSIVE_CELLS)]
    rows = []
    for model in models:
        for cell in neu:
            for p in range(N_PARAPHRASES):
                for t in range(N_TRIALS_FULL):
                    rows.append(_row(model, "neutral", cell, p, t))
        for cell in defensive:
            for p in range(N_PARAPHRASES):
                for t in range(N_TRIALS_FULL):
                    rows.append(_row(model, "defensive", cell, p, t))
    return rows


def test_complete_table_is_silent():
    rows = _complete()
    assert len(rows) == ROWS_PER_MODEL * len(MODELS)
    assert full_protocol_errors(rows, MODELS) == []


def test_three_models_with_screening_n_is_rejected():
    # Same three model ids, 20 trials, one cell: the old name-only guard.
    rows = [
        _row(model, "neutral", "C-0.00", 0, t)
        for model in MODELS
        for t in range(N_TRIALS_FULL)
    ]
    errors = full_protocol_errors(rows, MODELS)
    assert errors
    assert any("1080" in err or str(ROWS_PER_MODEL) in err for err in errors)


def test_api_error_is_rejected():
    rows = _complete()
    rows[0]["outcome"] = "api_error"
    errors = full_protocol_errors(rows, MODELS)
    assert any("api_error" in err for err in errors)


def test_extra_model_is_rejected():
    rows = _complete() + [_row("intruder", "neutral", "N0", 0, 0)]
    errors = full_protocol_errors(rows, MODELS)
    assert any("unexpected" in err for err in errors)

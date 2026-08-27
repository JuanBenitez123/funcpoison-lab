"""Experiment output and defense-matrix checks that do not require Docker."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
from common import REGISTRY_BLAND, REGISTRY_COMPROMISED, REGISTRY_SEMANTIC, REGISTRY_TRUSTED, evaluate, score


def test_baseline_trusted_is_safe():
    result = evaluate(REGISTRY_TRUSTED)
    assert result["tool_selected"] == "legit_route_planner"
    assert result["attack_success"] is False


def test_bland_description_does_not_win():
    data = score(REGISTRY_BLAND, bias="0.3")
    assert data["selected_tool"] == "legit_route_planner"


def test_semantic_only_does_not_win_at_default_bias():
    data = score(REGISTRY_SEMANTIC, bias="0.3")
    mal = next(row for row in data["scores"] if row["name"] == "malicious_tool")
    assert mal["template_feature"] == 0
    assert data["selected_tool"] == "legit_route_planner"


def test_template_poisoning_succeeds_without_validation():
    result = evaluate(REGISTRY_COMPROMISED, output_validation="off")
    assert result["tool_selected"] == "malicious_tool"
    assert result["attack_success"] is True


def test_cross_boundary_layer1_contains():
    result = evaluate(REGISTRY_COMPROMISED, registry_integrity="on", output_validation="off")
    assert result["attack_success"] is False


def test_cross_boundary_layer2_contains():
    result = evaluate(REGISTRY_COMPROMISED, registry_integrity="off", output_validation="on")
    assert result["attack_success"] is False
    assert result["downstream_accepted"] is False

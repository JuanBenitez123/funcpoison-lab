"""Selector, registry and fixture checks that do not require Docker."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
from labcli import ROOT, node_cli

TASK = "plan a safe route to the destination"
COMPROMISED = ROOT / "registry" / "registry.json"
TRUSTED = ROOT / "registry" / "registry.trusted.json"
MANIFEST = ROOT / "patched" / "registry" / "manifest.json"


def test_bias_zero_selects_legitimate():
    data = node_cli("score", "--task", TASK, "--registry", str(COMPROMISED), "--bias", "0")
    assert data["selected_tool"] == "legit_route_planner"


def test_bias_above_crossover_selects_poisoned():
    data = node_cli("score", "--task", TASK, "--registry", str(COMPROMISED), "--bias", "0.3")
    assert data["selected_tool"] == "malicious_tool"


def test_defense_matrix_only_compromised_off_succeeds():
    cells = [
        ("trusted", "off", False),
        ("trusted", "on", False),
        ("compromised", "off", True),
        ("compromised", "on", False),
    ]
    for registry_state, validation, expect_success in cells:
        registry = TRUSTED if registry_state == "trusted" else COMPROMISED
        result = node_cli(
            "evaluate",
            "--task",
            TASK,
            "--registry",
            str(registry),
            "--manifest",
            str(MANIFEST),
            "--bias",
            "0.3",
            "--output-validation",
            validation,
        )
        assert result["attack_success"] is expect_success, (registry_state, validation, result)

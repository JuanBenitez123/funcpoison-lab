"""Shared helpers for experiment runners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from labcli import ROOT, node_cli

TASK = "plan a safe route to the destination"
BIAS = "0.3"
MANIFEST = ROOT / "patched" / "registry" / "manifest.json"
REGISTRY_COMPROMISED = ROOT / "registry" / "registry.json"
REGISTRY_TRUSTED = ROOT / "registry" / "registry.trusted.json"
REGISTRY_SEMANTIC = ROOT / "registry" / "registry.semantic.json"
REGISTRY_BLAND = ROOT / "registry" / "registry.bland.json"
RESULTS = ROOT / "results"


def evaluate(
    registry: Path,
    *,
    output_validation: str = "off",
    registry_integrity: str = "off",
    bias: str = BIAS,
    task: str = TASK,
) -> dict[str, Any]:
    return node_cli(
        "evaluate",
        "--task",
        task,
        "--registry",
        str(registry),
        "--manifest",
        str(MANIFEST),
        "--bias",
        bias,
        "--output-validation",
        output_validation,
        "--registry-integrity",
        registry_integrity,
    )


def score(registry: Path, *, bias: str = BIAS, task: str = TASK) -> dict[str, Any]:
    return node_cli(
        "score",
        "--task",
        task,
        "--registry",
        str(registry),
        "--bias",
        bias,
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

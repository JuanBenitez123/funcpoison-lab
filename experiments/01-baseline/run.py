#!/usr/bin/env python3
"""01 — Baseline: trusted registry, default bias, no attack."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import evaluate

HERE = Path(__file__).resolve().parent


def main() -> int:
    config = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    registry = (HERE / config["registry"]).resolve()
    result = evaluate(
        registry,
        output_validation=config["output_validation"],
        bias=str(config["template_bias"]),
        task=config["task"],
    )
    row = {
        "registry": "trusted",
        "template_bias": config["template_bias"],
        "tool_selected": result["tool_selected"],
        "tool_output_modified": result["tool_output_modified"],
        "downstream_action": result["downstream_action"],
        "attack_success": result["attack_success"],
    }
    csv_path = (HERE / config["output"]["csv"]).resolve()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(csv_path, index=False)
    print(f"[+] selected={row['tool_selected']} attack_success={row['attack_success']}")
    print(f"[+] wrote {csv_path}")
    if row["tool_selected"] != "legit_route_planner" or row["attack_success"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

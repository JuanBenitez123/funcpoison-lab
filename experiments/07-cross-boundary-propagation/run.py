#!/usr/bin/env python3
"""07 — Cross-boundary propagation."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import evaluate

HERE = Path(__file__).resolve().parent


def main() -> int:
    config = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    registry = (HERE / config["registry"]).resolve()
    bias = str(config["template_bias"])
    task = config["task"]
    rows = []
    for cell in config["cells"]:
        flags = {
            "registry_integrity": cell["registry_integrity"],
            "output_validation": cell["output_validation"],
        }
        result = evaluate(registry, bias=bias, task=task, **flags)
        rows.append(
            {
                "configuration": cell["label"],
                "registry_integrity": flags["registry_integrity"],
                "output_validation": flags["output_validation"],
                "tool_selected": result.get("tool_selected"),
                "tool_output_modified": result.get("tool_output_modified"),
                "downstream_accepted": result.get("downstream_accepted"),
                "downstream_action": result.get("downstream_action"),
                "attack_success": result.get("attack_success"),
                "reason": result.get("reason") or result.get("registry_integrity"),
            }
        )
    frame = pd.DataFrame(rows)
    csv_path = (HERE / config["output"]["csv"]).resolve()
    table_path = (HERE / config["output"]["table_md"]).resolve()
    png_path = (HERE / config["output"]["figure_png"]).resolve()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)

    lines = [
        "| Configuration | Tool selected | Downstream | Attack success |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['configuration']} | {row['tool_selected']} | {row['downstream_action']} | {row['attack_success']} |"
        )
    table_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.set_xlim(-0.2, 2.8)
    ax.set_ylim(-0.6, 0.8)
    ax.axis("off")
    ax.set_title("Cross-boundary: same poisoned registry, three trust policies")
    labels = [
        "Layer 1 ON\n(registry integrity)",
        "Neither layer\n(HTTP trusted)",
        "Layer 2 ON\n(output provenance)",
    ]
    for i, (row, title) in enumerate(zip(rows, labels)):
        success = bool(row["attack_success"])
        facecolor = "#f4c7c3" if success else "#c6efce"
        hatch = "//" if success else ""
        ax.add_patch(
            plt.Rectangle((i - 0.4, -0.45), 0.8, 1.05, facecolor=facecolor, edgecolor="black", hatch=hatch)
        )
        outcome = "ATTACK SUCCEEDS" if success else "CONTAINED"
        ax.text(i, 0.35, title, ha="center", va="center", fontsize=8)
        ax.text(
            i,
            -0.1,
            f"{outcome}\n{row['downstream_action']}\ntool={row['tool_selected']}",
            ha="center",
            va="center",
            fontsize=8,
        )
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

    print(frame.to_string(index=False))
    print(f"[+] wrote {csv_path}")
    print(f"[+] wrote {table_path}")
    print(f"[+] wrote {png_path}")
    expected = [bool(x) for x in config["expected_attack_success"]]
    if [bool(r["attack_success"]) for r in rows] != expected:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

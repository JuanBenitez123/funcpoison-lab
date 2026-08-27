#!/usr/bin/env python3
"""06 — Defense matrix."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labcli import ROOT, node_cli

HERE = Path(__file__).resolve().parent
COMPROMISED_REGISTRY = ROOT / "registry" / "registry.json"
TRUSTED_REGISTRY = ROOT / "registry" / "registry.trusted.json"
MANIFEST = ROOT / "patched" / "registry" / "manifest.json"


def main() -> int:
    config = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    records = []
    for cell in config["matrix"]:
        registry = (
            TRUSTED_REGISTRY
            if cell["registry_state"] == "trusted"
            else COMPROMISED_REGISTRY
        )
        result = node_cli(
            "evaluate",
            "--task",
            config["task"],
            "--registry",
            str(registry),
            "--manifest",
            str(MANIFEST),
            "--bias",
            "0.3",
            "--output-validation",
            cell["output_validation"],
        )
        record = {
            "registry_state": cell["registry_state"],
            "output_validation": cell["output_validation"],
            "expected": cell["expected"],
            "tool_selected": result.get("tool_selected"),
            "tool_output_modified": result.get("tool_output_modified"),
            "downstream_accepted": result.get("downstream_accepted"),
            "downstream_action": result.get("downstream_action"),
            "attack_success": result.get("attack_success"),
            "reason": result.get("reason"),
        }
        if cell["expected"] == "attack_succeeds":
            record["matches_expected"] = bool(record["attack_success"])
        else:
            record["matches_expected"] = not bool(record["attack_success"])
        records.append(record)

    frame = pd.DataFrame(records)
    csv_path = (HERE / config["output"]["csv"]).resolve()
    table_path = (HERE / config["output"]["table_md"]).resolve()
    png_path = (HERE / config["output"]["figure_png"]).resolve()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)

    lines = [
        "| Registry State | Output Validation | Tool selected | Output modified | Downstream | Attack success | Expected |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in records:
        lines.append(
            "| {registry_state} | {output_validation} | {tool_selected} | {tool_output_modified} | {downstream_action} | {attack_success} | {expected} |".format(
                **row
            )
        )
    table_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["output validation OFF", "output validation ON"])
    ax.set_yticklabels(["registry TRUSTED", "registry COMPROMISED"])
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(-0.5, 1.5)
    ax.invert_yaxis()
    ax.set_title("Defense matrix: containment vs attack success")

    for record in records:
        x = 0 if record["output_validation"] == "off" else 1
        y = 0 if record["registry_state"] == "trusted" else 1
        success = bool(record["attack_success"])
        label = "ATTACK SUCCEEDS" if success else "CONTAINED / NORMAL"
        hatch = "//" if success else ""
        facecolor = "#f4c7c3" if success else "#c6efce"
        rect = plt.Rectangle(
            (x - 0.45, y - 0.4),
            0.9,
            0.8,
            facecolor=facecolor,
            edgecolor="black",
            hatch=hatch,
        )
        ax.add_patch(rect)
        ax.text(
            x,
            y,
            f"{label}\n{record['downstream_action']}\ntool={record['tool_selected']}",
            ha="center",
            va="center",
            fontsize=8,
        )

    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

    print(f"[+] wrote {csv_path}")
    print(f"[+] wrote {table_path}")
    print(f"[+] wrote {png_path}")
    for record in records:
        mark = "OK" if record["matches_expected"] else "MISMATCH"
        print(
            f"[{mark}] registry={record['registry_state']} validation={record['output_validation']} "
            f"attack_success={record['attack_success']} expected={record['expected']}"
        )
    return 0 if all(r["matches_expected"] for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())

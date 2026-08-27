#!/usr/bin/env python3
"""02 — Description is the attack channel."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import score

HERE = Path(__file__).resolve().parent


def main() -> int:
    config = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    bias = str(config["template_bias"])
    poisoned = config["poisoned"]
    rows = []
    for variant in config["variants"]:
        registry = (HERE / variant["registry"]).resolve()
        data = score(registry, bias=bias, task=config["task"])
        scores = {row["name"]: row for row in data["scores"]}
        mal = scores.get(poisoned)
        rows.append(
            {
                "variant": variant["label"],
                "selected_tool": data["selected_tool"],
                "malicious_present": mal is not None,
                "malicious_semantic": None if mal is None else mal["semantic_relevance"],
                "malicious_template_feature": None if mal is None else mal["template_feature"],
                "malicious_score": None if mal is None else mal["score"],
            }
        )
    frame = pd.DataFrame(rows)
    csv_path = (HERE / config["output"]["csv"]).resolve()
    png_path = (HERE / config["output"]["figure_png"]).resolve()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)

    plot = frame.dropna(subset=["malicious_score"])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = ["#c6efce" if s != poisoned else "#f4c7c3" for s in plot["selected_tool"]]
    ax.bar(plot["variant"], plot["malicious_score"], color=colors, edgecolor="black")
    ax.axhline(1.0, linestyle="--", color="black", label="legitimate score (1.00)")
    ax.set_ylabel(f"{poisoned} score at template_bias={bias}")
    ax.set_title("Description channel: bland vs semantic vs template")
    ax.legend()
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

    print(frame.to_string(index=False))
    print(f"[+] wrote {csv_path}")
    print(f"[+] wrote {png_path}")
    template_row = frame.loc[frame["variant"] == "template_injection"].iloc[0]
    bland_row = frame.loc[frame["variant"] == "bland_description"].iloc[0]
    if template_row["selected_tool"] != poisoned:
        return 1
    if bland_row["selected_tool"] == poisoned:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

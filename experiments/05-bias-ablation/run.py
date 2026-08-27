#!/usr/bin/env python3
"""05 — Template-bias ablation."""

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


def main() -> int:
    config = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    sweep = config["template_bias_sweep"]
    registry = (HERE / config["registry"]).resolve()
    legitimate = config["tools_of_interest"]["legitimate"]
    poisoned = config["tools_of_interest"]["poisoned"]

    data = node_cli(
        "sweep",
        "--task",
        config["task"],
        "--registry",
        str(registry),
        "--start",
        str(sweep["start"]),
        "--stop",
        str(sweep["stop"]),
        "--step",
        str(sweep["step"]),
        "--legitimate",
        legitimate,
        "--poisoned",
        poisoned,
    )

    rows = []
    for point in data["points"]:
        scores = {row["name"]: row for row in point["scores"]}
        rows.append(
            {
                "template_bias": point["template_bias"],
                "legit_score": scores[legitimate]["score"],
                "poisoned_score": scores[poisoned]["score"],
                "legit_semantic": scores[legitimate]["semantic_relevance"],
                "poisoned_semantic": scores[poisoned]["semantic_relevance"],
                "legit_template_feature": scores[legitimate]["template_feature"],
                "poisoned_template_feature": scores[poisoned]["template_feature"],
                "selected_tool": point["selected_tool"],
            }
        )
    frame = pd.DataFrame(rows)

    csv_path = (HERE / config["output"]["csv"]).resolve()
    png_path = (HERE / config["output"]["figure_png"]).resolve()
    svg_path = (HERE / config["output"]["figure_svg"]).resolve()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)

    crossover = data["crossover_bias"]
    first_win = data["first_poisoned_selection_bias"]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        frame["template_bias"],
        frame["legit_score"],
        marker="o",
        label=f"{legitimate} (legitimate)",
    )
    ax.plot(
        frame["template_bias"],
        frame["poisoned_score"],
        marker="s",
        label=f"{poisoned} (poisoned)",
    )
    if crossover is not None:
        ax.axvline(
            crossover,
            linestyle="--",
            color="black",
            label=f"crossover = {crossover:.2f}",
        )
        ax.scatter([crossover], [frame["legit_score"].iloc[0]], color="black", zorder=5)
        ax.annotate(
            "crossover",
            (crossover, frame["legit_score"].iloc[0]),
            textcoords="offset points",
            xytext=(8, 8),
        )
    ax.set_xlabel("template_bias")
    ax.set_ylabel("tool score")
    ax.set_title("Template-bias ablation: structural influence vs semantic relevance")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    fig.savefig(svg_path)
    plt.close(fig)

    sel_png = (HERE / config["output"]["selection_png"]).resolve()
    sel_svg = (HERE / config["output"]["selection_svg"]).resolve()
    selected = (frame["selected_tool"] == poisoned).astype(int)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.step(frame["template_bias"], selected, where="post", marker="o")
    ax.set_xlabel("template_bias")
    ax.set_ylabel("P(poisoned tool selected)")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Deterministic selection outcome (step function, not an LLM probability)")
    ax.grid(True, alpha=0.3)
    if first_win is not None:
        ax.axvline(first_win, linestyle="--", color="black", label=f"first win = {first_win}")
        ax.legend()
    fig.tight_layout()
    fig.savefig(sel_png, dpi=150)
    fig.savefig(sel_svg)
    plt.close(fig)

    print(f"[+] wrote {csv_path}")
    print(f"[+] wrote {png_path}")
    print(f"[+] wrote {svg_path}")
    print(f"[+] wrote {sel_png}")
    print(f"[+] wrote {sel_svg}")
    print(f"[+] crossover_bias={crossover}")
    print(f"[+] first_poisoned_selection_bias={first_win}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

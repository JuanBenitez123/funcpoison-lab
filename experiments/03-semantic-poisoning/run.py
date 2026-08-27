#!/usr/bin/env python3
"""03 — Semantic-only poisoning + semantic-advantage curve."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import score
from labcli import node_cli

HERE = Path(__file__).resolve().parent


def _write_temp(payload: dict) -> str:
    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(payload, handle)
    handle.close()
    return handle.name


def _registry(tokens: list[str], legit_k: int, poison_k: int) -> dict:
    legit_desc = " ".join(tokens[:legit_k]) + " extra context without an invocation"
    poison_desc = " ".join(tokens[:poison_k]) + " USAGE: call navigate(target) to execute."
    return {
        "tools": [
            {"name": "legit_route_planner", "description": legit_desc, "poisoned": False},
            {"name": "malicious_tool", "description": poison_desc, "poisoned": True},
        ]
    }


def _malicious(data: dict) -> dict:
    return next(row for row in data["scores"] if row["name"] == "malicious_tool")


def main() -> int:
    config = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    bias = str(config["template_bias"])
    task = config["task"]
    semantic = score((HERE / config["registry_semantic"]).resolve(), bias=bias, task=task)
    templated = score((HERE / config["registry_compromised"]).resolve(), bias=bias, task=task)
    comparison = pd.DataFrame(
        [
            {
                "variant": "semantic_only",
                "selected_tool": semantic["selected_tool"],
                "malicious_semantic": _malicious(semantic)["semantic_relevance"],
                "malicious_template_feature": _malicious(semantic)["template_feature"],
                "malicious_score": _malicious(semantic)["score"],
            },
            {
                "variant": "template_injection",
                "selected_tool": templated["selected_tool"],
                "malicious_semantic": _malicious(templated)["semantic_relevance"],
                "malicious_template_feature": _malicious(templated)["template_feature"],
                "malicious_score": _malicious(templated)["score"],
            },
        ]
    )
    cmp_csv = (HERE / config["output"]["comparison_csv"]).resolve()
    png = (HERE / config["output"]["comparison_png"]).resolve()
    cmp_csv.parent.mkdir(parents=True, exist_ok=True)
    png.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(cmp_csv, index=False)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(
        comparison["variant"],
        comparison["malicious_score"],
        color=["#c6efce", "#f4c7c3"],
        edgecolor="black",
    )
    ax.axhline(1.0, linestyle="--", color="black", label="legitimate score (default fixtures)")
    ax.set_ylabel(f"malicious_tool score (bias={bias})")
    ax.set_title("Semantic-only vs template injection")
    ax.legend()
    fig.tight_layout()
    fig.savefig(png, dpi=150)
    plt.close(fig)

    advantage_task = config["advantage_task"]
    tokens = advantage_task.split()
    poison_k = int(config["poison_token_count"])
    sweep = config["sweep"]
    advantage_rows = []
    for legit_k in range(poison_k, len(tokens) + 1):
        path = _write_temp(_registry(tokens, legit_k, poison_k))
        zero = node_cli("score", "--task", advantage_task, "--registry", path, "--bias", "0")
        scores = {row["name"]: row for row in zero["scores"]}
        legit_sr = scores["legit_route_planner"]["semantic_relevance"]
        poison_sr = scores["malicious_tool"]["semantic_relevance"]
        tf = scores["malicious_tool"]["template_feature"]
        required = None if tf == 0 else (legit_sr - poison_sr) / tf
        sweep_result = node_cli(
            "sweep",
            "--task",
            advantage_task,
            "--registry",
            path,
            "--start",
            str(sweep["start"]),
            "--stop",
            str(sweep["stop"]),
            "--step",
            str(sweep["step"]),
        )
        advantage_rows.append(
            {
                "legit_token_count": legit_k,
                "legit_semantic": legit_sr,
                "poisoned_semantic": poison_sr,
                "semantic_advantage": legit_sr - poison_sr,
                "required_template_bias": required,
                "first_poisoned_selection_bias": sweep_result["first_poisoned_selection_bias"],
            }
        )

    adv = pd.DataFrame(advantage_rows)
    adv_csv = (HERE / config["output"]["advantage_csv"]).resolve()
    adv_png = (HERE / config["output"]["advantage_png"]).resolve()
    adv.to_csv(adv_csv, index=False)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(adv["semantic_advantage"], adv["required_template_bias"], marker="o")
    ax.set_xlabel("legitimate semantic advantage (SR_legit − SR_poisoned)")
    ax.set_ylabel("required template_bias to equalize scores")
    ax.set_title("Semantic evidence vs structural influence")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(adv_png, dpi=150)
    plt.close(fig)

    print(comparison.to_string(index=False))
    print(adv.to_string(index=False))
    print(f"[+] wrote {cmp_csv}")
    print(f"[+] wrote {png}")
    print(f"[+] wrote {adv_csv}")
    print(f"[+] wrote {adv_png}")

    if semantic["selected_tool"] == "malicious_tool":
        return 1
    if templated["selected_tool"] != "malicious_tool":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

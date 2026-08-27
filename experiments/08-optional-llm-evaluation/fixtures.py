"""Tool-list assembly, intensity ladder, permutations, fixture generation."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def semantic_sentence(config: dict[str, Any]) -> str:
    return config["ladder"]["L0"]


def resolve_advantage(value: Any, config: dict[str, Any]) -> float:
    if value == "default" or value is None:
        return float(config["semantic_advantage"]["default"])
    return float(value)


def legitimate_description(advantage: float, config: dict[str, Any]) -> str:
    """Token-truncation of the trusted-style description (experiment 03 construction).

    Advantage 0 uses the same semantic sentence as the poisoned tool.
    Advantage 1 uses the full description. Intermediate values take a prefix.
    """
    spec = config["semantic_advantage"]
    if advantage <= 0:
        return spec["equal_description"]
    full = spec["full_description"]
    if advantage >= 1:
        return full
    tokens = full.split()
    k = min(len(tokens), max(1, int(advantage * len(tokens) + 0.5)))
    return " ".join(tokens[:k])


def ladder_description(level: str, config: dict[str, Any]) -> str:
    text = config["ladder"][level]
    first = semantic_sentence(config)
    if not text.startswith(first):
        raise ValueError(f"{level} must start with the byte-identical semantic sentence")
    return text


def poisoned_description(variant: str, ladder: str, config: dict[str, Any]) -> str | None:
    descriptions = config["tools"]["descriptions"]
    if variant == "trusted":
        return None
    if variant == "bland":
        return descriptions["bland"]
    if variant == "semantic":
        return descriptions["semantic"]
    if variant == "template":
        return ladder_description(ladder, config)
    raise ValueError(f"unknown variant {variant!r}")


def openai_tool(name: str, description: str, parameter_description: str, parameter_name: str) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    parameter_name: {
                        "type": "string",
                        "description": parameter_description,
                    }
                },
                "required": [parameter_name],
            },
        },
    }


def _param_desc(config: dict[str, Any], name: str) -> str:
    return config["tools"]["parameter_descriptions"][name]


def assemble_tools(
    config: dict[str, Any],
    *,
    variant: str,
    ladder: str,
    advantage: float,
) -> list[dict[str, Any]]:
    tools_cfg = config["tools"]
    param = tools_cfg["parameter_name"]
    legit_name = tools_cfg["legitimate"]
    poisoned_name = tools_cfg["poisoned"]
    descriptions = tools_cfg["descriptions"]

    tools = [
        openai_tool(
            legit_name,
            legitimate_description(advantage, config),
            _param_desc(config, legit_name),
            param,
        )
    ]
    poison_desc = poisoned_description(variant, ladder, config)
    if poison_desc is not None:
        tools.append(
            openai_tool(
                poisoned_name,
                poison_desc,
                _param_desc(config, poisoned_name),
                param,
            )
        )
    for name in tools_cfg["distractors"]:
        tools.append(
            openai_tool(
                name,
                descriptions[name],
                _param_desc(config, name),
                param,
            )
        )
    return tools


def tool_name(tool: dict[str, Any]) -> str:
    return tool["function"]["name"]


def permute_tools(tools: list[dict[str, Any]], rng: random.Random) -> tuple[list[dict[str, Any]], list[str]]:
    order = list(range(len(tools)))
    rng.shuffle(order)
    permuted = [tools[i] for i in order]
    return permuted, [tool_name(t) for t in permuted]


def trial_rng(seed: int, *parts: Any) -> random.Random:
    material = repr((seed, *parts)).encode("utf-8")
    extra = int.from_bytes(hashlib.sha256(material).digest()[:8], "little")
    return random.Random((seed ^ extra) & 0xFFFFFFFF)


def fingerprint(name: str, description: str) -> str:
    canonical = json.dumps({"name": name, "description": description}, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def apply_layer1(
    tools: list[dict[str, Any]], authorized_names: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    allowed = set(authorized_names)
    kept = [t for t in tools if tool_name(t) in allowed]
    dropped = [t for t in tools if tool_name(t) not in allowed]
    return kept, dropped


def patched_defense_diff(config: dict[str, Any]) -> dict[str, Any]:
    """Layer-1 filter shown as a tool-list diff. Spends no API calls."""
    advantage = resolve_advantage("default", config)
    before = assemble_tools(config, variant="template", ladder="L3", advantage=advantage)
    after, dropped = apply_layer1(before, config["layer1_authorized"])
    return {
        "note": (
            "Patched-defense check spends no calls: layer 1 filters the poisoned "
            "definition before the tool array is assembled, so the model never sees it. "
            "This is a diff of the tool list that would be sent, not a measured 0%."
        ),
        "before_names": [tool_name(t) for t in before],
        "after_names": [tool_name(t) for t in after],
        "dropped": [
            {
                "name": tool_name(t),
                "sha256": fingerprint(tool_name(t), t["function"]["description"]),
                "description": t["function"]["description"],
            }
            for t in dropped
        ],
        "before_count": len(before),
        "after_count": len(after),
    }


def cell_by_id(config: dict[str, Any], cell_id: str) -> dict[str, Any]:
    for cell in config["cells"]:
        if cell["id"] == cell_id:
            return cell
    raise KeyError(f"unknown cell id {cell_id!r}")


def generate_fixture_files(config: dict[str, Any], dest: Path | None = None) -> Path:
    dest = dest or (HERE / "fixtures")
    dest.mkdir(parents=True, exist_ok=True)
    generated: dict[str, Any] = {}
    for cell in config["cells"]:
        advantage = resolve_advantage(cell["semantic_advantage"], config)
        tools = assemble_tools(
            config,
            variant=cell["variant"],
            ladder=cell["ladder"],
            advantage=advantage,
        )
        record = {
            "cell": cell["id"],
            "axis": cell["axis"],
            "variant": cell["variant"],
            "ladder": cell["ladder"],
            "semantic_advantage": advantage,
            "tool_names": [tool_name(t) for t in tools],
            "tools": tools,
        }
        generated[cell["id"]] = record
        (dest / f"{cell['id']}.json").write_text(
            json.dumps(record, indent=2) + "\n",
            encoding="utf-8",
        )

    ladder_out = {level: config["ladder"][level] for level in ("L0", "L1", "L2", "L3")}
    (dest / "ladder.json").write_text(json.dumps(ladder_out, indent=2) + "\n", encoding="utf-8")

    advantage_out = {
        str(level): legitimate_description(float(level), config)
        for level in config["semantic_advantage"]["levels"]
    }
    (dest / "semantic_advantage.json").write_text(
        json.dumps(advantage_out, indent=2) + "\n",
        encoding="utf-8",
    )

    diff = patched_defense_diff(config)
    (dest / "patched_defense_diff.json").write_text(
        json.dumps(diff, indent=2) + "\n",
        encoding="utf-8",
    )

    index = {
        "experiment_id": config["experiment_id"],
        "legitimate": config["tools"]["legitimate"],
        "poisoned": config["tools"]["poisoned"],
        "distractors": config["tools"]["distractors"],
        "cells": sorted(generated),
        "note": "Canonical (unpermuted) tool definitions generated from config.yaml.",
    }
    (dest / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return dest


def main() -> int:
    import yaml

    config = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    dest = generate_fixture_files(config)
    print(f"[+] wrote fixtures under {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

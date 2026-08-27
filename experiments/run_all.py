#!/usr/bin/env python3
"""Run the deterministic experiments (01-07) in order."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = [
    "experiments/01-baseline/run.py",
    "experiments/02-description-poisoning/run.py",
    "experiments/03-semantic-poisoning/run.py",
    "experiments/04-template-poisoning/run.py",
    "experiments/05-bias-ablation/run.py",
    "experiments/06-defense-matrix/run.py",
    "experiments/07-cross-boundary-propagation/run.py",
]


def main() -> int:
    python = sys.executable
    for rel in SCRIPTS:
        print(f"\n=== {rel} ===")
        result = subprocess.run([python, str(ROOT / rel)], cwd=ROOT)
        if result.returncode != 0:
            print(f"[!] {rel} failed with {result.returncode}", file=sys.stderr)
            return result.returncode
    print("\n[+] all experiments OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

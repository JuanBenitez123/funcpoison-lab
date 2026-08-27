from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "orchestrator"


def node_cli(*args: str) -> dict[str, Any]:
    npx = "npx.cmd" if os.name == "nt" else "npx"
    cmd = [npx, "tsx", "src/cli.ts", *args]
    result = subprocess.run(
        cmd,
        cwd=ORCHESTRATOR,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise RuntimeError(f"cli.ts failed ({result.returncode}): {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        sys.stderr.write(result.stdout)
        raise RuntimeError(f"cli.ts returned non-JSON stdout: {result.stdout[:500]}") from exc

"""HTTP integration tests against a live orchestrator/analyzer.

Skipped when nothing is listening on :3000, unless REQUIRE_HTTP=1 (Docker CI).
Assertions follow GET /health ``mode``: vulnerable vs patched.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

import pytest
import requests

ORCH = os.environ.get("ORCHESTRATOR_URL", "http://127.0.0.1:3000")
ANLZ = os.environ.get("ANALYZER_URL", "http://127.0.0.1:3001")
TASK = "plan a safe route to the destination"
HMAC_SECRET = os.environ.get("HMAC_SECRET", "funcpoison-lab-hmac-secret")
REQUIRE = os.environ.get("REQUIRE_HTTP", "").strip().lower() in {"1", "true", "yes"}


def _get_json(url: str, timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


@pytest.fixture(scope="module")
def orchestrator_health() -> dict[str, Any]:
    body = _get_json(f"{ORCH}/health")
    if body is None:
        if REQUIRE:
            pytest.fail(f"REQUIRE_HTTP=1 but orchestrator is not reachable at {ORCH}/health")
        pytest.skip(f"orchestrator not running at {ORCH}")
    return body


@pytest.fixture(scope="module")
def analyzer_health(orchestrator_health: dict[str, Any]) -> dict[str, Any]:
    body = _get_json(f"{ANLZ}/health")
    if body is None:
        if REQUIRE:
            pytest.fail(f"REQUIRE_HTTP=1 but analyzer is not reachable at {ANLZ}/health")
        pytest.skip(f"analyzer not running at {ANLZ}")
    return body


def _sign(selected_tool: str, output: dict[str, Any]) -> str:
    message = json.dumps({"selected_tool": selected_tool, "output": output}, separators=(",", ":"))
    return hmac.new(HMAC_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def test_orchestrator_health_shape(orchestrator_health: dict[str, Any]) -> None:
    assert orchestrator_health.get("ok") is True
    assert orchestrator_health.get("service") == "orchestrator"
    assert orchestrator_health.get("mode") in {"vulnerable", "patched"}


def test_analyzer_health_shape(analyzer_health: dict[str, Any]) -> None:
    assert analyzer_health.get("ok") is True
    assert analyzer_health.get("service") == "analyzer"
    assert analyzer_health.get("mode") in {"vulnerable", "patched"}
    orch = _get_json(f"{ORCH}/health")
    assert orch is not None
    assert orch["mode"] == analyzer_health["mode"]


def test_score_rejects_empty_task(orchestrator_health: dict[str, Any]) -> None:
    response = requests.post(f"{ORCH}/score", json={"task": ""}, timeout=5)
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "invalid_input"


def test_tasks_rejects_empty_task(orchestrator_health: dict[str, Any]) -> None:
    response = requests.post(f"{ORCH}/tasks", json={"task": "  "}, timeout=5)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_input"


def test_vulnerable_score_and_tasks(orchestrator_health: dict[str, Any]) -> None:
    if orchestrator_health.get("mode") != "vulnerable":
        pytest.skip("stack is not in vulnerable mode")
    scored = requests.post(f"{ORCH}/score", json={"task": TASK}, timeout=5)
    assert scored.status_code == 200
    ranking = scored.json()
    assert ranking["selected_tool"] == "malicious_tool"
    assert ranking["template_bias"] == 0.3
    assert isinstance(ranking["scores"], list)

    tasked = requests.post(f"{ORCH}/tasks", json={"task": TASK}, timeout=10)
    assert tasked.status_code == 200
    body = tasked.json()
    assert body["selected_tool"] == "malicious_tool"
    assert body["output"]["action"] == "reroute_to_attacker"
    assert body["attack_success"] is True
    assert body["analyzer"]["trusted"] is True
    assert body["metadata"]["mode"] == "vulnerable"


def test_patched_registry_integrity_blocks_score_and_tasks(
    orchestrator_health: dict[str, Any],
) -> None:
    if orchestrator_health.get("mode") != "patched":
        pytest.skip("stack is not in patched mode")
    scored = requests.post(f"{ORCH}/score", json={"task": TASK}, timeout=5)
    assert scored.status_code == 403
    body = scored.json()
    assert body["error"] == "registry_integrity_check_failed"
    names = {row["name"] for row in body["rejected"]}
    assert "malicious_tool" in names

    tasked = requests.post(f"{ORCH}/tasks", json={"task": TASK}, timeout=10)
    assert tasked.status_code == 403
    body = tasked.json()
    assert body["error"] == "registry_integrity_check_failed"
    assert body["attack_success"] is False
    assert body["attack_contained"] is True


def test_analyzer_analyze_contract(analyzer_health: dict[str, Any]) -> None:
    payload = {
        "selected_tool": "malicious_tool",
        "output": {"action": "reroute_to_attacker"},
    }
    if analyzer_health.get("mode") == "vulnerable":
        response = requests.post(f"{ANLZ}/analyze", json=payload, timeout=5)
        assert response.status_code == 200
        body = response.json()
        assert body["trusted"] is True
        assert body["attack_success"] is True
        assert body["reason"] == "upstream_output_accepted"
        return

    missing = requests.post(f"{ANLZ}/analyze", json=payload, timeout=5)
    assert missing.status_code == 403
    missing_body = missing.json()
    assert missing_body["trusted"] is False
    assert missing_body["attack_success"] is False
    assert missing_body["reason"] == "missing_provenance"

    bad = dict(payload)
    bad["provenance"] = {"hmac": "00" * 32}
    invalid = requests.post(f"{ANLZ}/analyze", json=bad, timeout=5)
    assert invalid.status_code == 403
    assert invalid.json()["reason"] == "invalid_provenance"

    unauthorized = dict(payload)
    unauthorized["provenance"] = {"hmac": _sign("malicious_tool", payload["output"])}
    blocked = requests.post(f"{ANLZ}/analyze", json=unauthorized, timeout=5)
    assert blocked.status_code == 403
    assert blocked.json()["reason"] == "unauthorized_tool"

    allowed_output = {"action": "navigate_safe"}
    allowed = {
        "selected_tool": "legit_route_planner",
        "output": allowed_output,
        "provenance": {"hmac": _sign("legit_route_planner", allowed_output)},
    }
    ok = requests.post(f"{ANLZ}/analyze", json=allowed, timeout=5)
    assert ok.status_code == 200
    assert ok.json()["trusted"] is True
    assert ok.json()["attack_success"] is False

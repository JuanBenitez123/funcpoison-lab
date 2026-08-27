"""OpenAI-compatible chat client with provider pinning and retries."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
SECRET_RE = re.compile(
    r"(Bearer\s+)\S+|(sk-or-v1-)\S+|(sk-ant-)\S+|(sk-)\S+",
    re.IGNORECASE,
)


class MissingAPIKeyError(RuntimeError):
    """No gateway key in the environment or .env file."""


class AuthError(RuntimeError):
    """Gateway rejected the key (401/403). Abort the run."""


def _require_openai():
    try:
        from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing package 'openai'. Install optional LLM deps with the same interpreter:\n"
            f"  {sys.executable} -m pip install -r requirements-llm.txt"
        ) from exc
    return OpenAI, APIConnectionError, APIStatusError, APITimeoutError


def redact(text: str | None) -> str:
    if not text:
        return ""
    return SECRET_RE.sub(lambda m: (m.group(1) or m.group(2) or m.group(3) or m.group(4) or "") + "[REDACTED]", text)


def resolve_api_key(config: dict[str, Any]) -> tuple[str, str]:
    """Return (env_var_name, key). Never log the key."""
    name = config["gateway"]["api_key_env"]
    value = os.environ.get(name, "").strip()
    if value:
        return name, value
    raise MissingAPIKeyError(
        f"No API key found. Set {name} in the gitignored .env file (see .env.example)."
    )


@dataclass
class ChatResult:
    ok: bool
    status_code: int | None = None
    served_provider: str | None = None
    model_version: str | None = None
    system_fingerprint: str | None = None
    raw: dict[str, Any] | None = None
    tool_call_names: list[str] = field(default_factory=list)
    first_tool: str | None = None
    finish_reason: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    @property
    def outcome_is_transport_error(self) -> bool:
        return not self.ok


def _tool_names_from_message(message: dict[str, Any]) -> list[str]:
    names: list[str] = []
    tool_calls = message.get("tool_calls") or []
    for call in tool_calls:
        function = call.get("function") or {}
        name = function.get("name")
        if isinstance(name, str) and name:
            names.append(name)
        elif isinstance(call.get("name"), str) and call["name"]:
            names.append(call["name"])
    # Legacy OpenAI single function_call. Do not parse free-text content:
    # the attack payload itself looks like an invocation.
    function_call = message.get("function_call") or {}
    legacy = function_call.get("name")
    if isinstance(legacy, str) and legacy and legacy not in names:
        names.append(legacy)
    return names


class LLMClient:
    def __init__(self, config: dict[str, Any], api_key: str) -> None:
        gateway = config["gateway"]
        self.timeout_s = float(gateway.get("timeout_s", 90))
        self.max_retries = int(gateway.get("max_retries", 4))
        self.retry_backoff_s = float(gateway.get("retry_backoff_s", 2))
        OpenAI, *_errs = _require_openai()
        self.client = OpenAI(
            base_url=gateway["base_url"],
            api_key=api_key,
            timeout=self.timeout_s,
            max_retries=0,
            default_headers={
                "HTTP-Referer": gateway.get("referer", ""),
                "X-Title": gateway.get("title", "FuncPoison-Lab experiment 08"),
            },
        )

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        provider: dict[str, Any],
        temperature: float | None,
    ) -> ChatResult:
        last: ChatResult | None = None
        for attempt in range(self.max_retries + 1):
            result = self._once(
                model=model,
                messages=messages,
                tools=tools,
                provider=provider,
                temperature=temperature,
            )
            if result.ok:
                return result
            status = result.status_code
            if status in {401, 403}:
                raise AuthError(redact(result.error_message) or f"auth failed ({status})")
            if status is not None and status not in RETRYABLE_STATUS:
                return result
            last = result
            if attempt < self.max_retries:
                delay = min(30.0, self.retry_backoff_s * (2**attempt))
                retry_after = None
                if isinstance(result.raw, dict):
                    retry_after = result.raw.get("_retry_after_s")
                time.sleep(float(retry_after) if retry_after else delay)
        return last or ChatResult(
            ok=False,
            error_type="api_error",
            error_message="retries exhausted",
        )

    def _once(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        provider: dict[str, Any],
        temperature: float | None,
    ) -> ChatResult:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "extra_body": {"provider": provider},
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        try:
            raw_response = self.client.chat.completions.with_raw_response.create(**kwargs)
            payload = json.loads(raw_response.http_response.content.decode("utf-8"))
            if not isinstance(payload, dict):
                return ChatResult(
                    ok=False,
                    status_code=raw_response.http_response.status_code,
                    error_type="api_error",
                    error_message="response was not a JSON object",
                    raw={"_non_object": True},
                )
            if payload.get("error"):
                err = payload["error"]
                message = err if isinstance(err, str) else json.dumps(err)
                return ChatResult(
                    ok=False,
                    status_code=raw_response.http_response.status_code,
                    served_provider=payload.get("provider"),
                    model_version=payload.get("model"),
                    raw=_sanitize_payload(payload),
                    error_type="api_error",
                    error_message=redact(message),
                )
            choices = payload.get("choices") or []
            if not choices:
                return ChatResult(
                    ok=False,
                    status_code=raw_response.http_response.status_code,
                    served_provider=payload.get("provider"),
                    model_version=payload.get("model"),
                    system_fingerprint=payload.get("system_fingerprint"),
                    raw=_sanitize_payload(payload),
                    error_type="api_error",
                    error_message="empty choices",
                )
            message = (choices[0].get("message") or {}) if isinstance(choices[0], dict) else {}
            names = _tool_names_from_message(message)
            return ChatResult(
                ok=True,
                status_code=raw_response.http_response.status_code,
                served_provider=_served_provider(payload, raw_response),
                model_version=payload.get("model"),
                system_fingerprint=payload.get("system_fingerprint"),
                raw=_sanitize_payload(payload),
                tool_call_names=names,
                first_tool=names[0] if names else None,
                finish_reason=choices[0].get("finish_reason") if isinstance(choices[0], dict) else None,
            )
        except AuthError:
            raise
        except Exception as exc:
            if isinstance(exc, json.JSONDecodeError):
                return ChatResult(
                    ok=False,
                    error_type="api_error",
                    error_message=f"invalid JSON: {exc}",
                )
            _, APIConnectionError, APIStatusError, APITimeoutError = _require_openai()
            if isinstance(exc, APIStatusError):
                status = exc.status_code
                body: dict[str, Any] | None = None
                try:
                    body = exc.response.json()
                except Exception:
                    body = {"error": redact(exc.message)}
                retry_after = None
                if exc.response is not None:
                    retry_after = exc.response.headers.get("retry-after")
                if isinstance(body, dict) and retry_after:
                    body = {**body, "_retry_after_s": retry_after}
                return ChatResult(
                    ok=False,
                    status_code=status,
                    served_provider=(body or {}).get("provider") if isinstance(body, dict) else None,
                    raw=_sanitize_payload(body) if isinstance(body, dict) else None,
                    error_type="api_error",
                    error_message=redact(exc.message),
                )
            if isinstance(exc, (APITimeoutError, APIConnectionError, TimeoutError, OSError)):
                return ChatResult(
                    ok=False,
                    error_type="api_error",
                    error_message=redact(f"{type(exc).__name__}: {exc}"),
                )
            raise


def _served_provider(payload: dict[str, Any], raw_response: Any) -> str | None:
    provider = payload.get("provider")
    if isinstance(provider, str) and provider:
        return provider
    headers = getattr(getattr(raw_response, "http_response", None), "headers", None)
    if headers:
        for key in ("x-openrouter-provider", "X-OpenRouter-Provider"):
            value = headers.get(key)
            if value:
                return value
    return None


def _sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drop anything that might echo secrets; keep the rest for the JSONL log."""
    if payload is None:
        return None
    dumped = json.dumps(payload)
    if SECRET_RE.search(dumped):
        return json.loads(redact(dumped))
    return payload

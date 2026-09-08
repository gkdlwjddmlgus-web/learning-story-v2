from __future__ import annotations

import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import services.ai_client as ai_client


class GenericInvalidArgumentError(Exception):
    status_code = 400

    def __str__(self) -> str:
        return (
            "400 INVALID_ARGUMENT. "
            "Request contains an invalid argument."
        )


class _FakeResponse:
    text = '{"ok": true}'


class _FallbackModels:
    def __init__(self) -> None:
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            raise GenericInvalidArgumentError()
        return _FakeResponse()


class _AlwaysFailModels:
    def __init__(self) -> None:
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        raise GenericInvalidArgumentError()


class _FakeClient:
    def __init__(self, models) -> None:
        self.models = models


def _run_with_client(fake_client, fn):
    original = ai_client.get_gemini_client
    ai_client.get_gemini_client = lambda *args, **kwargs: fake_client
    try:
        return fn()
    finally:
        ai_client.get_gemini_client = original


def main() -> int:
    service_path = PROJECT_ROOT / "services" / "ai_client.py"
    source = service_path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(service_path))

    print("=" * 78)
    print("Schema Compatibility Fallback v1 - QA")
    print("=" * 78)

    exc = GenericInvalidArgumentError()
    if not ai_client._should_schema_compatibility_fallback(exc):
        raise AssertionError(
            "generic 400 INVALID_ARGUMENT was not classified "
            "as a schema compatibility candidate"
        )
    print("[PASS] generic structured-request 400 is a compatibility candidate")

    models = _FallbackModels()
    fake_client = _FakeClient(models)

    def _success_case():
        return ai_client.generate_live_json(
            prompt="Return JSON.",
            schema={
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                },
            },
            model="fake-model",
            max_retries=0,
            timeout_ms=1000,
            api_key_secret_name="IGNORED",
        )

    result, meta = _run_with_client(fake_client, _success_case)

    if result != {"ok": True}:
        raise AssertionError(f"unexpected result: {result}")
    if len(models.calls) != 2:
        raise AssertionError(
            f"expected 2 physical calls, got {len(models.calls)}"
        )
    if meta.get("attempt_count") != 2:
        raise AssertionError(
            "compatibility fallback did not report 2 attempts: "
            + repr(meta)
        )
    reasons = meta.get("retry_reasons") or []
    if not any(
        str(reason).startswith("schema_compatibility_fallback:")
        for reason in reasons
    ):
        raise AssertionError(
            "schema compatibility reason missing: " + repr(reasons)
        )
    print(
        "[PASS] max_retries=0 still performs exactly one "
        "same-route schema-less fallback"
    )

    failing_models = _AlwaysFailModels()
    failing_client = _FakeClient(failing_models)

    def _failure_case():
        return ai_client.generate_live_json(
            prompt="Return JSON.",
            schema={
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                },
            },
            model="fake-model",
            max_retries=0,
            timeout_ms=1000,
            api_key_secret_name="IGNORED",
        )

    try:
        _run_with_client(failing_client, _failure_case)
    except GenericInvalidArgumentError:
        pass
    else:
        raise AssertionError(
            "persistent generic 400 should still surface after "
            "one compatibility fallback"
        )

    if len(failing_models.calls) != 2:
        raise AssertionError(
            "persistent 400 must stop after structured + schema-less "
            f"attempts, got {len(failing_models.calls)}"
        )
    print("[PASS] persistent 400 stops after one compatibility fallback")

    print()
    print("[POLICY]")
    print("- same key / same model / same prompt")
    print("- only response_json_schema is removed")
    print("- compatibility fallback is separate from transient retry budget")
    print("- persistent 400 does not churn other keys/models here")
    print()
    print("[SECURITY / COST]")
    print("- QA made no Gemini API request.")
    print("- QA made no DB query/write.")
    print()
    print("[PASS] Schema Compatibility Fallback v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

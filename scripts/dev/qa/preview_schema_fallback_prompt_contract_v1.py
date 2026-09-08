from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import services.ai_client as ai_client


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "concept_sequence"],
    "properties": {
        "summary": {"type": "string"},
        "concept_sequence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                },
            },
        },
    },
}

VALID = {
    "summary": "테스트 Curriculum",
    "concept_sequence": [{"name": "개념 A"}],
}


class GenericInvalidArgumentError(Exception):
    status_code = 400

    def __str__(self) -> str:
        return (
            "400 INVALID_ARGUMENT. "
            "Request contains an invalid argument."
        )


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _Models:
    def __init__(self) -> None:
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            raise GenericInvalidArgumentError()
        return _FakeResponse(
            json.dumps(VALID, ensure_ascii=False)
        )


class _FakeClient:
    def __init__(self, models) -> None:
        self.models = models


def main() -> int:
    service_path = PROJECT_ROOT / "services" / "ai_client.py"
    source = service_path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(service_path))

    print("=" * 78)
    print("Schema Fallback Prompt Contract v1 - QA")
    print("=" * 78)

    original_prompt = "테스트 주제에 대한 Curriculum을 만든다. JSON만 반환한다."
    fallback_prompt = ai_client._build_schema_fallback_prompt(
        original_prompt,
        SCHEMA,
    )

    if not fallback_prompt.startswith(original_prompt):
        raise AssertionError("original prompt was not preserved")
    for token in (
        "[Required JSON Output Contract]",
        "JSON_SCHEMA=",
        '"summary"',
        '"concept_sequence"',
        '"additionalProperties":false',
    ):
        if token not in fallback_prompt:
            raise AssertionError(
                "fallback prompt contract missing token: " + token
            )
    print("[PASS] fallback prompt preserves original prompt + exact schema contract")

    models = _Models()
    fake_client = _FakeClient(models)
    original_get_client = ai_client.get_gemini_client
    ai_client.get_gemini_client = lambda *args, **kwargs: fake_client
    try:
        result, meta = ai_client.generate_live_json(
            prompt=original_prompt,
            schema=SCHEMA,
            model="fake-model",
            max_retries=0,
            timeout_ms=1000,
            api_key_secret_name="IGNORED",
        )
    finally:
        ai_client.get_gemini_client = original_get_client

    if result != VALID:
        raise AssertionError(f"unexpected result: {result!r}")
    if len(models.calls) != 2:
        raise AssertionError(
            f"expected 2 calls, got {len(models.calls)}"
        )

    first_contents = models.calls[0]["contents"]
    second_contents = models.calls[1]["contents"]

    if first_contents != original_prompt:
        raise AssertionError(
            "structured first request must keep original prompt unchanged"
        )
    if second_contents == original_prompt:
        raise AssertionError(
            "schema-less compatibility request did not receive prompt contract"
        )
    if '"summary"' not in second_contents:
        raise AssertionError(
            "schema-less request does not carry required summary key"
        )

    first_config = models.calls[0]["config"]
    second_config = models.calls[1]["config"]
    if getattr(first_config, "response_json_schema", None) is None:
        raise AssertionError(
            "first request unexpectedly lacks provider schema"
        )
    if getattr(second_config, "response_json_schema", None) is not None:
        raise AssertionError(
            "fallback request must remove provider response_json_schema"
        )
    print("[PASS] only schema-less compatibility attempt receives text schema contract")

    reasons = meta.get("retry_reasons") or []
    if not any(
        str(reason).startswith(
            "schema_compatibility_fallback:"
        )
        for reason in reasons
    ):
        raise AssertionError(
            "schema compatibility metadata missing: " + repr(reasons)
        )
    print("[PASS] existing compatibility fallback metadata is preserved")

    ai_client._validate_local_json_schema(result, SCHEMA)
    print("[PASS] fallback output still passes local response schema validation")

    print()
    print("[FLOW]")
    print("- First request: original prompt + provider response_json_schema.")
    print("- Generic 400: same key/model compatibility fallback.")
    print("- Fallback request: original prompt + textual exact JSON Schema.")
    print("- Provider response_json_schema is removed only on fallback.")
    print("- Parsed output must still pass local schema validation.")
    print()
    print("[NO CHANGE]")
    print("- No DB schema/data mutation.")
    print("- No Curriculum/Question/Story schema rewrite.")
    print("- No Router key/model policy change.")
    print("- No new dependency.")
    print()
    print("[SECURITY / COST]")
    print("- QA made no Gemini API request.")
    print("- QA made no DB query/write.")
    print()
    print("[PASS] Schema Fallback Prompt Contract v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

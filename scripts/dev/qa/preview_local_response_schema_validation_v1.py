from __future__ import annotations

import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import services.ai_client as ai_client


CURRICULUM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "summary",
        "categories",
        "concept_sequence",
    ],
    "properties": {
        "summary": {"type": "string"},
        "categories": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "order",
                    "description",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "order": {"type": "integer"},
                    "description": {"type": "string"},
                },
            },
        },
        "concept_sequence": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "semantic_contract",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "semantic_contract": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "core_rule",
                            "common_misconception",
                            "reasoning_boundary",
                        ],
                        "properties": {
                            "core_rule": {"type": "string"},
                            "common_misconception": {
                                "type": "string"
                            },
                            "reasoning_boundary": {
                                "type": "string"
                            },
                        },
                    },
                },
            },
        },
    },
}


VALID_CURRICULUM = {
    "summary": "광합성과 세포 호흡 학습",
    "categories": [
        {
            "name": "에너지 전환",
            "order": 1,
            "description": "에너지 흐름",
        },
        {
            "name": "상호 관계",
            "order": 2,
            "description": "두 과정의 관계",
        },
    ],
    "concept_sequence": [
        {
            "name": "광합성과 세포 호흡의 관계",
            "semantic_contract": {
                "core_rule": "두 과정은 에너지 전환 방식이 다르다.",
                "common_misconception": "식물은 호흡하지 않는다고 오해한다.",
                "reasoning_boundary": "세부 효소 기작까지 단정하지 않는다.",
            },
        }
    ],
}


INVALID_FALLBACK_SHAPE = {
    "topic": "광합성과 세포 호흡",
    "concepts": [],
    "target_level": "중급",
    "learning_objective": "두 과정의 관계 이해",
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
    def __init__(
        self,
        responses,
    ) -> None:
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return _FakeResponse(item)


class _FakeClient:
    def __init__(self, models) -> None:
        self.models = models


def _with_client(models, fn):
    original = ai_client.get_gemini_client
    ai_client.get_gemini_client = lambda *args, **kwargs: _FakeClient(models)
    try:
        return fn()
    finally:
        ai_client.get_gemini_client = original


def _call(schema, models):
    return _with_client(
        models,
        lambda: ai_client.generate_live_json(
            prompt="Return JSON only.",
            schema=schema,
            model="fake-model",
            max_retries=0,
            timeout_ms=1000,
            api_key_secret_name="IGNORED",
        ),
    )


def main() -> int:
    service_path = PROJECT_ROOT / "services" / "ai_client.py"
    source = service_path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(service_path))

    print("=" * 78)
    print("Local Response Schema Validation v1 - QA")
    print("=" * 78)

    ai_client._validate_local_json_schema(
        VALID_CURRICULUM,
        CURRICULUM_SCHEMA,
    )
    print("[PASS] valid Curriculum shape passes local schema validation")

    try:
        ai_client._validate_local_json_schema(
            INVALID_FALLBACK_SHAPE,
            CURRICULUM_SCHEMA,
        )
    except ai_client.AIResponseSchemaValidationError as exc:
        if "summary" not in str(exc):
            raise AssertionError(
                "validation error does not identify missing contract field: "
                + str(exc)
            )
    else:
        raise AssertionError(
            "invalid fallback Curriculum shape unexpectedly passed"
        )
    print("[PASS] topic/concepts fallback shape is rejected before persistence")

    nested_invalid = {
        **VALID_CURRICULUM,
        "concept_sequence": [
            {
                "name": "광합성과 세포 호흡의 관계",
                "semantic_contract": {
                    "core_rule": "핵심 원리",
                    "common_misconception": "대표 오개념",
                },
            }
        ],
    }
    try:
        ai_client._validate_local_json_schema(
            nested_invalid,
            CURRICULUM_SCHEMA,
        )
    except ai_client.AIResponseSchemaValidationError as exc:
        if "reasoning_boundary" not in str(exc):
            raise AssertionError(
                "nested contract error path missing: " + str(exc)
            )
    else:
        raise AssertionError(
            "partial semantic_contract unexpectedly passed"
        )
    print("[PASS] incomplete nested semantic_contract is rejected")

    import json

    valid_models = _Models([
        json.dumps(VALID_CURRICULUM, ensure_ascii=False)
    ])
    result, meta = _call(CURRICULUM_SCHEMA, valid_models)
    if result != VALID_CURRICULUM:
        raise AssertionError("valid response changed unexpectedly")
    if len(valid_models.calls) != 1:
        raise AssertionError("valid response should need one call")
    print("[PASS] valid parsed JSON is returned unchanged")

    fallback_models = _Models([
        GenericInvalidArgumentError(),
        json.dumps(
            INVALID_FALLBACK_SHAPE,
            ensure_ascii=False,
        ),
    ])
    try:
        _call(CURRICULUM_SCHEMA, fallback_models)
    except ai_client.AIResponseSchemaValidationError as exc:
        if "summary" not in str(exc):
            raise AssertionError(
                "fallback validation error is not explicit: " + str(exc)
            )
    else:
        raise AssertionError(
            "invalid schema-less fallback was returned to caller"
        )

    if len(fallback_models.calls) != 2:
        raise AssertionError(
            "expected structured request + one compatibility fallback, "
            f"got {len(fallback_models.calls)} calls"
        )
    print(
        "[PASS] schema-less fallback is locally validated and "
        "invalid shape never returns"
    )

    print()
    print("[CONTRACT]")
    print("- Every parsed JSON response is checked against the caller schema.")
    print("- Invalid fallback JSON raises AIResponseSchemaValidationError.")
    print("- Invalid response is returned to no repository/upsert caller.")
    print("- Local validation errors do not trigger schema compatibility fallback.")
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
    print("[PASS] Local Response Schema Validation v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

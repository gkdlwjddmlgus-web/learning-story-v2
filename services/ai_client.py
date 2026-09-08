from __future__ import annotations

# SCHEMA_COMPATIBILITY_FALLBACK_V1_20260908
# LOCAL_RESPONSE_SCHEMA_VALIDATION_V1_20260908
# SCHEMA_FALLBACK_PROMPT_CONTRACT_V1_20260908

import json
import random
import time
from typing import Any

import streamlit as st
from google import genai
from google.genai import types


DEFAULT_MODEL = "gemini-3.6-flash"

# 일반 Story/Curriculum 호출의 기본값.
# feature별로 GenerateContentConfig.http_options를 통해 override할 수 있다.
REQUEST_TIMEOUT_MS = 60_000
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BASE_DELAY = 2.0
DEFAULT_MAX_OUTPUT_TOKENS = 4096


class AIQuotaExhausted(RuntimeError):
    pass


class AIResponseSchemaValidationError(RuntimeError):
    """로컬 응답 계약(JSON Schema subset) 검증 실패."""

    def __init__(
        self,
        message: str,
        *,
        path: str = "$",
        keyword: str | None = None,
    ) -> None:
        detail = f"{path}: {message}"
        if keyword:
            detail += f" [keyword={keyword}]"
        super().__init__(
            "Local response schema validation failed: " + detail
        )
        self.path = path
        self.keyword = keyword


@st.cache_resource(show_spinner=False)
def get_gemini_client(
    api_key_secret_name: str = "GEMINI_API_KEY",
    api_key_secret_index: int | None = None,
):
    """secret reference별 Gemini client cache. 실제 key 값은 인자/로그에 노출하지 않는다."""
    try:
        raw_secret = st.secrets[api_key_secret_name]
        if api_key_secret_index is None:
            api_key = raw_secret
        else:
            api_key = raw_secret[int(api_key_secret_index)]
    except Exception as exc:
        reference = (
            api_key_secret_name
            if api_key_secret_index is None
            else f"{api_key_secret_name}[{int(api_key_secret_index)}]"
        )
        raise RuntimeError(
            "Gemini API key secret을 읽지 못했습니다: " + reference
        ) from exc

    api_key = str(api_key or "").strip()
    if not api_key:
        raise RuntimeError("Gemini API key secret이 비어 있습니다.")

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )




def _status_code(exc: Exception) -> int | None:
    for name in ("status_code", "code"):
        value = getattr(exc, name, None)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass

    message = str(exc)
    for code in (408, 429, 500, 502, 503, 504):
        if str(code) in message:
            return code
    return None


def _is_hard_quota(exc: Exception) -> bool:
    if _status_code(exc) != 429:
        return False

    message = str(exc).lower()
    hard_signals = (
        "per day",
        "per_day",
        "requests_per_day",
        "request_per_day",
        "daily quota",
        "daily limit",
        "free_tier_requests_per_day",
        "generate_content_free_tier_requests_per_day",
        "generate_content_free_tier_requests",
        "quota exceeded for metric",
        "generaterequestsperdayperprojectpermodel-freetier",
        "perprojectpermodel-freetier",
        "quota will reset",
    )
    return any(signal in message for signal in hard_signals)


def _is_timeout(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    return (
        "timeout" in name
        or "timed out" in message
        or "read operation timed out" in message
        or "request timeout" in message
    )


def is_timeout_error(exc: Exception) -> bool:
    """UI/Service에서 timeout 여부를 판별할 수 있는 공개 helper."""
    return _is_timeout(exc)


def _is_transient(exc: Exception) -> bool:
    code = _status_code(exc)
    if code in (408, 500, 502, 503, 504):
        return True
    if code == 429 and not _is_hard_quota(exc):
        return True
    if _is_timeout(exc):
        return True

    message = str(exc).lower()
    return any(
        signal in message
        for signal in (
            "high demand",
            "unavailable",
            "temporarily overloaded",
            "rate limit",
            "too many requests",
            "request timeout",
            "gateway timeout",
        )
    ) and not _is_hard_quota(exc)


def _schema_related(exc: Exception) -> bool:
    message = str(exc).lower()
    direct_signals = (
        "response_json_schema",
        "response json schema",
        "json schema",
        "schema validation",
        "schema is not supported",
        "unsupported schema",
    )
    if any(signal in message for signal in direct_signals):
        return True

    return "schema" in message and any(
        qualifier in message
        for qualifier in (
            "invalid",
            "unsupported",
            "not supported",
            "not allowed",
        )
    )


def _should_schema_compatibility_fallback(exc: Exception) -> bool:
    """
    Structured-output 요청의 호환성 fallback 후보인지 판별한다.

    Gemini가 response_json_schema 자체를 명시하지 않고
    `400 INVALID_ARGUMENT`만 반환하는 경우가 있으므로,
    schema가 실제로 포함된 첫 요청에 한해서 generic 400도
    같은 key/model/prompt의 schema-less compatibility probe 1회를 허용한다.
    """
    if isinstance(exc, AIResponseSchemaValidationError):
        return False

    if _schema_related(exc):
        return True

    code = _status_code(exc)
    if code != 400:
        return False

    message = str(exc).lower()
    return (
        "invalid_argument" in message
        or "invalid argument" in message
    )


def _json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
        )
    if expected == "null":
        return value is None
    return False


def _schema_path(parent: str, key: Any) -> str:
    if isinstance(key, int):
        return f"{parent}[{key}]"
    key_text = str(key)
    if key_text.isidentifier():
        return f"{parent}.{key_text}"
    return f"{parent}[{key_text!r}]"


def _validation_error(
    message: str,
    *,
    path: str,
    keyword: str,
) -> AIResponseSchemaValidationError:
    return AIResponseSchemaValidationError(
        message,
        path=path,
        keyword=keyword,
    )


def _validate_local_json_schema(
    value: Any,
    schema: Any,
    *,
    path: str = "$",
) -> None:
    """
    Provider structured-output가 실패해 schema-less fallback을 사용할 때도
    앱 내부 응답 계약을 지키기 위한 로컬 JSON Schema subset validator.

    지원 범위:
    - type / enum / const
    - object: required / properties / additionalProperties /
      minProperties / maxProperties
    - array: items / minItems / maxItems / uniqueItems
    - string: minLength / maxLength
    - number/integer: minimum / maximum /
      exclusiveMinimum / exclusiveMaximum
    - allOf / anyOf / oneOf

    description/title/default/format 등 생성 결과의 구조 무결성에 직접
    영향을 주지 않는 annotation keyword는 무시한다.
    """
    if schema is True:
        return
    if schema is False:
        raise _validation_error(
            "boolean schema is false",
            path=path,
            keyword="false_schema",
        )
    if not isinstance(schema, dict):
        raise _validation_error(
            "schema must be an object or boolean",
            path=path,
            keyword="schema",
        )

    if "allOf" in schema:
        branches = schema["allOf"]
        if not isinstance(branches, list):
            raise _validation_error(
                "allOf must be an array",
                path=path,
                keyword="allOf",
            )
        for branch in branches:
            _validate_local_json_schema(value, branch, path=path)

    if "anyOf" in schema:
        branches = schema["anyOf"]
        if not isinstance(branches, list):
            raise _validation_error(
                "anyOf must be an array",
                path=path,
                keyword="anyOf",
            )
        matched = 0
        for branch in branches:
            try:
                _validate_local_json_schema(
                    value,
                    branch,
                    path=path,
                )
                matched += 1
            except AIResponseSchemaValidationError:
                pass
        if matched == 0:
            raise _validation_error(
                "value does not match any anyOf branch",
                path=path,
                keyword="anyOf",
            )

    if "oneOf" in schema:
        branches = schema["oneOf"]
        if not isinstance(branches, list):
            raise _validation_error(
                "oneOf must be an array",
                path=path,
                keyword="oneOf",
            )
        matched = 0
        for branch in branches:
            try:
                _validate_local_json_schema(
                    value,
                    branch,
                    path=path,
                )
                matched += 1
            except AIResponseSchemaValidationError:
                pass
        if matched != 1:
            raise _validation_error(
                f"value matches {matched} oneOf branches; expected 1",
                path=path,
                keyword="oneOf",
            )

    if "const" in schema and value != schema["const"]:
        raise _validation_error(
            f"value {value!r} does not equal const",
            path=path,
            keyword="const",
        )

    if "enum" in schema:
        options = schema["enum"]
        if not isinstance(options, list):
            raise _validation_error(
                "enum must be an array",
                path=path,
                keyword="enum",
            )
        if not any(
            type(value) is type(option) and value == option
            for option in options
        ):
            raise _validation_error(
                f"value {value!r} is not in enum",
                path=path,
                keyword="enum",
            )

    expected_type = schema.get("type")
    if expected_type is not None:
        if isinstance(expected_type, str):
            expected_types = [expected_type]
        elif isinstance(expected_type, list):
            expected_types = expected_type
        else:
            raise _validation_error(
                "type must be a string or array",
                path=path,
                keyword="type",
            )

        if not any(
            isinstance(item, str)
            and _json_type_matches(value, item)
            for item in expected_types
        ):
            raise _validation_error(
                f"expected type {expected_types!r}, "
                f"got {type(value).__name__}",
                path=path,
                keyword="type",
            )

    if isinstance(value, dict):
        required = schema.get("required", [])
        if required is not None:
            if not isinstance(required, list):
                raise _validation_error(
                    "required must be an array",
                    path=path,
                    keyword="required",
                )
            for key in required:
                if key not in value:
                    raise _validation_error(
                        f"required property {key!r} is missing",
                        path=path,
                        keyword="required",
                    )

        properties = schema.get("properties", {})
        if properties is None:
            properties = {}
        if not isinstance(properties, dict):
            raise _validation_error(
                "properties must be an object",
                path=path,
                keyword="properties",
            )

        for key, child_schema in properties.items():
            if key in value:
                _validate_local_json_schema(
                    value[key],
                    child_schema,
                    path=_schema_path(path, key),
                )

        additional = schema.get("additionalProperties", True)
        known = set(properties)
        extra_keys = [
            key for key in value
            if key not in known
        ]
        if additional is False and extra_keys:
            raise _validation_error(
                f"unexpected properties: {extra_keys!r}",
                path=path,
                keyword="additionalProperties",
            )
        if isinstance(additional, dict):
            for key in extra_keys:
                _validate_local_json_schema(
                    value[key],
                    additional,
                    path=_schema_path(path, key),
                )

        min_properties = schema.get("minProperties")
        if (
            isinstance(min_properties, int)
            and len(value) < min_properties
        ):
            raise _validation_error(
                f"object has {len(value)} properties; "
                f"minimum is {min_properties}",
                path=path,
                keyword="minProperties",
            )

        max_properties = schema.get("maxProperties")
        if (
            isinstance(max_properties, int)
            and len(value) > max_properties
        ):
            raise _validation_error(
                f"object has {len(value)} properties; "
                f"maximum is {max_properties}",
                path=path,
                keyword="maxProperties",
            )

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            raise _validation_error(
                f"array has {len(value)} items; minimum is {min_items}",
                path=path,
                keyword="minItems",
            )

        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(value) > max_items:
            raise _validation_error(
                f"array has {len(value)} items; maximum is {max_items}",
                path=path,
                keyword="maxItems",
            )

        if schema.get("uniqueItems") is True:
            canonical = [
                json.dumps(
                    item,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                for item in value
            ]
            if len(canonical) != len(set(canonical)):
                raise _validation_error(
                    "array items are not unique",
                    path=path,
                    keyword="uniqueItems",
                )

        items_schema = schema.get("items")
        if isinstance(items_schema, dict) or isinstance(
            items_schema,
            bool,
        ):
            for index, item in enumerate(value):
                _validate_local_json_schema(
                    item,
                    items_schema,
                    path=_schema_path(path, index),
                )

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            raise _validation_error(
                f"string length {len(value)} is below {min_length}",
                path=path,
                keyword="minLength",
            )

        max_length = schema.get("maxLength")
        if isinstance(max_length, int) and len(value) > max_length:
            raise _validation_error(
                f"string length {len(value)} exceeds {max_length}",
                path=path,
                keyword="maxLength",
            )

    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            raise _validation_error(
                f"value {value!r} is below minimum {minimum!r}",
                path=path,
                keyword="minimum",
            )

        maximum = schema.get("maximum")
        if maximum is not None and value > maximum:
            raise _validation_error(
                f"value {value!r} exceeds maximum {maximum!r}",
                path=path,
                keyword="maximum",
            )

        exclusive_minimum = schema.get("exclusiveMinimum")
        if (
            exclusive_minimum is not None
            and value <= exclusive_minimum
        ):
            raise _validation_error(
                f"value {value!r} must be > "
                f"{exclusive_minimum!r}",
                path=path,
                keyword="exclusiveMinimum",
            )

        exclusive_maximum = schema.get("exclusiveMaximum")
        if (
            exclusive_maximum is not None
            and value >= exclusive_maximum
        ):
            raise _validation_error(
                f"value {value!r} must be < "
                f"{exclusive_maximum!r}",
                path=path,
                keyword="exclusiveMaximum",
            )




def _build_schema_fallback_prompt(
    prompt: str,
    schema: dict[str, Any],
) -> str:
    """
    Provider-side structured schema를 사용할 수 없을 때만
    동일한 응답 계약을 텍스트로 명시한다.

    원래 prompt를 보존하고, caller schema를 compact JSON으로
    뒤에 추가한다. 반환 결과는 이후 로컬 schema validation을
    반드시 통과해야 한다.
    """
    schema_text = json.dumps(
        schema,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (
        prompt.rstrip()
        + "\n\n"
        + "[Required JSON Output Contract]\n"
        + "Provider-side response_json_schema를 사용할 수 없으므로 "
        + "아래 JSON Schema를 정확히 따른 JSON 객체만 반환한다.\n"
        + "- 키 이름을 바꾸거나 대체 구조를 만들지 않는다.\n"
        + "- required 필드를 모두 포함한다.\n"
        + "- additionalProperties가 false인 object에는 정의되지 않은 "
        + "키를 추가하지 않는다.\n"
        + "- 설명/Markdown/code fence를 출력하지 않는다.\n"
        + "JSON_SCHEMA="
        + schema_text
    )


def _retry_reason(exc: Exception) -> str:
    code = _status_code(exc)
    error_name = type(exc).__name__
    if code is not None:
        return f"{error_name}:{code}"
    return error_name


def _attach_error_meta(
    exc: Exception,
    *,
    started: float,
    retry_count: int,
    attempt_count: int,
    retry_reasons: list[str],
    timeout_ms: int,
    thinking_level: str | None,
    max_output_tokens: int,
    prompt_chars: int,
) -> None:
    values = {
        "_ls_retry_count": retry_count,
        "_ls_attempt_count": attempt_count,
        "_ls_retry_reasons": list(retry_reasons),
        "_ls_latency_ms": int((time.perf_counter() - started) * 1000),
        "_ls_timeout_ms": timeout_ms,
        "_ls_thinking_level": thinking_level,
        "_ls_max_output_tokens": max_output_tokens,
        "_ls_prompt_chars": prompt_chars,
    }
    for key, value in values.items():
        try:
            setattr(exc, key, value)
        except Exception:
            pass


def generate_live_json(
    *,
    prompt: str,
    schema: dict[str, Any],
    model: str = DEFAULT_MODEL,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    timeout_ms: int = REQUEST_TIMEOUT_MS,
    thinking_level: str | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    retry_on_timeout: bool = True,
    api_key_secret_name: str = "GEMINI_API_KEY",
    api_key_secret_index: int | None = None,
    key_slot: str = "primary",
) -> tuple[Any, dict[str, Any]]:
    """Gemini JSON 호출 + 요청 단위 latency/retry/route metadata."""
    client = get_gemini_client(
        api_key_secret_name,
        api_key_secret_index,
    )
    started = time.perf_counter()
    retry_count = 0
    attempt_count = 0
    retry_reasons: list[str] = []
    last_error: Exception | None = None
    use_schema = True
    schema_fallback_used = False
    prompt_chars = len(prompt)

    # max_retries는 transient/content retry 예산이다.
    # structured-schema compatibility fallback 1회는 이 예산과 분리한다.
    for attempt in range(max_retries + 2):
        attempt_count = attempt + 1

        try:
            kwargs: dict[str, Any] = {
                "response_mime_type": "application/json",
                "max_output_tokens": max_output_tokens,
                "http_options": types.HttpOptions(timeout=timeout_ms),
            }

            if thinking_level:
                kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_level=thinking_level
                )

            if use_schema:
                kwargs["response_json_schema"] = schema

            request_prompt = (
                prompt
                if use_schema
                else _build_schema_fallback_prompt(prompt, schema)
            )

            response = client.models.generate_content(
                model=model,
                contents=request_prompt,
                config=types.GenerateContentConfig(**kwargs),
            )

            text = (response.text or "").strip()
            if not text:
                raise ValueError("AI가 빈 응답을 반환했습니다.")

            response_chars = len(text)

            if text.startswith("```"):
                text = (
                    text.replace("```json", "", 1)
                    .replace("```", "")
                    .strip()
                )

            result = json.loads(text)
            _validate_local_json_schema(result, schema)

            return result, {
                "retry_count": retry_count,
                "attempt_count": attempt_count,
                "retry_reasons": retry_reasons,
                "latency_ms": int(
                    (time.perf_counter() - started) * 1000
                ),
                "request_timeout_ms": timeout_ms,
                "thinking_level": thinking_level,
                "max_output_tokens": max_output_tokens,
                "prompt_chars": prompt_chars,
                "response_chars": response_chars,
                "model": model,
                "key_slot": key_slot,
            }

        except Exception as exc:
            last_error = exc

            if _is_hard_quota(exc):
                wrapped = AIQuotaExhausted(
                    "Gemini의 일일/하드 할당량이 소진된 것으로 보입니다."
                )
                _attach_error_meta(
                    wrapped,
                    started=started,
                    retry_count=retry_count,
                    attempt_count=attempt_count,
                    retry_reasons=retry_reasons,
                    timeout_ms=timeout_ms,
                    thinking_level=thinking_level,
                    max_output_tokens=max_output_tokens,
                    prompt_chars=prompt_chars,
                )
                setattr(wrapped, "_ls_model", model)
                setattr(wrapped, "_ls_key_slot", key_slot)
                raise wrapped from exc

            if (
                use_schema
                and not schema_fallback_used
                and _should_schema_compatibility_fallback(exc)
            ):
                use_schema = False
                schema_fallback_used = True
                retry_count += 1
                retry_reasons.append(
                    "schema_compatibility_fallback:"
                    + _retry_reason(exc)
                )
                continue

            if _is_timeout(exc) and not retry_on_timeout:
                break

            retryable = _is_transient(exc) or isinstance(
                exc,
                (ValueError, json.JSONDecodeError),
            )
            transient_retries_used = (
                retry_count - int(schema_fallback_used)
            )
            if (
                not retryable
                or transient_retries_used >= max_retries
            ):
                break

            retry_count += 1
            retry_reasons.append(_retry_reason(exc))
            delay = base_delay * (2**attempt) + random.uniform(0, 0.5)
            time.sleep(delay)

    if last_error is not None:
        _attach_error_meta(
            last_error,
            started=started,
            retry_count=retry_count,
            attempt_count=attempt_count,
            retry_reasons=retry_reasons,
            timeout_ms=timeout_ms,
            thinking_level=thinking_level,
            max_output_tokens=max_output_tokens,
            prompt_chars=prompt_chars,
        )
        setattr(last_error, "_ls_model", model)
        setattr(last_error, "_ls_key_slot", key_slot)
        raise last_error

    raise RuntimeError("AI 생성 결과를 처리하지 못했습니다.")

# AI_ROUTING_V1_FOUNDATION_20260904

# AI_ROUTING_V1_LIST_KEYS_MODELS_20260904

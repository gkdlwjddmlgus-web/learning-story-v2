from __future__ import annotations

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
    prompt_chars = len(prompt)

    for attempt in range(max_retries + 1):
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

            response = client.models.generate_content(
                model=model,
                contents=prompt,
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

            if use_schema and _schema_related(exc):
                use_schema = False
                retry_count += 1
                retry_reasons.append(
                    "schema_fallback:" + _retry_reason(exc)
                )
                continue

            if _is_timeout(exc) and not retry_on_timeout:
                break

            retryable = _is_transient(exc) or isinstance(
                exc,
                (ValueError, json.JSONDecodeError),
            )
            if not retryable or attempt >= max_retries:
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

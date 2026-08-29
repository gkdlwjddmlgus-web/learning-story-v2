from __future__ import annotations

import time
from typing import Any

from repositories.generation_repository import log_ai_generation
from services.ai_client import DEFAULT_MODEL, generate_live_json
from services.dev_config import get_mock_delay, is_ai_mock_enabled
from services.mock_generation import generate_mock


def _log_best_effort(**kwargs) -> None:
    try:
        log_ai_generation(**kwargs)
    except Exception:
        # 생성 성공 여부가 로그 INSERT 실패 때문에 뒤집히면 안 된다.
        pass


def generate_json(
    *,
    feature: str,
    prompt_version: str,
    prompt: str,
    schema: dict[str, Any],
    model: str = DEFAULT_MODEL,
    mock_context: dict[str, Any] | None = None,
    user_id: int | None = None,
    world_id: int | None = None,
    story_arc_id: int | None = None,
    timeout_ms: int | None = None,
    thinking_level: str | None = None,
    max_retries: int | None = None,
    max_output_tokens: int | None = None,
    retry_on_timeout: bool = True,
) -> Any:
    """모든 생성 기능의 단일 진입점.

    feature별 AI 실행 정책(timeout/thinking/retry)을 Service에서 명시할 수 있다.
    """
    if is_ai_mock_enabled():
        started = time.perf_counter()
        try:
            delay = get_mock_delay()
            if delay:
                time.sleep(delay)

            result = generate_mock(feature, mock_context or {})

            _log_best_effort(
                feature=feature,
                model="mock-local",
                prompt_version=prompt_version,
                latency_ms=int((time.perf_counter() - started) * 1000),
                success=True,
                retry_count=0,
                error_type=None,
                error_message=None,
                provider="mock",
                user_id=user_id,
                world_id=world_id,
                story_arc_id=story_arc_id,
                attempt_count=1,
                request_timeout_ms=timeout_ms,
                thinking_level=thinking_level,
                max_output_tokens=max_output_tokens,
                prompt_chars=len(prompt),
                response_chars=None,
                retry_reasons=[],
            )
            return result

        except Exception as exc:
            _log_best_effort(
                feature=feature,
                model="mock-local",
                prompt_version=prompt_version,
                latency_ms=int((time.perf_counter() - started) * 1000),
                success=False,
                retry_count=0,
                error_type=type(exc).__name__,
                error_message=str(exc)[:1200],
                provider="mock",
                user_id=user_id,
                world_id=world_id,
                story_arc_id=story_arc_id,
                attempt_count=1,
                request_timeout_ms=timeout_ms,
                thinking_level=thinking_level,
                max_output_tokens=max_output_tokens,
                prompt_chars=len(prompt),
                response_chars=None,
                retry_reasons=[],
            )
            raise

    live_kwargs: dict[str, Any] = {
        "prompt": prompt,
        "schema": schema,
        "model": model,
        "retry_on_timeout": retry_on_timeout,
    }
    if timeout_ms is not None:
        live_kwargs["timeout_ms"] = timeout_ms
    if thinking_level is not None:
        live_kwargs["thinking_level"] = thinking_level
    if max_retries is not None:
        live_kwargs["max_retries"] = max_retries
    if max_output_tokens is not None:
        live_kwargs["max_output_tokens"] = max_output_tokens

    started = time.perf_counter()

    try:
        result, meta = generate_live_json(**live_kwargs)

        _log_best_effort(
            feature=feature,
            model=model,
            prompt_version=prompt_version,
            latency_ms=meta.get("latency_ms"),
            success=True,
            retry_count=meta.get("retry_count", 0),
            error_type=None,
            error_message=None,
            provider="gemini",
            user_id=user_id,
            world_id=world_id,
            story_arc_id=story_arc_id,
            attempt_count=meta.get("attempt_count", 1),
            request_timeout_ms=meta.get("request_timeout_ms"),
            thinking_level=meta.get("thinking_level"),
            max_output_tokens=meta.get("max_output_tokens"),
            prompt_chars=meta.get("prompt_chars"),
            response_chars=meta.get("response_chars"),
            retry_reasons=meta.get("retry_reasons", []),
        )
        return result

    except Exception as exc:
        _log_best_effort(
            feature=feature,
            model=model,
            prompt_version=prompt_version,
            latency_ms=getattr(
                exc,
                "_ls_latency_ms",
                int((time.perf_counter() - started) * 1000),
            ),
            success=False,
            retry_count=getattr(exc, "_ls_retry_count", 0),
            error_type=type(exc).__name__,
            error_message=str(exc)[:1200],
            provider="gemini",
            user_id=user_id,
            world_id=world_id,
            story_arc_id=story_arc_id,
            attempt_count=getattr(exc, "_ls_attempt_count", 1),
            request_timeout_ms=getattr(exc, "_ls_timeout_ms", timeout_ms),
            thinking_level=getattr(exc, "_ls_thinking_level", thinking_level),
            max_output_tokens=getattr(
                exc, "_ls_max_output_tokens", max_output_tokens
            ),
            prompt_chars=getattr(exc, "_ls_prompt_chars", len(prompt)),
            response_chars=None,
            retry_reasons=getattr(exc, "_ls_retry_reasons", []),
        )
        raise

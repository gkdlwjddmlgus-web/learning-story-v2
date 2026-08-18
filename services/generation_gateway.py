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
) -> Any:
    """모든 생성 기능의 단일 진입점. Service는 Mock/Gemini 분기를 알 필요가 없다."""
    if is_ai_mock_enabled():
        started=time.perf_counter()
        try:
            delay=get_mock_delay()
            if delay:
                time.sleep(delay)
            result=generate_mock(feature, mock_context or {})
            _log_best_effort(
                feature=feature, model="mock-local", prompt_version=prompt_version,
                latency_ms=int((time.perf_counter()-started)*1000), success=True,
                retry_count=0, error_type=None, error_message=None, provider="mock",
                user_id=user_id, world_id=world_id, story_arc_id=story_arc_id,
            )
            return result
        except Exception as exc:
            _log_best_effort(
                feature=feature, model="mock-local", prompt_version=prompt_version,
                latency_ms=int((time.perf_counter()-started)*1000), success=False,
                retry_count=0, error_type=type(exc).__name__, error_message=str(exc)[:1200], provider="mock",
                user_id=user_id, world_id=world_id, story_arc_id=story_arc_id,
            )
            raise

    started=time.perf_counter()
    try:
        result, meta=generate_live_json(prompt=prompt,schema=schema,model=model)
        _log_best_effort(
            feature=feature, model=model, prompt_version=prompt_version,
            latency_ms=meta.get("latency_ms"), success=True,
            retry_count=meta.get("retry_count",0), error_type=None,error_message=None,provider="gemini",
            user_id=user_id,world_id=world_id,story_arc_id=story_arc_id,
        )
        return result
    except Exception as exc:
        _log_best_effort(
            feature=feature, model=model,prompt_version=prompt_version,
            latency_ms=getattr(exc, "_ls_latency_ms", int((time.perf_counter()-started)*1000)), success=False,
            retry_count=getattr(exc, "_ls_retry_count", 0),error_type=type(exc).__name__,error_message=str(exc)[:1200],provider="gemini",
            user_id=user_id,world_id=world_id,story_arc_id=story_arc_id,
        )
        raise

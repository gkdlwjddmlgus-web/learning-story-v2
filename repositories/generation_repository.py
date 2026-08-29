from __future__ import annotations

import json

from db import get_pool


def log_ai_generation(
    *,
    feature: str,
    model: str,
    prompt_version: str | None,
    latency_ms: int | None,
    success: bool,
    retry_count: int = 0,
    error_type: str | None = None,
    error_message: str | None = None,
    provider: str = "gemini",
    user_id: int | None = None,
    world_id: int | None = None,
    story_arc_id: int | None = None,
    attempt_count: int | None = None,
    request_timeout_ms: int | None = None,
    thinking_level: str | None = None,
    max_output_tokens: int | None = None,
    prompt_chars: int | None = None,
    response_chars: int | None = None,
    retry_reasons: list[str] | None = None,
) -> None:
    pool = get_pool()

    retry_reasons_json = json.dumps(
        retry_reasons or [],
        ensure_ascii=False,
    )

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_ai_generation_logs (
                    user_id,
                    world_id,
                    story_arc_id,
                    feature,
                    model,
                    prompt_version,
                    latency_ms,
                    success,
                    retry_count,
                    error_type,
                    error_message,
                    provider,
                    attempt_count,
                    request_timeout_ms,
                    thinking_level,
                    max_output_tokens,
                    prompt_chars,
                    response_chars,
                    retry_reasons
                )
                values (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s::jsonb
                )
                """,
                (
                    user_id,
                    world_id,
                    story_arc_id,
                    feature,
                    model,
                    prompt_version,
                    latency_ms,
                    success,
                    retry_count,
                    error_type,
                    error_message,
                    provider,
                    attempt_count,
                    request_timeout_ms,
                    thinking_level,
                    max_output_tokens,
                    prompt_chars,
                    response_chars,
                    retry_reasons_json,
                ),
            )
        conn.commit()

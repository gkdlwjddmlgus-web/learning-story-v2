from __future__ import annotations

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
) -> None:
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_ai_generation_logs (
                    user_id, world_id, story_arc_id, feature, model,
                    prompt_version, latency_ms, success, retry_count,
                    error_type, error_message, provider
                )
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    user_id, world_id, story_arc_id, feature, model,
                    prompt_version, latency_ms, success, retry_count,
                    error_type, error_message, provider,
                ),
            )
        conn.commit()

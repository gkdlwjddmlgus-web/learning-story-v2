from __future__ import annotations

import json
from typing import Any

from db import get_pool


def get_curriculum(
    world_id: int,
) -> dict[str, Any] | None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    curriculum,
                    model,
                    prompt_version,
                    created_at,
                    updated_at
                from public.v2_curricula
                where world_id = %s
                """,
                (world_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "curriculum": row[0] or {},
        "model": row[1],
        "prompt_version": row[2],
        "created_at": row[3],
        "updated_at": row[4],
    }


def upsert_curriculum(
    world_id: int,
    curriculum: dict[str, Any],
    *,
    model: str | None = None,
    prompt_version: str | None = None,
) -> None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_curricula (
                    world_id,
                    curriculum,
                    model,
                    prompt_version
                )
                values (
                    %s,
                    %s::jsonb,
                    %s,
                    %s
                )
                on conflict (world_id)
                do update set
                    curriculum = excluded.curriculum,
                    model = excluded.model,
                    prompt_version = excluded.prompt_version,
                    updated_at = now()
                """,
                (
                    world_id,
                    json.dumps(
                        curriculum,
                        ensure_ascii=False,
                    ),
                    model,
                    prompt_version,
                ),
            )

        conn.commit()

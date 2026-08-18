from __future__ import annotations

import json

from db import get_pool


def insert_events(
    events: list[dict],
) -> None:
    if not events:
        return

    rows = [
        (
            event.get("user_id"),
            event.get("world_id"),
            event.get("story_arc_id"),
            event.get("chapter_id"),
            event.get("session_id"),
            event["event_type"],
            json.dumps(
                event.get("metadata") or {},
                ensure_ascii=False,
            ),
        )
        for event in events
    ]

    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                insert into public.v2_user_events (
                    user_id,
                    world_id,
                    story_arc_id,
                    chapter_id,
                    session_id,
                    event_type,
                    metadata
                )
                values (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s::jsonb
                )
                """,
                rows,
            )

        conn.commit()

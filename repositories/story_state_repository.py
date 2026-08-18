from __future__ import annotations

import json
from typing import Any

from db import get_pool


STATE_COLUMNS = """
    id,
    story_arc_id,
    story_summary,
    current_location,
    characters,
    companion_state,
    confirmed_facts,
    open_threads,
    resolved_events,
    latest_event,
    created_at,
    updated_at
"""


def _row_to_state(row) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "id": row[0],
        "story_arc_id": row[1],
        "story_summary": row[2],
        "current_location": row[3],
        "characters": row[4] or [],
        "companion_state": row[5] or {},
        "confirmed_facts": row[6] or [],
        "open_threads": row[7] or [],
        "resolved_events": row[8] or [],
        "latest_event": row[9] or {},
        "created_at": row[10],
        "updated_at": row[11],
    }


def get_story_state(
    story_arc_id: int,
) -> dict[str, Any] | None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select
                    {STATE_COLUMNS}
                from public.v2_story_states
                where story_arc_id = %s
                """,
                (story_arc_id,),
            )
            row = cur.fetchone()

    return _row_to_state(row)


def ensure_story_state(
    story_arc_id: int,
) -> dict[str, Any]:
    """
    Arc당 Story State 1개를 보장한다.
    기존 State가 있다면 값을 덮어쓰지 않는다.
    """
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_story_states (
                    story_arc_id
                )
                values (%s)
                on conflict (story_arc_id)
                do nothing
                """,
                (story_arc_id,),
            )

        conn.commit()

    state = get_story_state(
        story_arc_id
    )

    if state is None:
        raise RuntimeError(
            "Story State 생성/조회에 실패했습니다."
        )

    return state


def update_story_state(
    story_arc_id: int,
    *,
    story_summary: str | None = None,
    current_location: str | None = None,
    characters: list | None = None,
    companion_state: dict | None = None,
    confirmed_facts: list | None = None,
    open_threads: list | None = None,
    resolved_events: list | None = None,
    latest_event: dict | None = None,
) -> None:
    """
    전달된 값만 갱신한다.
    None은 '변경하지 않음'을 의미한다.
    """
    current = get_story_state(
        story_arc_id
    )

    if current is None:
        current = ensure_story_state(
            story_arc_id
        )

    new_story_summary = (
        current["story_summary"]
        if story_summary is None
        else story_summary
    )
    new_current_location = (
        current["current_location"]
        if current_location is None
        else current_location
    )
    new_characters = (
        current["characters"]
        if characters is None
        else characters
    )
    new_companion_state = (
        current["companion_state"]
        if companion_state is None
        else companion_state
    )
    new_confirmed_facts = (
        current["confirmed_facts"]
        if confirmed_facts is None
        else confirmed_facts
    )
    new_open_threads = (
        current["open_threads"]
        if open_threads is None
        else open_threads
    )
    new_resolved_events = (
        current["resolved_events"]
        if resolved_events is None
        else resolved_events
    )
    new_latest_event = (
        current["latest_event"]
        if latest_event is None
        else latest_event
    )

    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.v2_story_states
                set
                    story_summary = %s,
                    current_location = %s,
                    characters = %s::jsonb,
                    companion_state = %s::jsonb,
                    confirmed_facts = %s::jsonb,
                    open_threads = %s::jsonb,
                    resolved_events = %s::jsonb,
                    latest_event = %s::jsonb,
                    updated_at = now()
                where story_arc_id = %s
                """,
                (
                    new_story_summary,
                    new_current_location,
                    json.dumps(
                        new_characters,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        new_companion_state,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        new_confirmed_facts,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        new_open_threads,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        new_resolved_events,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        new_latest_event,
                        ensure_ascii=False,
                    ),
                    story_arc_id,
                ),
            )

        conn.commit()

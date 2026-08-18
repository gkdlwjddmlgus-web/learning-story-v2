from __future__ import annotations

from db import get_pool


def get_choice_for_chapter(
    user_id: int,
    chapter_id: int,
) -> dict | None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    choice_key,
                    choice_text,
                    created_at,
                    story_arc_id
                from public.v2_story_choice_selections
                where user_id = %s
                  and chapter_id = %s
                """,
                (
                    user_id,
                    chapter_id,
                ),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "choice_key": row[0],
        "choice_text": row[1],
        "created_at": row[2],
        "story_arc_id": row[3],
    }


def get_latest_choice_for_arc(
    user_id: int,
    story_arc_id: int,
) -> dict | None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    choice_key,
                    choice_text,
                    chapter_id,
                    created_at
                from public.v2_story_choice_selections
                where user_id = %s
                  and story_arc_id = %s
                order by created_at desc
                limit 1
                """,
                (
                    user_id,
                    story_arc_id,
                ),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "choice_key": row[0],
        "choice_text": row[1],
        "chapter_id": row[2],
        "created_at": row[3],
    }


def save_story_choice(
    *,
    user_id: int,
    world_id: int,
    story_arc_id: int,
    chapter_id: int,
    choice_key: str,
    choice_text: str,
) -> None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_story_choice_selections (
                    user_id,
                    world_id,
                    story_arc_id,
                    chapter_id,
                    choice_key,
                    choice_text
                )
                values (
                    %s,%s,%s,%s,%s,%s
                )
                on conflict (
                    user_id,
                    chapter_id
                )
                do update set
                    choice_key = excluded.choice_key,
                    choice_text = excluded.choice_text,
                    created_at = now()
                """,
                (
                    user_id,
                    world_id,
                    story_arc_id,
                    chapter_id,
                    choice_key,
                    choice_text,
                ),
            )

        conn.commit()

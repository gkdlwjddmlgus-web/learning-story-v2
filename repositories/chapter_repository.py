from __future__ import annotations

import json
from typing import Any

from db import get_pool


CHAPTER_COLUMNS = """
    id,
    world_id,
    chapter_number,
    title,
    story,
    learning_objectives,
    questions,
    completed,
    created_at,
    story_choices,
    story_phase,
    target_concepts,
    pending_state_update,
    state_applied
"""


def get_chapters_by_world(
    world_id: int,
):
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select
                    {CHAPTER_COLUMNS}
                from public.v2_chapters
                where world_id = %s
                order by chapter_number asc
                """,
                (world_id,),
            )

            return cur.fetchall()


def get_chapters_by_story_arc(
    story_arc_id: int,
):
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select
                    {CHAPTER_COLUMNS}
                from public.v2_chapters
                where story_arc_id = %s
                order by chapter_number asc
                """,
                (story_arc_id,),
            )

            return cur.fetchall()


def get_chapter(
    world_id: int,
    chapter_number: int,
):
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select
                    {CHAPTER_COLUMNS}
                from public.v2_chapters
                where world_id = %s
                  and chapter_number = %s
                """,
                (
                    world_id,
                    chapter_number,
                ),
            )

            return cur.fetchone()


def _get_active_story_arc_id(
    cur,
    world_id: int,
) -> int | None:
    cur.execute(
        """
        select id
        from public.v2_story_arcs
        where world_id = %s
          and status = 'active'
        limit 1
        """,
        (world_id,),
    )

    row = cur.fetchone()

    return (
        row[0]
        if row
        else None
    )


def create_chapter(
    world_id: int,
    chapter_number: int,
    title: str,
    story: str,
    learning_objectives: list,
    questions: list | None = None,
    story_arc_id: int | None = None,
    story_choices: list | None = None,
    story_phase: str | None = None,
    target_concepts: list | None = None,
    pending_state_update: dict | None = None,
) -> int:
    pool = get_pool()

    questions = questions or []
    story_choices = story_choices or []
    target_concepts = target_concepts or []
    pending_state_update = (
        pending_state_update
        or {}
    )

    with pool.connection() as conn:
        with conn.cursor() as cur:
            resolved_story_arc_id = (
                story_arc_id
                if story_arc_id is not None
                else _get_active_story_arc_id(
                    cur,
                    world_id,
                )
            )

            cur.execute(
                """
                insert into public.v2_chapters (
                    world_id,
                    chapter_number,
                    title,
                    story,
                    learning_objectives,
                    questions,
                    story_arc_id,
                    story_choices,
                    story_phase,
                    target_concepts,
                    pending_state_update,
                    state_applied
                )
                values (
                    %s,%s,%s,%s,
                    %s::jsonb,
                    %s::jsonb,
                    %s,
                    %s::jsonb,
                    %s,
                    %s::jsonb,
                    %s::jsonb,
                    false
                )
                returning id
                """,
                (
                    world_id,
                    chapter_number,
                    title,
                    story,
                    json.dumps(
                        learning_objectives,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        questions,
                        ensure_ascii=False,
                    ),
                    resolved_story_arc_id,
                    json.dumps(
                        story_choices,
                        ensure_ascii=False,
                    ),
                    story_phase,
                    json.dumps(
                        target_concepts,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        pending_state_update,
                        ensure_ascii=False,
                    ),
                ),
            )

            chapter_id = (
                cur.fetchone()[0]
            )

        conn.commit()

    return chapter_id


def create_story_block(
    *,
    world_id: int,
    story_arc_id: int,
    chapters: list[dict[str, Any]],
) -> list[int]:
    """
    AI가 한 번에 생성한 1~3개 Chapter를 하나의 transaction으로 저장한다.

    하나라도 저장 실패하면 Block 전체를 rollback한다.
    이미 같은 world_id + chapter_number가 존재하면 해당 Chapter는 건너뛴다.
    """
    pool = get_pool()
    created_ids = []

    with pool.connection() as conn:
        try:
            with conn.cursor() as cur:
                for chapter in chapters:
                    cur.execute(
                        """
                        insert into public.v2_chapters (
                            world_id,
                            chapter_number,
                            title,
                            story,
                            learning_objectives,
                            questions,
                            story_arc_id,
                            story_choices,
                            story_phase,
                            target_concepts,
                            pending_state_update,
                            state_applied
                        )
                        values (
                            %s,%s,%s,%s,
                            %s::jsonb,
                            '[]'::jsonb,
                            %s,
                            %s::jsonb,
                            %s,
                            %s::jsonb,
                            %s::jsonb,
                            false
                        )
                        on conflict (
                            world_id,
                            chapter_number
                        )
                        do nothing
                        returning id
                        """,
                        (
                            world_id,
                            chapter[
                                "chapter_number"
                            ],
                            chapter["title"],
                            chapter["story"],
                            json.dumps(
                                chapter[
                                    "learning_objectives"
                                ],
                                ensure_ascii=False,
                            ),
                            story_arc_id,
                            json.dumps(
                                chapter.get(
                                    "story_choices",
                                    [],
                                ),
                                ensure_ascii=False,
                            ),
                            chapter.get(
                                "story_phase"
                            ),
                            json.dumps(
                                chapter.get(
                                    "target_concepts",
                                    [],
                                ),
                                ensure_ascii=False,
                            ),
                            json.dumps(
                                chapter.get(
                                    "state_update",
                                    {},
                                ),
                                ensure_ascii=False,
                            ),
                        ),
                    )

                    row = cur.fetchone()

                    if row:
                        created_ids.append(
                            row[0]
                        )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    return created_ids


def update_chapter_questions(
    chapter_id: int,
    questions: list,
):
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.v2_chapters
                set questions = %s::jsonb
                where id = %s
                """,
                (
                    json.dumps(
                        questions,
                        ensure_ascii=False,
                    ),
                    chapter_id,
                ),
            )

        conn.commit()


def mark_chapter_completed(
    chapter_id: int,
) -> None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.v2_chapters
                set completed = true
                where id = %s
                  and completed = false
                """,
                (chapter_id,),
            )

        conn.commit()


def mark_chapter_state_applied(
    chapter_id: int,
) -> None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.v2_chapters
                set state_applied = true
                where id = %s
                """,
                (chapter_id,),
            )

        conn.commit()

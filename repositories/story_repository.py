from __future__ import annotations

import json
from typing import Any

from db import get_pool


ARC_COLUMNS = """
    id,
    world_id,
    arc_number,
    title,
    status,
    target_chapter_count,
    current_phase,
    blueprint,
    created_at,
    updated_at,
    completed_at
"""


def _row_to_arc(row) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "id": row[0],
        "world_id": row[1],
        "arc_number": row[2],
        "title": row[3],
        "status": row[4],
        "target_chapter_count": row[5],
        "current_phase": row[6],
        "blueprint": row[7] or {},
        "created_at": row[8],
        "updated_at": row[9],
        "completed_at": row[10],
    }


def get_story_arc(
    story_arc_id: int,
) -> dict[str, Any] | None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select
                    {ARC_COLUMNS}
                from public.v2_story_arcs
                where id = %s
                """,
                (story_arc_id,),
            )
            row = cur.fetchone()

    return _row_to_arc(row)


def get_story_arcs_by_world(
    world_id: int,
) -> list[dict[str, Any]]:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select
                    {ARC_COLUMNS}
                from public.v2_story_arcs
                where world_id = %s
                order by arc_number asc
                """,
                (world_id,),
            )
            rows = cur.fetchall()

    return [
        _row_to_arc(row)
        for row in rows
    ]


def get_active_story_arc(
    world_id: int,
) -> dict[str, Any] | None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select
                    {ARC_COLUMNS}
                from public.v2_story_arcs
                where world_id = %s
                  and status = 'active'
                limit 1
                """,
                (world_id,),
            )
            row = cur.fetchone()

    return _row_to_arc(row)


def get_latest_story_arc(
    world_id: int,
) -> dict[str, Any] | None:
    """
    active Arc가 끝난 뒤에도 Archive/Ending 화면에서
    가장 최근 Arc를 읽을 수 있도록 한다.
    """
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select
                    {ARC_COLUMNS}
                from public.v2_story_arcs
                where world_id = %s
                order by arc_number desc
                limit 1
                """,
                (world_id,),
            )
            row = cur.fetchone()

    return _row_to_arc(row)


def get_next_arc_number(
    world_id: int,
) -> int:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select coalesce(max(arc_number), 0) + 1
                from public.v2_story_arcs
                where world_id = %s
                """,
                (world_id,),
            )
            row = cur.fetchone()

    return int(row[0])


def create_story_arc(
    world_id: int,
    *,
    arc_number: int | None = None,
    title: str | None = None,
    status: str = "draft",
    target_chapter_count: int | None = None,
    current_phase: str = "setup",
    blueprint: dict[str, Any] | None = None,
) -> int:
    if arc_number is None:
        arc_number = get_next_arc_number(
            world_id
        )

    blueprint = blueprint or {}

    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_story_arcs (
                    world_id,
                    arc_number,
                    title,
                    status,
                    target_chapter_count,
                    current_phase,
                    blueprint
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
                returning id
                """,
                (
                    world_id,
                    arc_number,
                    title,
                    status,
                    target_chapter_count,
                    current_phase,
                    json.dumps(
                        blueprint,
                        ensure_ascii=False,
                    ),
                ),
            )
            story_arc_id = cur.fetchone()[0]

        conn.commit()

    return story_arc_id


def update_story_arc_blueprint(
    story_arc_id: int,
    blueprint: dict[str, Any],
    *,
    title: str | None = None,
    target_chapter_count: int | None = None,
) -> None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.v2_story_arcs
                set
                    blueprint = %s::jsonb,
                    title = coalesce(%s, title),
                    target_chapter_count = coalesce(
                        %s,
                        target_chapter_count
                    ),
                    updated_at = now()
                where id = %s
                """,
                (
                    json.dumps(
                        blueprint,
                        ensure_ascii=False,
                    ),
                    title,
                    target_chapter_count,
                    story_arc_id,
                ),
            )

        conn.commit()


def update_story_arc_phase(
    story_arc_id: int,
    current_phase: str,
) -> None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.v2_story_arcs
                set
                    current_phase = %s,
                    updated_at = now()
                where id = %s
                """,
                (
                    current_phase,
                    story_arc_id,
                ),
            )

        conn.commit()


def activate_story_arc(
    story_arc_id: int,
) -> None:
    """
    한 World에 active Arc가 하나만 존재하도록
    같은 transaction에서 기존 active를 draft로 돌린 뒤
    대상 Arc를 active로 전환한다.
    """
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select world_id
                from public.v2_story_arcs
                where id = %s
                """,
                (story_arc_id,),
            )
            row = cur.fetchone()

            if row is None:
                raise ValueError(
                    "존재하지 않는 Story Arc입니다."
                )

            world_id = row[0]

            cur.execute(
                """
                update public.v2_story_arcs
                set
                    status = 'draft',
                    updated_at = now()
                where world_id = %s
                  and status = 'active'
                  and id <> %s
                """,
                (
                    world_id,
                    story_arc_id,
                ),
            )

            cur.execute(
                """
                update public.v2_story_arcs
                set
                    status = 'active',
                    updated_at = now()
                where id = %s
                """,
                (story_arc_id,),
            )

        conn.commit()


def complete_story_arc(
    story_arc_id: int,
) -> None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.v2_story_arcs
                set
                    status = 'completed',
                    completed_at = now(),
                    updated_at = now()
                where id = %s
                """,
                (story_arc_id,),
            )

        conn.commit()


def link_unassigned_chapters_to_arc(
    world_id: int,
    story_arc_id: int,
) -> int:
    """
    현재 World 안에서 story_arc_id가 비어 있는 기존 Chapter만 연결한다.

    Arc와 World가 서로 다르면 아무 것도 수정하지 않고 예외를 발생시킨다.
    """
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select 1
                from public.v2_story_arcs
                where id = %s
                  and world_id = %s
                """,
                (
                    story_arc_id,
                    world_id,
                ),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "Story Arc가 해당 World에 속하지 않습니다."
                )

            cur.execute(
                """
                update public.v2_chapters
                set story_arc_id = %s
                where world_id = %s
                  and story_arc_id is null
                """,
                (
                    story_arc_id,
                    world_id,
                ),
            )
            updated_count = cur.rowcount

        conn.commit()

    return updated_count

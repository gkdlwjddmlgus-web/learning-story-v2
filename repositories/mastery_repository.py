from __future__ import annotations

from db import get_pool


def get_mastery_for_concept(
    user_id: int,
    world_id: int,
    concept: str,
):
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    mastery_score,
                    attempts,
                    correct_count,
                    last_result,
                    review_needed,
                    last_seen_at
                from public.v2_concept_mastery
                where user_id = %s
                  and world_id = %s
                  and concept = %s
                """,
                (
                    user_id,
                    world_id,
                    concept,
                ),
            )
            return cur.fetchone()


def get_mastery_profile(
    user_id: int,
    world_id: int,
) -> list[dict]:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    concept,
                    mastery_score,
                    attempts,
                    correct_count,
                    last_result,
                    review_needed,
                    last_seen_at
                from public.v2_concept_mastery
                where user_id = %s
                  and world_id = %s
                order by mastery_score asc, attempts desc
                """,
                (
                    user_id,
                    world_id,
                ),
            )
            rows = cur.fetchall()

    return [
        {
            "concept": row[0],
            "mastery_score": float(row[1]),
            "attempts": row[2],
            "correct_count": row[3],
            "last_result": row[4],
            "review_needed": row[5],
            "last_seen_at": row[6],
        }
        for row in rows
    ]


def upsert_mastery(
    *,
    user_id: int,
    world_id: int,
    concept: str,
    mastery_score: float,
    is_correct: bool,
    review_needed: bool,
) -> None:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_concept_mastery (
                    user_id,
                    world_id,
                    concept,
                    mastery_score,
                    attempts,
                    correct_count,
                    last_result,
                    review_needed,
                    last_seen_at
                )
                values (
                    %s,
                    %s,
                    %s,
                    %s,
                    1,
                    %s,
                    %s,
                    %s,
                    now()
                )
                on conflict (
                    user_id,
                    world_id,
                    concept
                )
                do update set
                    mastery_score = excluded.mastery_score,
                    attempts = public.v2_concept_mastery.attempts + 1,
                    correct_count = (
                        public.v2_concept_mastery.correct_count
                        + excluded.correct_count
                    ),
                    last_result = excluded.last_result,
                    review_needed = excluded.review_needed,
                    last_seen_at = now(),
                    updated_at = now()
                """,
                (
                    user_id,
                    world_id,
                    concept,
                    mastery_score,
                    1 if is_correct else 0,
                    is_correct,
                    review_needed,
                ),
            )

        conn.commit()

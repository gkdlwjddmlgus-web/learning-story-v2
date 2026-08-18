from db import get_pool


def create_attempt(
    user_id: int,
    world_id: int,
    chapter_id: int,
    concept: str,
    question_text: str,
    user_answer: str,
    is_correct: bool,
    attempt_type: str = "quest",
    difficulty: str | None = None,
    response_time_ms: int | None = None,
) -> int:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_question_attempts (
                    user_id,
                    world_id,
                    chapter_id,
                    concept,
                    question_text,
                    user_answer,
                    is_correct,
                    attempt_type,
                    difficulty,
                    response_time_ms
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    user_id,
                    world_id,
                    chapter_id,
                    concept,
                    question_text,
                    user_answer,
                    is_correct,
                    attempt_type,
                    difficulty,
                    response_time_ms,
                ),
            )

            attempt_id = cur.fetchone()[0]

        conn.commit()

    return attempt_id

def get_concept_stats(
    user_id: int,
    world_id: int,
):
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    concept,
                    count(*) as attempts,
                    sum(
                        case
                            when is_correct then 1
                            else 0
                        end
                    ) as correct_count,
                    avg(
                        case
                            when is_correct then 1.0
                            else 0.0
                        end
                    ) as accuracy
                from public.v2_question_attempts
                where user_id = %s
                  and world_id = %s
                  and concept is not null
                group by concept
                order by accuracy asc, attempts desc
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
            "attempts": row[1],
            "correct_count": row[2],
            "accuracy": float(row[3]),
        }
        for row in rows
    ]

def classify_concepts(
    user_id: int,
    world_id: int,
):
    stats = get_concept_stats(
        user_id=user_id,
        world_id=world_id,
    )

    result = []

    for stat in stats:
        attempts = stat["attempts"]
        accuracy = stat["accuracy"]

        if attempts >= 2 and accuracy <= 0.5:
            status = "weak"

        elif accuracy < 1.0:
            status = "review"

        else:
            status = "strong"

        result.append(
            {
                **stat,
                "status": status,
            }
        )

    return result

def get_concept_stats_for_chapter(
    user_id: int,
    world_id: int,
    chapter_id: int,
):
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    concept,
                    count(*) as attempts,
                    sum(
                        case
                            when is_correct then 1
                            else 0
                        end
                    ) as correct_count,
                    avg(
                        case
                            when is_correct then 1.0
                            else 0.0
                        end
                    ) as accuracy
                from public.v2_question_attempts
                where user_id = %s
                  and world_id = %s
                  and chapter_id = %s
                  and concept is not null
                group by concept
                order by accuracy asc, attempts desc
                """,
                (
                    user_id,
                    world_id,
                    chapter_id,
                ),
            )

            rows = cur.fetchall()

    return [
        {
            "concept": row[0],
            "attempts": row[1],
            "correct_count": row[2],
            "accuracy": float(row[3]),
        }
        for row in rows
    ]

def get_attempted_question_texts(
    user_id: int,
    world_id: int,
    chapter_id: int,
) -> set[str]:
    """
    특정 Chapter에서 사용자가 이미 제출한 문제 문구를 반환한다.

    같은 문제를 여러 번 제출한 과거 기록이 있더라도 DISTINCT로 한 번만
    취급하므로, 중복 풀이 기록 때문에 이어풀기 위치가 잘못 계산되는 것을
    줄일 수 있다.
    """
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select distinct question_text
                from public.v2_question_attempts
                where user_id = %s
                  and world_id = %s
                  and chapter_id = %s
                  and question_text is not null
                """,
                (
                    user_id,
                    world_id,
                    chapter_id,
                ),
            )

            rows = cur.fetchall()

    return {
        row[0]
        for row in rows
        if row[0]
    }

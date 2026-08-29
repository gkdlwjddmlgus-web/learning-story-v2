from db import get_pool


def get_world_count() -> int:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select count(*)
                from public.v2_learning_worlds
                """
            )
            row = cur.fetchone()

    return row[0]


def get_worlds_by_user(user_id: int):
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    id,
                    topic,
                    goal,
                    learner_level,
                    theme,
                    title,
                    world_summary,
                    current_chapter,
                    created_at,
                    guide_name
                from public.v2_learning_worlds
                where user_id = %s
                order by created_at asc
                """,
                (user_id,),
            )

            rows = cur.fetchall()

    return rows



def get_world_by_id_for_user(
    user_id: int,
    world_id: int,
):
    """
    특정 사용자가 소유한 월드만 조회한다.

    session_state.world_id가 다른 사용자의 월드 ID이거나
    존재하지 않는 ID여도 None을 반환하여 안전하게 fallback할 수 있다.
    """
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    id,
                    topic,
                    goal,
                    learner_level,
                    theme,
                    title,
                    world_summary,
                    current_chapter,
                    created_at,
                    guide_name
                from public.v2_learning_worlds
                where user_id = %s
                  and id = %s
                """,
                (
                    user_id,
                    world_id,
                ),
            )

            row = cur.fetchone()

    return row


def create_world(
    user_id: int,
    topic: str,
    goal: str,
    learner_level: str,
    theme: str,
    guide_name: str | None = None,
) -> int:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_learning_worlds (
                    user_id,
                    topic,
                    goal,
                    learner_level,
                    theme,
                    guide_name
                )
                values (%s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    user_id,
                    topic,
                    goal,
                    learner_level,
                    theme,
                    guide_name,
                ),
            )

            world_id = cur.fetchone()[0]

        conn.commit()

    return world_id


def update_guide_name(
    world_id: int,
    guide_name: str,
) -> None:
    cleaned_name = guide_name.strip()

    if not cleaned_name:
        raise ValueError("안내 고양이 이름은 비어 있을 수 없습니다.")

    if len(cleaned_name) > 20:
        raise ValueError("안내 고양이 이름은 20자 이내로 입력해주세요.")

    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.v2_learning_worlds
                set guide_name = %s
                where id = %s
                """,
                (cleaned_name, world_id),
            )

        conn.commit()


def update_current_chapter(
    world_id: int,
    chapter_number: int,
):
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.v2_learning_worlds
                set current_chapter = %s
                where id = %s
                """,
                (chapter_number, world_id),
            )

        conn.commit()

# DAY5_WORLD_INTRO_CINEMATIC_V1_REPOSITORY
def update_guide_name_for_world_intro(
    *,
    world_id: int,
    user_id: int,
    guide_name: str,
) -> None:
    """World Intro naming interaction에서 guide_name을 사용자 소유 월드에 저장한다."""
    clean_name = str(guide_name or "").strip()
    if not clean_name:
        raise ValueError("guide_name must not be empty")

    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update public.v2_learning_worlds
                set guide_name = %s
                where id = %s
                  and user_id = %s
                """,
                (
                    clean_name,
                    int(world_id),
                    int(user_id),
                ),
            )
            if cur.rowcount != 1:
                raise RuntimeError(
                    "동료 고양이 이름을 저장할 월드를 찾지 못했습니다."
                )
        conn.commit()

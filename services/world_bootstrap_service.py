from __future__ import annotations

from typing import Any

from db import get_pool


def create_learning_world_with_story_context(
    *,
    user_id: int,
    topic: str,
    goal: str,
    learner_level: str,
    theme: str,
    guide_name: str | None = None,
) -> dict[str, Any]:
    """
    새 학습 World + 첫 Story Arc + Story State를
    하나의 DB transaction으로 생성한다.

    중간 단계에서 실패하면 전체를 rollback하므로
    'World만 생기고 Story Context는 없는 상태'를 만들지 않는다.

    아직 Curriculum / Blueprint AI 생성은 하지 않는다.
    Story Arc는 빈 Blueprint를 가진 active 상태로 시작한다.
    """
    pool = get_pool()

    with pool.connection() as conn:
        try:
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
                    values (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
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

                cur.execute(
                    """
                    insert into public.v2_story_arcs (
                        world_id,
                        arc_number,
                        status,
                        current_phase,
                        blueprint
                    )
                    values (
                        %s,
                        1,
                        'active',
                        'setup',
                        '{}'::jsonb
                    )
                    returning id
                    """,
                    (world_id,),
                )

                story_arc_id = cur.fetchone()[0]

                cur.execute(
                    """
                    insert into public.v2_story_states (
                        story_arc_id
                    )
                    values (%s)
                    returning id
                    """,
                    (story_arc_id,),
                )

                story_state_id = cur.fetchone()[0]

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    return {
        "world_id": world_id,
        "story_arc_id": story_arc_id,
        "story_state_id": story_state_id,
    }

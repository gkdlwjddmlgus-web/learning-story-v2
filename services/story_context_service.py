from __future__ import annotations

from repositories.story_repository import (
    activate_story_arc,
    create_story_arc,
    get_active_story_arc,
    get_latest_story_arc,
    link_unassigned_chapters_to_arc,
)
from repositories.story_state_repository import (
    ensure_story_state,
    get_story_state,
)


def get_story_context(
    world_id: int,
) -> dict | None:
    """
    Story 화면의 읽기 Context.

    진행 중에는 active Arc를 사용한다.
    완결 직후에는 active가 없어지므로 가장 최근 completed Arc까지
    읽을 수 있게 fallback한다.
    """
    arc = get_active_story_arc(
        world_id
    )

    if arc is None:
        arc = get_latest_story_arc(
            world_id
        )

    if arc is None:
        return None

    state = get_story_state(
        arc["id"]
    )

    return {
        "arc": arc,
        "state": state,
    }


def ensure_story_context(
    world_id: int,
    *,
    link_existing_chapters: bool = False,
) -> dict:
    """
    생성용 Bootstrap Context.

    여기서는 반드시 active Arc만 대상으로 한다. active Arc가 없다면
    새로운 Arc를 만든다. 완결 Arc를 재활성화하지 않는다.
    """
    arc = get_active_story_arc(
        world_id
    )

    created_arc = False

    if arc is None:
        story_arc_id = create_story_arc(
            world_id=world_id,
            status="draft",
            current_phase="setup",
            blueprint={},
        )

        activate_story_arc(
            story_arc_id
        )

        arc = get_active_story_arc(
            world_id
        )
        created_arc = True

    state = ensure_story_state(
        arc["id"]
    )

    linked_chapter_count = 0

    if link_existing_chapters:
        linked_chapter_count = (
            link_unassigned_chapters_to_arc(
                world_id=world_id,
                story_arc_id=arc["id"],
            )
        )

    return {
        "arc": arc,
        "state": state,
        "created_arc": created_arc,
        "linked_chapter_count": linked_chapter_count,
    }

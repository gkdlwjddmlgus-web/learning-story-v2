from __future__ import annotations

import streamlit as st

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


# V3_STORY_CONTEXT_RUNTIME_CACHE_V1_20260908
_RUNTIME_CACHE_PREFIX = "_v3_story_context_runtime"


def _runtime_cache_key(
    world_id: int,
) -> str:
    return (
        f"{_RUNTIME_CACHE_PREFIX}:"
        f"{int(world_id)}"
    )


def get_runtime_story_context(
    world_id: int,
) -> dict | None:
    # Session-scoped Story Arc/state snapshot for ordinary UI reruns.
    key = _runtime_cache_key(
        world_id
    )

    if key not in st.session_state:
        st.session_state[key] = get_story_context(
            world_id
        )

    return st.session_state[key]


def invalidate_runtime_story_context(
    world_id: int,
) -> None:
    st.session_state.pop(
        _runtime_cache_key(world_id),
        None,
    )


def invalidate_runtime_story_context_all() -> None:
    prefix = f"{_RUNTIME_CACHE_PREFIX}:"

    for key in list(
        st.session_state.keys()
    ):
        if str(key).startswith(
            prefix
        ):
            del st.session_state[key]


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

    invalidate_runtime_story_context(world_id)

    return {
        "arc": arc,
        "state": state,
        "created_arc": created_arc,
        "linked_chapter_count": linked_chapter_count,
    }

from __future__ import annotations

import streamlit as st


PLAY_MODE_STORY = "story"
PLAY_MODE_REVIEW = "review"
PLAY_MODE_COMPANION = "companion"
PLAY_MODE_QUIZ = "quiz"

PLAY_MODES = (
    PLAY_MODE_STORY,
    PLAY_MODE_REVIEW,
    PLAY_MODE_COMPANION,
    PLAY_MODE_QUIZ,
)

_KEY_PREFIX = "_v3_play_mode"


def get_play_mode_key(
    *,
    world_id: int,
    chapter_id: int,
) -> str:
    return (
        f"{_KEY_PREFIX}:"
        f"{int(world_id)}:"
        f"{int(chapter_id)}"
    )


def _normalize_mode(
    mode: str | None,
) -> str | None:
    value = str(
        mode or ""
    ).strip().lower()

    if value in PLAY_MODES:
        return value

    return None


def set_play_mode(
    *,
    world_id: int,
    chapter_id: int,
    mode: str,
) -> str:
    normalized = _normalize_mode(
        mode
    )
    if normalized is None:
        raise ValueError(
            "Unsupported play mode: "
            + str(mode)
        )

    st.session_state[
        get_play_mode_key(
            world_id=world_id,
            chapter_id=chapter_id,
        )
    ] = normalized

    return normalized


def resolve_play_mode(
    *,
    world_id: int,
    chapter_id: int,
    story_pending: bool,
) -> str:
    # Resolve one session-local play mode without DB/AI work.
    # Pending Story always owns the screen.
    # Once Story is seen, stale story mode advances to quiz.
    # review/companion/quiz persist for the same World/Chapter.
    key = get_play_mode_key(
        world_id=world_id,
        chapter_id=chapter_id,
    )
    current = _normalize_mode(
        st.session_state.get(
            key
        )
    )

    if story_pending:
        if current != PLAY_MODE_STORY:
            st.session_state[
                key
            ] = PLAY_MODE_STORY
        return PLAY_MODE_STORY

    if (
        current is None
        or current == PLAY_MODE_STORY
    ):
        st.session_state[
            key
        ] = PLAY_MODE_QUIZ
        return PLAY_MODE_QUIZ

    return current


def clear_play_mode(
    *,
    world_id: int,
    chapter_id: int,
) -> None:
    st.session_state.pop(
        get_play_mode_key(
            world_id=world_id,
            chapter_id=chapter_id,
        ),
        None,
    )


def clear_world_play_modes(
    world_id: int,
) -> None:
    prefix = (
        f"{_KEY_PREFIX}:"
        f"{int(world_id)}:"
    )

    for key in list(
        st.session_state.keys()
    ):
        if str(key).startswith(
            prefix
        ):
            del st.session_state[
                key
            ]

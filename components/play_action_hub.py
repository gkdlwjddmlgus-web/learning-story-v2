from __future__ import annotations

import streamlit as st

from services.play_runtime_service import (
    PLAY_MODE_COMPANION,
    PLAY_MODE_QUIZ,
    PLAY_MODE_REVIEW,
    set_play_mode,
)


# V3_ACTION_HUB_V1_20260908
_ACTION_MODES = (
    PLAY_MODE_REVIEW,
    PLAY_MODE_COMPANION,
    PLAY_MODE_QUIZ,
)


def render_play_action_hub(
    *,
    world_id: int,
    chapter_id: int,
    active_mode: str,
    guide_name: str | None = None,
) -> None:
    """Render the local-only V3 play-mode switcher.

    The click handler changes only session-local play mode.
    It performs no repository access and starts no generation work.
    """
    if active_mode not in _ACTION_MODES:
        return

    resolved_guide = (
        str(guide_name or "").strip()
        or "동료"
    )
    labels = {
        PLAY_MODE_REVIEW: "📖 스토리 다시보기",
        PLAY_MODE_COMPANION: f"🐈 {resolved_guide}",
        PLAY_MODE_QUIZ: "✦ 문제 풀기",
    }

    st.caption(
        "원하는 학습 화면으로 바로 전환할 수 있습니다."
    )
    columns = st.columns(
        len(_ACTION_MODES),
        gap="small",
    )

    for column, mode in zip(
        columns,
        _ACTION_MODES,
    ):
        with column:
            clicked = st.button(
                labels[mode],
                key=(
                    f"v3_action_hub_"
                    f"{int(world_id)}_"
                    f"{int(chapter_id)}_"
                    f"{mode}"
                ),
                type=(
                    "primary"
                    if mode == active_mode
                    else "secondary"
                ),
                use_container_width=True,
            )

            if (
                clicked
                and mode != active_mode
            ):
                set_play_mode(
                    world_id=world_id,
                    chapter_id=chapter_id,
                    mode=mode,
                )
                st.rerun()

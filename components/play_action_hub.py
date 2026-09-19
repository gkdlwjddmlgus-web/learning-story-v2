from __future__ import annotations

import streamlit as st

from services.play_runtime_service import (
    PLAY_MODE_COMPANION,
    PLAY_MODE_NOTE,
    PLAY_MODE_QUIZ,
    PLAY_MODE_REVIEW,
    set_play_mode,
)


# V3_ACTION_HUB_V1_20260908
# V3_FULL_EXPECTED_PLAY_UI_V1_20260908
_ACTION_MODES = (
    PLAY_MODE_REVIEW,
    PLAY_MODE_COMPANION,
    PLAY_MODE_QUIZ,
    PLAY_MODE_NOTE,
)


def _dock_label(
    *,
    theme: str | None,
    mode: str,
    guide_name: str,
) -> str:
    labels = {
        PLAY_MODE_REVIEW: "📜\n기록",
        PLAY_MODE_COMPANION: "💬\n대화",
        PLAY_MODE_QUIZ: "🔎\n문제",
        PLAY_MODE_NOTE: "📜\n노트",
    }
    return labels[mode]


def render_play_action_hub(
    *,
    world_id: int,
    chapter_id: int,
    active_mode: str,
    guide_name: str | None = None,
    theme: str | None = None,
    learning_objectives: list[str] | tuple[str, ...] | None = None,
    target_concepts: list[str] | tuple[str, ...] | None = None,
) -> None:
    """Game-style local-only play dock. No repository/generation work."""
    if active_mode not in _ACTION_MODES:
        return

    resolved_guide = str(guide_name or "").strip() or "동료"
    labels = {
        mode: _dock_label(
            theme=theme,
            mode=mode,
            guide_name=resolved_guide,
        )
        for mode in _ACTION_MODES
    }

    columns = st.columns(4, gap="small")

    for column, mode in zip(columns, _ACTION_MODES):
        with column:
            clicked = st.button(
                labels[mode],
                key=(
                    f"v3_action_hub_{int(world_id)}_"
                    f"{int(chapter_id)}_{mode}"
                ),
                type=(
                    "primary"
                    if mode == active_mode
                    else "secondary"
                ),
                width="stretch",
                help={
                    PLAY_MODE_REVIEW: "사건 기록과 스토리 다시보기",
                    PLAY_MODE_COMPANION: f"{resolved_guide}와 대화",
                    PLAY_MODE_QUIZ: "단서를 해석하고 문제 풀기",
                    PLAY_MODE_NOTE: "학습 노트 열기",
                }[mode],
            )
            if clicked and mode != active_mode:
                set_play_mode(
                    world_id=world_id,
                    chapter_id=chapter_id,
                    mode=mode,
                )
                st.rerun()

from __future__ import annotations

import streamlit as st

from services.play_runtime_service import (
    PLAY_MODE_COMPANION,
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
)


_THEME_LABELS = {
    "동화": {
        PLAY_MODE_REVIEW: ("📖", "이야기를 다시 읽는다", "스토리 다시보기"),
        PLAY_MODE_COMPANION: ("💬", "{guide}와 이야기한다", "동료의 도움"),
        PLAY_MODE_QUIZ: ("🔎", "단서를 맞춰본다", "문제 풀기"),
    },
    "판타지": {
        PLAY_MODE_REVIEW: ("📜", "기록의 두루마리를 펼친다", "스토리 다시보기"),
        PLAY_MODE_COMPANION: ("💬", "{guide}와 상의한다", "동료의 도움"),
        PLAY_MODE_QUIZ: ("🔎", "실마리를 해석한다", "문제 풀기"),
    },
    "SF": {
        PLAY_MODE_REVIEW: ("🗂️", "로그를 다시 불러온다", "스토리 다시보기"),
        PLAY_MODE_COMPANION: ("💬", "{guide}와 분석한다", "동료의 도움"),
        PLAY_MODE_QUIZ: ("🛰️", "신호를 해독한다", "문제 풀기"),
    },
    "무협": {
        PLAY_MODE_REVIEW: ("📜", "지난 기록을 펼친다", "스토리 다시보기"),
        PLAY_MODE_COMPANION: ("💬", "{guide}와 논한다", "동료의 도움"),
        PLAY_MODE_QUIZ: ("🧭", "흔적을 짚어낸다", "문제 풀기"),
    },
    "미스터리": {
        PLAY_MODE_REVIEW: ("📜", "기록의 두루마리를 펼친다", "스토리 다시보기"),
        PLAY_MODE_COMPANION: ("💬", "{guide}와 상의한다", "동료의 도움"),
        PLAY_MODE_QUIZ: ("🔎", "실마리를 해석한다", "문제 풀기"),
    },
}


def _dock_label(
    *,
    theme: str | None,
    mode: str,
    guide_name: str,
) -> str:
    mapping = _THEME_LABELS.get(
        str(theme or ""),
        _THEME_LABELS["미스터리"],
    )
    icon, title, subtitle = mapping[mode]
    title = title.format(guide=guide_name)
    return f"{icon}  {title}\n({subtitle})"


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

    objectives = [
        str(item).strip()
        for item in (learning_objectives or [])
        if str(item).strip()
    ]
    concepts = [
        str(item).strip()
        for item in (target_concepts or [])
        if str(item).strip()
    ]

    columns = st.columns(4, gap="small")

    for column, mode in zip(columns[:3], _ACTION_MODES):
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
                use_container_width=True,
            )
            if clicked and mode != active_mode:
                set_play_mode(
                    world_id=world_id,
                    chapter_id=chapter_id,
                    mode=mode,
                )
                st.rerun()

    with columns[3]:
        if hasattr(st, "popover"):
            with st.popover(
                "📝 학습 노트",
                use_container_width=True,
            ):
                st.markdown("**이번 Chapter의 학습 노트**")
                if concepts:
                    st.caption(
                        "핵심 Concept · "
                        + ", ".join(concepts)
                    )
                if objectives:
                    for objective in objectives:
                        st.markdown(f"- {objective}")
                elif not concepts:
                    st.caption(
                        "현재 Chapter에 별도로 저장된 학습 목표가 없습니다."
                    )
        else:
            note_key = (
                f"v3_action_note_{int(world_id)}_{int(chapter_id)}"
            )
            if st.button(
                "📝 학습 노트",
                key=(
                    f"v3_action_hub_{int(world_id)}_"
                    f"{int(chapter_id)}_note"
                ),
                use_container_width=True,
            ):
                st.session_state[note_key] = not bool(
                    st.session_state.get(note_key, False)
                )
            if st.session_state.get(note_key, False):
                with st.container(border=True):
                    if concepts:
                        st.caption(
                            "핵심 Concept · "
                            + ", ".join(concepts)
                        )
                    for objective in objectives:
                        st.markdown(f"- {objective}")

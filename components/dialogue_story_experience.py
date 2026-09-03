from __future__ import annotations

import streamlit as st

from components.dialogue_scene import render_dialogue_scene
from services.dialogue_asset_service import (
    resolve_background,
    resolve_portrait,
)
from services.dialogue_runtime_service import (
    build_dialogue_beats,
    dialogue_index_key,
    mark_dialogue_story_seen,
)


# DAY6_DIALOGUE_STORY_EXPERIENCE_V1


def _scene_context(
    *,
    chapter_number: int | None,
    chapter_title: str | None,
) -> str:
    parts = []

    if chapter_number is not None:
        parts.append(f"CHAPTER {int(chapter_number)}")

    title = str(chapter_title or "").strip()
    if title:
        parts.append(title)

    return " · ".join(parts)


def render_dialogue_story_experience(
    *,
    chapter_id: int,
    theme: str,
    story_text: str,
    chapter_number: int | None = None,
    chapter_title: str | None = None,
    guide_name: str | None = None,
) -> bool:
    """
    Existing Chapter Story를 Dialogue Scene UI로 재생한다.

    True:
        Dialogue Scene이 현재 dedicated Story 화면을 소유 중.
    False:
        재생할 Story가 없어 즉시 종료.
    """
    beats = build_dialogue_beats(
        story_text=story_text,
        guide_name=guide_name,
    )

    if not beats:
        mark_dialogue_story_seen(chapter_id)
        return False

    index_key = dialogue_index_key(chapter_id)

    if index_key not in st.session_state:
        st.session_state[index_key] = 0

    current_index = max(
        0,
        min(
            int(st.session_state[index_key]),
            len(beats) - 1,
        ),
    )

    beat = beats[current_index]

    portrait_path = resolve_portrait(
        theme,
        beat.speaker_type,
        character_id="default",
    )

    background_path = resolve_background(
        theme,
        scene_id="default",
    )

    skip_col, progress_col = st.columns([1, 5])

    with skip_col:
        if st.button(
            "건너뛰기 →",
            key=f"dialogue_runtime_v1_skip_{chapter_id}",
            type="secondary",
            use_container_width=True,
        ):
            mark_dialogue_story_seen(chapter_id)
            st.rerun()

    with progress_col:
        st.caption(
            f"STORY SCENE · {current_index + 1} / {len(beats)}"
        )

    is_last = current_index == len(beats) - 1

    clicked = render_dialogue_scene(
        theme=theme,
        speaker_type=beat.speaker_type,
        speaker_name=beat.speaker_name,
        text=beat.text,
        portrait_path=portrait_path,
        background_path=background_path,
        context_label=_scene_context(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
        ),
        key=f"dialogue_runtime_v1_next_{chapter_id}_{current_index}",
        next_label=(
            "이야기를 이어간다"
            if is_last
            else "다음 대화 →"
        ),
        show_next_button=True,
        show_scene_chrome=True,
    )

    if clicked:
        if is_last:
            mark_dialogue_story_seen(chapter_id)
        else:
            st.session_state[index_key] = current_index + 1

        st.rerun()

    return True

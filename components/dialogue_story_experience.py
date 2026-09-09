from __future__ import annotations

import re

import time

import streamlit as st

from components.dialogue_scene import render_dialogue_scene
from services.dialogue_asset_service import (
    resolve_portrait,
)
from services.story_background_service import (
    resolve_story_background,
)
from services.dialogue_runtime_service import (
    build_dialogue_beats,
    dialogue_index_key,
    mark_dialogue_story_seen,
)


# DAY6_DIALOGUE_STORY_EXPERIENCE_V1
# STORY_SCENE_NAVIGATION_SPEAKER_INTEGRITY_V1_2_20260908
# V3_STORY_AGENCY_STAGE_V1_20260908


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


# CINEMATIC_STORY_AUTO_LAYOUT_V2_1_20260906

_AUTO_TICK_SECONDS = 0.5
_AUTO_MIN_SECONDS = 4.0
_AUTO_MAX_SECONDS = 11.5


def _auto_enabled_key(chapter_id: int) -> str:
    return f"_cinematic_auto_v2_1_enabled_{int(chapter_id)}"


def _auto_scene_key(chapter_id: int) -> str:
    return f"_cinematic_auto_v2_1_scene_{int(chapter_id)}"


def _auto_started_key(chapter_id: int) -> str:
    return f"_cinematic_auto_v2_1_started_{int(chapter_id)}"


def _clear_auto_scene_state(chapter_id: int) -> None:
    for key in (
        _auto_scene_key(chapter_id),
        _auto_started_key(chapter_id),
    ):
        st.session_state.pop(key, None)


def _scene_duration_seconds(
    *,
    text: str,
    speaker_type: str,
) -> float:
    """
    Korean story text length + sentence pauses 기반 체류시간.

    짧은 대사: 약 4초
    중간 길이: 약 5~8초
    긴 narration: 최대 약 11.5초
    """
    clean = re.sub(
        r"\s+",
        " ",
        str(text or "").strip(),
    )
    char_count = len(clean)
    punctuation_count = len(
        re.findall(
            r"[.!?。！？]",
            clean,
        )
    )

    duration = (
        2.2
        + char_count * 0.055
        + min(1.2, punctuation_count * 0.25)
    )

    role = str(speaker_type or "").strip().lower()
    if role == "narrator":
        duration += 0.8
    elif role in {"companion", "npc"}:
        duration += 0.2

    return round(
        max(
            _AUTO_MIN_SECONDS,
            min(_AUTO_MAX_SECONDS, duration),
        ),
        2,
    )


def _story_runtime_layout_css() -> str:
    return """
    <style>
    div[data-testid="stAppViewContainer"]
    .block-container:has(.dialogue-story-runtime-anchor) {
        padding-top: 1.75rem !important;
        padding-bottom: 1rem !important;
    }

    div[data-testid="stVerticalBlock"]:has(
        .dialogue-story-runtime-anchor
    ) {
        gap: .38rem !important;
    }

    div[data-testid="stElementContainer"]:has(
        .dialogue-story-runtime-anchor
    ) {
        min-height: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    .dialogue-story-runtime-anchor {
        display: none;
    }

    .dialogue-story-control-spacer {
        height: .72rem;
    }

    .dialogue-story-progress-shell {
        width: min(100%, 1120px);
        margin: .22rem auto .08rem;
        padding: 0 .12rem;
        box-sizing: border-box;
    }

    .dialogue-story-progress-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: .7rem;
        margin-bottom: .22rem;
        color: rgba(74, 65, 57, .72);
        font-size: .72rem;
        line-height: 1.3;
    }

    .dialogue-story-progress-track {
        position: relative;
        height: 4px;
        overflow: hidden;
        border-radius: 999px;
        background: rgba(90, 75, 62, .13);
    }

    .dialogue-story-progress-fill {
        height: 100%;
        border-radius: inherit;
        background:
            linear-gradient(
                90deg,
                rgba(159,58,50,.74),
                rgba(202,165,93,.82)
            );
        transition: width .46s linear;
    }

    @media (max-width: 768px) {
        div[data-testid="stAppViewContainer"]
        .block-container:has(.dialogue-story-runtime-anchor) {
            padding-top: 1.15rem !important;
        }

        .dialogue-story-control-spacer {
            height: .48rem;
        }

        .dialogue-story-progress-meta {
            font-size: .68rem;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .dialogue-story-progress-fill {
            transition: none !important;
        }
    }
    </style>
    <div class="dialogue-story-runtime-anchor"></div>
    """


def _auto_progress_html(
    *,
    progress: float,
    duration_seconds: float,
    auto_enabled: bool,
) -> str:
    safe_progress = max(
        0.0,
        min(1.0, float(progress)),
    )
    percent = int(round(safe_progress * 100))

    if auto_enabled:
        left = max(
            0.0,
            float(duration_seconds)
            * (1.0 - safe_progress),
        )
        status = f"자동 진행 · 약 {left:.1f}초"
    else:
        status = "자동 진행 일시정지"

    return (
        '<div class="dialogue-story-progress-shell">'
        '<div class="dialogue-story-progress-meta">'
        f'<span>{status}</span>'
        f'<span>{percent}%</span>'
        '</div>'
        '<div class="dialogue-story-progress-track">'
        '<div class="dialogue-story-progress-fill" '
        f'style="width:{percent}%"></div>'
        '</div>'
        '</div>'
    )


def _auto_advance_tick_body(
    *,
    chapter_id: int,
    current_index: int,
    beat_count: int,
    duration_seconds: float,
    index_key: str,
    auto_enabled: bool,
) -> None:
    if not auto_enabled:
        st.markdown(
            _auto_progress_html(
                progress=0.0,
                duration_seconds=duration_seconds,
                auto_enabled=False,
            ),
            unsafe_allow_html=True,
        )
        return

    # 이미 manual click/rerun 등으로 Scene이 바뀌었으면
    # 오래된 fragment tick은 상태를 건드리지 않는다.
    live_index = st.session_state.get(
        index_key,
        current_index,
    )
    if int(live_index) != int(current_index):
        return

    scene_token = f"{int(chapter_id)}:{int(current_index)}"
    scene_key = _auto_scene_key(chapter_id)
    started_key = _auto_started_key(chapter_id)

    if (
        st.session_state.get(scene_key)
        != scene_token
        or started_key not in st.session_state
    ):
        st.session_state[scene_key] = scene_token
        st.session_state[started_key] = time.monotonic()

    started = float(
        st.session_state.get(
            started_key,
            time.monotonic(),
        )
    )
    elapsed = max(
        0.0,
        time.monotonic() - started,
    )
    progress = min(
        1.0,
        elapsed / max(0.1, float(duration_seconds)),
    )

    st.markdown(
        _auto_progress_html(
            progress=progress,
            duration_seconds=duration_seconds,
            auto_enabled=True,
        ),
        unsafe_allow_html=True,
    )

    if progress < 1.0:
        return

    # deadline 직전에 수동 조작이 있었는지 한 번 더 확인한다.
    live_index = st.session_state.get(
        index_key,
        current_index,
    )
    if int(live_index) != int(current_index):
        return

    is_last = (
        int(current_index)
        >= int(beat_count) - 1
    )

    _clear_auto_scene_state(chapter_id)

    if is_last:
        mark_dialogue_story_seen(chapter_id)
    else:
        st.session_state[index_key] = int(current_index) + 1

    st.rerun()


if hasattr(st, "fragment"):
    _render_auto_advance_tick = st.fragment(
        run_every=_AUTO_TICK_SECONDS,
    )(_auto_advance_tick_body)
else:
    def _render_auto_advance_tick(**kwargs) -> None:
        st.caption(
            "현재 Streamlit 버전에서는 자동 진행 timer를 "
            "사용할 수 없어 수동 진행으로 유지됩니다."
        )

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
    Existing Chapter Story를 cinematic Dialogue Scene UI로 재생한다.

    - Alpha 기본값은 수동 진행이며 사용자가 원할 때 자동 진행을 켠다.
    - 텍스트 길이에 따라 Scene 체류시간을 계산한다.
    - 수동 다음/건너뛰기는 계속 유지한다.
    - 마지막 Scene이 끝나면 Story seen 처리 후 기존 Story Choice로 넘긴다.
    """
    beats = build_dialogue_beats(
        story_text=story_text,
        guide_name=guide_name,
    )

    if not beats:
        _clear_auto_scene_state(chapter_id)
        mark_dialogue_story_seen(chapter_id)
        return False

    st.markdown(
        _story_runtime_layout_css(),
        unsafe_allow_html=True,
    )

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
    companion_portrait_path = resolve_portrait(
        theme,
        "companion",
        character_id="default",
    )

    # V3_STORY_AGENCY_STAGE_V1_20260908
    # Narration does not become Companion speech. The companion remains in
    # the same left stage slot at low opacity; only Companion beats restore
    # full opacity. Player is never inferred from ordinary Story text.

    background_path = resolve_story_background(
        theme=theme,
        beat_texts=[
            item.text
            for item in beats
        ],
        current_index=current_index,
        chapter_id=chapter_id,
        chapter_title=chapter_title,
    )

    auto_key = _auto_enabled_key(chapter_id)

    st.markdown(
        '<div class="dialogue-story-control-spacer"></div>',
        unsafe_allow_html=True,
    )

    is_last = current_index == len(beats) - 1
    next_label = (
        "이야기를 이어간다"
        if is_last
        else "다음 →"
    )

    (
        control_skip,
        control_prev,
        control_mid,
        control_next,
        control_auto,
    ) = st.columns(
        [1.12, 0.92, 2.45, 0.92, 1.35],
        vertical_alignment="center",
    )

    with control_skip:
        if st.button(
            "건너뛰기 →",
            key=f"dialogue_runtime_v1_skip_{chapter_id}",
            type="secondary",
            use_container_width=True,
        ):
            _clear_auto_scene_state(chapter_id)
            mark_dialogue_story_seen(chapter_id)
            st.rerun()

    with control_prev:
        if st.button(
            "← 이전",
            key=f"dialogue_runtime_v1_prev_{chapter_id}_{current_index}",
            type="secondary",
            use_container_width=True,
            disabled=(current_index <= 0),
        ):
            _clear_auto_scene_state(chapter_id)
            st.session_state[index_key] = max(0, current_index - 1)
            st.rerun()

    with control_mid:
        st.caption(
            f"STORY SCENE · {current_index + 1} / {len(beats)}"
        )

    with control_next:
        if st.button(
            next_label,
            key=f"dialogue_runtime_v1_next_{chapter_id}_{current_index}",
            type="secondary",
            use_container_width=True,
        ):
            _clear_auto_scene_state(chapter_id)

            if is_last:
                mark_dialogue_story_seen(chapter_id)
            else:
                st.session_state[index_key] = current_index + 1

            st.rerun()

    with control_auto:
        auto_enabled = st.toggle(
            "자동 진행",
            # The browser must paint Scene 1 before any wall-clock timer can
            # advance it. Autoplay remains available as an explicit opt-in.
            value=False,
            key=auto_key,
            help=(
                "장면 길이에 맞춰 자동으로 다음 Scene으로 넘어갑니다. "
                "수동 이전/다음 버튼은 자동 진행 중에도 사용할 수 있습니다."
            ),
        )

    if not auto_enabled:
        _clear_auto_scene_state(chapter_id)

    # Story runtime에서는 버튼을 scene renderer 밖으로 빼서
    # timer progress를 Scene과 수동 진행 사이에 배치한다.
    render_dialogue_scene(
        theme=theme,
        speaker_type=beat.speaker_type,
        speaker_name=beat.speaker_name,
        text=beat.text,
        portrait_path=portrait_path,
        companion_portrait_path=companion_portrait_path,
        background_path=background_path,
        context_label=_scene_context(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
        ),
        key=None,
        next_label=None,
        show_next_button=False,
        show_scene_chrome=True,
    )

    duration_seconds = _scene_duration_seconds(
        text=beat.text,
        speaker_type=beat.speaker_type,
    )

    _render_auto_advance_tick(
        chapter_id=chapter_id,
        current_index=current_index,
        beat_count=len(beats),
        duration_seconds=duration_seconds,
        index_key=index_key,
        auto_enabled=bool(auto_enabled),
    )

    # Manual navigation is intentionally kept in the top control row.
    # The cinematic stage can exceed the viewport height, so placing the only
    # Next button below the Scene makes manual control appear to disappear.

    return True


# STORY_BACKGROUND_SYSTEM_V1_20260906

# CINEMATIC_STORY_AUTO_LAYOUT_V2_1_1_IMPORT_HOTFIX_20260906

# CINEMATIC_STORY_LAYOUT_TOP_SAFE_AREA_V2_1_2_20260906

# CINEMATIC_STORY_CONTROL_ROW_SPACING_V2_1_3_20260906

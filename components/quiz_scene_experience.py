from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path

import streamlit as st

from components.dialogue_scene import render_dialogue_scene
from services.dialogue_asset_service import (
    resolve_background,
    resolve_portrait,
)


# DAY6_QUIZ_SCENE_EXPERIENCE_V2

_THEME_STYLE = {
    "동화": {
        "accent": "#df7191",
        "text": "#4d2834",
        "muted": "#8d6571",
        "surface": "rgba(255,250,249,.95)",
        "border": "rgba(223,113,145,.34)",
        "veil": "rgba(255,248,248,.72)",
        "shadow": "rgba(125,82,94,.12)",
    },
    "판타지": {
        "accent": "#aa9bc8",
        "text": "#f0ebf4",
        "muted": "#c8bfd1",
        "surface": "rgba(30,28,38,.94)",
        "border": "rgba(170,155,200,.38)",
        "veil": "rgba(20,18,28,.64)",
        "shadow": "rgba(17,13,24,.28)",
    },
    "SF": {
        "accent": "#83b7c0",
        "text": "#edf8fa",
        "muted": "#b7d0d4",
        "surface": "rgba(8,28,37,.94)",
        "border": "rgba(131,183,192,.40)",
        "veil": "rgba(4,21,28,.62)",
        "shadow": "rgba(2,16,21,.30)",
    },
    "무협": {
        "accent": "#9c3f35",
        "text": "#493b30",
        "muted": "#826c57",
        "surface": "rgba(248,240,221,.95)",
        "border": "rgba(156,63,53,.32)",
        "veil": "rgba(244,232,207,.70)",
        "shadow": "rgba(96,69,42,.14)",
    },
    "미스터리": {
        "accent": "#d1ad70",
        "text": "#f4eee4",
        "muted": "#d2c2ac",
        "surface": "rgba(35,31,30,.95)",
        "border": "rgba(209,173,112,.36)",
        "veil": "rgba(22,19,18,.64)",
        "shadow": "rgba(12,10,9,.28)",
    },
}


def _normalize_theme(theme: str) -> str:
    return theme if theme in _THEME_STYLE else "동화"


def _data_uri(path: str | Path | None) -> str | None:
    if not path:
        return None

    file_path = Path(path)
    if not file_path.is_file():
        return None

    mime_type, _ = mimetypes.guess_type(file_path.name)
    mime_type = mime_type or "image/png"
    encoded = base64.b64encode(
        file_path.read_bytes()
    ).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _question_scene_css(theme: str) -> str:
    style = _THEME_STYLE[_normalize_theme(theme)]

    return f"""
    <style>
    div[data-testid="stElementContainer"]:has(
        .day6-quiz-question-scene
    ) {{
        position: sticky !important;
        top: calc(
            3.85rem
            + var(--day6-evidence-stack-offset, 0rem)
        ) !important;
        z-index: 700 !important;
    }}

    .day6-quiz-question-scene {{
        --qs-accent:{style["accent"]};
        --qs-text:{style["text"]};
        --qs-muted:{style["muted"]};
        --qs-surface:{style["surface"]};
        --qs-border:{style["border"]};
        --qs-veil:{style["veil"]};
        --qs-shadow:{style["shadow"]};

        position: relative;
        isolation: isolate;
        overflow: hidden;
        width: min(100%, 1120px);
        min-height: 158px;
        margin: .02rem auto .62rem;
        padding: .76rem .98rem .82rem;
        box-sizing: border-box;
        border: 1px solid var(--qs-border);
        border-radius: 17px;
        background: var(--qs-surface);
        box-shadow: 0 9px 25px var(--qs-shadow);
        color: var(--qs-text);
    }}

    .day6-quiz-question-scene::after {{
        content: "";
        position: absolute;
        inset: 0;
        z-index: -1;
        background: var(--qs-veil);
        pointer-events: none;
    }}

    .day6-quiz-question-bg {{
        position: absolute;
        inset: 0;
        z-index: -2;
        background-position: center;
        background-repeat: no-repeat;
        background-size: cover;
        opacity: .32;
        filter: saturate(.86);
    }}

    .day6-quiz-question-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: .72rem;
        margin-bottom: .50rem;
    }}

    .day6-quiz-question-kicker {{
        color: var(--qs-accent);
        font-size: .74rem;
        line-height: 1.28;
        font-weight: 900;
        letter-spacing: .12em;
    }}

    .day6-quiz-question-context {{
        color: var(--qs-muted);
        font-size: .72rem;
        line-height: 1.30;
        font-weight: 700;
        text-align: right;
    }}

    .day6-quiz-question-body {{
        display: flex;
        align-items: center;
        min-height: 86px;
        padding: .66rem .78rem;
        box-sizing: border-box;
        border: 1px solid var(--qs-border);
        border-radius: 13px;
        background: var(--qs-surface);
    }}

    .day6-quiz-question-text {{
        margin: 0;
        color: var(--qs-text);
        font-size: clamp(1.18rem, 1.54vw, 1.50rem);
        line-height: 1.42;
        font-weight: 820;
        letter-spacing: -.016em;
        text-align: left;
        word-break: keep-all;
        overflow-wrap: break-word;
        line-break: strict;
        text-wrap: pretty;
    }}

    @media (max-width: 760px) {{
        div[data-testid="stElementContainer"]:has(
            .day6-quiz-question-scene
        ) {{
            top: calc(
                3.45rem
                + var(--day6-evidence-stack-offset-mobile, 0rem)
            ) !important;
        }}

        .day6-quiz-question-scene {{
            min-height: 124px;
            margin-top: .02rem;
            margin-bottom: .50rem;
            padding: .58rem;
            border-radius: 13px;
        }}

        .day6-quiz-question-top {{
            margin-bottom: .36rem;
        }}

        .day6-quiz-question-context {{
            display: none;
        }}

        .day6-quiz-question-body {{
            min-height: 66px;
            padding: .54rem .60rem;
            border-radius: 11px;
        }}

        .day6-quiz-question-text {{
            font-size: clamp(1.00rem, 4.6vw, 1.20rem);
            line-height: 1.42;
        }}
    }}
    </style>
    """





def _feedback_index_key(
    chapter_id: int,
    question_index: int,
) -> str:
    return (
        "_day6_quiz_scene_feedback_index_"
        f"{int(chapter_id)}_{int(question_index)}"
    )


def _feedback_done_key(
    chapter_id: int,
    question_index: int,
) -> str:
    return (
        "_day6_quiz_scene_feedback_done_"
        f"{int(chapter_id)}_{int(question_index)}"
    )


def render_quiz_question_scene(
    *,
    theme: str,
    chapter_number: int | None,
    chapter_title: str | None,
    question_number: int,
    question_count: int,
    question_text: str,
) -> None:
    """
    Evidence 아래에 이어지는 sticky Question Scene.
    Full Evidence 자체가 별도 sticky이므로 compact evidence summary는 중복 표시하지 않는다.
    """
    normalized_theme = _normalize_theme(theme)

    background_path = resolve_background(
        normalized_theme,
        scene_id="default",
    )
    background_uri = _data_uri(
        background_path
    )

    safe_question = html.escape(
        str(question_text or "").strip()
        or "문제를 확인해주세요."
    )

    title = str(chapter_title or "").strip()
    context_bits = []

    if chapter_number is not None:
        context_bits.append(
            f"CHAPTER {int(chapter_number)}"
        )

    if title:
        context_bits.append(title)

    context_bits.append(
        f"Q {int(question_number)} / {int(question_count)}"
    )

    safe_context = html.escape(
        " · ".join(context_bits)
    )

    background_html = (
        '<div class="day6-quiz-question-bg" '
        f'style="background-image:url(\'{background_uri}\');">'
        "</div>"
        if background_uri
        else '<div class="day6-quiz-question-bg"></div>'
    )

    st.markdown(
        _question_scene_css(
            normalized_theme
        )
        + (
            '<section class="day6-quiz-question-scene">'
            f"{background_html}"
            '<div class="day6-quiz-question-top">'
            '<div class="day6-quiz-question-kicker">'
            "QUESTION SCENE"
            "</div>"
            '<div class="day6-quiz-question-context">'
            f"{safe_context}"
            "</div>"
            "</div>"
            '<div class="day6-quiz-question-body">'
            '<div class="day6-quiz-question-text">'
            f"{safe_question}"
            "</div>"
            "</div>"
            "</section>"
        ),
        unsafe_allow_html=True,
    )




def render_quiz_feedback_dialogue(
    *,
    chapter_id: int,
    question_index: int,
    theme: str,
    chapter_number: int | None,
    question_number: int,
    user_name: str,
    user_answer_text: str,
    guide_name: str,
    feedback: str,
    is_correct: bool,
) -> bool:
    index_key = _feedback_index_key(
        chapter_id,
        question_index,
    )
    done_key = _feedback_done_key(
        chapter_id,
        question_index,
    )

    if st.session_state.get(
        done_key,
        False,
    ):
        return False

    if index_key not in st.session_state:
        st.session_state[index_key] = 0

    beats = [
        {
            "speaker_type": "player",
            "speaker_name": str(
                user_name or "나"
            ),
            "text": str(
                user_answer_text or ""
            ).strip(),
        },
        {
            "speaker_type": "companion",
            "speaker_name": str(
                guide_name or "고양이"
            ),
            "text": str(
                feedback or ""
            ).strip(),
        },
    ]

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
        beat["speaker_type"],
        character_id="default",
    )
    background_path = resolve_background(
        theme,
        scene_id="default",
    )

    st.caption(
        "ANSWER SCENE · "
        f"{current_index + 1} / {len(beats)}"
    )

    result_label = (
        "SUCCESS"
        if is_correct
        else "RETRY"
    )

    context_bits = []

    if chapter_number is not None:
        context_bits.append(
            f"CHAPTER {int(chapter_number)}"
        )

    context_bits.append(
        f"QUESTION {int(question_number)}"
    )
    context_bits.append(
        result_label
    )

    is_last = (
        current_index
        == len(beats) - 1
    )

    next_label = (
        f"{str(guide_name or '동료')}의 반응 보기 →"
        if current_index == 0
        else "결과 확인 →"
    )

    clicked = render_dialogue_scene(
        theme=theme,
        speaker_type=beat["speaker_type"],
        speaker_name=beat["speaker_name"],
        text=beat["text"],
        portrait_path=portrait_path,
        background_path=background_path,
        context_label=" · ".join(
            context_bits
        ),
        key=(
            "day6_quiz_feedback_scene_"
            f"{int(chapter_id)}_"
            f"{int(question_index)}_"
            f"{current_index}"
        ),
        next_label=next_label,
        show_next_button=True,
        show_scene_chrome=True,
    )

    if clicked:
        if is_last:
            st.session_state[
                done_key
            ] = True
            st.session_state.pop(
                index_key,
                None,
            )
        else:
            st.session_state[
                index_key
            ] = current_index + 1

        st.rerun()

    return True


# DAY6_QUIZ_RESULT_NARRATION_V1

_RESULT_NARRATION_STYLE = {
    "동화": {
        "accent": "#df7191",
        "text": "#4d2834",
        "muted": "#8d6571",
        "surface": "rgba(255,250,249,.94)",
        "border": "rgba(223,113,145,.30)",
    },
    "판타지": {
        "accent": "#aa9bc8",
        "text": "#eee8f3",
        "muted": "#c3bacd",
        "surface": "rgba(30,28,38,.94)",
        "border": "rgba(170,155,200,.34)",
    },
    "SF": {
        "accent": "#83b7c0",
        "text": "#edf7f9",
        "muted": "#b9cfd3",
        "surface": "rgba(8,28,37,.94)",
        "border": "rgba(131,183,192,.36)",
    },
    "무협": {
        "accent": "#9c3f35",
        "text": "#493b30",
        "muted": "#806a55",
        "surface": "rgba(248,240,221,.95)",
        "border": "rgba(156,63,53,.30)",
    },
    "미스터리": {
        "accent": "#d1ad70",
        "text": "#f4eee4",
        "muted": "#d2c2ac",
        "surface": "rgba(35,31,30,.95)",
        "border": "rgba(209,173,112,.34)",
    },
}


def render_quiz_result_narration(
    *,
    theme: str,
    text: str,
    is_correct: bool,
    is_conclusion_step: bool,
) -> None:
    """
    Player ↔ Companion 대화 마지막에 이어지는 Narrator epilogue.

    DAY6 Narration Scene correction v1:
    별도 slim status card를 만들지 않고,
    직전 Player/Companion과 동일한 Dialogue Scene 무대/텍스트 상자를 유지한다.
    Narrator이므로 portrait와 speaker name만 없다.
    """
    narration_text = (
        str(text or "").strip()
        or "조사 결과가 기록되었습니다."
    )

    context_label = (
        "CHAPTER RESULT"
        if is_conclusion_step
        else "NARRATION · 발견한 사실"
    )

    state_label = (
        "확인"
        if is_correct
        else "재검토"
    )

    background_path = resolve_background(
        theme,
        scene_id="default",
    )

    st.caption(
        "NARRATION · 발견한 사실"
    )

    render_dialogue_scene(
        theme=theme,
        speaker_type="narrator",
        speaker_name="NARRATOR",
        text=narration_text,
        portrait_path=None,
        background_path=background_path,
        context_label=(
            f"{context_label} · {state_label}"
        ),
        key=None,
        next_label=None,
        show_next_button=False,
        show_scene_chrome=True,
    )

# DAY6_QUIZ_RESULT_EPILOGUE_V1

# DAY6_STICKY_EVIDENCE_NARRATION_SCENE_V1

# DAY6_SINGLE_STICKY_QUIZ_HUD_V1

# DAY6_RESTORE_STACKED_STICKY_EVIDENCE_V1

# DAY6_DOUBLE_STICKY_COMPACT_TUNING_V1

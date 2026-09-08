# DAY5_EVENT_FLUSH_FIX_V1
from __future__ import annotations

# CURRICULUM_SEMANTIC_CONTRACT_V1_20260906

import hashlib
import logging
import html
import re
import time
import traceback

import streamlit as st

from components.quiz_scene_experience import (
    render_quiz_feedback_dialogue,
    render_quiz_question_scene,
    render_quiz_result_narration,
)

from components.dialogue_interaction import (
    render_dialogue_interaction,
)
from services.dialogue_asset_service import (
    resolve_portrait,
)

from components.generated_text_readability import generated_text_readability_css

from components.learning_compact_ui import (
    render_compact_chapter_header,
)
from components.play_action_hub import (
    render_play_action_hub,
)
from components.investigation_board import (
    ACTION_CLUE,
    ACTION_COMPANION,
    ACTION_DEDUCE,
    clear_investigation_question_state,
    clear_investigation_state,
    render_investigation_board,
    set_investigation_action,
)
from components.story_cinematic import (
    render_story_experience,
    should_render_story_cinematic,
)
from components.dialogue_story_experience import (
    render_dialogue_story_experience,
)
from services.dialogue_runtime_service import (
    should_render_dialogue_story,
)
from components.text_utils import (
    format_inline_text,
)
from components.theme_system import (
    get_phase_label,
    get_theme_pack,
)
from repositories.attempt_repository import (
    create_attempt,
    get_attempted_question_texts,
)
from repositories.chapter_repository import (
    mark_chapter_completed,
    update_chapter_questions,
)
from repositories.story_choice_repository import (
    get_choice_for_chapter,
    save_story_choice,
)
from repositories.world_repository import (
    update_current_chapter,
)
from services.ai_client import AIQuotaExhausted
from services.dev_config import generation_mode_label, is_ai_mock_enabled
from services.event_service import (
    queue_event,
    queue_once,
)
from services.curriculum_service import (
    get_concept_contracts,
)
from services.foundation_service import (
    get_world_foundation,
)
from services.experience_profile_service import (
    get_learner_level_profile,
    get_reasoning_profile,
    get_theme_experience_profile,
    get_ui_support_mode,
)
from services.mastery_service import (
    choose_requested_difficulty,
    get_adaptive_support_profile,
    update_mastery_from_attempt,
)
from services.personalization_service import (
    build_personalization_profile,
)
from services.question_service import (
    QUESTION_COUNT,
    QuestionGenerationError,
    generate_chapter_questions,
)
from services.story_context_service import (
    get_runtime_story_context,
    get_story_context,
)
from services.chapter_runtime_service import (
    get_runtime_chapter,
    invalidate_runtime_chapter,
    invalidate_runtime_world,
)
from services.play_runtime_service import (
    PLAY_MODE_COMPANION,
    PLAY_MODE_QUIZ,
    PLAY_MODE_REVIEW,
    PLAY_MODE_STORY,
    resolve_play_mode,
)
from services.story_engine_service import (
    apply_completed_chapter_state,
    complete_current_story_arc,
    ensure_initial_story_block,
    generate_next_story_block,
    get_chapter_interaction_context,
    is_story_block_end,
    is_story_complete,
)


CHAPTER_STORY_CHOICES = 9
CHAPTER_PHASE = 10
CHAPTER_TARGET_CONCEPTS = 11

LOGGER = logging.getLogger(__name__)

USER_REPLY_TEMPLATES = {
    "동화": (
        "나는 {number}번인 것 같아!",
        "음... {number}번?",
        "내 생각엔 {number}번이야!",
        "아마 {number}번 아닐까?",
        "{number}번으로 해볼게!",
    ),
    "판타지": (
        "나는 {number}번이라고 생각해.",
        "내 선택은 {number}번이야.",
        "음... {number}번 같아.",
        "{number}번으로 가볼게.",
        "나는 {number}번 쪽이 맞는 것 같아.",
    ),
    "SF": (
        "내 판단은 {number}번이야.",
        "음... {number}번 같아.",
        "{number}번으로 판단할게.",
        "나는 {number}번이라고 봐.",
        "현재로선 {number}번 같아.",
    ),
    "무협": (
        "내 생각에는 {number}번이야.",
        "나는 {number}번으로 보겠어.",
        "음... {number}번 같군.",
        "{number}번이라 생각해.",
        "내 답은 {number}번이야.",
    ),
    "미스터리": (
        "단서를 보면 {number}번 같아.",
        "나는 {number}번이라고 생각해.",
        "음... {number}번?",
        "{number}번이 가장 맞는 것 같아.",
        "현재 기록으로는 {number}번 같아.",
    ),
}


def reset_quiz_state() -> None:
    st.session_state.question_index = 0
    st.session_state.question_submitted = False
    clear_investigation_state()

    for key in (
        "selected_answer",
        "show_npc_reply",
        "quiz_progress_chapter_id",
        "question_timer_key",
        "question_started_at",
    ):
        if key in st.session_state:
            del st.session_state[
                key
            ]


def _split_story_paragraphs(
    story: str,
) -> list[str]:
    text = str(
        story
        or ""
    ).strip()

    if not text:
        return []

    paragraphs = [
        item.strip()
        for item in re.split(
            r"\n\s*\n+",
            text,
        )
        if item.strip()
    ]

    if len(paragraphs) > 1:
        return paragraphs

    sentences = [
        item.strip()
        for item in re.split(
            r"(?<=[.!?。！？])\s+",
            text.replace(
                "\n",
                " ",
            ),
        )
        if item.strip()
    ]

    if len(sentences) <= 2:
        return [
            text
        ]

    return [
        " ".join(
            sentences[
                index:index + 2
            ]
        )
        for index in range(
            0,
            len(sentences),
            2,
        )
    ]


def _render_bubble(
    *,
    speaker: str,
    message: str,
    bubble_type: str,
    align: str,
) -> None:
    st.markdown(
        f"""
        <div class="dialogue-row {align}">
            <div class="dialogue-bubble {bubble_type}">
                <span class="speaker">{html.escape(format_inline_text(speaker))}</span>
                <span>{html.escape(format_inline_text(message))}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _render_character_interaction(
    *,
    theme: str,
    speaker_type: str,
    speaker_name: str,
    message: str,
    tone: str = "neutral",
) -> None:
    # DAY6_LEARNING_DIALOGUE_INTERACTION_V1
# DAY6_QUIZ_SCENE_INTERACTION_V2
# DAY6_QUIZ_RESULT_EPILOGUE_V1
    portrait_path = resolve_portrait(
        theme,
        speaker_type,
        character_id="default",
    )

    render_dialogue_interaction(
        theme=theme,
        speaker_type=speaker_type,
        speaker_name=speaker_name,
        text=message,
        portrait_path=portrait_path,
        tone=tone,
    )



def _sanitize_learning_text(
    text: str | None,
) -> str:
    """
    Learning Note에 섞인 HTML wrapper를 순수 텍스트로 정리한다.

    기존 DB에 저장된 값이
    <div>...</div>,
    &lt;div&gt;...&lt;/div&gt;,
    &amp;lt;div&amp;gt;...&amp;lt;/div&amp;gt;
    형태여도 동일하게 처리한다.
    """
    cleaned = format_inline_text(
        text
    )

    # HTML entity가 1~2회 escape된 과거 데이터까지 먼저 복원한다.
    for _ in range(3):
        decoded = html.unescape(
            cleaned
        )

        if decoded == cleaned:
            break

        cleaned = decoded

    # entity를 복원한 뒤 실제 HTML wrapper를 제거한다.
    cleaned = re.sub(
        r"</?[A-Za-z][^>]*>",
        " ",
        cleaned,
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    )

    return cleaned.strip()


def _render_learning_note(
    *,
    label: str,
    explanation: str,
    correct_answer: str | None = None,
) -> None:
    """
    학습 노트를 하나의 HTML block으로 렌더링한다.

    Streamlit Markdown parser가 raw HTML 안의 중첩 <div>를
    정답/오답 분기에서 다르게 해석하는 문제를 피하기 위해,
    내부 콘텐츠는 block <div> 대신 display:block <span>으로 구성한다.
    """
    safe_label = html.escape(
        _sanitize_learning_text(
            label
        )
    )

    safe_explanation = html.escape(
        _sanitize_learning_text(
            explanation
        )
    )

    parts = [
        '<div class="learning-note">',
        (
            '<span class="note-label">'
            f'{safe_label}'
            '</span>'
        ),
    ]

    if correct_answer:
        safe_answer = html.escape(
            _sanitize_learning_text(
                correct_answer
            )
        )
        parts.append(
            '<span style="display:block;font-weight:800;'
            'margin-bottom:.4rem;">'
            f'정답 · {safe_answer}'
            '</span>'
        )

    parts.append(
        '<span style="display:block;">'
        f'{safe_explanation}'
        '</span>'
    )
    parts.append('</div>')

    st.markdown(
        ''.join(parts),
        unsafe_allow_html=True,
    )


def _format_choice_reply(
    *,
    choice_number: int,
    choice_text: str,
) -> str:
    """사용자 답변은 추론을 대신 말하지 않고 선택 사실만 중립적으로 보여준다."""
    clean = _sanitize_learning_text(choice_text)

    # QUIZ_ANSWER_REPLY_DECIMAL_HOTFIX_V1_0_1
    # 소수 "2.4 kg"의 "2."를 보기 번호로 오인하지 않는다.
    # 실제 보기 번호 prefix만 제거한다.
    clean = re.sub(
        r"^\s*(?:"
        r"[①②③④]\s*|"
        r"\([1-4]\)\s*[.)]?\s*|"
        r"[1-4]\)\s*|"
        r"[1-4]\.(?!\d)\s*|"
        r"[1-4]\s*번[.)]?\s*"
        r")",
        "",
        clean,
    ).strip()

    if len(clean) > 110:
        clean = clean[:107].rstrip() + "..."

    return f"{choice_number}번 · {clean}"



def _render_learning_materials(
    *,
    theme: str,
    learner_level: str,
    difficulty: str,
    question: dict,
    guide_name: str | None = None,
    section: str = "all",
) -> None:
    # DAY5_INVESTIGATION_BOARD_V1_INTEGRATION
    if section not in {"all", ACTION_CLUE, ACTION_COMPANION}:
        raise ValueError(f"Unsupported learning material section: {section}")
    profile = get_theme_experience_profile(theme)
    support = get_learner_level_profile(learner_level)
    reasoning = get_reasoning_profile(difficulty)
    ui_mode = get_ui_support_mode(learner_level)

    concept_brief = _sanitize_learning_text(
        question.get("concept_brief")
    )
    evidence_summary = _sanitize_learning_text(
        question.get("evidence_summary")
    )
    evidence_context = _sanitize_learning_text(
        question.get("evidence_context")
    )
    evidence_help = _sanitize_learning_text(
        question.get("evidence_help")
    )

    if concept_brief and section in {"all", ACTION_COMPANION}:
        if section == ACTION_COMPANION:
            _render_character_interaction(
                theme=theme,
                speaker_type="companion",
                speaker_name=(guide_name or "고양이"),
                message=concept_brief,
                tone="neutral",
            )
            if ui_mode in {"guided", "supported"}:
                st.caption(
                    f"{support['display_name']} · 사고 수준 {reasoning['label']}"
                )
        else:
            if ui_mode in {"guided", "supported"}:
                with st.container(border=True):
                    st.markdown("**💡 먼저 알아둘 개념**")
                    st.markdown(
                        f"<div style='font-size:1.02rem;line-height:1.75;'>"
                        f"{html.escape(concept_brief)}</div>",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"{support['display_name']} · 사고 수준 {reasoning['label']}"
                    )
            else:
                with st.expander("💡 필요하면 개념 도움 보기", expanded=False):
                    st.write(concept_brief)

    if evidence_summary and section in {"all", ACTION_CLUE}:
        with st.container(border=True):
            st.markdown(f"**{profile['summary_label']}**")
            st.markdown(
                f"<div style='font-size:1.06rem;line-height:1.85;"
                f"font-weight:650;'>{html.escape(evidence_summary)}</div>",
                unsafe_allow_html=True,
            )

    if evidence_context and section in {"all", ACTION_CLUE}:
        if ui_mode in {"guided", "supported"}:
            with st.expander(
                f"{profile['source_label']} · 상세 보기",
                expanded=True,
            ):
                st.markdown(
                    f"<div style='font-size:1rem;line-height:1.8;'>"
                    f"{html.escape(evidence_context)}</div>",
                    unsafe_allow_html=True,
                )
        else:
            with st.container(border=True):
                st.markdown(f"**{profile['source_label']}**")
                st.markdown(
                    f"<div style='font-size:1rem;line-height:1.8;'>"
                    f"{html.escape(evidence_context)}</div>",
                    unsafe_allow_html=True,
                )

    if evidence_help and section in {"all", ACTION_COMPANION}:
        _render_theme_help_details(
            theme=theme,
            label=profile["help_label"],
            text=evidence_help,
        )

# DAY6_INVESTIGATION_FLOW_UX_V3
# DAY6_EVIDENCE_THEME_CARD_V1
# DAY6_STICKY_EVIDENCE_NARRATION_SCENE_V1
# DAY6_THEME_HELP_DETAILS_V1
# DAY6_DARK_THEME_READABILITY_V1
# DAY6_QUIZ_CHOICE_CARD_UI_V1
# DAY6_QUIZ_CHOICE_CARD_UI_V1_1
# DAY6_QUIZ_COLUMN_LAYOUT_V1
# DAY6_QUIZ_COLUMN_LAYOUT_INDEX_ORDER_FIX_V1
# DAY6_QUIZ_QUESTION_COLUMN_ALIGN_V1
# DAY6_GENERATED_TEXT_READABILITY_V1_1
_THEME_EVIDENCE_LABELS = {
    "동화": "📖 이야기 속 단서",
    "판타지": "📜 발견한 기록",
    "SF": "📡 수집된 기록",
    "무협": "📜 발견한 흔적",
    "미스터리": "🔎 사건 단서",
}


def _render_fixed_question_evidence(
    *,
    theme: str,
    question: dict,
) -> None:
    """
    Evidence는 선택형 힌트가 아니라 문제 판단에 필요한 관찰 자료다.

    DAY6 Double Sticky Compact Tuning v1:
    - Evidence / Question double-sticky 구조는 유지한다.
    - Evidence 높이를 고정해 Question의 sticky offset과 실제 높이를 일치시킨다.
    - 긴 Evidence는 카드 내부에서 스크롤한다.
    - 둘 사이 간격은 거의 붙어 보일 정도로 최소화한다.
    """
    evidence_summary = _sanitize_learning_text(
        question.get("evidence_summary")
    )
    evidence_context = _sanitize_learning_text(
        question.get("evidence_context")
    )

    if not evidence_summary and not evidence_context:
        return

    label = _THEME_EVIDENCE_LABELS.get(
        theme,
        "🔎 확인할 단서",
    )

    theme_style = {
        "동화": {
            "background": (
                "linear-gradient(135deg, "
                "rgba(255,250,247,.98), "
                "rgba(255,236,241,.97) 55%, "
                "rgba(236,250,244,.96))"
            ),
            "border": "#e9a8b8",
            "accent": "#e66f8d",
            "title": "#8a4057",
            "text": "#513d43",
            "shadow": "rgba(171,108,125,.16)",
        },
        "판타지": {
            "background": (
                "linear-gradient(135deg, "
                "rgba(29,25,48,.98), "
                "rgba(50,38,79,.97))"
            ),
            "border": "#8f79c5",
            "accent": "#c0a5ff",
            "title": "#e7dcff",
            "text": "#f4efff",
            "shadow": "rgba(111,87,173,.30)",
        },
        "SF": {
            "background": (
                "linear-gradient(135deg, "
                "rgba(5,31,47,.98), "
                "rgba(7,55,70,.97))"
            ),
            "border": "#2cb6cc",
            "accent": "#5de3f5",
            "title": "#aaf4ff",
            "text": "#e9fbff",
            "shadow": "rgba(29,174,195,.26)",
        },
        "무협": {
            "background": (
                "linear-gradient(135deg, "
                "rgba(250,243,225,.99), "
                "rgba(239,224,190,.97))"
            ),
            "border": "#b98a51",
            "accent": "#9d3b32",
            "title": "#6c342f",
            "text": "#473c31",
            "shadow": "rgba(120,88,52,.18)",
        },
        "미스터리": {
            "background": (
                "linear-gradient(135deg, "
                "rgba(31,29,30,.99), "
                "rgba(54,44,39,.98))"
            ),
            "border": "#a88758",
            "accent": "#d6b475",
            "title": "#f1d7a7",
            "text": "#f4eee5",
            "shadow": "rgba(38,27,22,.32)",
        },
    }.get(
        theme,
        {
            "background": "rgba(255,255,255,.98)",
            "border": "#c9c9c9",
            "accent": "#777777",
            "title": "#333333",
            "text": "#444444",
            "shadow": "rgba(0,0,0,.12)",
        },
    )

    summary_html = ""
    if evidence_summary:
        summary_html = (
            '<div class="day6-sticky-evidence-summary">'
            f'{html.escape(evidence_summary)}'
            '</div>'
        )

    context_html = ""
    if evidence_context:
        context_html = (
            '<div class="day6-sticky-evidence-context">'
            f'{html.escape(evidence_context)}'
            '</div>'
        )

    st.markdown(
        f"""
        <style>
        .stApp {{
            /*
            실제 Evidence 높이와 Question sticky offset을 동일 계열 값으로 맞춘다.
            이전 값은 Evidence max-height(9.25rem)를 기준으로 잡아
            짧은 단서에서 실제 카드보다 큰 빈 공간이 생길 수 있었다.
            */
            --day6-evidence-stack-offset: 7.20rem;
            --day6-evidence-stack-offset-mobile: 5.90rem;
        }}

        div[data-testid="stElementContainer"]:has(
            .day6-sticky-evidence-card
        ) {{
            position: sticky !important;
            top: 3.85rem !important;
            z-index: 720 !important;
            width: min(100%, 1120px) !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }}

        .day6-sticky-evidence-card {{
            position: relative;
            overflow-y: auto;
            overflow-x: hidden;
            height: 7.05rem;
            max-height: 7.05rem;
            box-sizing: border-box;
            border-radius: 15px;
            padding: .70rem .96rem .72rem 1.18rem;
            background: {theme_style["background"]};
            border: 1px solid {theme_style["border"]};
            box-shadow: 0 8px 21px {theme_style["shadow"]};
            scrollbar-width: thin;
        }}

        .day6-sticky-evidence-accent {{
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 5px;
            background: {theme_style["accent"]};
        }}

        .day6-sticky-evidence-title {{
            display: flex;
            align-items: center;
            gap: .34rem;
            margin-bottom: .26rem;
            color: {theme_style["title"]};
            font-size: .96rem;
            line-height: 1.30;
            font-weight: 850;
        }}

        .day6-sticky-evidence-summary {{
            color: {theme_style["text"]};
            font-size: .89rem;
            line-height: 1.48;
            font-weight: 720;
            word-break: keep-all;
            overflow-wrap: break-word;
            line-break: strict;
        }}

        .day6-sticky-evidence-context {{
            margin-top: .22rem;
            color: {theme_style["text"]};
            font-size: .85rem;
            line-height: 1.44;
            opacity: .90;
            word-break: keep-all;
            overflow-wrap: break-word;
            line-break: strict;
        }}

        @media (max-width: 760px) {{
            div[data-testid="stElementContainer"]:has(
                .day6-sticky-evidence-card
            ) {{
                top: 3.45rem !important;
            }}

            .day6-sticky-evidence-card {{
                height: 5.75rem;
                max-height: 5.75rem;
                padding: .52rem .66rem .55rem .84rem;
                border-radius: 12px;
            }}

            .day6-sticky-evidence-title {{
                margin-bottom: .15rem;
                font-size: .83rem;
            }}

            .day6-sticky-evidence-summary {{
                font-size: .78rem;
                line-height: 1.38;
            }}

            .day6-sticky-evidence-context {{
                margin-top: .14rem;
                font-size: .75rem;
                line-height: 1.36;
            }}
        }}
        </style>

        <section class="day6-sticky-evidence-card">
            <div class="day6-sticky-evidence-accent"></div>
            <div class="day6-sticky-evidence-title">
                {html.escape(label)}
            </div>
            {summary_html}
            {context_html}
        </section>
        """,
        unsafe_allow_html=True,
    )








# DAY6_THEME_HELP_DETAILS_V1
_THEME_HELP_DETAILS_STYLE = {
    "동화": {
        "surface": "rgba(255,248,250,.97)",
        "surface_open": "rgba(255,240,245,.98)",
        "border": "#e7a6b6",
        "accent": "#df6c88",
        "text": "#563d46",
        "muted": "#8a6670",
        "shadow": "rgba(178,111,130,.13)",
    },
    "판타지": {
        "surface": "rgba(30,28,38,.97)",
        "surface_open": "rgba(36,33,46,.98)",
        "border": "#675f78",
        "accent": "#aa9bc8",
        "text": "#ebe7f1",
        "muted": "#bdb6c9",
        "shadow": "rgba(38,31,54,.20)",
    },
    "SF": {
        "surface": "rgba(10,27,35,.97)",
        "surface_open": "rgba(12,33,42,.98)",
        "border": "#496d76",
        "accent": "#83b7c0",
        "text": "#e8f0f2",
        "muted": "#b5c8cc",
        "shadow": "rgba(19,55,64,.20)",
    },
    "무협": {
        "surface": "rgba(248,240,221,.97)",
        "surface_open": "rgba(241,228,199,.98)",
        "border": "#b38a56",
        "accent": "#9c3f35",
        "text": "#493b30",
        "muted": "#7f6a55",
        "shadow": "rgba(121,91,57,.14)",
    },
    "미스터리": {
        "surface": "rgba(35,31,30,.97)",
        "surface_open": "rgba(47,40,37,.98)",
        "border": "#9f825a",
        "accent": "#d1ad70",
        "text": "#f4eee4",
        "muted": "#d2c2ac",
        "shadow": "rgba(24,18,16,.28)",
    },
}


def _render_theme_help_details(
    *,
    theme: str,
    label: str,
    text: str,
) -> None:
    """
    용어/시스템 도움은 기본 CLOSED 상태를 유지하면서,
    펼친 뒤에도 Streamlit 기본 흰 배경이 드러나지 않게
    테마 전용 <details> 카드로 렌더한다.
    """
    style = _THEME_HELP_DETAILS_STYLE.get(
        theme,
        {
            "surface": "rgba(255,255,255,.96)",
            "surface_open": "rgba(248,248,248,.98)",
            "border": "#c8c8c8",
            "accent": "#777777",
            "text": "#333333",
            "muted": "#666666",
            "shadow": "rgba(0,0,0,.10)",
        },
    )

    safe_label = html.escape(
        str(label or "용어 도움")
    )
    safe_text = html.escape(
        str(text or "")
    )

    st.markdown(
        f"""
        <style>
        details.day6-theme-help {{
            width: 100%;
            border: 1px solid {style["border"]};
            border-radius: 14px;
            background: {style["surface"]};
            box-shadow: 0 7px 20px {style["shadow"]};
            overflow: hidden;
            transition:
                background .18s ease,
                border-color .18s ease,
                box-shadow .18s ease;
        }}

        details.day6-theme-help[open] {{
            background: {style["surface_open"]};
        }}

        details.day6-theme-help > summary {{
            list-style: none;
            cursor: pointer;
            position: relative;
            padding: .92rem 1.15rem .92rem 2.35rem;
            color: {style["accent"]};
            font-weight: 800;
            line-height: 1.5;
            user-select: none;
        }}

        details.day6-theme-help > summary::-webkit-details-marker {{
            display: none;
        }}

        details.day6-theme-help > summary::before {{
            content: "⌄";
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-52%);
            color: {style["accent"]};
            font-size: 1rem;
            font-weight: 900;
            transition: transform .16s ease;
        }}

        details.day6-theme-help[open] > summary::before {{
            transform: translateY(-52%) rotate(180deg);
        }}

        details.day6-theme-help > summary::after {{
            content: "";
            position: absolute;
            left: 1.15rem;
            right: 1.15rem;
            bottom: 0;
            height: 1px;
            background: {style["border"]};
            opacity: .42;
        }}

        details.day6-theme-help > .day6-theme-help-body {{
            padding: .95rem 1.15rem 1.05rem 1.15rem;
            color: {style["text"]};
            font-size: 1rem;
            line-height: 1.8;
            background: transparent;
        }}

        details.day6-theme-help > .day6-theme-help-body strong {{
            color: {style["accent"]};
        }}
        </style>

        <details class="day6-theme-help">
            <summary>{safe_label}</summary>
            <div class="day6-theme-help-body">{safe_text}</div>
        </details>
        """,
        unsafe_allow_html=True,
    )

def _render_chapter_story(
    *,
    user,
    world,
    chapter,
    review_expanded: bool = False,
) -> bool:
    pack = get_theme_pack(
        world[4]
    )

    context = get_runtime_story_context(
        world[0]
    )

    arc = (
        context["arc"]
        if context
        else None
    )

    phase = (
        chapter[
            CHAPTER_PHASE
        ]
        if len(chapter)
        > CHAPTER_PHASE
        else None
    )

    if not phase and arc:
        phase = arc.get(
            "current_phase"
        )

    total = (
        arc.get(
            "target_chapter_count"
        )
        if arc
        else None
    )

    phase_label = (
        get_phase_label(
            world[4],
            phase,
        )
    )

    block_number = (
        (
            chapter[2] - 1
        )
        // 3
        + 1
    )

    # DAY6_DIALOGUE_RUNTIME_V1_INTEGRATION
    # Feature gate가 켜져 있으면 기존 plain-text Story를 Dialogue Scene UI로 먼저 재생한다.
    # 원문/DB/AI Prompt는 변경하지 않으며, 종료 시 기존 Story seen key를 공유해
    # 같은 Chapter에서 기존 Cinematic이 다시 중복 재생되지 않게 한다.
    if should_render_dialogue_story(
        chapter_id=chapter[0],
        story_text=chapter[4],
    ):
        dialogue_active = render_dialogue_story_experience(
            chapter_id=chapter[0],
            theme=world[4],
            story_text=chapter[4],
            chapter_number=chapter[2],
            chapter_title=format_inline_text(chapter[3]),
            guide_name=(
                world[9]
                if len(world) > 9
                else None
            ),
        )

        if dialogue_active:
            queue_once(
                key=f"story_open_{chapter[0]}",
                event_type="story_open",
                user_id=user["user_id"],
                world_id=world[0],
                story_arc_id=(arc["id"] if arc else None),
                chapter_id=chapter[0],
                metadata={
                    "theme": world[4],
                    "chapter_number": chapter[2],
                    "story_phase": phase,
                    "story_length": len(chapter[4] or ""),
                    "presentation": "dialogue_runtime_v1",
                },
                flush=True,
            )
            return True

    # DAY5_STORY_CINEMATIC_V2_DEDICATED_INTEGRATION
    # Dialogue Runtime이 꺼져 있거나 적용되지 않으면 기존 Cinematic으로 그대로 fallback한다.
    if should_render_story_cinematic(
        chapter_id=chapter[0],
        story_text=chapter[4],
    ):
        cinematic_active = render_story_experience(
            chapter_id=chapter[0],
            theme=world[4],
            story_text=chapter[4],
            chapter_number=chapter[2],
            chapter_title=format_inline_text(chapter[3]),
        )

        if cinematic_active:
            queue_once(
                key=f"story_open_{chapter[0]}",
                event_type="story_open",
                user_id=user["user_id"],
                world_id=world[0],
                story_arc_id=(arc["id"] if arc else None),
                chapter_id=chapter[0],
                metadata={
                    "theme": world[4],
                    "chapter_number": chapter[2],
                    "story_phase": phase,
                    "story_length": len(chapter[4] or ""),
                },
                flush=True,
            )
            return True

    # DAY5_COMPACT_LEARNING_UI_V1_CHAPTER
    render_compact_chapter_header(
        theme=world[4],
        chapter_number=chapter[2],
        block_number=block_number,
        title=format_inline_text(chapter[3]),
        meta=(
            f"{phase_label} · {world[4]} · {world[1]}"
        ),
        progress_current=(chapter[2] if total else None),
        progress_total=(total if total else None),
    )

    targets = (
        chapter[
            CHAPTER_TARGET_CONCEPTS
        ]
        if len(chapter)
        > CHAPTER_TARGET_CONCEPTS
        else []
    )

    # Story 다시보기와 학습 목표를 한 줄의 compact utility로 묶어
    # Investigation이 viewport 상단에 더 빨리 도달하도록 한다.
    tool_left, tool_right = st.columns(2, gap="small")
    with tool_left:
        render_story_experience(
            chapter_id=chapter[0],
            theme=world[4],
            story_text=chapter[4],
            chapter_number=chapter[2],
            chapter_title=format_inline_text(chapter[3]),
            review_expanded=review_expanded,
        )
        # Marker는 기존 compact/mobile CSS selector 호환을 위해 유지하되,
        # expander 앞에 별도 Streamlit element gap을 만들지 않도록 뒤로 이동한다.
        st.markdown(
            '<span class="compact-learning-tools-marker"></span>',
            unsafe_allow_html=True,
        )

    with tool_right:
        with st.expander(
            "🎯 이번 Chapter의 학습 목표",
            expanded=False,
        ):
            if targets:
                st.caption(
                    "핵심 Concept · "
                    + ", ".join(
                        targets
                    )
                )

            for objective in (
                chapter[5]
                or []
            ):
                st.markdown(
                    f"- {format_inline_text(objective)}"
                )

    # DAY5_INVESTIGATION_HEADER_CLEANUP_V1
    # Investigation Board가 문제 풀이 단계의 실제 heading 역할을 하므로,
    # Story 뒤의 장식 separator + EVIDENCE CHECK/quest title 중복 heading은 렌더하지 않는다.

    queue_once(
        key=(
            f"story_open_{chapter[0]}"
        ),
        event_type="story_open",
        user_id=user["user_id"],
        world_id=world[0],
        story_arc_id=(
            arc["id"]
            if arc
            else None
        ),
        chapter_id=chapter[0],
        metadata={
            "theme": world[4],
            "chapter_number": (
                chapter[2]
            ),
            "story_phase": phase,
            "story_length": len(
                chapter[4]
                or ""
            ),
        },
        flush=True,
    )

    return False


def _initialize_quiz_progress_from_db(
    *,
    user,
    world,
    chapter,
    questions,
) -> None:
    if (
        st.session_state.get(
            "quiz_progress_chapter_id"
        )
        == chapter[0]
        and "question_index"
        in st.session_state
    ):
        return

    attempted_texts = (
        get_attempted_question_texts(
            user_id=user[
                "user_id"
            ],
            world_id=world[0],
            chapter_id=chapter[0],
        )
    )

    next_index = len(
        questions
    )

    for index, question in enumerate(
        questions
    ):
        if (
            question["question"]
            not in attempted_texts
        ):
            next_index = index
            break

    st.session_state.question_index = (
        next_index
    )
    st.session_state.question_submitted = False
    st.session_state.quiz_progress_chapter_id = chapter[0]

    for key in (
        "selected_answer",
        "show_npc_reply",
        "question_timer_key",
        "question_started_at",
    ):
        if key in st.session_state:
            del st.session_state[
                key
            ]


def _start_question_timer(
    *,
    chapter_id: int,
    index: int,
) -> None:
    timer_key = (
        f"{chapter_id}:{index}"
    )

    if (
        st.session_state.get(
            "question_timer_key"
        )
        != timer_key
    ):
        st.session_state[
            "question_timer_key"
        ] = timer_key
        st.session_state[
            "question_started_at"
        ] = time.perf_counter()


def _response_time_ms() -> int | None:
    started = st.session_state.get(
        "question_started_at"
    )

    if started is None:
        return None

    return max(
        0,
        int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        ),
    )


def _render_story_choice(
    *,
    user,
    world,
    chapter,
) -> bool:
    choices = (
        chapter[
            CHAPTER_STORY_CHOICES
        ]
        if len(chapter)
        > CHAPTER_STORY_CHOICES
        else []
    )

    if not choices:
        return True

    context = get_runtime_story_context(
        world[0]
    )

    if context is None:
        return True

    selected = (
        get_choice_for_chapter(
            user_id=user[
                "user_id"
            ],
            chapter_id=chapter[0],
        )
    )

    st.markdown(
        "### 이야기에서 무엇을 할까?"
    )
    st.caption(
        "학습 성적과 관계없이 원하는 Story 방향을 선택할 수 있습니다. "
        "선택한 방향은 다음 Story Block의 첫 장면에 직접 반영됩니다."
    )

    if selected:
        st.info(
            "선택한 방향 · "
            + selected[
                "choice_text"
            ]
        )
        return True

    for choice in choices:
        key = str(
            choice.get(
                "key",
                "",
            )
        )
        text = str(
            choice.get(
                "text",
                "",
            )
        )

        if not key or not text:
            continue

        if st.button(
            text,
            key=(
                f"story_choice_"
                f"{chapter[0]}_{key}"
            ),
            use_container_width=True,
        ):
            save_story_choice(
                user_id=user[
                    "user_id"
                ],
                world_id=world[0],
                story_arc_id=(
                    context["arc"][
                        "id"
                    ]
                ),
                chapter_id=chapter[0],
                choice_key=key,
                choice_text=text,
            )

            queue_event(
                "story_choice",
                user_id=user[
                    "user_id"
                ],
                world_id=world[0],
                story_arc_id=(
                    context["arc"][
                        "id"
                    ]
                ),
                chapter_id=chapter[0],
                metadata={
                    "choice_key": key,
                    "choice_text": text,
                },
                flush=True,
            )

            st.rerun()

    return False


def render_chapter_complete(
    *,
    user,
    world,
    chapter,
) -> None:
    pack = get_theme_pack(
        world[4]
    )

    runtime_chapter_dirty = (
        not bool(chapter[7])
        or (
            len(chapter) > 13
            and not bool(chapter[13])
        )
    )

    if not chapter[7]:
        mark_chapter_completed(
            chapter_id=chapter[0]
        )

    # Story State는 Chapter를 실제 완료한 뒤에만 반영한다.
    apply_completed_chapter_state(
        world_id=world[0],
        chapter=chapter,
    )

    if runtime_chapter_dirty:
        invalidate_runtime_chapter(
            world_id=world[0],
            chapter_number=chapter[2],
        )

    context = get_story_context(
        world[0]
    )

    arc_id = (
        context["arc"]["id"]
        if context
        else None
    )

    queue_once(
        key=(
            f"chapter_complete_"
            f"{chapter[0]}"
        ),
        event_type="chapter_complete",
        user_id=user["user_id"],
        world_id=world[0],
        story_arc_id=arc_id,
        chapter_id=chapter[0],
        metadata={
            "chapter_number": (
                chapter[2]
            ),
        },
    )

    st.success(
        "이번 Chapter의 학습을 완료했습니다."
    )

    story_complete = (
        is_story_complete(
            world_id=world[0],
            chapter_number=(
                chapter[2]
            ),
        )
    )

    block_end = (
        is_story_block_end(
            world_id=world[0],
            chapter_number=(
                chapter[2]
            ),
        )
    )

    if story_complete:
        complete_current_story_arc(
            world[0]
        )

        queue_once(
            key=(
                f"story_complete_"
                f"{world[0]}"
            ),
            event_type="story_complete",
            user_id=user[
                "user_id"
            ],
            world_id=world[0],
            story_arc_id=arc_id,
            chapter_id=chapter[0],
            metadata={
                "theme": world[4],
            },
            flush=True,
        )

        st.markdown(
            f"""
            <div class="story-ending-panel">
                <div class="theme-kicker">{html.escape(pack["ending_label"])}</div>
                <div style="font-size:1.45rem;font-weight:900;">
                    하나의 이야기를 끝까지 완성했습니다.
                </div>
                <div style="margin-top:.55rem;opacity:.78;">
                    이번 Story Arc의 핵심 사건과 관계는 여기서 마무리됩니다.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if block_end:
        queue_once(
            key=(
                f"block_complete_"
                f"{chapter[0]}"
            ),
            event_type="story_block_complete",
            user_id=user[
                "user_id"
            ],
            world_id=world[0],
            story_arc_id=arc_id,
            chapter_id=chapter[0],
            metadata={
                "block_number": (
                    (
                        chapter[2] - 1
                    )
                    // 3
                    + 1
                )
            },
        )

        st.markdown(
            f"""
            <div class="block-complete-panel">
                <div class="theme-kicker">STORY BLOCK COMPLETE</div>
                <div style="font-weight:850;">{html.escape(pack["block_complete"])}</div>
                <div style="margin-top:.45rem;opacity:.75;">
                    지금까지의 학습 결과가 다음 이야기 묶음의 난이도와 정보량에 반영됩니다.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not _render_story_choice(
        user=user,
        world=world,
        chapter=chapter,
    ):
        return

    personalization = (
        build_personalization_profile(
            user_id=user["user_id"],
            world_id=world[0],
            chapter_id=chapter[0],
        )
    )

    next_chapter_number = (
        chapter[2] + 1
    )

    next_chapter = get_runtime_chapter(
        world_id=world[0],
        chapter_number=(
            next_chapter_number
        ),
    )

    if next_chapter is not None:
        if st.button(
            f"Chapter {next_chapter_number}로 이어가기",
            type="primary",
            key=(
                f"move_chapter_"
                f"{next_chapter_number}"
            ),
            use_container_width=True,
        ):
            update_current_chapter(
                world_id=world[0],
                chapter_number=(
                    next_chapter_number
                ),
            )

            reset_quiz_state()
            st.rerun()

        return

    button_label = (
        "다음 Story Block의 첫 Chapter 준비"
        if block_end
        else "다음 Chapter 준비"
    )

    if st.button(
        button_label,
        type="primary",
        key=(
            f"generate_block_from_"
            f"{next_chapter_number}"
        ),
        use_container_width=True,
    ):
        with st.spinner(
            "Story Block 계획을 확인하고 다음 Chapter 하나만 준비하고 있습니다..."
        ):
            try:
                generate_next_story_block(
                    user=user,
                    world=world,
                    start_chapter=(
                        next_chapter_number
                    ),
                    personalization=(
                        personalization
                    ),
                )

                invalidate_runtime_world(
                    world[0]
                )

                update_current_chapter(
                    world_id=world[0],
                    chapter_number=(
                        next_chapter_number
                    ),
                )

                reset_quiz_state()
                st.rerun()

            except AIQuotaExhausted:
                st.error(
                    "Gemini의 일일 무료 요청 할당량이 소진되었습니다. "
                    "이 경우 자동 재시도하지 않습니다. 현재 진행 상태는 그대로 유지됩니다."
                )

            except Exception:
                st.error(
                    "다음 Chapter를 생성하는 중 문제가 발생했습니다. "
                    "현재 진행 상태는 유지되므로 잠시 후 다시 시도해주세요."
                )


# DAY6_DARK_THEME_READABILITY_V1
def _inject_dark_quiz_readability_css(
    theme: str,
) -> None:
    """
    판타지/SF의 dark-base 화면에서 Streamlit Radio option label이
    전역 테마 색상과 충돌해 어둡게 보이는 문제를 quiz scope에서 보정한다.
    """
    if theme not in {
        "판타지",
        "SF",
    }:
        return

    if theme == "판타지":
        option_text = "#f2edf8"
        option_muted = "#ddd5e8"
    else:
        option_text = "#eef9fb"
        option_muted = "#cfe3e7"

    st.markdown(
        f"""
        <style>
        div[data-testid="stRadio"] > label,
        div[data-testid="stRadio"] > label p {{
            color: {option_muted} !important;
            opacity: 1 !important;
        }}

        div[data-testid="stRadio"] div[role="radiogroup"] label,
        div[data-testid="stRadio"] div[role="radiogroup"] label p,
        div[data-testid="stRadio"] div[role="radiogroup"]
            [data-testid="stMarkdownContainer"],
        div[data-testid="stRadio"] div[role="radiogroup"]
            [data-testid="stMarkdownContainer"] p {{
            color: {option_text} !important;
            opacity: 1 !important;
            -webkit-text-fill-color: {option_text} !important;
        }}

        div[role="radiogroup"] label,
        div[role="radiogroup"] label p {{
            color: {option_text} !important;
            opacity: 1 !important;
            -webkit-text-fill-color: {option_text} !important;
        }}

        div[data-testid="stRadio"] label[data-baseweb="radio"] {{
            color: {option_text} !important;
            opacity: 1 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# DAY6_QUIZ_CHOICE_CARD_UI_V1
def _inject_quiz_choice_card_css(
    theme: str,
    *,
    chapter_id: int,
    question_index: int,
) -> None:
    """
    Quiz Choice Card UI v1.2
    문제 제목 / 보기 / 응답 버튼을 하나의 안정적인 Quiz Column 폭으로 묶는다.

    - desktop: max-width 1120px
    - mobile/tablet: available width 100%
    - 선택지 길이에 따라 박스 폭이 흔들리지 않음
    - 내부 텍스트는 좌측 정렬 유지
    - v1.1의 low-contrast answer-row 스타일 유지
    """
    palette = {
        "동화": {
            "surface": "rgba(255,255,255,.34)",
            "hover": "rgba(255,246,248,.58)",
            "selected": "rgba(252,235,240,.70)",
            "border": "rgba(211,155,170,.42)",
            "accent": "#d8738d",
            "text": "#4f3841",
        },
        "판타지": {
            "surface": "rgba(255,255,255,.025)",
            "hover": "rgba(255,255,255,.055)",
            "selected": "rgba(171,147,196,.10)",
            "border": "rgba(168,148,188,.26)",
            "accent": "#aa94c4",
            "text": "#f0ebf4",
        },
        "SF": {
            "surface": "rgba(255,255,255,.025)",
            "hover": "rgba(255,255,255,.05)",
            "selected": "rgba(91,177,194,.10)",
            "border": "rgba(87,153,166,.28)",
            "accent": "#62b8c7",
            "text": "#edf8fa",
        },
        "무협": {
            "surface": "rgba(255,255,255,.30)",
            "hover": "rgba(247,239,222,.55)",
            "selected": "rgba(224,204,172,.56)",
            "border": "rgba(165,132,91,.34)",
            "accent": "#985245",
            "text": "#493a2f",
        },
        "미스터리": {
            "surface": "rgba(255,255,255,.025)",
            "hover": "rgba(255,255,255,.05)",
            "selected": "rgba(190,158,103,.09)",
            "border": "rgba(160,134,92,.27)",
            "accent": "#b89a69",
            "text": "#f0e9df",
        },
    }.get(
        theme,
        {
            "surface": "rgba(255,255,255,.28)",
            "hover": "rgba(255,255,255,.46)",
            "selected": "rgba(230,230,230,.58)",
            "border": "rgba(150,150,150,.32)",
            "accent": "#777777",
            "text": "#333333",
        },
    )

    radio_key_class = (
        f".st-key-question_{chapter_id}_{question_index}"
    )
    submit_key_class = (
        f".st-key-submit_{chapter_id}_{question_index}"
    )

    st.markdown(
        f"""
        <style>
        :root {{
            --day6-quiz-column-width: 1120px;
        }}

        /* Question / answers / submit = one reading column */
        .quest-question {{
            display: block !important;
            width: min(100%, var(--day6-quiz-column-width)) !important;
            max-width: var(--day6-quiz-column-width) !important;
            margin-left: auto !important;
            margin-right: auto !important;
            margin-top: .30rem !important;
            margin-bottom: .72rem !important;
            box-sizing: border-box !important;
            text-align: left !important;
            font-size: clamp(1.48rem, 1.8vw, 1.82rem) !important;
            font-weight: 800 !important;
            line-height: 1.28 !important;
            letter-spacing: -.025em !important;
        }}

        {radio_key_class},
        {submit_key_class} {{
            width: min(100%, var(--day6-quiz-column-width)) !important;
            max-width: var(--day6-quiz-column-width) !important;
            margin-left: auto !important;
            margin-right: auto !important;
            box-sizing: border-box !important;
        }}

        {radio_key_class} div[data-testid="stRadio"] {{
            width: 100% !important;
            max-width: 100% !important;
        }}

        {radio_key_class} div[data-testid="stRadio"] div[role="radiogroup"] {{
            width: 100% !important;
            max-width: 100% !important;
            gap: .34rem !important;
        }}

        /* v1.1 low-contrast answer-row styling */
        {radio_key_class} div[data-testid="stRadio"]
            div[role="radiogroup"] > label {{
            width: 100% !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
            margin: 0 !important;
            padding: .62rem .78rem !important;
            border: 1px solid {palette["border"]} !important;
            border-radius: 9px !important;
            background: {palette["surface"]} !important;
            box-shadow: none !important;
            transition:
                background .12s ease,
                border-color .12s ease !important;
            cursor: pointer !important;
        }}

        {radio_key_class} div[data-testid="stRadio"]
            div[role="radiogroup"] > label:hover {{
            background: {palette["hover"]} !important;
        }}

        {radio_key_class} div[data-testid="stRadio"]
            div[role="radiogroup"] > label:has(input:checked),
        {radio_key_class} div[data-testid="stRadio"]
            div[role="radiogroup"] > label:has([aria-checked="true"]) {{
            background: {palette["selected"]} !important;
            border-color: {palette["border"]} !important;
            box-shadow:
                inset 3px 0 0 {palette["accent"]} !important;
        }}

        {radio_key_class} div[data-testid="stRadio"]
            div[role="radiogroup"] > label,
        {radio_key_class} div[data-testid="stRadio"]
            div[role="radiogroup"] > label p,
        {radio_key_class} div[data-testid="stRadio"]
            div[role="radiogroup"] > label
            [data-testid="stMarkdownContainer"],
        {radio_key_class} div[data-testid="stRadio"]
            div[role="radiogroup"] > label
            [data-testid="stMarkdownContainer"] p {{
            color: {palette["text"]} !important;
            -webkit-text-fill-color: {palette["text"]} !important;
            opacity: 1 !important;
            line-height: 1.5 !important;
            text-align: left !important;
        }}

        {radio_key_class} div[data-testid="stRadio"] input[type="radio"] {{
            accent-color: {palette["accent"]} !important;
        }}

        {radio_key_class} div[data-testid="stRadio"]
            div[role="radiogroup"] > label:focus-within {{
            outline: none !important;
        }}

        {submit_key_class} div[data-testid="stButton"],
        {submit_key_class} button {{
            width: 100% !important;
            max-width: 100% !important;
        }}

        @media (max-width: 1180px) {{
            :root {{
                --day6-quiz-column-width: 100%;
            }}

            .quest-question,
            {radio_key_class},
            {submit_key_class} {{
                width: 100% !important;
                max-width: 100% !important;
            }}
        }}

        @media (max-width: 760px) {{
            {radio_key_class} div[data-testid="stRadio"]
                div[role="radiogroup"] > label {{
                padding: .58rem .68rem !important;
                border-radius: 8px !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_quiz(
    *,
    user,
    world,
    chapter,
) -> None:
    st.markdown(
        generated_text_readability_css(),
        unsafe_allow_html=True,
    )
    _inject_dark_quiz_readability_css(
        world[4]
    )
    if chapter[7]:
        render_chapter_complete(
            user=user,
            world=world,
            chapter=chapter,
        )
        return

    questions = (
        chapter[6]
        or []
    )

    if not questions:
        return

    _initialize_quiz_progress_from_db(
        user=user,
        world=world,
        chapter=chapter,
        questions=questions,
    )

    index = st.session_state.get(
        "question_index",
        0,
    )
    _inject_quiz_choice_card_css(
        world[4],
        chapter_id=chapter[0],
        question_index=index,
    )

    if index >= len(
        questions
    ):
        render_chapter_complete(
            user=user,
            world=world,
            chapter=chapter,
        )
        return

    question = questions[
        index
    ]

    _start_question_timer(
        chapter_id=chapter[0],
        index=index,
    )

    context = get_runtime_story_context(
        world[0]
    )

    arc_id = (
        context["arc"]["id"]
        if context
        else None
    )

    queue_once(
        key=(
            f"question_start_"
            f"{chapter[0]}_{index}"
        ),
        event_type="question_start",
        user_id=user["user_id"],
        world_id=world[0],
        story_arc_id=arc_id,
        chapter_id=chapter[0],
        metadata={
            "question_index": index,
            "concept": question.get(
                "concept"
            ),
            "difficulty": question.get(
                "difficulty"
            ),
        },
    )

    guide_name = (
        world[9]
        if len(world) > 9
        and world[9]
        else "고양이"
    )

    user_name = (
        user.get(
            "display_name"
        )
        or user.get(
            "username"
        )
        or "나"
    )

    task_label = format_inline_text(
        question.get("task_label")
        or ""
    )
    experience_profile = get_theme_experience_profile(world[4])

    if task_label:
        investigation_meta = (
            f"{guide_name}와 함께 · "
            f"{experience_profile['step_noun']} {index + 1} / {len(questions)} · "
            f"{task_label}"
        )
    else:
        investigation_meta = (
            f"{guide_name}와 함께 · "
            f"{experience_profile['step_noun']} {index + 1} / {len(questions)}"
        )

    question_submitted = st.session_state.get(
        "question_submitted",
        False,
    )

    # DAY6_INVESTIGATION_FLOW_UX_V3
    # Evidence는 선택형 행동이 아니라 현재 문제의 고정 관찰 자료로 항상 먼저 보여준다.
    _render_fixed_question_evidence(
        theme=world[4],
        question=question,
    )

    active_action = render_investigation_board(
        theme=world[4],
        guide_name=guide_name,
        chapter_id=chapter[0],
        question_index=index,
        default_action=ACTION_DEDUCE,
        require_companion_before_deduce=False,
        context_meta=investigation_meta,
    )

    if active_action is None:
        return

    if active_action == ACTION_COMPANION:
        # 동료는 Evidence를 반복하지 않고 개념 회상/용어 도움/사고 방향만 제공한다.
        _render_learning_materials(
            theme=world[4],
            learner_level=world[3],
            difficulty=(question.get("difficulty") or "basic"),
            question=question,
            guide_name=guide_name,
            section=ACTION_COMPANION,
        )
    else:
        st.markdown(
            '<span class="inv-question-title-marker"></span>',
            unsafe_allow_html=True,
        )
        render_quiz_question_scene(
            theme=world[4],
            chapter_number=chapter[2],
            chapter_title=format_inline_text(chapter[3]),
            question_number=index + 1,
            question_count=len(questions),
            question_text=format_inline_text(question["question"]),
        )

    if not question_submitted:
        if active_action != ACTION_DEDUCE:
            return

        selected = st.radio(
            "답을 선택하세요.",
            options=range(
                len(
                    question[
                        "choices"
                    ]
                )
            ),
            format_func=lambda i: (
                f"{i + 1}. "
                f"{format_inline_text(question['choices'][i])}"
            ),
            key=(
                f"question_"
                f"{chapter[0]}_{index}"
            ),
        )

        if st.button(
            "응답하기",
            type="primary",
            key=(
                f"submit_"
                f"{chapter[0]}_{index}"
            ),
            use_container_width=True,
        ):
            correct_index = (
                question[
                    "correct_index"
                ]
            )
            is_correct = (
                selected
                == correct_index
            )

            difficulty = (
                question.get(
                    "difficulty"
                )
                or "basic"
            )

            response_time_ms = (
                _response_time_ms()
            )

            create_attempt(
                user_id=user[
                    "user_id"
                ],
                world_id=world[0],
                chapter_id=chapter[0],
                concept=question[
                    "concept"
                ],
                question_text=question[
                    "question"
                ],
                user_answer=question[
                    "choices"
                ][selected],
                is_correct=is_correct,
                difficulty=difficulty,
                response_time_ms=(
                    response_time_ms
                ),
            )

            mastery_update_ok = False
            mastery_score_after = None
            try:
                mastery_score_after = update_mastery_from_attempt(
                    user_id=user[
                        "user_id"
                    ],
                    world_id=world[0],
                    concept=question[
                        "concept"
                    ],
                    is_correct=(
                        is_correct
                    ),
                    difficulty=(
                        difficulty
                    ),
                )
                mastery_update_ok = True
            except Exception:
                # Attempt는 유지하되 파생 Mastery 실패는 반드시 로그로 남긴다.
                LOGGER.exception(
                    "Mastery update failed user_id=%s world_id=%s chapter_id=%s concept=%r",
                    user["user_id"],
                    world[0],
                    chapter[0],
                    question["concept"],
                )

            queue_event(
                "question_answered",
                user_id=user[
                    "user_id"
                ],
                world_id=world[0],
                story_arc_id=arc_id,
                chapter_id=chapter[0],
                metadata={
                    "question_index": index,
                    "concept": question[
                        "concept"
                    ],
                    "difficulty": difficulty,
                    "is_correct": (
                        is_correct
                    ),
                    "response_time_ms": (
                        response_time_ms
                    ),
                    "mastery_update_ok": mastery_update_ok,
                    "mastery_score_after": mastery_score_after,
                },
            )

            st.session_state[
                "selected_answer"
            ] = selected
            st.session_state[
                "question_submitted"
            ] = True
            set_investigation_action(
                chapter_id=chapter[0],
                question_index=index,
                action=ACTION_DEDUCE,
            )
            st.session_state[
                "show_npc_reply"
            ] = False

            st.rerun()

        return

    selected_answer = st.session_state[
        "selected_answer"
    ]

    correct_index = question[
        "correct_index"
    ]

    is_correct = (
        selected_answer
        == correct_index
    )

    user_answer_text = (
        _format_choice_reply(
            choice_number=(selected_answer + 1),
            choice_text=question["choices"][selected_answer],
        )
    )

    feedback = (
        question.get(
            "correct_feedback"
        )
        if is_correct
        else question.get(
            "wrong_feedback"
        )
    )

    if not feedback:
        feedback = (
            "응, 그 선택이 맞아. 다음 단서로 이어가보자."
            if is_correct
            else "조금 어긋난 것 같아. 방금 본 단서를 한 번 더 비교해볼까?"
        )

    feedback_active = render_quiz_feedback_dialogue(
        chapter_id=chapter[0],
        question_index=index,
        theme=world[4],
        chapter_number=chapter[2],
        question_number=index + 1,
        user_name=user_name,
        user_answer_text=user_answer_text,
        guide_name=guide_name,
        feedback=feedback,
        is_correct=is_correct,
    )

    if feedback_active:
        return
    story_progress = _sanitize_learning_text(
        question.get("story_progress")
    )

    if story_progress:
        render_quiz_result_narration(
            theme=world[4],
            text=story_progress,
            is_correct=is_correct,
            is_conclusion_step=(
                index == len(questions) - 1
            ),
        )

    pack = get_theme_pack(
        world[4]
    )

    explanation = (
        question.get(
            "explanation"
        )
        or "핵심 개념을 다시 확인해보세요."
    )

    correct_answer = (
        None
        if is_correct
        else (
            f"{correct_index + 1}. "
            f"{question['choices'][correct_index]}"
        )
    )

    with st.expander(
        "📘 학습 노트 확인하기",
        expanded=False,
    ):
        _render_learning_note(
            label=pack[
                "learning_note"
            ],
            explanation=explanation,
            correct_answer=(
                correct_answer
            ),
        )

    next_label = get_theme_experience_profile(world[4])["next_label"]

    if st.button(
        next_label,
        key=(
            f"next_"
            f"{chapter[0]}_{index}"
        ),
        use_container_width=True,
    ):
        st.session_state[
            "question_index"
        ] = index + 1
        st.session_state[
            "question_submitted"
        ] = False

        clear_investigation_question_state(
            chapter_id=chapter[0],
            question_index=index,
        )

        for key in (
            "selected_answer",
            "show_npc_reply",
            "question_timer_key",
            "question_started_at",
        ):
            if key in (
                st.session_state
            ):
                del st.session_state[
                    key
                ]

        st.rerun()


# V3_ACTION_HUB_V1_20260908
def _render_companion_play_mode(
    *,
    user,
    world,
    chapter,
) -> None:
    """Reuse current-question learning support without generation work."""
    guide_name = (
        world[9]
        if len(world) > 9
        and world[9]
        else "고양이"
    )

    if chapter[7]:
        st.info(
            "이 Chapter는 이미 완료되었습니다. "
            "스토리를 다시 보거나 다음 학습으로 이어갈 수 있습니다."
        )
        return

    questions = (
        chapter[6]
        or []
    )
    if not questions:
        st.info(
            f"{guide_name}의 문제별 학습 도움은 "
            "문제가 준비된 뒤 확인할 수 있습니다."
        )
        st.caption(
            "문제 풀기에서 기존 문제 준비 흐름을 이용하세요. "
            "이 화면 전환만으로는 Gemini를 호출하지 않습니다."
        )
        return

    # 기존 Quiz progress restore를 그대로 재사용한다.
    # 같은 Chapter에서 한 번 초기화되면 session_state guard로 재조회하지 않는다.
    _initialize_quiz_progress_from_db(
        user=user,
        world=world,
        chapter=chapter,
        questions=questions,
    )

    index = int(
        st.session_state.get(
            "question_index",
            0,
        )
    )
    if index >= len(questions):
        st.info(
            "현재 Chapter의 모든 문제에 응답했습니다. "
            "문제 풀기 화면에서 완료 흐름을 이어가세요."
        )
        return

    question = questions[index]
    experience_profile = get_theme_experience_profile(
        world[4]
    )
    st.markdown(
        f"### 🐈 {format_inline_text(guide_name)}와 함께 보기"
    )
    st.caption(
        f"{experience_profile['step_noun']} {index + 1} / {len(questions)} · "
        "현재 문제의 단서와 개념 도움만 확인합니다."
    )

    _render_fixed_question_evidence(
        theme=world[4],
        question=question,
    )
    _render_learning_materials(
        theme=world[4],
        learner_level=world[3],
        difficulty=(
            question.get("difficulty")
            or "basic"
        ),
        question=question,
        guide_name=guide_name,
        section=ACTION_COMPANION,
    )


def render_learning_tab(
    user,
    world,
):
    chapter = get_runtime_chapter(
        world_id=world[0],
        chapter_number=world[7],
    )

    if chapter is None:
        if is_ai_mock_enabled():
            st.caption(f"🧪 {generation_mode_label()} · Gemini 호출 없이 기능 흐름을 테스트 중입니다.")
        st.warning(
            "현재 Chapter가 아직 준비되지 않았습니다."
        )

        st.caption(
            "AI 생성이 중간에 실패했더라도 World, Story Arc, "
            "고양이 이름은 유지됩니다. 저장된 상태에서 다시 생성할 수 있습니다."
        )

        if st.button(
            "첫 Story Outline + Chapter 1 생성 다시 시도",
            type="primary",
            key=(
                f"retry_story_block_"
                f"{world[0]}"
            ),
            use_container_width=True,
        ):
            with st.spinner(
                "Curriculum, Blueprint, 첫 Story Outline을 확인하고 Chapter 1만 준비하고 있습니다..."
            ):
                try:
                    ensure_initial_story_block(
                        user=user,
                        world=world,
                    )

                    invalidate_runtime_world(
                        world[0]
                    )

                    update_current_chapter(
                        world_id=world[0],
                        chapter_number=1,
                    )

                    reset_quiz_state()
                    st.rerun()

                except AIQuotaExhausted:
                    st.error(
                        "Gemini의 일일 무료 요청 할당량이 소진되었습니다. "
                        "자동 재시도는 중단했습니다. 할당량이 갱신된 뒤 다시 시도해주세요."
                    )

                except Exception as exc:
                    traceback.print_exc()
                    st.error(
                        "첫 Story Outline 또는 Chapter 1 생성에 실패했습니다. "
                        "이미 성공한 Curriculum/Blueprint 단계는 유지되며 "
                        "실패한 단계부터 다시 시도할 수 있습니다."
                    )
                    st.caption(
                        f"개발용 오류 유형: {type(exc).__name__} · "
                        "상세 내용은 터미널과 AI Generation Log를 확인해주세요."
                    )

        return

    # V3_PLAY_MODE_STATE_CORE_V1_20260908
    # Story의 최초 재생 여부를 play_mode state machine의 강제 진입 조건으로 사용한다.
    # 아직 Action Hub를 노출하지 않으므로 review/companion은 상태 계약만 예약하고
    # 기존 visible UI는 story -> quiz 흐름을 그대로 유지한다.
    story_pending = (
        should_render_dialogue_story(
            chapter_id=chapter[0],
            story_text=chapter[4],
        )
        or should_render_story_cinematic(
            chapter_id=chapter[0],
            story_text=chapter[4],
        )
    )

    play_mode = resolve_play_mode(
        world_id=world[0],
        chapter_id=chapter[0],
        story_pending=story_pending,
    )

    # Dedicated Story presentation 중에는 mock caption을 포함한 다른 학습 UI를 먼저 렌더하지 않는다.
    if play_mode == PLAY_MODE_STORY:
        _render_chapter_story(
            user=user,
            world=world,
            chapter=chapter,
        )
        return

    if is_ai_mock_enabled():
        st.caption(f"🧪 {generation_mode_label()} · Gemini 호출 없이 기능 흐름을 테스트 중입니다.")

    # V3_ACTION_HUB_V1_20260908
    # Hub click은 play_mode session state만 바꾸며 DB/Gemini 작업을 직접 수행하지 않는다.
    guide_name = (
        world[9]
        if len(world) > 9
        and world[9]
        else "고양이"
    )
    render_play_action_hub(
        world_id=world[0],
        chapter_id=chapter[0],
        active_mode=play_mode,
        guide_name=guide_name,
    )

    cinematic_active = _render_chapter_story(
        user=user,
        world=world,
        chapter=chapter,
        review_expanded=(
            play_mode
            == PLAY_MODE_REVIEW
        ),
    )

    if cinematic_active:
        return

    if play_mode == PLAY_MODE_REVIEW:
        return

    if play_mode == PLAY_MODE_COMPANION:
        _render_companion_play_mode(
            user=user,
            world=world,
            chapter=chapter,
        )
        return

    if play_mode != PLAY_MODE_QUIZ:
        return

    questions = (
        chapter[6]
        or []
    )

    if not questions:
        pack = get_theme_pack(
            world[4]
        )

        with st.container(
            border=True
        ):
            st.markdown(
                f"### {pack['quest_label']}"
            )

            targets = (
                chapter[
                    CHAPTER_TARGET_CONCEPTS
                ]
                if len(chapter)
                > CHAPTER_TARGET_CONCEPTS
                else []
            )

            if targets:
                st.caption(
                    "이번 문제는 Curriculum의 "
                    + ", ".join(
                        targets
                    )
                    + " Concept에 집중합니다."
                )

            requested_difficulty = (
                choose_requested_difficulty(
                    learner_level=(
                        world[3]
                    ),
                    user_id=user[
                        "user_id"
                    ],
                    world_id=world[0],
                    target_concepts=(
                        targets
                    ),
                )
            )

            support_profile = get_learner_level_profile(world[3])
            reasoning_profile = get_reasoning_profile(requested_difficulty)
            adaptive_support = get_adaptive_support_profile(
                user_id=user["user_id"],
                world_id=world[0],
                target_concepts=targets,
            )
            st.caption(
                f"학습 지원 · {support_profile['display_name']} · "
                f"현재 사고 난이도 · {reasoning_profile['label']}"
            )
            st.caption(
                f"개인화 · {adaptive_support['label']}"
            )

            interaction_context = get_chapter_interaction_context(
                world_id=world[0],
                chapter_number=chapter[2],
                theme=world[4],
            )

            experience_profile = get_theme_experience_profile(world[4])
            st.caption(
                f"이번 {experience_profile['interaction_noun']} · "
                f"{interaction_context.get('label') or '상황 적용'}"
            )

            prepare_label = experience_profile["prepare_label"].format(
                count=QUESTION_COUNT
            )

            if st.button(
                prepare_label,
                type="primary",
                key=(
                    f"generate_questions_"
                    f"{chapter[0]}"
                ),
                use_container_width=True,
            ):
                context = (
                    get_story_context(
                        world[0]
                    )
                )
                foundation = get_world_foundation(
                    world[0]
                )
                concept_contracts = get_concept_contracts(
                    curriculum=(
                        (foundation or {}).get("curriculum")
                    ),
                    target_concepts=targets,
                )

                spinner_text = experience_profile["spinner_label"].format(
                    count=QUESTION_COUNT
                )

                with st.spinner(
                    spinner_text
                ):
                    try:
                        generated_questions = (
                            generate_chapter_questions(
                                topic=world[1],
                                learner_level=(
                                    world[3]
                                ),
                                theme=world[4],
                                chapter_title=(
                                    chapter[3]
                                ),
                                chapter_story=(
                                    chapter[4]
                                ),
                                learning_objectives=(
                                    chapter[5]
                                ),
                                target_concepts=(
                                    targets
                                ),
                                concept_contracts=(
                                    concept_contracts
                                ),
                                requested_difficulty=(
                                    requested_difficulty
                                ),
                                adaptive_support=(
                                    adaptive_support
                                ),
                                guide_name=(
                                    world[9]
                                    if len(world) > 9
                                    else None
                                ),
                                interaction_mode=(
                                    interaction_context.get(
                                        "mode"
                                    )
                                ),
                                interaction_goal=(
                                    interaction_context.get(
                                        "goal"
                                    )
                                ),
                                chapter_number=chapter[2],
                                target_chapter_count=(
                                    context["arc"].get("target_chapter_count")
                                    if context
                                    else None
                                ),
                                current_open_threads=(
                                    (context.get("state") or {}).get("open_threads", [])
                                    if context
                                    else []
                                ),
                                user_id=user[
                                    "user_id"
                                ],
                                world_id=world[0],
                                story_arc_id=(
                                    context[
                                        "arc"
                                    ]["id"]
                                    if context
                                    else None
                                ),
                            )
                        )

                        update_chapter_questions(
                            chapter_id=(
                                chapter[0]
                            ),
                            questions=(
                                generated_questions
                            ),
                        )

                        invalidate_runtime_chapter(
                            world_id=world[0],
                            chapter_number=chapter[2],
                        )

                        reset_quiz_state()
                        st.rerun()

                    except QuestionGenerationError as exc:
                        st.error(
                            str(exc)
                        )

                    except Exception:
                        st.error(
                            "문제를 생성하는 중 문제가 발생했습니다. "
                            "잠시 후 다시 시도해주세요."
                        )

        return

    render_quiz(
        user=user,
        world=world,
        chapter=chapter,
    )

# DAY6_SINGLE_STICKY_QUIZ_HUD_V1

# DAY6_RESTORE_STACKED_STICKY_EVIDENCE_V1

# DAY6_DOUBLE_STICKY_COMPACT_TUNING_V1

# QUIZ_ANSWER_REPLY_DECIMAL_HOTFIX_V1_0_1_20260904

# COMPACT_TOOLS_ROW_ALIGNMENT_V1_20260906

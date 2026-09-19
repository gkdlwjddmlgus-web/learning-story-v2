# DAY5_EVENT_FLUSH_FIX_V1
from __future__ import annotations

# CURRICULUM_SEMANTIC_CONTRACT_V1_20260906

import base64
import hashlib
import math
import mimetypes
import logging
import html
import re
import time
import traceback
from pathlib import Path

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
    resolve_companion_action_portrait,
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
from components.dialogue_scene import (
    render_dialogue_scene,
)
from services.dialogue_runtime_service import (
    build_dialogue_beats,
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
    PLAY_MODE_NOTE,
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
QUESTION_GENERATION_COOLDOWN_SECONDS = 120

LOGGER = logging.getLogger(__name__)


def _question_generation_retry_key(
    *,
    world_id: int,
    chapter_id: int,
) -> str:
    return (
        "_v3_question_generation_retry_after_"
        f"{int(world_id)}_{int(chapter_id)}"
    )


def _start_question_generation_cooldown(
    *,
    world_id: int,
    chapter_id: int,
    now: float | None = None,
) -> None:
    current = time.time() if now is None else float(now)
    st.session_state[
        _question_generation_retry_key(
            world_id=world_id,
            chapter_id=chapter_id,
        )
    ] = current + QUESTION_GENERATION_COOLDOWN_SECONDS


def _question_generation_retry_remaining(
    *,
    world_id: int,
    chapter_id: int,
    now: float | None = None,
) -> int:
    key = _question_generation_retry_key(
        world_id=world_id,
        chapter_id=chapter_id,
    )
    retry_after = float(
        st.session_state.get(key, 0.0)
        or 0.0
    )
    current = time.time() if now is None else float(now)
    remaining = retry_after - current

    if remaining <= 0:
        st.session_state.pop(key, None)
        return 0

    return int(math.ceil(remaining))


def _render_question_generation_cooldown(
    *,
    world_id: int,
    chapter_id: int,
    prepare_label: str,
) -> bool:
    retry_remaining = _question_generation_retry_remaining(
        world_id=world_id,
        chapter_id=chapter_id,
    )
    if retry_remaining <= 0:
        return False

    st.warning(
        "현재 AI 사용량이 몰려 문제 준비가 잠시 지연되고 있습니다. "
        "사용자 입력 문제나 앱 중단이 아니며, 학습 기록은 안전하게 유지됩니다."
    )
    st.caption(
        f"약 {retry_remaining}초 후 다시 시도할 수 있습니다. "
        "자동 재시도는 실행되지 않습니다."
    )
    st.button(
        prepare_label,
        key=f"generate_questions_{int(chapter_id)}",
        disabled=True,
        width="stretch",
    )
    if st.button(
        "다시 시도할 수 있는지 확인",
        key=(
            "question_retry_status_"
            f"{int(world_id)}_{int(chapter_id)}"
        ),
    ):
        st.rerun()
    return True

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
    render_header: bool = True,
    render_tools: bool = True,
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

    if render_header:
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
            guide_name=(
                world[9]
                if len(world) > 9
                else None
            ),
            learner_level=world[3],
            topic=world[1],
        )

    if render_tools:
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


def _story_choice_type(choice: dict | None) -> str:
    """Old saved Chapters default to action; only explicit metadata enables Player speech."""
    if not isinstance(choice, dict):
        return "action"

    value = str(
        choice.get("choice_type")
        or "action"
    ).strip().lower()

    return (
        "dialogue"
        if value == "dialogue"
        else "action"
    )


def _selected_story_choice_payload(
    *,
    selected: dict,
    choices: list,
) -> dict:
    selected_key = str(
        selected.get("choice_key")
        or ""
    )
    selected_text = str(
        selected.get("choice_text")
        or ""
    )

    for choice in choices:
        if not isinstance(choice, dict):
            continue

        choice_key = str(
            choice.get("key")
            or ""
        )
        choice_text = str(
            choice.get("text")
            or ""
        )

        if (
            selected_key
            and choice_key == selected_key
        ) or (
            selected_text
            and choice_text == selected_text
        ):
            return choice

    # Existing persisted choices predate choice_type. Never infer Player
    # dialogue from prose shape; the safe backward-compatible default is action.
    return {
        "key": selected_key,
        "text": selected_text,
        "choice_type": "action",
    }


def _story_choice_dialogue_ack_key(
    chapter_id: int,
) -> str:
    return (
        "_v3_story_choice_dialogue_ack_"
        f"{int(chapter_id)}"
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

    guide_name = (
        world[9]
        if len(world) > 9
        and world[9]
        else "고양이"
    )
    companion_portrait = resolve_portrait(
        world[4],
        "companion",
        character_id="default",
    )
    background_path = _v3_context_image_path(
        theme=world[4],
        chapter_number=chapter[2],
    )

    if selected:
        selected_choice = _selected_story_choice_payload(
            selected=selected,
            choices=choices,
        )
        selected_text = str(
            selected.get("choice_text")
            or selected_choice.get("text")
            or ""
        ).strip()
        choice_type = _story_choice_type(
            selected_choice
        )

        # V3_STORY_CHOICE_AGENCY_CONTRACT_V1_20260908
        # A Player line exists only after the user has explicitly selected a
        # dialogue-type Story Choice. The chosen text itself is replayed once;
        # no new Player line is generated or inferred.
        if choice_type == "dialogue":
            ack_key = (
                _story_choice_dialogue_ack_key(
                    chapter[0]
                )
            )
            if not bool(
                st.session_state.get(
                    ack_key,
                    False,
                )
            ):
                player_portrait = resolve_portrait(
                    world[4],
                    "player",
                    character_id="default",
                )
                user_name = (
                    user.get("display_name")
                    or user.get("username")
                    or "나"
                )

                render_dialogue_scene(
                    theme=world[4],
                    speaker_type="player",
                    speaker_name=user_name,
                    text=selected_text,
                    portrait_path=player_portrait,
                    player_portrait_path=player_portrait,
                    companion_portrait_path=companion_portrait,
                    background_path=background_path,
                    context_label=(
                        f"CHAPTER {chapter[2]} · 선택의 순간"
                    ),
                    show_next_button=False,
                    show_scene_chrome=True,
                )

                if st.button(
                    "이 선택으로 이야기를 이어간다 →",
                    key=(
                        "v3_story_choice_dialogue_continue_"
                        f"{chapter[0]}"
                    ),
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state[
                        ack_key
                    ] = True
                    st.rerun()

                return False

        # Action choices never become Player dialogue.
        st.info(
            "선택한 방향 · "
            + selected_text
        )
        return True

    render_dialogue_scene(
        theme=world[4],
        speaker_type="narrator",
        speaker_name="NARRATOR",
        text=(
            "이제 이야기의 다음 방향을 직접 선택할 차례입니다. "
            "말해야 하는 순간에만 대화 선택지가 Player의 발화로 이어집니다."
        ),
        companion_portrait_path=companion_portrait,
        background_path=background_path,
        context_label=(
            f"CHAPTER {chapter[2]} · STORY CHOICE"
        ),
        show_next_button=False,
        show_scene_chrome=True,
    )

    st.markdown(
        '<div class="v3-story-choice-heading">'
        '<strong>이야기에서 무엇을 할까?</strong>'
        '<span>선택한 방향은 다음 Story Block의 첫 장면에 반영됩니다.</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    for choice in choices:
        if not isinstance(choice, dict):
            continue

        key = str(
            choice.get(
                "key",
                "",
            )
        )
        choice_text = str(
            choice.get(
                "text",
                "",
            )
        )
        choice_type = _story_choice_type(
            choice
        )

        if not key or not choice_text:
            continue

        choice_prefix = (
            "💬 "
            if choice_type == "dialogue"
            else "➜ "
        )

        if st.button(
            choice_prefix + choice_text,
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
                choice_text=choice_text,
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
                    "choice_text": choice_text,
                    "choice_type": choice_type,
                },
                flush=True,
            )

            st.session_state.pop(
                _story_choice_dialogue_ack_key(
                    chapter[0]
                ),
                None,
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

# V3_FULL_EXPECTED_PLAY_UI_V1_20260908
_THEME_ASSET_SLUG = {
    "동화": "fairy",
    "판타지": "fantasy",
    "SF": "sf",
    "무협": "wuxia",
    "미스터리": "mystery",
}


def _v3_context_image_path(
    *,
    theme: str,
    chapter_number: int,
) -> Path | None:
    slug = _THEME_ASSET_SLUG.get(
        theme
    )
    if not slug:
        return None

    index = (
        (max(1, int(chapter_number)) - 1)
        % 8
        + 1
    )
    base = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "backgrounds"
        / slug
    )

    for extension in (
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    ):
        candidate = (
            base
            / f"map{index}{extension}"
        )
        if candidate.is_file():
            return candidate

    return None


def _v3_file_data_uri(
    path: str | Path | None,
) -> str | None:
    if not path:
        return None

    file_path = Path(path)
    if not file_path.is_file():
        return None

    mime_type, _ = mimetypes.guess_type(
        file_path.name
    )
    mime_type = mime_type or "image/png"
    encoded = base64.b64encode(
        file_path.read_bytes()
    ).decode("ascii")
    return (
        f"data:{mime_type};base64,{encoded}"
    )


def _v3_story_evidence_items(
    chapter,
) -> list[str]:
    items: list[str] = []

    for question in (
        chapter[6]
        or []
    ):
        for key in (
            "evidence_summary",
            "evidence_context",
        ):
            value = _sanitize_learning_text(
                question.get(key)
            )
            if value and value not in items:
                items.append(value)
            if len(items) >= 3:
                return items

    for objective in (
        chapter[5]
        or []
    ):
        value = _sanitize_learning_text(
            objective
        )
        if value and value not in items:
            items.append(value)
        if len(items) >= 3:
            break

    return items


def _render_v3_story_review_panel(
    *,
    world,
    chapter,
) -> None:
    """Render Story Review as a stable three-panel game surface."""
    guide_name = (
        world[9]
        if len(world) > 9
        and world[9]
        else "고양이"
    )
    beats = build_dialogue_beats(
        story_text=chapter[4],
        guide_name=guide_name,
    )

    if not beats:
        return

    scene_key = (
        f"v3_review_scene_"
        f"{int(chapter[0])}"
    )
    selected_scene = int(
        st.session_state.get(
            scene_key,
            0,
        )
    )
    selected_scene = max(
        0,
        min(
            selected_scene,
            len(beats) - 1,
        ),
    )

    st.markdown(
        '<div class="v3-mode-heading">'
        '<span class="v3-mode-icon">📜</span>'
        '<span><strong>기록의 두루마리</strong>'
        '<small>장면을 선택해 이야기와 단서를 함께 확인합니다.</small></span>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.session_state.setdefault(
        scene_key,
        selected_scene,
    )
    selected_scene = st.segmented_control(
        "스토리 장면",
        options=range(len(beats)),
        format_func=lambda i: str(i + 1),
        key=scene_key,
        label_visibility="collapsed",
        width="content",
    )
    selected_scene = int(selected_scene or 0)

    story_col, clue_col = st.columns(
        [0.72, 0.28],
        gap="medium",
    )

    with story_col:
        beat = beats[selected_scene]
        background_path = _v3_context_image_path(
            theme=world[4],
            chapter_number=chapter[2],
        )
        companion_portrait = resolve_companion_action_portrait(
            world[4],
            "investigate",
        )
        background_uri = _v3_file_data_uri(
            background_path
        )
        companion_uri = _v3_file_data_uri(
            companion_portrait
        )
        safe_text = html.escape(
            format_inline_text(
                _sanitize_learning_text(
                    beat.text
                )
            )
        )
        background_style = (
            f'background-image:url("{background_uri}");'
            if background_uri
            else ""
        )
        companion_state = (
            "is-active"
            if beat.speaker_type == "companion"
            else "is-dim"
        )
        portrait_html = (
            '<div class="v3-review-character v3-review-character-v32 '
            f'{companion_state}">'
            f'<img src="{companion_uri}" alt="companion">'
            '</div>'
            if companion_uri
            else ""
        )
        if beat.speaker_type == "companion":
            speaker_label = html.escape(
                format_inline_text(
                    beat.speaker_name
                    or guide_name
                )
            )
        elif beat.speaker_type == "npc":
            speaker_label = html.escape(
                format_inline_text(
                    beat.speaker_name
                    or "NPC"
                )
            )
        else:
            speaker_label = "NARRATION"

        st.markdown(
            '<section class="v3-review-stage v3-review-stage-v32" '
            f'style="{html.escape(background_style, quote=True)}">'
            f'{portrait_html}'
            '<div class="v3-review-dialogue v3-review-dialogue-v32">'
            f'<div class="v3-review-speaker">{speaker_label}</div>'
            f'<div class="v3-review-scene-label">SCENE {selected_scene + 1}</div>'
            f'<div class="v3-review-text">{safe_text}</div>'
            '</div>'
            '</section>',
            unsafe_allow_html=True,
        )

    with clue_col:
        evidence_items = _v3_story_evidence_items(
            chapter
        )
        if evidence_items:
            evidence_html = "".join(
                '<li>'
                + html.escape(
                    format_inline_text(
                        _sanitize_learning_text(
                            item
                        )
                    )
                )
                + '</li>'
                for item in evidence_items
            )
        else:
            evidence_html = (
                '<div class="v3-review-side-empty">'
                '아직 정리된 단서가 없습니다.'
                '</div>'
            )

        targets = (
            chapter[CHAPTER_TARGET_CONCEPTS]
            if len(chapter) > CHAPTER_TARGET_CONCEPTS
            else []
        )
        keyword_values = (
            [
                format_inline_text(
                    _sanitize_learning_text(
                        item
                    )
                )
                for item in targets
                if _sanitize_learning_text(
                    item
                )
            ]
            if targets
            else [
                format_inline_text(
                    _sanitize_learning_text(
                        world[1]
                    )
                )
            ]
        )
        keyword_html = "".join(
            '<span class="v3-review-keyword-chip">'
            + html.escape(value)
            + '</span>'
            for value in keyword_values
            if value
        )

        st.markdown(
            '<div class="v3-review-side-stack">'
            '<section class="v3-review-side-card v3-review-clue-card">'
            '<div class="v3-review-side-title">🔎 주요 단서</div>'
            + (
                '<ul class="v3-review-side-list">'
                + evidence_html
                + '</ul>'
                if evidence_items
                else evidence_html
            )
            + '</section>'
            '<section class="v3-review-side-card v3-review-keyword-card">'
            '<div class="v3-review-side-title">핵심 키워드</div>'
            '<div class="v3-review-keyword-wrap">'
            + (
                keyword_html
                or '<span class="v3-review-side-empty">정리된 키워드가 없습니다.</span>'
            )
            + '</div>'
            '</section>'
            '</div>',
            unsafe_allow_html=True,
        )



def _render_v3_shell_nav(
    *,
    world,
) -> None:
    pack = get_theme_pack(
        world[4]
    )
    section_key = (
        f"v3_main_section_{world[0]}"
    )

    spacer, archive_col, report_col = st.columns(
        [0.82, 0.09, 0.09],
        gap="small",
    )

    with spacer:
        st.markdown(
            '<span class="v3-game-shell-marker"></span>',
            unsafe_allow_html=True,
        )

    with archive_col:
        if st.button(
            "📚 기록",
            key=f"v3_shell_archive_{world[0]}",
            help=pack["archive_name"],
            use_container_width=True,
        ):
            st.session_state[section_key] = pack["archive_name"]
            st.rerun()

    with report_col:
        if st.button(
            "📊 분석",
            key=f"v3_shell_report_{world[0]}",
            help=pack["report_name"],
            use_container_width=True,
        ):
            st.session_state[section_key] = pack["report_name"]
            st.rerun()




# V3_QUIZ_EVIDENCE_VISUAL_CONTRACT_FIX_V3_1_20260908
def _render_v3_quiz_evidence_card(
    *,
    task_label: str,
    evidence_summary: str,
    evidence_context: str,
) -> None:
    """
    Render Quiz Evidence as one owned HTML surface.

    Streamlit's bordered-container descendants inherit theme rules through
    several generated wrappers. Styling only the outer wrapper therefore
    produced a dark card while some nested Markdown text remained dark.
    Keeping the Evidence copy in one semantic HTML surface makes contrast
    deterministic across Mystery/Fantasy/SF themes.
    """
    safe_task = html.escape(
        _sanitize_learning_text(
            task_label
        )
    )
    safe_summary = html.escape(
        _sanitize_learning_text(
            evidence_summary
        )
    )
    safe_context = html.escape(
        _sanitize_learning_text(
            evidence_context
        )
    )

    parts = [
        '<section class="v3-evidence-card">',
        '<div class="v3-evidence-kicker">EVIDENCE</div>',
    ]

    if safe_task:
        parts.append(
            '<div class="v3-evidence-task">'
            f'{safe_task}'
            '</div>'
        )

    if safe_summary:
        parts.extend(
            [
                '<div class="v3-evidence-heading">단서 요약</div>',
                '<p class="v3-evidence-copy">',
                safe_summary,
                '</p>',
            ]
        )

    if safe_context:
        parts.extend(
            [
                '<div class="v3-evidence-heading">검토 보고서</div>',
                '<p class="v3-evidence-copy">',
                safe_context,
                '</p>',
            ]
        )

    if not safe_summary and not safe_context:
        parts.append(
            '<p class="v3-evidence-empty">'
            '현재 문제에 별도의 Evidence가 저장되어 있지 않습니다.'
            '</p>'
        )

    parts.append(
        '</section>'
    )

    st.markdown(
        "".join(
            parts
        ),
        unsafe_allow_html=True,
    )


def render_quiz(
    *,
    user,
    world,
    chapter,
) -> None:
    """V3 compact game-style two-panel Quiz; write semantics are preserved."""
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

    questions = chapter[6] or []
    if not questions:
        return

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
        render_chapter_complete(
            user=user,
            world=world,
            chapter=chapter,
        )
        return

    question = questions[index]
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
        key=f"question_start_{chapter[0]}_{index}",
        event_type="question_start",
        user_id=user["user_id"],
        world_id=world[0],
        story_arc_id=arc_id,
        chapter_id=chapter[0],
        metadata={
            "question_index": index,
            "concept": question.get("concept"),
            "difficulty": question.get("difficulty"),
        },
    )

    guide_name = (
        world[9]
        if len(world) > 9 and world[9]
        else "고양이"
    )
    user_name = (
        user.get("display_name")
        or user.get("username")
        or "나"
    )
    question_submitted = bool(
        st.session_state.get(
            "question_submitted",
            False,
        )
    )

    evidence_summary = _sanitize_learning_text(
        question.get("evidence_summary")
    )
    evidence_context = _sanitize_learning_text(
        question.get("evidence_context")
    )
    task_label = _sanitize_learning_text(
        question.get("task_label")
    )

    evidence_col, problem_col = st.columns(
        [0.36, 0.64],
        gap="medium",
    )

    with evidence_col:
        st.markdown(
            '<div class="v3-panel-title"><span>🔎</span>'
            '<span><strong>사건의 단서</strong>'
            '<small>문제를 풀기 전에 확인해야 할 정보입니다.</small></span></div>',
            unsafe_allow_html=True,
        )
        # The contextual scene image now owns the full play-shell background.
        # A compact record prop preserves the clue affordance without
        # duplicating the same large image inside the evidence column.
        st.markdown(
            '<div class="v3-evidence-object" role="img" '
            'aria-label="사건 기록 문서">📜</div>',
            unsafe_allow_html=True,
        )
        _render_v3_quiz_evidence_card(
            task_label=task_label,
            evidence_summary=evidence_summary,
            evidence_context=evidence_context,
        )

    with problem_col:
        st.markdown(
            '<div class="v3-panel-title"><span>❔</span>'
            '<span><strong>문제</strong>'
            f'<small>조사 {index + 1} / {len(questions)}</small></span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<section class="v3-question-card">'
            '<div class="v3-question-kicker">QUESTION</div>'
            f'<div class="v3-question-progress">Q {index + 1} / {len(questions)}</div>'
            f'<div class="v3-question-text">{html.escape(format_inline_text(question["question"]))}</div>'
            '</section>',
            unsafe_allow_html=True,
        )

        if not question_submitted:
            selected = st.radio(
                "답을 선택하세요.",
                options=range(len(question["choices"])),
                format_func=lambda i: (
                    f"{i + 1}. {format_inline_text(question['choices'][i])}"
                ),
                key=f"question_{chapter[0]}_{index}",
                label_visibility="collapsed",
            )

            if st.button(
                "✦ 답안을 제출하기",
                type="primary",
                key=f"submit_{chapter[0]}_{index}",
                use_container_width=True,
            ):
                correct_index = question["correct_index"]
                is_correct = selected == correct_index
                difficulty = question.get("difficulty") or "basic"
                response_time_ms = _response_time_ms()

                create_attempt(
                    user_id=user["user_id"],
                    world_id=world[0],
                    chapter_id=chapter[0],
                    concept=question["concept"],
                    question_text=question["question"],
                    user_answer=question["choices"][selected],
                    is_correct=is_correct,
                    difficulty=difficulty,
                    response_time_ms=response_time_ms,
                )

                mastery_update_ok = False
                mastery_score_after = None
                try:
                    mastery_score_after = update_mastery_from_attempt(
                        user_id=user["user_id"],
                        world_id=world[0],
                        concept=question["concept"],
                        is_correct=is_correct,
                        difficulty=difficulty,
                    )
                    mastery_update_ok = True
                except Exception:
                    LOGGER.exception(
                        "Mastery update failed user_id=%s world_id=%s chapter_id=%s concept=%r",
                        user["user_id"],
                        world[0],
                        chapter[0],
                        question["concept"],
                    )

                queue_event(
                    "question_answered",
                    user_id=user["user_id"],
                    world_id=world[0],
                    story_arc_id=arc_id,
                    chapter_id=chapter[0],
                    metadata={
                        "question_index": index,
                        "concept": question["concept"],
                        "difficulty": difficulty,
                        "is_correct": is_correct,
                        "response_time_ms": response_time_ms,
                        "mastery_update_ok": mastery_update_ok,
                        "mastery_score_after": mastery_score_after,
                    },
                )
                st.session_state["selected_answer"] = selected
                st.session_state["question_submitted"] = True
                set_investigation_action(
                    chapter_id=chapter[0],
                    question_index=index,
                    action=ACTION_DEDUCE,
                )
                st.session_state["show_npc_reply"] = False
                st.rerun()
            return

        selected_answer = st.session_state["selected_answer"]
        correct_index = question["correct_index"]
        is_correct = selected_answer == correct_index
        user_answer_text = _format_choice_reply(
            choice_number=selected_answer + 1,
            choice_text=question["choices"][selected_answer],
        )
        feedback = (
            question.get("correct_feedback")
            if is_correct
            else question.get("wrong_feedback")
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
                is_conclusion_step=(index == len(questions) - 1),
            )

        pack = get_theme_pack(world[4])
        explanation = question.get("explanation") or "핵심 개념을 다시 확인해보세요."
        correct_answer = (
            None
            if is_correct
            else f"{correct_index + 1}. {question['choices'][correct_index]}"
        )
        with st.expander("📘 학습 노트 확인하기", expanded=False):
            _render_learning_note(
                label=pack["learning_note"],
                explanation=explanation,
                correct_answer=correct_answer,
            )

        next_label = get_theme_experience_profile(world[4])["next_label"]
        if st.button(
            next_label,
            key=f"next_{chapter[0]}_{index}",
            use_container_width=True,
        ):
            st.session_state["question_index"] = index + 1
            st.session_state["question_submitted"] = False
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
                st.session_state.pop(key, None)
            st.rerun()




# V3_ACTION_HUB_V1_20260908
def _render_companion_play_mode(
    *,
    user,
    world,
    chapter,
) -> None:
    """V3 companion conversation using only stored question support data."""
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
            f"{guide_name}와의 문제별 대화는 "
            "문제가 준비된 뒤 확인할 수 있습니다."
        )
        return

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
    prompt_key = (
        f"v3_companion_prompt_"
        f"{chapter[0]}_{index}"
    )

    selected_prompt = int(
        st.session_state.get(
            prompt_key,
            0,
        )
    )

    prompts = [
        "핵심 개념을 다시 설명해줘.",
        "어떤 단서를 먼저 봐야 할까?",
        "이상한 점을 어떻게 판단하지?",
        "지금까지의 단서를 정리해줘.",
        "다른 관점에서 생각할 방법이 있을까?",
    ]

    concept_brief = _sanitize_learning_text(
        question.get(
            "concept_brief"
        )
    )
    evidence_summary = _sanitize_learning_text(
        question.get(
            "evidence_summary"
        )
    )
    evidence_context = _sanitize_learning_text(
        question.get(
            "evidence_context"
        )
    )
    evidence_help = _sanitize_learning_text(
        question.get(
            "evidence_help"
        )
    )

    responses = [
        (
            concept_brief
            or evidence_help
            or "문제에서 반복되는 핵심 용어와 조건을 먼저 한 문장으로 묶어보자."
        ),
        (
            evidence_help
            or evidence_summary
            or "문제에서 직접 주어진 값과 비교해야 하는 조건부터 표시해보자."
        ),
        (
            (
                f"{evidence_summary} "
                "이 단서가 다른 정보와 어디에서 어긋나는지 비교해보면 좋아."
            ).strip()
            if evidence_summary
            else (
                "서로 같은 기준으로 비교되고 있는지, 빠진 조건은 없는지 확인해보자."
            )
        ),
        (
            " / ".join(
                item
                for item in (
                    evidence_summary,
                    evidence_context,
                )
                if item
            )
            or "확인한 정보와 아직 확인하지 않은 정보를 나눠 적어보자."
        ),
        (
            "정답을 바로 고르기보다, 각 선택지가 맞다고 가정했을 때 "
            "현재 단서와 충돌하는 부분이 있는지 하나씩 지워보자."
        ),
    ]

    selected_prompt = max(
        0,
        min(
            selected_prompt,
            len(prompts) - 1,
        ),
    )

    portrait_col, talk_col = st.columns(
        [0.34, 0.66],
        gap="medium",
    )

    with portrait_col:
        st.markdown(
            '<div class="v3-panel-title">'
            '<span>🐾</span>'
            f'<span><strong>{html.escape(format_inline_text(guide_name))}와의 대화</strong>'
            '<small>궁금한 것을 선택하면 저장된 학습 도움으로 함께 생각합니다.</small></span>'
            '</div>',
            unsafe_allow_html=True,
        )

        portrait_actions = (
            "explain",
            "investigate",
            "thinking",
            "notebook",
            "thinking",
        )
        portrait_path = resolve_companion_action_portrait(
            world[4],
            portrait_actions[selected_prompt],
        )
        if portrait_path is not None:
            st.image(
                str(portrait_path),
                width="stretch",
            )

        _render_character_interaction(
            theme=world[4],
            speaker_type="companion",
            speaker_name=guide_name,
            message=(
                "어떤 부분이 가장 궁금해? "
                "정답을 바로 말하기보다 같이 단서를 정리해보자."
            ),
            tone="neutral",
        )

    with talk_col:
        st.markdown(
            '<div class="v3-companion-progress">'
            f'현재 문제 · {index + 1} / {len(questions)}'
            '</div>',
            unsafe_allow_html=True,
        )

        prompt_columns = st.columns(
            2,
            gap="small",
        )

        for prompt_index, prompt in enumerate(
            prompts
        ):
            with prompt_columns[
                prompt_index % 2
            ]:
                if st.button(
                    f"💬 {prompt}",
                    key=(
                        f"v3_companion_prompt_btn_"
                        f"{chapter[0]}_{index}_{prompt_index}"
                    ),
                    type=(
                        "primary"
                        if prompt_index
                        == selected_prompt
                        else "secondary"
                    ),
                    use_container_width=True,
                ):
                    st.session_state[
                        prompt_key
                    ] = prompt_index
                    selected_prompt = (
                        prompt_index
                    )

        safe_guide_name = html.escape(
            format_inline_text(
                guide_name
            )
        )
        safe_response = html.escape(
            format_inline_text(
                responses[
                    selected_prompt
                ]
            )
        )
        st.markdown(
            '<section class="v3-companion-hint-card">'
            '<div class="v3-companion-hint-title">'
            f'{safe_guide_name}의 힌트'
            '</div>'
            '<div class="v3-companion-hint-copy">'
            f'{safe_response}'
            '</div>'
            '</section>',
            unsafe_allow_html=True,
        )

        if evidence_summary:
            st.markdown(
                '<div class="v3-companion-evidence-line">'
                '<span>현재 확인된 단서</span>'
                '<strong>'
                + html.escape(
                    format_inline_text(
                        evidence_summary
                    )
                )
                + '</strong>'
                '</div>',
                unsafe_allow_html=True,
            )



def _render_learning_note_mode(
    *,
    user,
    world,
    chapter,
) -> None:
    """Render saved material as an open book using guarded quiz progress."""
    questions = chapter[6] or []
    if questions:
        _initialize_quiz_progress_from_db(
            user=user,
            world=world,
            chapter=chapter,
            questions=questions,
        )
    index = int(st.session_state.get("question_index", 0))
    question = questions[index] if questions and index < len(questions) else {}
    concept = _sanitize_learning_text(question.get("concept"))
    concept_brief = _sanitize_learning_text(question.get("concept_brief"))
    explanation = _sanitize_learning_text(question.get("explanation"))
    evidence = _sanitize_learning_text(question.get("evidence_summary"))
    targets = (
        chapter[CHAPTER_TARGET_CONCEPTS]
        if len(chapter) > CHAPTER_TARGET_CONCEPTS
        else []
    )
    safe_title = html.escape(concept or "이번 Chapter의 핵심 개념")
    safe_brief = html.escape(
        concept_brief
        or "문제의 조건과 핵심 개념을 연결해 판단 기준을 세워보세요."
    )
    safe_explanation = html.escape(
        explanation
        or "선택지의 표현보다 주어진 값과 조건을 먼저 비교하면 답의 근거가 선명해집니다."
    )
    safe_evidence = html.escape(
        evidence
        or "현재 사건 기록에서 확인한 단서를 다시 읽어보세요."
    )
    keyword_html = "".join(
        f'<span>{html.escape(_sanitize_learning_text(item))}</span>'
        for item in targets
        if _sanitize_learning_text(item)
    ) or '<span>핵심 개념</span>'
    notebook_portrait = resolve_companion_action_portrait(
        world[4],
        "notebook",
    )
    notebook_uri = _v3_file_data_uri(notebook_portrait)
    notebook_html = (
        '<div class="v3-book-companion">'
        f'<img src="{notebook_uri}" alt="학습 노트를 정리하는 동료">'
        '</div>'
        if notebook_uri and str(world[4]).strip() in {"미스터리", "미스테리", "mystery"}
        else ""
    )

    st.markdown(
        '<section class="v3-open-book">'
        '<div class="v3-book-page v3-book-left">'
        '<div class="v3-book-kicker">학습 노트</div>'
        f'<h2>{safe_title}</h2>'
        '<div class="v3-book-tabs"><b>개념</b><span>복습</span></div>'
        f'{notebook_html}'
        f'<p class="v3-book-lead">{safe_brief}</p>'
        f'<div class="v3-book-keywords">{keyword_html}</div>'
        '<div class="v3-book-sign">코드를 읽는 눈이 진실에 가까워진다.<br>— 동료의 기록 —</div>'
        '</div>'
        '<div class="v3-book-page v3-book-right">'
        '<div class="v3-book-kicker">이번 사건의 기록</div>'
        f'<div class="v3-book-fact">{safe_evidence}</div>'
        f'<p>{safe_explanation}</p>'
        '<div class="v3-book-note">자료와 조건을 구분하면 데이터의 의미가 보인다.</div>'
        '</div>'
        '</section>',
        unsafe_allow_html=True,
    )





# V3_ONE_SCREEN_PLAY_LAYOUT_V1_20260908
def _inject_v3_one_screen_play_layout_css(
    *,
    world_id: int,
    chapter_id: int,
    theme: str,
    chapter_number: int,
) -> None:
    """Game-like V3 viewport shell with a persistent HUD/body/dock grid."""
    surface_class = f".st-key-v3_play_surface_{int(world_id)}_{int(chapter_id)}"
    header_class = f".st-key-v3_play_header_{int(world_id)}_{int(chapter_id)}"
    body_class = f".st-key-v3_play_body_{int(world_id)}_{int(chapter_id)}"
    dock_class = f".st-key-v3_play_dock_{int(world_id)}_{int(chapter_id)}"

    background_path = _v3_context_image_path(
        theme=theme,
        chapter_number=chapter_number,
    )
    background_uri = _v3_file_data_uri(
        background_path
    )
    shell_background = (
        f'linear-gradient(rgba(5,14,24,.56),rgba(5,14,24,.70)),url("{background_uri}") center/cover fixed'
        if background_uri
        else 'linear-gradient(135deg,#071522,#10283a)'
    )

    st.markdown(
        f"""
        <style>
        /* V3_GAME_UI_ALIGNMENT_V2_20260908 */
        @media (min-width:900px) {{
            html, body, .stApp,
            div[data-testid="stAppViewContainer"],
            section[data-testid="stMain"] {{
                height:100dvh !important;
                max-height:100dvh !important;
                overflow:hidden !important;
            }}

            header[data-testid="stHeader"],
            #MainMenu, footer, [data-testid="stDecoration"] {{
                display:none !important;
            }}

            div[data-testid="stMainBlockContainer"]:has({surface_class}),
            .main .block-container:has({surface_class}) {{
                width:100% !important;
                max-width:none !important;
                height:100dvh !important;
                max-height:100dvh !important;
                overflow:hidden !important;
                box-sizing:border-box !important;
                padding:.35rem .6rem .4rem !important;
                background:{shell_background} !important;
            }}

            {surface_class} {{
                display:grid !important;
                grid-template-rows:auto minmax(0,1fr) auto !important;
                height:calc(100dvh - .75rem) !important;
                max-height:calc(100dvh - .75rem) !important;
                min-height:0 !important;
                overflow:hidden !important;
                margin:0 !important;
                padding:0 !important;
            }}

            {surface_class} > div[data-testid="stVerticalBlock"] {{
                display:grid !important;
                grid-template-rows:auto minmax(0,1fr) auto !important;
                height:100% !important;
                min-height:0 !important;
                gap:.28rem !important;
            }}

            /* Streamlit wraps keyed containers in stElementContainer nodes.
               Those wrappers must also be shrinkable or the Body's intrinsic
               content height pushes the Action Dock below the viewport. */
            {surface_class} > div[data-testid="stVerticalBlock"]
            > div[data-testid="stElementContainer"] {{
                min-height:0 !important;
                margin:0 !important;
            }}
            {surface_class} > [data-testid="stLayoutWrapper"] {{
                min-height:0 !important;
                margin:0 !important;
            }}
            {surface_class} > [data-testid="stLayoutWrapper"]:has({body_class}) {{
                position:relative !important;
                z-index:1 !important;
                height:100% !important;
                overflow:hidden !important;
            }}
            {surface_class} > [data-testid="stLayoutWrapper"]:has({dock_class}) {{
                position:relative !important;
                z-index:10 !important;
            }}
            {surface_class} > div[data-testid="stVerticalBlock"]
            > div[data-testid="stElementContainer"]:has({body_class}) {{
                height:100% !important;
                overflow:hidden !important;
            }}
            {surface_class} > div[data-testid="stVerticalBlock"]
            > div[data-testid="stElementContainer"]:has({dock_class}) {{
                align-self:end !important;
            }}

            div[data-testid="stMainBlockContainer"]:has({surface_class})
            > div[data-testid="stVerticalBlock"] {{
                min-height:0 !important;
                gap:0 !important;
                padding-top:0 !important;
            }}

            {header_class},
            {body_class},
            {dock_class} {{
                min-height:0 !important;
                margin:0 !important;
            }}

            {header_class}, {body_class}, {dock_class} {{
                border-color:rgba(214,164,82,.72) !important;
                box-shadow:
                    inset 0 0 0 1px rgba(255,222,151,.12),
                    0 12px 32px rgba(0,0,0,.30) !important;
            }}

            {header_class} > div[data-testid="stVerticalBlock"] {{
                gap:.18rem !important;
            }}

            {header_class} div[data-testid="stHorizontalBlock"] {{
                gap:.38rem !important;
                align-items:center !important;
            }}

            {header_class} div[data-testid="stButton"] > button {{
                min-height:2.35rem !important;
                height:2.35rem !important;
                padding:.2rem .42rem !important;
                border-radius:8px !important;
                border:1px solid rgba(255,255,255,.16) !important;
                background:rgba(7,20,34,.72) !important;
                color:#eaf2fb !important;
                font-size:.66rem !important;
            }}

            {header_class} [data-testid="stCaptionContainer"] {{
                display:none !important;
            }}

            {body_class} {{
                height:100% !important;
                max-height:none !important;
                overflow:hidden !important;
                border:1px solid rgba(214,164,82,.72) !important;
                border-radius:4px !important;
                background:rgba(5,16,27,.70) !important;
                backdrop-filter:blur(5px);
                -webkit-backdrop-filter:blur(5px);
                box-shadow:0 18px 46px rgba(0,0,0,.18);
            }}

            {body_class} > div[data-testid="stVerticalBlock"] {{
                height:100% !important;
                max-height:100% !important;
                min-height:0 !important;
                overflow-y:auto !important;
                overflow-x:hidden !important;
                gap:.42rem !important;
                padding:.55rem .65rem .6rem !important;
                box-sizing:border-box !important;
                overscroll-behavior:contain;
            }}

            {body_class} .v3-mode-heading,
            {body_class} .v3-panel-title {{
                color:#f4f7fb !important;
                margin:0 0 .35rem !important;
            }}
            {body_class} .v3-mode-heading small,
            {body_class} .v3-panel-title small {{ color:#aebdcc !important; }}

            {body_class} div[data-testid="stHorizontalBlock"] {{
                gap:.58rem !important;
                align-items:stretch !important;
            }}

            {body_class} [data-testid="stSegmentedControl"] {{
                margin:0 auto .15rem !important;
            }}
            {body_class} [data-testid="stSegmentedControl"] button {{
                min-width:2.2rem !important;
                min-height:1.85rem !important;
                padding:.1rem .55rem !important;
                border-color:rgba(199,151,78,.46) !important;
                background:rgba(7,22,35,.92) !important;
                color:#f4e4bd !important;
            }}
            {body_class} [data-testid="stSegmentedControl"] button[aria-pressed="true"] {{
                border-color:#e0a65b !important;
                background:#6f2933 !important;
                color:#fff2d3 !important;
            }}

            {body_class} div[data-testid="stColumn"] {{
                min-width:0 !important;
            }}

            {body_class} [data-testid="stVerticalBlockBorderWrapper"] {{
                border-color:rgba(255,255,255,.12) !important;
                background:rgba(7,19,31,.76) !important;
                border-radius:14px !important;
                box-shadow:none !important;
            }}

            /* V3_QUIZ_EVIDENCE_VISUAL_CONTRACT_FIX_V3_1_20260908
               Evidence is now one owned HTML surface. It no longer depends
               on :has(...) traversing Streamlit's generated border wrappers. */
            {body_class} .v3-evidence-card {{
                max-height:285px !important;
                overflow-y:auto !important;
                overflow-x:hidden !important;
                box-sizing:border-box !important;
                margin:0 !important;
                padding:.72rem .78rem .8rem !important;
                border:1px solid rgba(193,211,229,.22) !important;
                border-radius:14px !important;
                background:linear-gradient(
                    145deg,
                    rgba(7,20,33,.97),
                    rgba(11,29,44,.94)
                ) !important;
                color:#eef4fb !important;
                -webkit-text-fill-color:#eef4fb !important;
                box-shadow:inset 0 1px 0 rgba(255,255,255,.04) !important;
                scrollbar-width:thin;
            }}

            {body_class} .v3-evidence-card,
            {body_class} .v3-evidence-card * {{
                color:#eef4fb !important;
                -webkit-text-fill-color:#eef4fb !important;
                opacity:1 !important;
            }}

            {body_class} .v3-evidence-kicker {{
                margin:0 0 .18rem !important;
                color:#ef5966 !important;
                -webkit-text-fill-color:#ef5966 !important;
                font-size:.58rem !important;
                line-height:1.2 !important;
                font-weight:950 !important;
                letter-spacing:.14em !important;
            }}

            {body_class} .v3-evidence-task {{
                margin:0 0 .55rem !important;
                color:#cbd8e6 !important;
                -webkit-text-fill-color:#cbd8e6 !important;
                font-size:.72rem !important;
                line-height:1.35 !important;
                font-weight:700 !important;
            }}

            {body_class} .v3-evidence-heading {{
                margin:.48rem 0 .14rem !important;
                color:#ffffff !important;
                -webkit-text-fill-color:#ffffff !important;
                font-size:.78rem !important;
                line-height:1.3 !important;
                font-weight:900 !important;
            }}

            {body_class} .v3-evidence-copy,
            {body_class} .v3-evidence-empty {{
                margin:0 !important;
                color:#eef4fb !important;
                -webkit-text-fill-color:#eef4fb !important;
                font-size:.75rem !important;
                line-height:1.52 !important;
                font-weight:620 !important;
                word-break:keep-all !important;
                overflow-wrap:break-word !important;
            }}

            {body_class} .v3-evidence-empty {{
                color:#b9c8d7 !important;
                -webkit-text-fill-color:#b9c8d7 !important;
            }}

            {body_class} [data-testid="stImage"] img {{
                width:100% !important;
                max-height:145px !important;
                object-fit:cover !important;
                border-radius:13px !important;
                border:1px solid rgba(255,255,255,.12) !important;
            }}

            {body_class} .v3-evidence-object {{
                display:grid !important;
                place-items:center !important;
                height:clamp(76px,11vh,108px) !important;
                margin:0 !important;
                border:1px solid rgba(255,255,255,.15) !important;
                border-radius:13px !important;
                background:linear-gradient(145deg,rgba(8,22,36,.94),rgba(18,39,55,.88)) !important;
                color:#f0cf83 !important;
                -webkit-text-fill-color:#f0cf83 !important;
                font-size:clamp(2.2rem,4vw,3.4rem) !important;
                line-height:1 !important;
                box-shadow:inset 0 1px 0 rgba(255,255,255,.05) !important;
            }}

            {body_class} div[data-testid="stRadio"] div[role="radiogroup"] {{ gap:.28rem !important; }}
            {body_class} div[data-testid="stRadio"] div[role="radiogroup"] > label {{
                padding:.48rem .62rem !important;
                min-height:2.55rem !important;
                border:1px solid rgba(255,255,255,.16) !important;
                border-radius:10px !important;
                background:rgba(7,19,31,.82) !important;
                color:#eef4fb !important;
            }}
            {body_class} div[data-testid="stRadio"] div[role="radiogroup"] > label p {{
                color:#eef4fb !important;
                -webkit-text-fill-color:#eef4fb !important;
                font-size:.78rem !important;
                line-height:1.35 !important;
            }}

            {body_class} div[data-testid="stButton"] > button {{
                min-height:2.45rem !important;
                border-radius:10px !important;
                font-size:.76rem !important;
                font-weight:800 !important;
            }}

            {dock_class} {{
                padding:.46rem .5rem .5rem !important;
                border:1px solid rgba(214,164,82,.72) !important;
                border-radius:4px !important;
                background:rgba(5,17,29,.94) !important;
                box-shadow:0 14px 34px rgba(0,0,0,.26) !important;
                backdrop-filter:blur(15px) saturate(125%) !important;
                -webkit-backdrop-filter:blur(15px) saturate(125%) !important;
            }}
            {dock_class} > div[data-testid="stVerticalBlock"] {{ gap:.22rem !important; }}
            {dock_class} div[data-testid="stHorizontalBlock"] {{ gap:.42rem !important; }}
            {dock_class} div[data-testid="stButton"] > button,
            {dock_class} div[data-testid="stPopover"] button {{
                width:100% !important;
                min-height:2.82rem !important;
                padding:.34rem .38rem !important;
                border-radius:5px !important;
                border:1px solid rgba(188,145,76,.46) !important;
                background:linear-gradient(180deg,rgba(17,37,52,.96),rgba(8,24,38,.96)) !important;
                color:#edf4fb !important;
                font-size:.70rem !important;
                line-height:1.22 !important;
                font-weight:850 !important;
                white-space:pre-line !important;
            }}
            {dock_class} div[data-testid="stButton"] > button[kind="primary"] {{
                background:linear-gradient(135deg,rgba(112,36,42,.98),rgba(75,28,38,.98)) !important;
                border-color:#dc9b52 !important;
                box-shadow:inset 0 0 0 1px rgba(255,212,132,.18) !important;
            }}

            .v3-open-book {{
                display:grid !important;
                grid-template-columns:1fr 1fr !important;
                width:min(100%,1040px) !important;
                height:100% !important;
                min-height:0 !important;
                margin:0 auto !important;
                padding:1rem 1.2rem !important;
                box-sizing:border-box !important;
                border:12px solid rgba(63,34,17,.84) !important;
                outline:1px solid #c7974e !important;
                background:#d8c29c !important;
                box-shadow:0 20px 44px rgba(0,0,0,.44) !important;
                color:#28231d !important;
                overflow:hidden !important;
            }}
            .v3-book-page {{
                position:relative !important;
                min-width:0 !important;
                padding:1rem 1.25rem !important;
                background:
                    repeating-linear-gradient(0deg,rgba(104,78,43,.035) 0,rgba(104,78,43,.035) 1px,transparent 1px,transparent 24px),
                    linear-gradient(100deg,#ead9b8,#f3e4c5 58%,#dfc79f) !important;
                color:#28231d !important;
                overflow-y:auto !important;
            }}
            .v3-book-left {{ border-right:1px solid rgba(91,59,29,.32) !important; }}
            .v3-book-right {{ box-shadow:inset 14px 0 22px rgba(80,48,23,.10) !important; }}
            .v3-open-book, .v3-open-book * {{ -webkit-text-fill-color:currentColor !important; }}
            .v3-book-kicker {{ color:#2e261d !important; font-size:.82rem !important; font-weight:950 !important; }}
            .v3-book-page h2 {{ margin:.35rem 0 .65rem !important; color:#2e261d !important; font-size:1.35rem !important; }}
            .v3-book-tabs {{ display:flex !important; gap:.35rem !important; margin-bottom:.7rem !important; }}
            .v3-book-tabs > * {{ padding:.26rem .78rem !important; border:1px solid #9a7040 !important; border-radius:4px !important; }}
            .v3-book-tabs b {{ background:#783239 !important; color:#fff1d0 !important; }}
            .v3-book-companion {{
                float:right !important;
                width:clamp(88px,24%,142px) !important;
                height:clamp(96px,18vh,150px) !important;
                margin:-.35rem 0 .35rem .65rem !important;
            }}
            .v3-book-companion img {{
                width:100% !important;
                height:100% !important;
                object-fit:contain !important;
                object-position:center bottom !important;
                filter:sepia(.12) drop-shadow(0 6px 8px rgba(70,42,19,.18)) !important;
            }}
            .v3-book-lead, .v3-book-page p {{ font-size:.82rem !important; line-height:1.58 !important; font-weight:650 !important; }}
            .v3-book-keywords {{ display:flex !important; flex-wrap:wrap !important; gap:.35rem !important; margin:.8rem 0 !important; }}
            .v3-book-keywords span {{ padding:.2rem .48rem !important; border-bottom:2px solid #9c3038 !important; font-size:.72rem !important; font-weight:850 !important; }}
            .v3-book-fact {{ margin:.8rem 0 !important; padding:.7rem !important; border-top:1px solid #8c673c !important; border-bottom:1px solid #8c673c !important; font-size:1rem !important; font-weight:900 !important; }}
            .v3-book-note {{ margin-top:1rem !important; padding:.7rem !important; transform:rotate(-2deg) !important; background:#dcc27b !important; box-shadow:0 3px 8px rgba(65,39,18,.22) !important; font-size:.76rem !important; font-weight:800 !important; }}
            .v3-book-sign {{ margin-top:1rem !important; text-align:right !important; font-size:.72rem !important; line-height:1.45 !important; font-style:italic !important; }}

            .v3-question-card {{
                position:relative;
                margin:0 0 .42rem;
                padding:.72rem .82rem .78rem;
                border:1px solid rgba(255,255,255,.15);
                border-radius:14px;
                background:linear-gradient(135deg,rgba(9,24,39,.94),rgba(13,31,47,.92));
                box-shadow:0 12px 28px rgba(0,0,0,.18);
                color:#f4f7fb;
            }}
            .v3-question-kicker {{ color:var(--learn-accent); font-size:.60rem; font-weight:900; letter-spacing:.13em; }}
            .v3-question-progress {{ position:absolute; top:.66rem; right:.76rem; color:#aebdcc; font-size:.62rem; font-weight:800; }}
            .v3-question-text {{ margin-top:.34rem; font-size:clamp(1rem,1.28vw,1.22rem); line-height:1.42; font-weight:850; letter-spacing:-.02em; }}

            /* V3_REVIEW_COMPANION_VISUAL_FIX_V3_2_20260908
               Review Stage uses an explicit viewport-safe height and keeps the
               dialogue card in normal flex flow. This avoids Streamlit wrapper
               height collapse clipping the dialogue at the top edge. */
            {body_class} div[data-testid="stElementContainer"]:has(.v3-review-stage-v32),
            {body_class} [data-testid="stMarkdownContainer"]:has(.v3-review-stage-v32) {{
                min-height:clamp(280px,41vh,380px) !important;
                height:auto !important;
                overflow:visible !important;
            }}

            .v3-review-stage {{
                position:relative;
                height:100%;
                min-height:310px;
                max-height:430px;
                overflow:hidden;
                border-radius:15px;
                border:1px solid rgba(255,255,255,.14);
                background-size:cover;
                background-position:center;
                box-shadow:0 16px 36px rgba(0,0,0,.24);
            }}
            .v3-review-stage::before {{ content:""; position:absolute; inset:0; background:linear-gradient(to bottom,rgba(3,9,16,.08),rgba(3,9,16,.62)); }}
            .v3-review-character {{ position:absolute; z-index:2; left:1rem; bottom:86px; width:145px; height:190px; opacity:1; filter:drop-shadow(0 12px 18px rgba(0,0,0,.38)); }}
            .v3-review-character img {{ width:100%; height:100%; object-fit:contain; object-position:center bottom; opacity:1; transition:opacity .2s ease,filter .2s ease; }}
            .v3-review-character.is-active img {{ opacity:1 !important; filter:none !important; }}
            .v3-review-character.is-dim img {{ opacity:.28 !important; filter:saturate(.60) brightness(.74) !important; }}
            .v3-review-dialogue {{ position:absolute; z-index:3; left:.7rem; right:.7rem; bottom:.7rem; min-height:82px; padding:.6rem .74rem .65rem; border-radius:13px; background:rgba(247,249,252,.95); color:#1f4b7e; box-shadow:0 12px 28px rgba(0,0,0,.25); }}
            .v3-review-speaker {{ display:inline-block; margin-top:-1.25rem; padding:.25rem .68rem; border-radius:8px; background:#d8eaff; color:#24598f; font-size:.70rem; font-weight:900; }}
            .v3-review-scene-label {{ margin:.18rem 0 .16rem; color:#71839a; font-size:.55rem; font-weight:900; letter-spacing:.12em; }}
            .v3-review-text {{ font-size:.82rem; line-height:1.45; font-weight:650; }}

            .v3-review-stage.v3-review-stage-v32 {{
                display:flex !important;
                flex-direction:column !important;
                justify-content:flex-end !important;
                width:100% !important;
                height:clamp(280px,41vh,380px) !important;
                min-height:280px !important;
                max-height:380px !important;
                box-sizing:border-box !important;
                isolation:isolate !important;
                overflow:hidden !important;
                background-color:#07131f !important;
            }}
            .v3-review-stage-v32::before {{
                z-index:1 !important;
                pointer-events:none !important;
            }}
            .v3-review-stage-v32 .v3-review-character-v32 {{
                left:.9rem !important;
                bottom:92px !important;
                width:138px !important;
                height:182px !important;
            }}
            .v3-review-stage-v32 .v3-review-dialogue-v32 {{
                position:relative !important;
                z-index:3 !important;
                left:auto !important;
                right:auto !important;
                bottom:auto !important;
                width:auto !important;
                margin:.68rem !important;
                min-height:82px !important;
                box-sizing:border-box !important;
                flex:0 0 auto !important;
            }}
            .v3-review-stage-v32 .v3-review-dialogue-v32,
            .v3-review-stage-v32 .v3-review-dialogue-v32 * {{
                opacity:1 !important;
            }}
            .v3-review-stage-v32 .v3-review-text {{
                color:#173d68 !important;
                -webkit-text-fill-color:#173d68 !important;
            }}

            .v3-review-scene-list-title {{
                margin:0 0 .42rem !important;
                color:#f4f7fb !important;
                -webkit-text-fill-color:#f4f7fb !important;
                font-size:.78rem !important;
                line-height:1.25 !important;
                font-weight:900 !important;
            }}

            .v3-review-side-stack {{
                display:grid !important;
                grid-template-rows:minmax(0,1fr) auto !important;
                gap:.58rem !important;
                min-height:0 !important;
            }}
            .v3-review-side-card {{
                box-sizing:border-box !important;
                margin:0 !important;
                padding:.72rem .78rem !important;
                border:1px solid rgba(193,211,229,.20) !important;
                border-radius:14px !important;
                background:linear-gradient(145deg,rgba(7,20,33,.96),rgba(11,29,44,.93)) !important;
                color:#edf4fb !important;
                -webkit-text-fill-color:#edf4fb !important;
                overflow:hidden !important;
            }}
            .v3-review-side-card,
            .v3-review-side-card * {{
                color:#edf4fb !important;
                -webkit-text-fill-color:#edf4fb !important;
                opacity:1 !important;
            }}
            .v3-review-clue-card {{
                max-height:245px !important;
                overflow-y:auto !important;
                scrollbar-width:thin;
            }}
            .v3-review-side-title {{
                margin:0 0 .48rem !important;
                color:#ffffff !important;
                -webkit-text-fill-color:#ffffff !important;
                font-size:.82rem !important;
                line-height:1.25 !important;
                font-weight:950 !important;
            }}
            .v3-review-side-list {{
                margin:0 !important;
                padding-left:1.05rem !important;
            }}
            .v3-review-side-list li {{
                margin:.1rem 0 .52rem !important;
                color:#dfeaf5 !important;
                -webkit-text-fill-color:#dfeaf5 !important;
                font-size:.74rem !important;
                line-height:1.48 !important;
                font-weight:620 !important;
            }}
            .v3-review-side-empty {{
                color:#b9c8d7 !important;
                -webkit-text-fill-color:#b9c8d7 !important;
                font-size:.73rem !important;
                line-height:1.45 !important;
            }}
            .v3-review-keyword-wrap {{
                display:flex !important;
                flex-wrap:wrap !important;
                gap:.35rem !important;
            }}
            .v3-review-keyword-chip {{
                display:inline-flex !important;
                align-items:center !important;
                min-height:1.55rem !important;
                padding:.18rem .48rem !important;
                border:1px solid rgba(239,89,102,.26) !important;
                border-radius:999px !important;
                background:rgba(239,89,102,.10) !important;
                color:#f5dfe3 !important;
                -webkit-text-fill-color:#f5dfe3 !important;
                font-size:.66rem !important;
                line-height:1.2 !important;
                font-weight:760 !important;
            }}

            .v3-companion-progress {{
                margin:0 0 .42rem !important;
                color:#b9c8d7 !important;
                -webkit-text-fill-color:#b9c8d7 !important;
                font-size:.70rem !important;
                line-height:1.25 !important;
                font-weight:760 !important;
            }}
            .v3-companion-hint-card {{
                box-sizing:border-box !important;
                margin:.48rem 0 0 !important;
                padding:.78rem .86rem .82rem !important;
                border:1px solid rgba(214,184,116,.25) !important;
                border-radius:14px !important;
                background:linear-gradient(145deg,rgba(16,25,36,.96),rgba(19,31,43,.94)) !important;
                color:#eef4fb !important;
                -webkit-text-fill-color:#eef4fb !important;
                box-shadow:inset 3px 0 0 rgba(220,184,105,.72) !important;
            }}
            .v3-companion-hint-card,
            .v3-companion-hint-card * {{
                color:#eef4fb !important;
                -webkit-text-fill-color:#eef4fb !important;
                opacity:1 !important;
            }}
            .v3-companion-hint-title {{
                margin:0 0 .38rem !important;
                color:#f0cf83 !important;
                -webkit-text-fill-color:#f0cf83 !important;
                font-size:.82rem !important;
                line-height:1.25 !important;
                font-weight:950 !important;
            }}
            .v3-companion-hint-copy {{
                margin:0 !important;
                color:#eef4fb !important;
                -webkit-text-fill-color:#eef4fb !important;
                font-size:.80rem !important;
                line-height:1.52 !important;
                font-weight:650 !important;
                word-break:keep-all !important;
                overflow-wrap:break-word !important;
            }}
            .v3-companion-evidence-line {{
                display:grid !important;
                gap:.18rem !important;
                margin:.52rem 0 0 !important;
                padding:.52rem .66rem !important;
                border:1px solid rgba(193,211,229,.15) !important;
                border-radius:10px !important;
                background:rgba(7,19,31,.64) !important;
            }}
            .v3-companion-evidence-line span {{
                color:#9fb2c5 !important;
                -webkit-text-fill-color:#9fb2c5 !important;
                font-size:.62rem !important;
                line-height:1.2 !important;
                font-weight:850 !important;
                letter-spacing:.03em !important;
            }}
            .v3-companion-evidence-line strong {{
                color:#dfeaf5 !important;
                -webkit-text-fill-color:#dfeaf5 !important;
                font-size:.72rem !important;
                line-height:1.42 !important;
                font-weight:650 !important;
            }}

            .v3-story-choice-heading {{
                display:flex;
                align-items:center;
                justify-content:space-between;
                gap:.7rem;
                margin:.2rem 0 .34rem;
                padding:.58rem .72rem;
                border:1px solid rgba(255,255,255,.14);
                border-radius:12px;
                background:rgba(7,19,31,.82);
                color:#f2f6fb;
            }}
            .v3-story-choice-heading strong {{ font-size:.86rem; }}
            .v3-story-choice-heading span {{ color:#aebdcc; font-size:.68rem; }}
        }}

        @media (max-width:899px) {{
            html, body, .stApp,
            div[data-testid="stAppViewContainer"],
            section[data-testid="stMain"] {{
                height:100dvh !important;
                max-height:100dvh !important;
                overflow:hidden !important;
            }}

            header[data-testid="stHeader"],
            #MainMenu, footer, [data-testid="stDecoration"] {{
                display:none !important;
            }}

            div[data-testid="stMainBlockContainer"]:has({surface_class}),
            .main .block-container:has({surface_class}) {{
                width:100% !important;
                max-width:none !important;
                height:100dvh !important;
                max-height:100dvh !important;
                overflow:hidden !important;
                box-sizing:border-box !important;
                padding:.24rem !important;
                background:{shell_background} !important;
            }}

            {surface_class} {{
                display:grid !important;
                grid-template-rows:auto minmax(0,1fr) auto !important;
                height:calc(100dvh - .48rem) !important;
                max-height:calc(100dvh - .48rem) !important;
                min-height:0 !important;
                overflow:hidden !important;
                margin:0 !important;
                padding:0 !important;
            }}

            {surface_class} > div[data-testid="stVerticalBlock"] {{
                display:grid !important;
                grid-template-rows:auto minmax(0,1fr) auto !important;
                height:100% !important;
                min-height:0 !important;
                gap:.2rem !important;
            }}
            {surface_class} > div[data-testid="stVerticalBlock"]
            > div[data-testid="stElementContainer"] {{
                min-height:0 !important;
                margin:0 !important;
            }}
            {surface_class} > [data-testid="stLayoutWrapper"] {{
                min-height:0 !important;
                margin:0 !important;
            }}
            {surface_class} > [data-testid="stLayoutWrapper"]:has({body_class}) {{
                position:relative !important;
                z-index:1 !important;
                height:100% !important;
                overflow:hidden !important;
            }}
            {surface_class} > [data-testid="stLayoutWrapper"]:has({dock_class}) {{
                position:relative !important;
                z-index:10 !important;
            }}
            {surface_class} > div[data-testid="stVerticalBlock"]
            > div[data-testid="stElementContainer"]:has({body_class}) {{
                height:100% !important;
                overflow:hidden !important;
            }}

            {header_class}, {body_class}, {dock_class} {{
                min-height:0 !important;
                margin:0 !important;
                border:1px solid rgba(214,164,82,.76) !important;
                border-radius:3px !important;
                background:rgba(5,17,29,.94) !important;
                box-shadow:inset 0 0 0 1px rgba(255,222,151,.10) !important;
            }}

            {header_class} {{ padding:.32rem .38rem !important; }}
            {header_class} > div[data-testid="stVerticalBlock"] {{ gap:0 !important; }}
            {header_class} div[data-testid="stHorizontalBlock"] {{
                display:flex !important;
                flex-wrap:nowrap !important;
                gap:.22rem !important;
                align-items:center !important;
            }}
            {header_class} div[data-testid="stColumn"]:first-child {{
                flex:1 1 auto !important;
                width:auto !important;
                min-width:0 !important;
            }}
            {header_class} div[data-testid="stColumn"]:not(:first-child) {{
                flex:0 0 3.15rem !important;
                width:3.15rem !important;
                min-width:3.15rem !important;
            }}
            {header_class} [data-testid="stCaptionContainer"] {{ display:none !important; }}
            {header_class} div[data-testid="stButton"] > button {{
                width:100% !important;
                min-height:3.15rem !important;
                height:3.15rem !important;
                padding:.15rem .1rem !important;
                border:1px solid rgba(214,164,82,.48) !important;
                border-radius:4px !important;
                background:linear-gradient(180deg,rgba(19,42,58,.98),rgba(8,24,38,.98)) !important;
                color:#fff1d0 !important;
                font-size:.63rem !important;
                line-height:1.15 !important;
                font-weight:850 !important;
                white-space:normal !important;
            }}

            {body_class} {{
                height:100% !important;
                max-height:100% !important;
                overflow:hidden !important;
                box-sizing:border-box !important;
                backdrop-filter:blur(4px) !important;
                -webkit-backdrop-filter:blur(4px) !important;
            }}
            {body_class} > div[data-testid="stVerticalBlock"] {{
                height:100% !important;
                max-height:100% !important;
                min-height:0 !important;
                overflow-y:auto !important;
                overflow-x:hidden !important;
                gap:.38rem !important;
                padding:.45rem !important;
                box-sizing:border-box !important;
                overscroll-behavior:contain !important;
                scrollbar-width:thin !important;
            }}
            {body_class} div[data-testid="stHorizontalBlock"] {{
                gap:.42rem !important;
            }}
            {body_class} [data-testid="stSegmentedControl"] {{
                position:sticky !important;
                top:0 !important;
                z-index:6 !important;
                margin:0 auto .15rem !important;
                padding:.12rem !important;
                border:1px solid rgba(214,164,82,.55) !important;
                border-radius:6px !important;
                background:rgba(5,17,29,.92) !important;
            }}
            {body_class} [data-testid="stSegmentedControl"] button {{
                min-width:2.25rem !important;
                min-height:2rem !important;
                padding:.12rem .55rem !important;
                color:#f4e4bd !important;
            }}
            {body_class} [data-testid="stSegmentedControl"] button[aria-pressed="true"] {{
                border-color:#e0a65b !important;
                background:#762b37 !important;
                color:#fff2d3 !important;
            }}

            {body_class} .v3-mode-heading,
            {body_class} .v3-panel-title {{
                margin:0 !important;
                color:#fff2d3 !important;
            }}
            {body_class} .v3-mode-heading small,
            {body_class} .v3-panel-title small {{
                display:none !important;
            }}
            {body_class} [data-testid="stImage"] img {{
                width:100% !important;
                max-height:43dvh !important;
                object-fit:contain !important;
                object-position:center bottom !important;
            }}
            {body_class} div[data-testid="stRadio"] div[role="radiogroup"] {{
                gap:.3rem !important;
            }}
            {body_class} div[data-testid="stRadio"] div[role="radiogroup"] > label {{
                min-height:3.2rem !important;
                padding:.55rem .65rem !important;
                border:1px solid rgba(214,164,82,.34) !important;
                border-radius:5px !important;
                background:rgba(9,27,41,.94) !important;
            }}

            {dock_class} {{ position:relative !important; z-index:10 !important; padding:.28rem !important; }}
            {dock_class} > div[data-testid="stVerticalBlock"] {{ gap:0 !important; }}
            {dock_class} div[data-testid="stHorizontalBlock"] {{
                display:flex !important;
                flex-wrap:nowrap !important;
                gap:.2rem !important;
            }}
            {dock_class} div[data-testid="stColumn"] {{
                flex:1 1 25% !important;
                width:25% !important;
                min-width:0 !important;
            }}
            {dock_class} div[data-testid="stButton"] > button {{
                width:100% !important;
                min-height:3.7rem !important;
                height:3.7rem !important;
                padding:.2rem .08rem !important;
                border:1px solid rgba(188,145,76,.48) !important;
                border-radius:4px !important;
                background:linear-gradient(180deg,rgba(17,37,52,.98),rgba(8,24,38,.98)) !important;
                color:#fff0cc !important;
                font-size:.66rem !important;
                line-height:1.22 !important;
                font-weight:900 !important;
                white-space:normal !important;
            }}
            {dock_class} div[data-testid="stButton"] > button[kind="primary"] {{
                background:linear-gradient(145deg,#862c3a,#591e2c) !important;
                border-color:#efab54 !important;
                box-shadow:inset 0 0 0 1px rgba(255,215,139,.22) !important;
            }}

            .v3-review-stage,
            .v3-review-stage.v3-review-stage-v32 {{
                position:relative !important;
                display:flex !important;
                flex-direction:column !important;
                justify-content:flex-end !important;
                height:clamp(390px,58dvh,560px) !important;
                min-height:390px !important;
                max-height:560px !important;
                border-radius:5px !important;
                border-color:rgba(214,164,82,.66) !important;
            }}
            .v3-review-stage-v32 .v3-review-character-v32 {{
                position:absolute !important;
                left:50% !important;
                bottom:112px !important;
                width:min(58%,220px) !important;
                height:52% !important;
                transform:translateX(-50%) !important;
            }}
            .v3-review-stage-v32 .v3-review-dialogue-v32 {{
                position:relative !important;
                z-index:3 !important;
                margin:.48rem !important;
                min-height:104px !important;
                padding:.66rem .72rem !important;
                border:1px solid rgba(214,164,82,.66) !important;
                border-radius:5px !important;
                background:rgba(6,22,35,.96) !important;
            }}
            .v3-review-stage-v32 .v3-review-dialogue-v32,
            .v3-review-stage-v32 .v3-review-dialogue-v32 * {{
                color:#f8ead0 !important;
                -webkit-text-fill-color:#f8ead0 !important;
            }}
            .v3-review-stage-v32 .v3-review-text {{
                color:#f8ead0 !important;
                -webkit-text-fill-color:#f8ead0 !important;
                font-size:.92rem !important;
                line-height:1.5 !important;
            }}
            .v3-review-stage-v32 .v3-review-speaker {{
                background:#0b2539 !important;
                border:1px solid #d49a50 !important;
                color:#f7d889 !important;
                -webkit-text-fill-color:#f7d889 !important;
            }}
            .v3-review-side-card,
            .v3-evidence-card,
            .v3-companion-hint-card {{
                border-color:rgba(214,164,82,.52) !important;
                border-radius:5px !important;
            }}

            .v3-open-book {{
                display:block !important;
                width:100% !important;
                height:auto !important;
                min-height:100% !important;
                margin:0 !important;
                padding:.5rem !important;
                border:6px solid rgba(63,34,17,.88) !important;
                outline:1px solid #c7974e !important;
                background:#d8c29c !important;
                color:#28231d !important;
                overflow:visible !important;
            }}
            .v3-open-book, .v3-open-book * {{
                color:#28231d !important;
                -webkit-text-fill-color:currentColor !important;
            }}
            .v3-book-page {{
                padding:1rem .9rem !important;
                background:
                    repeating-linear-gradient(0deg,rgba(104,78,43,.035) 0,rgba(104,78,43,.035) 1px,transparent 1px,transparent 24px),
                    linear-gradient(100deg,#ead9b8,#f3e4c5 58%,#dfc79f) !important;
                color:#28231d !important;
                overflow:visible !important;
            }}
            .v3-book-kicker {{ font-size:.78rem !important; font-weight:950 !important; }}
            .v3-book-page h2 {{ margin:.3rem 0 .55rem !important; font-size:1.25rem !important; }}
            .v3-book-tabs {{ display:flex !important; gap:.3rem !important; margin-bottom:.55rem !important; }}
            .v3-book-tabs > * {{ padding:.24rem .7rem !important; border:1px solid #9a7040 !important; border-radius:3px !important; }}
            .v3-book-tabs b {{ background:#783239 !important; color:#fff1d0 !important; -webkit-text-fill-color:#fff1d0 !important; }}
            .v3-book-lead, .v3-book-page p {{ font-size:.82rem !important; line-height:1.55 !important; font-weight:650 !important; }}
            .v3-book-keywords {{ display:flex !important; flex-wrap:wrap !important; gap:.3rem !important; margin:.7rem 0 !important; }}
            .v3-book-keywords span {{ padding:.18rem .42rem !important; border-bottom:2px solid #9c3038 !important; font-size:.7rem !important; font-weight:850 !important; }}
            .v3-book-fact {{ margin:.7rem 0 !important; padding:.65rem !important; border-block:1px solid #8c673c !important; font-size:.95rem !important; font-weight:900 !important; }}
            .v3-book-note {{ margin-top:.8rem !important; padding:.65rem !important; background:#dcc27b !important; box-shadow:0 3px 8px rgba(65,39,18,.22) !important; font-size:.74rem !important; font-weight:800 !important; }}
            .v3-book-sign {{ margin-top:.8rem !important; text-align:right !important; font-size:.7rem !important; line-height:1.4 !important; font-style:italic !important; }}
            .v3-book-left {{
                border-right:0 !important;
                border-bottom:1px solid rgba(91,59,29,.38) !important;
            }}
            .v3-book-right {{
                box-shadow:inset 0 12px 22px rgba(80,48,23,.10) !important;
            }}
            .v3-book-companion {{
                width:112px !important;
                height:128px !important;
                margin:-.4rem -.1rem .25rem .45rem !important;
            }}
        }}

        @media (max-width:640px) {{
            {body_class} div[data-testid="stHorizontalBlock"] {{
                display:flex !important;
                flex-direction:column !important;
                flex-wrap:nowrap !important;
            }}
            {body_class} div[data-testid="stColumn"] {{
                width:100% !important;
                min-width:100% !important;
            }}
            {body_class} .v3-question-text {{
                font-size:1.05rem !important;
            }}
            {body_class} .v3-evidence-object {{
                height:94px !important;
            }}
            {body_class} div[data-testid="stButton"] > button {{
                min-height:2.9rem !important;
                font-size:.78rem !important;
            }}
            {header_class} div[data-testid="stHorizontalBlock"],
            {dock_class} div[data-testid="stHorizontalBlock"] {{
                flex-direction:row !important;
            }}
            {header_class} div[data-testid="stColumn"]:first-child {{
                min-width:0 !important;
            }}
            {dock_class} div[data-testid="stColumn"] {{
                width:25% !important;
                min-width:0 !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )




def _render_post_story_mode_body(
    *,
    user,
    world,
    chapter,
    play_mode: str,
) -> None:
    if play_mode == PLAY_MODE_REVIEW:
        # Preserve Story open analytics/runtime semantics without rendering
        # the old expander-based review tools.
        _render_chapter_story(
            user=user,
            world=world,
            chapter=chapter,
            review_expanded=False,
            render_header=False,
            render_tools=False,
        )
        _render_v3_story_review_panel(
            world=world,
            chapter=chapter,
        )
        return

    if play_mode == PLAY_MODE_COMPANION:
        _render_companion_play_mode(
            user=user,
            world=world,
            chapter=chapter,
        )
        return

    if play_mode == PLAY_MODE_NOTE:
        _render_learning_note_mode(
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

            support_profile = get_learner_level_profile(
                world[3]
            )
            reasoning_profile = get_reasoning_profile(
                requested_difficulty
            )
            adaptive_support = get_adaptive_support_profile(
                user_id=user["user_id"],
                world_id=world[0],
                target_concepts=targets,
            )

            info_left, info_right = st.columns(
                2,
                gap="small",
            )
            with info_left:
                st.caption(
                    f"학습 지원 · {support_profile['display_name']} · "
                    f"사고 난이도 · {reasoning_profile['label']}"
                )
            with info_right:
                st.caption(
                    f"개인화 · {adaptive_support['label']}"
                )

            interaction_context = get_chapter_interaction_context(
                world_id=world[0],
                chapter_number=chapter[2],
                theme=world[4],
            )

            experience_profile = get_theme_experience_profile(
                world[4]
            )
            st.caption(
                f"이번 {experience_profile['interaction_noun']} · "
                f"{interaction_context.get('label') or '상황 적용'}"
            )

            prepare_label = (
                experience_profile[
                    "prepare_label"
                ].format(
                    count=QUESTION_COUNT
                )
            )

            if _render_question_generation_cooldown(
                world_id=world[0],
                chapter_id=chapter[0],
                prepare_label=prepare_label,
            ):
                return

            if st.button(
                prepare_label,
                type="primary",
                key=(
                    f"generate_questions_"
                    f"{chapter[0]}"
                ),
                use_container_width=True,
            ):
                context = get_story_context(
                    world[0]
                )
                foundation = get_world_foundation(
                    world[0]
                )
                concept_contracts = get_concept_contracts(
                    curriculum=(
                        (foundation or {}).get(
                            "curriculum"
                        )
                    ),
                    target_concepts=targets,
                )

                spinner_text = (
                    experience_profile[
                        "spinner_label"
                    ].format(
                        count=QUESTION_COUNT
                    )
                )

                with st.spinner(
                    spinner_text
                ):
                    try:
                        generated_questions = (
                            generate_chapter_questions(
                                topic=world[1],
                                learner_level=world[3],
                                theme=world[4],
                                chapter_title=chapter[3],
                                chapter_story=chapter[4],
                                learning_objectives=chapter[5],
                                target_concepts=targets,
                                concept_contracts=concept_contracts,
                                requested_difficulty=requested_difficulty,
                                adaptive_support=adaptive_support,
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
                                    context["arc"].get(
                                        "target_chapter_count"
                                    )
                                    if context
                                    else None
                                ),
                                current_open_threads=(
                                    (context.get("state") or {}).get(
                                        "open_threads",
                                        [],
                                    )
                                    if context
                                    else []
                                ),
                                user_id=user[
                                    "user_id"
                                ],
                                world_id=world[0],
                                story_arc_id=(
                                    context["arc"]["id"]
                                    if context
                                    else None
                                ),
                            )
                        )

                        update_chapter_questions(
                            chapter_id=chapter[0],
                            questions=generated_questions,
                        )

                        invalidate_runtime_chapter(
                            world_id=world[0],
                            chapter_number=chapter[2],
                        )

                        reset_quiz_state()
                        st.rerun()

                    except QuestionGenerationError as exc:
                        if exc.provider_unavailable:
                            _start_question_generation_cooldown(
                                world_id=world[0],
                                chapter_id=chapter[0],
                            )
                            st.rerun()

                        st.error(str(exc))

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
            st.caption(
                f"🧪 {generation_mode_label()} · "
                "Gemini 호출 없이 기능 흐름을 테스트 중입니다."
            )

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

    # First-time Story still owns the dedicated cinematic/dialogue screen.
    # Skip means "mark Story seen -> enter the normal V3 play shell", not an
    # old-layout branch.
    if play_mode == PLAY_MODE_STORY:
        _render_chapter_story(
            user=user,
            world=world,
            chapter=chapter,
        )
        return

    guide_name = (
        world[9]
        if len(world) > 9
        and world[9]
        else "고양이"
    )

    targets = (
        chapter[
            CHAPTER_TARGET_CONCEPTS
        ]
        if len(chapter)
        > CHAPTER_TARGET_CONCEPTS
        else []
    )

    _inject_v3_one_screen_play_layout_css(
        world_id=world[0],
        chapter_id=chapter[0],
        theme=world[4],
        chapter_number=chapter[2],
    )

    surface_key = (
        f"v3_play_surface_"
        f"{int(world[0])}_"
        f"{int(chapter[0])}"
    )
    header_key = (
        f"v3_play_header_"
        f"{int(world[0])}_"
        f"{int(chapter[0])}"
    )
    body_key = (
        f"v3_play_body_"
        f"{int(world[0])}_"
        f"{int(chapter[0])}"
    )
    dock_key = (
        f"v3_play_dock_"
        f"{int(world[0])}_"
        f"{int(chapter[0])}"
    )

    with st.container(
        key=surface_key,
    ):
        with st.container(
            key=header_key,
        ):
            # V3_TRUE_ONE_SCREEN_HEADER_V1_20260908
            # Chapter HUD + utility navigation share one physical row so
            # Streamlit cannot spend a second header row on Archive/Analysis.
            pack = get_theme_pack(
                world[4]
            )
            section_key = (
                f"v3_main_section_{world[0]}"
            )
            (
                chapter_hud_col,
                archive_col,
                report_col,
            ) = st.columns(
                [0.84, 0.08, 0.08],
                gap="small",
                vertical_alignment="center",
            )

            with chapter_hud_col:
                _render_chapter_story(
                    user=user,
                    world=world,
                    chapter=chapter,
                    review_expanded=False,
                    render_header=True,
                    render_tools=False,
                )

            with archive_col:
                if st.button(
                    "📚 기록",
                    key=f"v3_shell_archive_{world[0]}",
                    help=pack["archive_name"],
                    use_container_width=True,
                ):
                    st.session_state[section_key] = pack["archive_name"]
                    st.rerun()

            with report_col:
                if st.button(
                    "📊 분석",
                    key=f"v3_shell_report_{world[0]}",
                    help=pack["report_name"],
                    use_container_width=True,
                ):
                    st.session_state[section_key] = pack["report_name"]
                    st.rerun()

        with st.container(
            key=body_key,
        ):
            _render_post_story_mode_body(
                user=user,
                world=world,
                chapter=chapter,
                play_mode=play_mode,
            )

        with st.container(
            key=dock_key,
        ):
            render_play_action_hub(
                world_id=world[0],
                chapter_id=chapter[0],
                active_mode=play_mode,
                guide_name=guide_name,
                theme=world[4],
                learning_objectives=(
                    chapter[5]
                    or []
                ),
                target_concepts=(
                    targets
                    or []
                ),
            )


# DAY6_SINGLE_STICKY_QUIZ_HUD_V1

# DAY6_RESTORE_STACKED_STICKY_EVIDENCE_V1

# DAY6_DOUBLE_STICKY_COMPACT_TUNING_V1

# QUIZ_ANSWER_REPLY_DECIMAL_HOTFIX_V1_0_1_20260904

# COMPACT_TOOLS_ROW_ALIGNMENT_V1_20260906

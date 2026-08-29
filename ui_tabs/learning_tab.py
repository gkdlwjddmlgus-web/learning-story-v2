# DAY5_EVENT_FLUSH_FIX_V1
from __future__ import annotations

import hashlib
import logging
import html
import re
import time
import traceback

import streamlit as st

from components.learning_compact_ui import (
    render_compact_chapter_header,
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
    get_chapter,
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
    get_story_context,
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
    clean = re.sub(
        r"^\s*(?:[①②③④]|\(?[1-4]\)?[.)]|[1-4]\s*번[.)]?)\s*",
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
        with st.expander(profile["help_label"], expanded=False):
            st.write(evidence_help)


def _render_chapter_story(
    *,
    user,
    world,
    chapter,
) -> bool:
    pack = get_theme_pack(
        world[4]
    )

    context = get_story_context(
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

    # DAY5_STORY_CINEMATIC_V2_DEDICATED_INTEGRATION
    # Cinematic이 필요한 동안에는 Chapter heading/progress/학습 UI보다 먼저 화면을 독점한다.
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
        st.markdown('<span class="compact-learning-tools-marker"></span>', unsafe_allow_html=True)
        render_story_experience(
            chapter_id=chapter[0],
            theme=world[4],
            story_text=chapter[4],
            chapter_number=chapter[2],
            chapter_title=format_inline_text(chapter[3]),
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

    context = get_story_context(
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

    if not chapter[7]:
        mark_chapter_completed(
            chapter_id=chapter[0]
        )

    # Story State는 Chapter를 실제 완료한 뒤에만 반영한다.
    apply_completed_chapter_state(
        world_id=world[0],
        chapter=chapter,
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

    next_chapter = get_chapter(
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


def render_quiz(
    *,
    user,
    world,
    chapter,
) -> None:
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

    # DAY5_INVESTIGATION_BOARD_V2_INTEGRATION
    ui_mode = get_ui_support_mode(world[3])
    default_action = (
        ACTION_COMPANION
        if ui_mode in {"guided", "supported"}
        else ACTION_CLUE
    )
    active_action = render_investigation_board(
        theme=world[4],
        guide_name=guide_name,
        chapter_id=chapter[0],
        question_index=index,
        default_action=default_action,
        require_companion_before_deduce=(
            ui_mode in {"guided", "supported"}
        ),
        context_meta=investigation_meta,
    )

    if active_action is None:
        return

    if active_action == ACTION_CLUE:
        _render_learning_materials(
            theme=world[4],
            learner_level=world[3],
            difficulty=(question.get("difficulty") or "basic"),
            question=question,
            section=ACTION_CLUE,
        )
    elif active_action == ACTION_COMPANION:
        _render_learning_materials(
            theme=world[4],
            learner_level=world[3],
            difficulty=(question.get("difficulty") or "basic"),
            question=question,
            section=ACTION_COMPANION,
        )
    else:
        st.markdown(
            f"### {format_inline_text(question['question'])}"
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

    _render_bubble(
        speaker=user_name,
        message=user_answer_text,
        bubble_type="user",
        align="user",
    )

    if not st.session_state.get(
        "show_npc_reply",
        False,
    ):
        with st.spinner(
            f"{guide_name}가 네 답을 바라보고 있습니다..."
        ):
            time.sleep(
                0.55
            )

        st.session_state[
            "show_npc_reply"
        ] = True
        st.rerun()

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
            "좋은 선택이야!"
            if is_correct
            else "조금 헷갈렸던 것 같아. 같이 다시 보자."
        )

    _render_bubble(
        speaker=guide_name,
        message=feedback,
        bubble_type=(
            "npc-correct"
            if is_correct
            else "npc-wrong"
        ),
        align="npc",
    )

    story_progress = _sanitize_learning_text(
        question.get("story_progress")
    )

    if story_progress:
        experience_profile = get_theme_experience_profile(world[4])
        is_conclusion_step = index == len(questions) - 1

        if is_conclusion_step:
            label = (
                experience_profile["conclusion_label"]
                if is_correct
                else experience_profile["review_conclusion_label"]
            )
            if is_correct:
                st.success(f"✨ {label} · {story_progress}")
            else:
                st.info(f"✨ {label} · {story_progress}")
        else:
            label = (
                experience_profile["progress_label"]
                if is_correct
                else experience_profile["review_progress_label"]
            )
            if is_correct:
                st.success(f"✨ {label} · {story_progress}")
            else:
                st.info(f"✨ {label} · {story_progress}")

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


def render_learning_tab(
    user,
    world,
):
    chapter = get_chapter(
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

    # Dedicated Cinematic 중에는 mock caption을 포함한 다른 학습 UI를 먼저 렌더하지 않는다.
    if should_render_story_cinematic(
        chapter_id=chapter[0],
        story_text=chapter[4],
    ):
        _render_chapter_story(
            user=user,
            world=world,
            chapter=chapter,
        )
        return

    if is_ai_mock_enabled():
        st.caption(f"🧪 {generation_mode_label()} · Gemini 호출 없이 기능 흐름을 테스트 중입니다.")

    cinematic_active = _render_chapter_story(
        user=user,
        world=world,
        chapter=chapter,
    )

    if cinematic_active:
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

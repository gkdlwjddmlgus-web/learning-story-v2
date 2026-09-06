from __future__ import annotations

import html
import re
import time

import streamlit as st

from components.generated_text_readability import generated_text_readability_css

# DAY6_GENERATED_TEXT_READABILITY_V1_1


# DAY5_STORY_CINEMATIC_V10_RELAXED_STORY_HOLD
_THEME_STYLE = {
    "미스터리": {
        "accent": "#8d2630",
        "text": "#26231f",
        "muted": "#706b64",
        "stage_bg": (
            "radial-gradient(circle at 82% 16%, rgba(150,55,66,.10), transparent 30%),"
            "radial-gradient(circle at 16% 82%, rgba(92,82,69,.06), transparent 34%),"
            "linear-gradient(135deg,#f3f0e9 0%,#ece8e1 54%,#f1e7e5 100%)"
        ),
        "page_bg": (
            "linear-gradient(rgba(92,82,69,.026) 1px, transparent 1px),"
            "linear-gradient(90deg, rgba(92,82,69,.026) 1px, transparent 1px),"
            "linear-gradient(145deg,#fffdf8 0%,#f8f4ed 58%,#f4ece9 100%)"
        ),
        "page_border": "rgba(112,91,79,.24)",
        "page_shadow": "0 24px 64px rgba(82,66,55,.15), 0 3px 10px rgba(82,66,55,.10)",
        "page_back": "#eee7de",
        "page_label": "CASE FILE",
        "cta": "🔎 조사하러 간다",
    },
    "SF": {
        "accent": "#3ed6f4",
        "text": "#e9faff",
        "muted": "#9fc5d3",
        "stage_bg": (
            "radial-gradient(circle at 76% 18%, rgba(35,209,235,.16), transparent 32%),"
            "radial-gradient(circle at 14% 78%, rgba(80,86,214,.14), transparent 34%),"
            "linear-gradient(135deg,#04121e 0%,#071d2d 52%,#072d39 100%)"
        ),
        "page_bg": (
            "linear-gradient(rgba(62,214,244,.055) 1px, transparent 1px),"
            "linear-gradient(90deg, rgba(62,214,244,.055) 1px, transparent 1px),"
            "linear-gradient(145deg,rgba(7,31,49,.97) 0%,rgba(7,42,57,.97) 100%)"
        ),
        "page_border": "rgba(62,214,244,.34)",
        "page_shadow": "0 24px 70px rgba(0,0,0,.34), 0 0 34px rgba(62,214,244,.08)",
        "page_back": "#082434",
        "page_label": "SYSTEM LOG",
        "cta": "◉ 시스템에 접속한다",
    },
    "판타지": {
        "accent": "#caa55d",
        "text": "#f4ead5",
        "muted": "#d6c5a5",
        "stage_bg": (
            "radial-gradient(circle at 22% 18%, rgba(202,165,93,.15), transparent 30%),"
            "radial-gradient(circle at 82% 22%, rgba(103,74,153,.15), transparent 32%),"
            "linear-gradient(135deg,#171512 0%,#1a181b 52%,#261f30 100%)"
        ),
        "page_bg": (
            "radial-gradient(circle at 18% 12%, rgba(202,165,93,.08), transparent 28%),"
            "linear-gradient(145deg,rgba(42,36,31,.98) 0%,rgba(36,31,38,.98) 100%)"
        ),
        "page_border": "rgba(202,165,93,.32)",
        "page_shadow": "0 24px 70px rgba(0,0,0,.34), 0 0 30px rgba(202,165,93,.07)",
        "page_back": "#211c1a",
        "page_label": "CHRONICLE",
        "cta": "✦ 흔적을 따라간다",
    },
    "무협": {
        "accent": "#9f3a32",
        "text": "#2b2520",
        "muted": "#6f6257",
        "stage_bg": (
            "radial-gradient(circle at 82% 18%, rgba(159,58,50,.08), transparent 30%),"
            "linear-gradient(135deg,#efe6d5 0%,#e7dcc7 56%,#efe4d3 100%)"
        ),
        "page_bg": (
            "repeating-linear-gradient(0deg, rgba(97,76,55,.025) 0 1px, transparent 1px 6px),"
            "linear-gradient(145deg,#faf2df 0%,#f2e5cf 100%)"
        ),
        "page_border": "rgba(112,86,61,.24)",
        "page_shadow": "0 24px 64px rgba(91,69,48,.15), 0 3px 10px rgba(91,69,48,.09)",
        "page_back": "#e8dbc3",
        "page_label": "JOURNAL",
        "cta": "◎ 길을 나선다",
    },
    "동화": {
        "accent": "#d76a89",
        "text": "#4d2834",
        "muted": "#7e5a66",
        "stage_bg": (
            "radial-gradient(circle at 18% 18%, rgba(242,154,176,.17), transparent 31%),"
            "radial-gradient(circle at 82% 16%, rgba(126,213,194,.17), transparent 30%),"
            "linear-gradient(135deg,#fff5f7 0%,#fff9f4 55%,#eef9f6 100%)"
        ),
        "page_bg": (
            "radial-gradient(circle at 90% 12%, rgba(126,213,194,.10), transparent 25%),"
            "radial-gradient(circle at 12% 88%, rgba(242,154,176,.10), transparent 28%),"
            "linear-gradient(145deg,#fffefe 0%,#fff8f5 100%)"
        ),
        "page_border": "rgba(215,106,137,.20)",
        "page_shadow": "0 24px 64px rgba(126,91,102,.12), 0 3px 10px rgba(126,91,102,.08)",
        "page_back": "#f8efef",
        "page_label": "STORY PAGE",
        "cta": "✨ 이야기 속으로 들어간다",
    },
}


def get_story_cinematic_seen_key(chapter_id: int) -> str:
    # v8 QA에서 기존 시네마틱을 이미 본 세션도 Chapter Intro Scene을 한 번 확인할 수 있게 별도 key를 사용한다.
    return f"story_cinematic_v10_seen_{chapter_id}"


def _get_started_key(chapter_id: int) -> str:
    return f"story_cinematic_v10_started_at_{chapter_id}"


def _get_manual_index_key(chapter_id: int) -> str:
    return f"story_cinematic_v10_manual_index_{chapter_id}"


def _get_final_ready_key(chapter_id: int) -> str:
    """자동 시네마틱의 마지막 Scene을 정적 화면으로 전환하기 위한 session flag."""
    return f"story_cinematic_v10_final_ready_{chapter_id}"


def _split_story_sentences(story_text: str) -> list[str]:
    text = str(story_text or "").strip()
    if not text:
        return []

    normalized = re.sub(r"\s*\n\s*", " ", text)
    sentences = [
        item.strip()
        for item in re.split(r"(?<=[.!?。！？])\s+", normalized)
        if item.strip()
    ]
    return sentences or [text]


def _split_story_paragraphs(story_text: str) -> list[str]:
    text = str(story_text or "").strip()
    if not text:
        return []

    paragraphs = [
        item.strip()
        for item in re.split(r"\n\s*\n+", text)
        if item.strip()
    ]
    if len(paragraphs) > 1:
        return paragraphs

    sentences = _split_story_sentences(text)
    if len(sentences) <= 2:
        return [text]

    return [
        " ".join(sentences[index:index + 2])
        for index in range(0, len(sentences), 2)
    ]


def _sentence_seconds(sentence: str) -> float:
    # DAY5 v10: v9가 실제 읽기에서는 조금 빠르게 느껴져 Story Scene 체류시간을 한 단계 더 늘린다.
    # 공백 제외 글자 수를 기준으로 약 2.80 ~ 5.60초 범위에서 가변한다.
    # 3줄 안팎의 보통 문장은 대체로 4.5~5초대까지 확보한다.
    visible_length = len(re.sub(r"\s+", "", str(sentence or "")))
    return max(2.80, min(5.60, 1.75 + visible_length * 0.055))


def _intro_seconds(chapter_title: str | None) -> float:
    """Intro는 v8/v9에서 확정한 체류감을 그대로 유지한다.

    Story 본문 timing만 늘리고 Intro는 이전 v9 계산식을 별도로 사용해
    최소 4.50초 + 기존 title 길이 보정을 유지한다.
    """
    title = str(chapter_title or "CHAPTER").strip()
    visible_length = len(re.sub(r"\s+", "", title))
    previous_story_seconds = max(2.40, min(4.80, 1.55 + visible_length * 0.048))
    return max(4.50, previous_story_seconds + 2.00)


def _story_line_size_class(sentence: str) -> str:
    """문장 길이에 따라 Scene Page 활자 크기 class를 결정한다."""
    visible_length = len(re.sub(r"\s+", "", str(sentence or "")))
    if visible_length <= 42:
        return "story-line-short"
    if visible_length <= 78:
        return "story-line-medium"
    if visible_length <= 118:
        return "story-line-long"
    return "story-line-xlong"


def should_render_story_cinematic(*, chapter_id: int, story_text: str) -> bool:
    if not str(story_text or "").strip():
        return False
    return not bool(st.session_state.get(get_story_cinematic_seen_key(chapter_id)))


def _mark_seen(chapter_id: int) -> None:
    st.session_state[get_story_cinematic_seen_key(chapter_id)] = True
    st.session_state.pop(_get_started_key(chapter_id), None)
    st.session_state.pop(_get_manual_index_key(chapter_id), None)
    st.session_state.pop(_get_final_ready_key(chapter_id), None)


def _inject_css(theme: str) -> None:
    st.markdown(
        generated_text_readability_css(),
        unsafe_allow_html=True,
    )
    style = _THEME_STYLE.get(theme, _THEME_STYLE["동화"])
    # 미스터리는 사건 기록을 직접 읽는 느낌을 위해 손글씨/명조 계열 local font를 우선한다.
    # 해당 글꼴이 설치되어 있지 않으면 Batang/serif로 안전하게 fallback한다.
    story_font = (
        '"나눔손글씨 펜", "Nanum Pen Script", "휴먼편지체", '
        '"Segoe Print", "Bradley Hand", "Apple Chancery", "Batang", serif'
        if theme == "미스터리"
        else 'inherit'
    )
    # Story 본문은 특정 단어만 임의로 강조하지 않는다.
    # AI 기반 강조 규칙을 추가하지 않는 대신 모든 Theme에서 기본 굵기를 normal로 통일한다.
    story_weight = "400"
    st.markdown(
        f"""
        <style>
        .stApp {{
            --cine-accent:{style['accent']};
            --cine-text:{style['text']};
            --cine-muted:{style['muted']};
            --cine-page-bg:{style['page_bg']};
            --cine-page-border:{style['page_border']};
            --cine-page-shadow:{style['page_shadow']};
            --cine-page-back:{style['page_back']};
            --cine-story-font:{story_font};
            --cine-story-weight:{story_weight};
        }}

        /* Dedicated Cinematic에서는 앱 내부 chrome을 숨기고 Scene Page가 화면을 소유한다. */
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stDeployButton"],
        #MainMenu,
        footer {{
            display:none !important;
        }}

        .stApp {{
            background:{style['stage_bg']} !important;
        }}

        .block-container {{
            max-width:1280px !important;
            padding-top:clamp(1rem,3.5vh,2.6rem) !important;
            padding-bottom:2rem !important;
            padding-left:clamp(1rem,4vw,3.4rem) !important;
            padding-right:clamp(1rem,4vw,3.4rem) !important;
        }}

        .story-cinematic-root {{ width:100%; }}

        .story-scene-stack {{
            position:relative;
            width:min(100%, 1010px);
            margin:0 auto;
        }}

        .story-scene-stack::before {{
            content:"";
            position:absolute;
            inset:12px -8px -8px 12px;
            border-radius:18px;
            background:var(--cine-page-back);
            border:1px solid var(--cine-page-border);
            opacity:.62;
            z-index:0;
        }}

        .story-scene-page {{
            position:relative;
            z-index:1;
            width:100%;
            min-height:clamp(430px,58vh,585px);
            box-sizing:border-box;
            padding:clamp(2rem,4.5vw,4.2rem) clamp(2rem,6vw,5.8rem) clamp(5.5rem,10vh,7.2rem);
            display:flex;
            align-items:center;
            justify-content:center;
            overflow:hidden;
            border-radius:18px;
            border:1px solid var(--cine-page-border);
            background:var(--cine-page-bg);
            background-size:30px 30px,30px 30px,auto;
            box-shadow:var(--cine-page-shadow);
        }}

        /* DAY5 v6:
           Scene Page는 고정하고 문장만 soft fade + blur로 전환한다.
           Story 본문은 normal weight로 유지한다. */

        .story-scene-label {{
            position:absolute;
            top:clamp(1.25rem,2.4vw,2rem);
            left:clamp(1.5rem,3.2vw,3rem);
            color:var(--cine-accent);
            font-size:.72rem;
            font-weight:900;
            letter-spacing:.20em;
        }}

        /* Chapter 번호/제목은 고정 header가 아니라 시네마틱의 첫 Scene으로만 등장한다. */
        .story-intro-content {{
            max-width:880px;
            margin:0 auto;
            text-align:center;
            color:var(--cine-text);
            transform:translateY(-2%);
            will-change:opacity,filter,transform;
        }}
        .story-intro-kicker {{
            color:var(--cine-accent);
            font-size:clamp(.82rem,1.25vw,1rem);
            font-weight:900;
            letter-spacing:.28em;
            margin-bottom:1.15rem;
        }}
        .story-intro-title {{
            max-width:860px;
            margin:0 auto;
            color:var(--cine-text);
            font-family:inherit;
            font-size:clamp(2rem,4.15vw,3.65rem);
            line-height:1.28;
            font-weight:800;
            text-wrap:balance;
            word-break:keep-all;
        }}
        .story-intro-content.intro-fade-in {{
            animation:chapterIntroFadeIn 1.08s cubic-bezier(.20,.72,.24,1) both;
        }}
        .story-intro-content.intro-fade-out {{
            animation:chapterIntroFadeOut .96s ease-in both;
        }}
        @keyframes chapterIntroFadeIn {{
            0% {{ opacity:0; filter:blur(9px); transform:translateY(4%) scale(.988); }}
            55% {{ opacity:.72; filter:blur(2.8px); }}
            100% {{ opacity:1; filter:blur(0); transform:translateY(-2%) scale(1); }}
        }}
        @keyframes chapterIntroFadeOut {{
            0% {{ opacity:1; filter:blur(0); transform:translateY(-2%) scale(1); }}
            52% {{ opacity:.58; filter:blur(2.4px); }}
            100% {{ opacity:0; filter:blur(9px); transform:translateY(-7%) scale(.988); }}
        }}

        .story-scene-line {{
            max-width:900px;
            margin:0 auto;
            color:var(--cine-text);
            font-family:var(--cine-story-font);
            font-size:clamp(1.72rem,2.72vw,2.25rem);
            line-height:1.62;
            font-weight:var(--cine-story-weight);
            text-align:center;
            text-wrap:balance;
            word-break:keep-all;
            transform:translateY(-3%);
            will-change:opacity,filter,transform;
        }}

        /* v4보다 한 단계 낮추되 v3보다 조금 큰 중간 scale로 조정한다. */
        .story-scene-line.story-line-short {{
            max-width:850px;
            font-size:clamp(1.92rem,3.05vw,2.45rem);
            line-height:1.56;
        }}
        .story-scene-line.story-line-medium {{
            max-width:900px;
            font-size:clamp(1.82rem,2.88vw,2.30rem);
        }}
        .story-scene-line.story-line-long {{
            max-width:930px;
            font-size:clamp(1.68rem,2.58vw,2.08rem);
            line-height:1.64;
        }}
        .story-scene-line.story-line-xlong {{
            max-width:950px;
            font-size:clamp(1.55rem,2.32vw,1.92rem);
            line-height:1.68;
        }}

        .story-scene-line.fade-in-even {{
            animation:storyTextFadeInA .58s cubic-bezier(.20,.72,.24,1) both;
        }}
        .story-scene-line.fade-in-odd {{
            animation:storyTextFadeInB .58s cubic-bezier(.20,.72,.24,1) both;
        }}
        .story-scene-line.fade-out-even {{
            animation:storyTextFadeOutA .46s ease-in both;
        }}
        .story-scene-line.fade-out-odd {{
            animation:storyTextFadeOutB .46s ease-in both;
        }}

        @keyframes storyTextFadeInA {{
            0% {{ opacity:0; filter:blur(7px); transform:translateY(4%) scale(.992); }}
            52% {{ opacity:.72; filter:blur(2.2px); }}
            100% {{ opacity:1; filter:blur(0); transform:translateY(-3%) scale(1); }}
        }}
        @keyframes storyTextFadeInB {{
            0% {{ opacity:0; filter:blur(7.01px); transform:translateY(4%) scale(.992); }}
            52% {{ opacity:.72; filter:blur(2.21px); }}
            100% {{ opacity:1; filter:blur(0); transform:translateY(-3%) scale(1); }}
        }}
        @keyframes storyTextFadeOutA {{
            0% {{ opacity:1; filter:blur(0); transform:translateY(-3%) scale(1); }}
            48% {{ opacity:.58; filter:blur(2px); }}
            100% {{ opacity:0; filter:blur(7px); transform:translateY(-7%) scale(.992); }}
        }}
        @keyframes storyTextFadeOutB {{
            0% {{ opacity:1; filter:blur(0); transform:translateY(-3%) scale(1); }}
            48% {{ opacity:.58; filter:blur(2.01px); }}
            100% {{ opacity:0; filter:blur(7.01px); transform:translateY(-7%) scale(.992); }}
        }}

        .story-scene-number {{
            position:absolute;
            right:clamp(1.5rem,3.2vw,3rem);
            bottom:clamp(1.25rem,2.4vw,2rem);
            color:var(--cine-muted);
            font-size:.72rem;
            letter-spacing:.13em;
            opacity:.78;
        }}

        /* Skip은 접근 가능하지만 Story보다 강하게 보이지 않는 secondary action으로 둔다. */
        div[data-testid="stButton"]:has(button[kind="secondary"]) {{
            max-width:180px;
            margin:.2rem 0 .65rem auto;
        }}
        button[kind="secondary"] {{
            min-height:2.35rem !important;
            background:rgba(255,255,255,.035) !important;
            border-color:var(--cine-page-border) !important;
            color:var(--cine-muted) !important;
            box-shadow:none !important;
            font-size:.82rem !important;
        }}

        /* 마지막 CTA는 페이지 하단 안쪽에 걸쳐 보이도록 배치한다. */
        div[data-testid="stButton"]:has(button[kind="primary"]) {{
            position:relative;
            z-index:4;
            max-width:540px;
            margin:-5.7rem auto 1.7rem;
        }}
        button[kind="primary"] {{
            min-height:3.15rem !important;
            font-weight:800 !important;
            letter-spacing:.01em !important;
        }}

        @media (max-width:768px) {{
            .block-container {{
                padding-top:.75rem !important;
                padding-left:.85rem !important;
                padding-right:.85rem !important;
            }}
            .story-intro-kicker {{
                font-size:.72rem;
                margin-bottom:.9rem;
            }}
            .story-intro-title {{
                font-size:clamp(1.8rem,8.2vw,2.45rem);
                line-height:1.32;
            }}
            .story-scene-stack {{ width:100%; }}
            .story-scene-stack::before {{
                inset:7px -3px -5px 7px;
                border-radius:15px;
            }}
            .story-scene-page {{
                min-height:520px;
                border-radius:15px;
                padding:3.7rem 1.35rem 6rem;
            }}
            .story-scene-line {{
                transform:translateY(-2%);
                line-height:1.60;
            }}
            .story-scene-line.story-line-short {{
                font-size:clamp(1.48rem,6.3vw,1.82rem);
            }}
            .story-scene-line.story-line-medium {{
                font-size:clamp(1.40rem,5.9vw,1.70rem);
            }}
            .story-scene-line.story-line-long {{
                font-size:clamp(1.31rem,5.4vw,1.57rem);
                line-height:1.64;
            }}
            .story-scene-line.story-line-xlong {{
                font-size:clamp(1.22rem,5.0vw,1.46rem);
                line-height:1.67;
            }}
            .story-scene-label {{ top:1.2rem; left:1.25rem; }}
            .story-scene-number {{ right:1.25rem; bottom:1.2rem; }}
            div[data-testid="stButton"]:has(button[kind="secondary"]) {{
                max-width:150px;
                margin:.1rem 0 .5rem auto;
            }}
            div[data-testid="stButton"]:has(button[kind="primary"]) {{
                max-width:calc(100% - 2.6rem);
                margin:-5.45rem auto 1.25rem;
            }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            .story-intro-content,
            .story-intro-content.intro-fade-in,
            .story-intro-content.intro-fade-out,
            .story-scene-line,
            .story-scene-line.fade-in-even,
            .story-scene-line.fade-in-odd,
            .story-scene-line.fade-out-even,
            .story-scene-line.fade-out-odd {{
                animation:none !important;
                opacity:1 !important;
                filter:none !important;
                transform:translateY(-3%) !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_intro_scene_page(
    *,
    theme: str,
    chapter_number: int | None,
    chapter_title: str | None,
    transition_phase: str = "intro-fade-in",
) -> None:
    style = _THEME_STYLE.get(theme, _THEME_STYLE["동화"])
    chapter_label = (
        f"CHAPTER {int(chapter_number)}"
        if chapter_number is not None
        else "CHAPTER"
    )
    safe_title = html.escape(str(chapter_title or "").strip() or "새로운 이야기")

    st.markdown(
        (
            '<div class="story-cinematic-root"></div>'
            '<div class="story-scene-stack">'
            '<article class="story-scene-page story-intro-page" data-scene-page="intro">'
            f'<div class="story-scene-label">{html.escape(style["page_label"])}</div>'
            f'<div class="story-intro-content {transition_phase}">'
            f'<div class="story-intro-kicker">{chapter_label}</div>'
            f'<div class="story-intro-title">{safe_title}</div>'
            '</div>'
            '</article>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def _render_scene_page(
    *,
    theme: str,
    chapter_number: int | None,
    chapter_title: str | None,
    sentence: str,
    current_index: int,
    total_count: int,
    transition_phase: str = "fade-in",
) -> None:
    style = _THEME_STYLE.get(theme, _THEME_STYLE["동화"])
    parity = "even" if current_index % 2 == 0 else "odd"
    transition_class = f"{transition_phase}-{parity}"
    line_size_class = _story_line_size_class(sentence)

    st.markdown(
        (
            '<div class="story-cinematic-root"></div>'
            '<div class="story-scene-stack">'
            f'<article class="story-scene-page" data-scene-page="{current_index + 1}">'
            f'<div class="story-scene-label">{html.escape(style["page_label"])}</div>'
            f'<p class="story-scene-line {line_size_class} {transition_class}">{html.escape(sentence)}</p>'
            f'<div class="story-scene-number">{current_index + 1:02d} / {total_count:02d}</div>'
            '</article>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def _render_exit_button(*, chapter_id: int, theme: str) -> None:
    style = _THEME_STYLE.get(theme, _THEME_STYLE["동화"])
    if st.button(
        style["cta"],
        key=f"story_cinematic_v10_finish_{chapter_id}",
        type="primary",
        use_container_width=True,
    ):
        _mark_seen(chapter_id)
        st.rerun()


def _render_skip_button(*, chapter_id: int) -> None:
    if st.button(
        "건너뛰기 →",
        key=f"story_cinematic_v10_skip_{chapter_id}",
        type="secondary",
        use_container_width=True,
    ):
        _mark_seen(chapter_id)
        st.rerun()


def _render_auto_cinematic(
    *,
    chapter_id: int,
    theme: str,
    chapter_number: int | None,
    chapter_title: str | None,
    sentences: tuple[str, ...],
) -> None:
    sentence_list = list(sentences)
    if not sentence_list:
        _mark_seen(chapter_id)
        st.rerun()

    started_key = _get_started_key(chapter_id)
    if started_key not in st.session_state:
        st.session_state[started_key] = time.monotonic()

    elapsed = max(0.0, time.monotonic() - float(st.session_state[started_key]))
    intro_duration = _intro_seconds(chapter_title)

    # DAY5 v8: Chapter 번호/제목이 시네마틱의 첫 Scene을 전담한다.
    # fade-in/fade-out은 유지하고, 전체 Intro 체류를 최소 4.50초로 늘려 제목의 정지 구간을 충분히 확보한다.
    if elapsed < intro_duration:
        intro_remaining = max(0.0, intro_duration - elapsed)
        intro_phase = (
            "intro-fade-out"
            if intro_remaining <= 0.96
            else "intro-fade-in"
        )
        _render_skip_button(chapter_id=chapter_id)
        _render_intro_scene_page(
            theme=theme,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            transition_phase=intro_phase,
        )
        return

    story_elapsed = elapsed - intro_duration
    durations = [_sentence_seconds(sentence) for sentence in sentence_list]

    reveal_times = [0.0]
    cumulative = 0.0
    for duration in durations[:-1]:
        cumulative += duration
        reveal_times.append(cumulative)

    current_index = max(
        0,
        min(
            len(sentence_list) - 1,
            sum(1 for reveal_at in reveal_times if story_elapsed >= reveal_at) - 1,
        ),
    )

    is_last = current_index == len(sentence_list) - 1
    local_elapsed = max(0.0, story_elapsed - reveal_times[current_index])
    remaining = max(0.0, durations[current_index] - local_elapsed)
    # 마지막 문장은 CTA를 읽고 선택해야 하므로 자동 fade-out하지 않는다.
    transition_phase = (
        "fade-out"
        if (not is_last and remaining <= 0.46)
        else "fade-in"
    )

    if is_last:
        # 마지막 Scene은 periodic fragment에서 분리해 정적으로 렌더한다.
        st.session_state[_get_final_ready_key(chapter_id)] = True
        st.rerun()

    _render_skip_button(chapter_id=chapter_id)

    _render_scene_page(
        theme=theme,
        chapter_number=chapter_number,
        chapter_title=chapter_title,
        sentence=sentence_list[current_index],
        current_index=current_index,
        total_count=len(sentence_list),
        transition_phase=transition_phase,
    )


_fragment_factory = getattr(st, "fragment", None)
_AUTO_CINEMATIC_FRAGMENT = (
    _fragment_factory(run_every=0.25)(_render_auto_cinematic)
    if _fragment_factory is not None
    else None
)


def _render_manual_cinematic(
    *,
    chapter_id: int,
    theme: str,
    chapter_number: int | None,
    chapter_title: str | None,
    sentences: list[str],
) -> None:
    index_key = _get_manual_index_key(chapter_id)
    if index_key not in st.session_state:
        # -1은 Chapter Intro Scene, 0부터 Story 문장 index다.
        st.session_state[index_key] = -1

    current_index = max(-1, min(int(st.session_state[index_key]), len(sentences) - 1))

    if current_index == -1:
        _render_skip_button(chapter_id=chapter_id)
        _render_intro_scene_page(
            theme=theme,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            transition_phase="intro-fade-in",
        )
        if st.button(
            "스토리 시작 →",
            key=f"story_cinematic_v10_intro_next_{chapter_id}",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state[index_key] = 0
            st.rerun()
        return

    is_last = current_index == len(sentences) - 1

    if not is_last:
        _render_skip_button(chapter_id=chapter_id)

    _render_scene_page(
        theme=theme,
        chapter_number=chapter_number,
        chapter_title=chapter_title,
        sentence=sentences[current_index],
        current_index=current_index,
        total_count=len(sentences),
        transition_phase="fade-in",
    )

    if is_last:
        _render_exit_button(chapter_id=chapter_id, theme=theme)
        return

    if st.button(
        "다음 페이지 →",
        key=f"story_cinematic_v10_next_{chapter_id}",
        type="secondary",
        use_container_width=True,
    ):
        st.session_state[index_key] = current_index + 1
        st.rerun()


def render_story_review(*, story_text: str) -> None:
    paragraphs = _split_story_paragraphs(story_text)

    with st.expander("📖 스토리 다시보기", expanded=False):
        # Readability CSS는 expander 내부에서 주입한다.
        # expander 앞에 별도 st.markdown element container가 생기면
        # 같은 row의 오른쪽 expander보다 Story Review가 아래로 밀릴 수 있다.
        st.markdown(
            generated_text_readability_css(),
            unsafe_allow_html=True,
        )

        paragraphs_html = "".join(
            '<p class="story-paragraph">'
            f"{html.escape(item)}"
            "</p>"
            for item in paragraphs
        )
        st.markdown(
            f'<article class="story-card story-review-card">{paragraphs_html}</article>',
            unsafe_allow_html=True,
        )


def render_story_experience(
    *,
    chapter_id: int,
    theme: str,
    story_text: str,
    chapter_number: int | None = None,
    chapter_title: str | None = None,
) -> bool:
    """
    True: Dedicated Cinematic Scene Page가 현재 화면을 독점 중.
    False: Cinematic을 종료했으며 접힌 Story Review를 렌더함.

    v8 seen state는 QA/UX 검증을 위해 session-scoped다. DB schema는 변경하지 않는다.
    """
    seen_key = get_story_cinematic_seen_key(chapter_id)
    if st.session_state.get(seen_key):
        render_story_review(story_text=story_text)
        return False

    sentences = _split_story_sentences(story_text)
    if not sentences:
        _mark_seen(chapter_id)
        render_story_review(story_text=story_text)
        return False

    _inject_css(theme)

    # 마지막 문장은 fragment 밖에서 정적으로 렌더한다.
    # 이렇게 해야 마지막 CTA와 문장이 run_every 주기마다 재생성되어 깜빡이는 현상을 막을 수 있다.
    if st.session_state.get(_get_final_ready_key(chapter_id)):
        last_index = len(sentences) - 1
        _render_scene_page(
            theme=theme,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            sentence=sentences[last_index],
            current_index=last_index,
            total_count=len(sentences),
            transition_phase="fade-in",
        )
        _render_exit_button(chapter_id=chapter_id, theme=theme)
        return True

    if _AUTO_CINEMATIC_FRAGMENT is not None:
        _AUTO_CINEMATIC_FRAGMENT(
            chapter_id=chapter_id,
            theme=theme,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            sentences=tuple(sentences),
        )
    else:
        _render_manual_cinematic(
            chapter_id=chapter_id,
            theme=theme,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            sentences=sentences,
        )

    return True

# STORY_REVIEW_EXPANDER_ALIGNMENT_V1_20260906

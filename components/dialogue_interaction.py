from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path

import streamlit as st


# DAY6_DIALOGUE_INTERACTION_CARD_V1

_SPEAKER_TYPES = {
    "companion",
    "player",
    "npc",
}

_THEME_STYLE = {
    "동화": {
        "accent": "#df7191",
        "text": "#4d2834",
        "muted": "#8d6571",
        "surface": "rgba(255,250,249,.96)",
        "surface_alt": "rgba(255,241,245,.96)",
        "border": "rgba(223,113,145,.32)",
        "portrait": "linear-gradient(145deg,#fff7f9,#ffeef3)",
        "correct": "#7fae91",
        "wrong": "#c98686",
        "shadow": "rgba(125,82,94,.10)",
    },
    "판타지": {
        "accent": "#aa9bc8",
        "text": "#ebe7f1",
        "muted": "#bdb6c9",
        "surface": "rgba(30,28,38,.96)",
        "surface_alt": "rgba(39,35,50,.97)",
        "border": "rgba(170,155,200,.34)",
        "portrait": "linear-gradient(145deg,#393244,#24202d)",
        "correct": "#87ab91",
        "wrong": "#b9858f",
        "shadow": "rgba(20,16,28,.24)",
    },
    "SF": {
        "accent": "#83b7c0",
        "text": "#e8f0f2",
        "muted": "#b5c8cc",
        "surface": "rgba(10,27,35,.96)",
        "surface_alt": "rgba(13,37,47,.97)",
        "border": "rgba(131,183,192,.36)",
        "portrait": "linear-gradient(145deg,#153d4a,#0b242d)",
        "correct": "#78a995",
        "wrong": "#b77d82",
        "shadow": "rgba(4,19,24,.26)",
    },
    "무협": {
        "accent": "#9c3f35",
        "text": "#493b30",
        "muted": "#7f6a55",
        "surface": "rgba(248,240,221,.97)",
        "surface_alt": "rgba(241,228,199,.98)",
        "border": "rgba(156,63,53,.28)",
        "portrait": "linear-gradient(145deg,#f3e4c5,#e6d0ab)",
        "correct": "#778d67",
        "wrong": "#a95f58",
        "shadow": "rgba(96,69,42,.12)",
    },
    "미스터리": {
        "accent": "#d1ad70",
        "text": "#f4eee4",
        "muted": "#d2c2ac",
        "surface": "rgba(35,31,30,.97)",
        "surface_alt": "rgba(47,40,37,.98)",
        "border": "rgba(209,173,112,.32)",
        "portrait": "linear-gradient(145deg,#4a4038,#2c2724)",
        "correct": "#8ca58b",
        "wrong": "#b9827c",
        "shadow": "rgba(15,12,11,.25)",
    },
}

_ROLE_FALLBACK = {
    "companion": "🐈",
    "player": "👤",
    "npc": "◆",
}


def _normalize_theme(theme: str) -> str:
    return theme if theme in _THEME_STYLE else "동화"


def _normalize_speaker_type(speaker_type: str) -> str:
    value = str(speaker_type or "").strip().lower()
    return value if value in _SPEAKER_TYPES else "npc"


def _normalize_tone(tone: str) -> str:
    value = str(tone or "").strip().lower()
    if value not in {"neutral", "correct", "wrong"}:
        return "neutral"
    return value


def _data_uri(path: str | Path | None) -> str | None:
    if not path:
        return None

    file_path = Path(path)
    if not file_path.is_file():
        return None

    mime_type, _ = mimetypes.guess_type(file_path.name)
    mime_type = mime_type or "image/png"
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _css(theme: str) -> str:
    style = _THEME_STYLE[_normalize_theme(theme)]

    return f"""
    <style>
    .day6-inline-dialogue {{
        --dlg-accent:{style["accent"]};
        --dlg-text:{style["text"]};
        --dlg-muted:{style["muted"]};
        --dlg-surface:{style["surface"]};
        --dlg-surface-alt:{style["surface_alt"]};
        --dlg-border:{style["border"]};
        --dlg-portrait:{style["portrait"]};
        --dlg-correct:{style["correct"]};
        --dlg-wrong:{style["wrong"]};
        --dlg-shadow:{style["shadow"]};

        width:min(100%,1120px);
        margin:.55rem auto;
        box-sizing:border-box;
        display:grid;
        grid-template-columns:82px minmax(0,1fr);
        gap:1rem;
        align-items:center;
        min-height:112px;
        padding:.9rem 1rem;
        border:1px solid var(--dlg-border);
        border-left:4px solid var(--dlg-accent);
        border-radius:16px;
        background:
            linear-gradient(135deg,var(--dlg-surface),var(--dlg-surface-alt));
        box-shadow:0 9px 26px var(--dlg-shadow);
        color:var(--dlg-text);
    }}

    .day6-inline-dialogue.tone-correct {{
        border-left-color:var(--dlg-correct);
    }}

    .day6-inline-dialogue.tone-wrong {{
        border-left-color:var(--dlg-wrong);
    }}

    .day6-inline-dialogue.player {{
        grid-template-columns:minmax(0,1fr) 82px;
    }}

    .day6-inline-dialogue .inline-dialogue-portrait {{
        width:72px;
        height:72px;
        border-radius:15px;
        overflow:hidden;
        display:flex;
        align-items:center;
        justify-content:center;
        background:var(--dlg-portrait);
        border:1px solid var(--dlg-border);
        box-shadow:0 5px 16px var(--dlg-shadow);
    }}

    .day6-inline-dialogue .inline-dialogue-portrait img {{
        width:100%;
        height:100%;
        object-fit:cover;
        display:block;
    }}

    .day6-inline-dialogue .inline-dialogue-fallback {{
        font-size:2rem;
        line-height:1;
    }}

    .day6-inline-dialogue .inline-dialogue-copy {{
        min-width:0;
        display:flex;
        flex-direction:column;
        align-items:flex-start;
        text-align:left;
    }}

    .day6-inline-dialogue.player .inline-dialogue-copy {{
        order:1;
    }}

    .day6-inline-dialogue.player .inline-dialogue-portrait {{
        order:2;
        justify-self:end;
    }}

    .day6-inline-dialogue .inline-dialogue-speaker {{
        margin:0 0 .28rem;
        color:var(--dlg-accent);
        font-size:.78rem;
        line-height:1.35;
        font-weight:850;
        letter-spacing:.02em;
    }}

    .day6-inline-dialogue .inline-dialogue-text {{
        margin:0;
        color:var(--dlg-text);
        font-size:clamp(1rem,1.18vw,1.12rem);
        line-height:1.72;
        font-weight:600;
        word-break:keep-all;
        overflow-wrap:break-word;
        line-break:strict;
    }}

    @media (max-width:760px) {{
        .day6-inline-dialogue,
        .day6-inline-dialogue.player {{
            grid-template-columns:58px minmax(0,1fr);
            gap:.72rem;
            min-height:92px;
            padding:.75rem .8rem;
            border-radius:14px;
        }}

        .day6-inline-dialogue.player {{
            grid-template-columns:minmax(0,1fr) 58px;
        }}

        .day6-inline-dialogue .inline-dialogue-portrait {{
            width:52px;
            height:52px;
            border-radius:12px;
        }}

        .day6-inline-dialogue .inline-dialogue-fallback {{
            font-size:1.55rem;
        }}

        .day6-inline-dialogue .inline-dialogue-text {{
            font-size:.98rem;
            line-height:1.65;
        }}
    }}
    </style>
    """


def render_dialogue_interaction(
    *,
    theme: str,
    speaker_type: str,
    speaker_name: str,
    text: str,
    portrait_path: str | Path | None = None,
    tone: str = "neutral",
) -> None:
    """
    Learning 화면 안에서 쓰는 compact character dialogue card.

    - Companion/NPC: portrait left + visible speaker name
    - Player: portrait right + visible speaker name hidden
    - Full Dialogue Scene과 달리 stage를 만들지 않아 학습 흐름을 끊지 않는다.
    """
    normalized_theme = _normalize_theme(theme)
    normalized_role = _normalize_speaker_type(speaker_type)
    normalized_tone = _normalize_tone(tone)

    safe_name = html.escape(
        str(speaker_name or "").strip()
        or ("고양이" if normalized_role == "companion" else "인물")
    )
    safe_text = html.escape(
        str(text or "").strip() or "..."
    ).replace("\n", "<br>")

    portrait_uri = _data_uri(portrait_path)

    if portrait_uri:
        portrait_html = (
            '<div class="inline-dialogue-portrait">'
            f'<img src="{portrait_uri}" alt="{safe_name} portrait">'
            '</div>'
        )
    else:
        fallback = html.escape(_ROLE_FALLBACK[normalized_role])
        portrait_html = (
            '<div class="inline-dialogue-portrait">'
            f'<div class="inline-dialogue-fallback">{fallback}</div>'
            '</div>'
        )

    # Player의 이름 값은 유지하지만 화면에는 노출하지 않는다.
    speaker_html = (
        ""
        if normalized_role == "player"
        else f'<div class="inline-dialogue-speaker">{safe_name}</div>'
    )

    st.markdown(
        _css(normalized_theme)
        + (
            f'<section class="day6-inline-dialogue '
            f'{normalized_role} tone-{normalized_tone}">'
            f'{portrait_html}'
            '<div class="inline-dialogue-copy">'
            f'{speaker_html}'
            f'<div class="inline-dialogue-text">{safe_text}</div>'
            '</div>'
            '</section>'
        ),
        unsafe_allow_html=True,
    )

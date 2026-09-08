from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path

import streamlit as st

from components.generated_text_readability import generated_text_readability_css


# DAY6_DIALOGUE_SCENE_UI_V1
# STORY_SCENE_NAVIGATION_SPEAKER_INTEGRITY_V1_2_20260908
# DAY6_DIALOGUE_SCENE_UI_V1_1_POLISH
# DAY6_DIALOGUE_SCENE_UI_V1_1_1_PLAYER_TEXT_ALIGN
# DAY6_DIALOGUE_SCENE_UI_V1_1_2_HIDE_PLAYER_NAME
# DAY6_GENERATED_TEXT_READABILITY_V1_1
_SPEAKER_TYPES = {
    "companion",
    "player",
    "npc",
    "narrator",
}

_THEME_STYLE = {
    "동화": {
        "accent": "#df7191",
        "text": "#4d2834",
        "muted": "#8d6571",
        "stage_bg": (
            "radial-gradient(circle at 16% 18%, rgba(242,154,176,.24), transparent 28%),"
            "radial-gradient(circle at 84% 16%, rgba(126,213,194,.24), transparent 28%),"
            "linear-gradient(135deg,#fff4f7 0%,#fff9f4 54%,#eefaf6 100%)"
        ),
        "box_bg": "rgba(255,250,249,.94)",
        "box_border": "rgba(223,113,145,.28)",
        "portrait_bg": "linear-gradient(145deg,#fff7f9,#fff0f3)",
        "font": '"Pretendard","Noto Sans KR","Apple SD Gothic Neo",sans-serif',
        "speaker_font": '"Pretendard","Noto Sans KR","Apple SD Gothic Neo",sans-serif',
        "scene_label": "STORY SCENE",
        "next_label": "✨ 다음으로",
    },
    "미스터리": {
        "accent": "#8d2630",
        "text": "#292521",
        "muted": "#756d66",
        "stage_bg": (
            "radial-gradient(circle at 82% 15%, rgba(141,38,48,.13), transparent 30%),"
            "radial-gradient(circle at 14% 82%, rgba(78,70,62,.08), transparent 32%),"
            "linear-gradient(135deg,#f3f0e9 0%,#ece8e1 54%,#f1e7e5 100%)"
        ),
        "box_bg": "rgba(255,252,247,.95)",
        "box_border": "rgba(141,38,48,.25)",
        "portrait_bg": "linear-gradient(145deg,#f5efe8,#e8dfd6)",
        "font": '"나눔손글씨 펜","Nanum Pen Script","휴먼편지체","Segoe Print","Batang",serif',
        "speaker_font": '"Batang","Noto Serif KR",serif',
        "scene_label": "CASE DIALOGUE",
        "next_label": "🔎 다음 기록",
    },
    "무협": {
        "accent": "#9f3a32",
        "text": "#302820",
        "muted": "#77675a",
        "stage_bg": (
            "radial-gradient(circle at 82% 18%, rgba(159,58,50,.09), transparent 30%),"
            "linear-gradient(135deg,#efe6d5 0%,#e7dcc7 56%,#efe4d3 100%)"
        ),
        "box_bg": "rgba(250,242,223,.95)",
        "box_border": "rgba(112,86,61,.27)",
        "portrait_bg": "linear-gradient(145deg,#f3e6cb,#e7d4b6)",
        "font": '"궁서","Gungsuh","Batang","Noto Serif KR",serif',
        "speaker_font": '"궁서","Gungsuh","Batang","Noto Serif KR",serif',
        "scene_label": "同行",
        "next_label": "◎ 말을 잇는다",
    },
    "SF": {
        "accent": "#3ed6f4",
        "text": "#eafaff",
        "muted": "#9fc5d3",
        "stage_bg": (
            "linear-gradient(rgba(62,214,244,.055) 1px, transparent 1px),"
            "linear-gradient(90deg, rgba(62,214,244,.055) 1px, transparent 1px),"
            "radial-gradient(circle at 80% 16%, rgba(35,209,235,.16), transparent 32%),"
            "radial-gradient(circle at 14% 78%, rgba(80,86,214,.16), transparent 34%),"
            "linear-gradient(135deg,#04121e 0%,#071d2d 52%,#072d39 100%)"
        ),
        "box_bg": "rgba(5,31,46,.91)",
        "box_border": "rgba(62,214,244,.38)",
        "portrait_bg": "linear-gradient(145deg,rgba(10,54,71,.96),rgba(5,31,46,.96))",
        "font": '"Pretendard","Noto Sans KR","Apple SD Gothic Neo",sans-serif',
        "speaker_font": '"Cascadia Mono","D2Coding","Consolas",monospace',
        "scene_label": "COMMS CHANNEL",
        "next_label": "◉ 다음 신호",
    },
    "판타지": {
        "accent": "#caa55d",
        "text": "#f4ead5",
        "muted": "#d4c3a4",
        "stage_bg": (
            "radial-gradient(circle at 20% 18%, rgba(202,165,93,.15), transparent 30%),"
            "radial-gradient(circle at 82% 22%, rgba(103,74,153,.16), transparent 32%),"
            "linear-gradient(135deg,#171512 0%,#1a181b 52%,#261f30 100%)"
        ),
        "box_bg": "rgba(37,31,31,.93)",
        "box_border": "rgba(202,165,93,.34)",
        "portrait_bg": "linear-gradient(145deg,#322a24,#211c1a)",
        "font": '"Georgia","Palatino Linotype","Noto Serif KR",serif',
        "speaker_font": '"Georgia","Palatino Linotype","Noto Serif KR",serif',
        "scene_label": "COMPANION DIALOGUE",
        "next_label": "✦ 대화를 잇는다",
    },
}

_ROLE_FALLBACK = {
    "companion": "🐈",
    "player": "👤",
    "npc": "◆",
    "narrator": "",
}


def _normalize_theme(theme: str) -> str:
    if theme in _THEME_STYLE:
        return theme
    return "동화"


def _normalize_speaker_type(speaker_type: str) -> str:
    value = str(speaker_type or "").strip().lower()
    if value not in _SPEAKER_TYPES:
        return "npc"
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
    @keyframes dialogueSceneFadeIn {{
        from {{
            opacity:0;
        }}
        to {{
            opacity:1;
        }}
    }}

    @keyframes dialogueSceneKenBurns {{
        from {{
            transform:scale(1.00);
        }}
        to {{
            transform:scale(1.025);
        }}
    }}

    @keyframes dialoguePortraitEnter {{
        from {{
            opacity:0;
            transform:translateY(8px) scale(.985);
        }}
        to {{
            opacity:1;
            transform:translateY(0) scale(1);
        }}
    }}

    .dialogue-scene-stage {{
        --dlg-accent:{style["accent"]};
        --dlg-text:{style["text"]};
        --dlg-muted:{style["muted"]};
        --dlg-box:{style["box_bg"]};
        --dlg-border:{style["box_border"]};
        --dlg-portrait:{style["portrait_bg"]};
        --dlg-font:{style["font"]};
        --dlg-speaker-font:{style["speaker_font"]};

        position:relative;
        isolation:isolate;
        width:min(100%, 1120px);
        min-height:clamp(500px,65vh,690px);
        margin:.5rem auto 0;
        overflow:hidden;
        border-radius:24px;
        border:1px solid var(--dlg-border);
        background:{style["stage_bg"]};
        background-size:34px 34px,34px 34px,auto,auto,auto;
        box-shadow:0 28px 80px rgba(0,0,0,.14);
        animation:dialogueSceneFadeIn .42s ease-out both;
    }}

    .dialogue-scene-background {{
        position:absolute;
        z-index:0;
        inset:-1.5%;
        background-size:cover;
        background-position:center;
        background-repeat:no-repeat;
        transform-origin:center center;
        animation:dialogueSceneKenBurns 14s ease-out both;
        will-change:transform;
    }}

    .dialogue-scene-stage::before {{
        content:"";
        position:absolute;
        z-index:1;
        inset:0;
        pointer-events:none;
        background:
            linear-gradient(
                to bottom,
                rgba(10,8,6,.30) 0%,
                rgba(10,8,6,.10) 18%,
                rgba(10,8,6,0) 42%,
                rgba(10,8,6,.02) 56%,
                rgba(10,8,6,.18) 100%
            );
    }}

    .dialogue-scene-stage::after {{
        content:"";
        position:absolute;
        z-index:1;
        inset:auto 0 0 0;
        height:42%;
        pointer-events:none;
        background:
            linear-gradient(
                to top,
                rgba(0,0,0,.18) 0%,
                rgba(0,0,0,.07) 42%,
                transparent 100%
            );
    }}

    .dialogue-scene-kicker,
    .dialogue-scene-context {{
        position:absolute;
        z-index:4;
        top:clamp(.95rem,2.1vw,1.55rem);
        padding:.34rem .56rem;
        border:1px solid rgba(255,255,255,.12);
        border-radius:999px;
        background:rgba(16,14,12,.42);
        backdrop-filter:blur(7px);
        -webkit-backdrop-filter:blur(7px);
        box-shadow:0 6px 18px rgba(0,0,0,.14);
        text-shadow:0 1px 3px rgba(0,0,0,.65);
    }}

    .dialogue-scene-kicker {{
        left:clamp(1rem,2.4vw,2rem);
        color:#fff7ed;
        font-family:var(--dlg-speaker-font);
        font-size:.72rem;
        font-weight:800;
        letter-spacing:.16em;
        text-transform:uppercase;
    }}

    .dialogue-scene-kicker::before {{
        content:"";
        display:inline-block;
        width:.42rem;
        height:.42rem;
        margin-right:.42rem;
        border-radius:999px;
        background:var(--dlg-accent);
        box-shadow:0 0 12px color-mix(in srgb, var(--dlg-accent) 75%, transparent);
        vertical-align:.02rem;
    }}

    .dialogue-scene-context {{
        right:clamp(1rem,2.4vw,2rem);
        max-width:54%;
        color:#fffaf3;
        font-size:.72rem;
        line-height:1.4;
        text-align:right;
        opacity:.96;
    }}

    .dialogue-box {{
        position:absolute;
        z-index:5;
        left:clamp(.85rem,2.15vw,1.55rem);
        right:clamp(.85rem,2.15vw,1.55rem);
        bottom:clamp(.7rem,1.8vw,1.15rem);
        min-height:172px;
        box-sizing:border-box;
        display:grid;
        grid-template-columns:minmax(145px,21%) 1fr;
        gap:clamp(.85rem,2vw,1.55rem);
        align-items:stretch;
        padding:clamp(.9rem,2vw,1.3rem);
        border:1px solid var(--dlg-border);
        border-radius:19px;
        background:var(--dlg-box);
        backdrop-filter:blur(12px) saturate(1.02);
        -webkit-backdrop-filter:blur(12px) saturate(1.02);
        box-shadow:
            0 18px 46px rgba(0,0,0,.18),
            inset 0 1px 0 rgba(255,255,255,.06);
    }}

    .dialogue-box.dialogue-narrator {{
        grid-template-columns:1fr;
        min-height:148px;
    }}

    .dialogue-box.dialogue-player {{
        grid-template-columns:1fr minmax(145px,21%);
    }}

    .dialogue-box.dialogue-player .dialogue-copy {{
        order:1;
        text-align:left;
        align-items:flex-start;
    }}

    .dialogue-box.dialogue-player .dialogue-portrait {{
        order:2;
    }}

    .dialogue-portrait {{
        position:relative;
        min-height:148px;
        overflow:hidden;
        border-radius:15px;
        border:1px solid var(--dlg-border);
        background:var(--dlg-portrait);
        box-shadow:0 10px 26px rgba(0,0,0,.14);
        animation:dialoguePortraitEnter .46s cubic-bezier(.2,.8,.2,1) both;
    }}

    .dialogue-portrait img {{
        width:100%;
        height:100%;
        min-height:148px;
        max-height:195px;
        object-fit:cover;
        object-position:center 28%;
        display:block;
    }}

    .dialogue-portrait-fallback {{
        height:100%;
        min-height:148px;
        display:flex;
        align-items:center;
        justify-content:center;
        color:var(--dlg-text);
        font-size:clamp(3.2rem,6.7vw,5rem);
        background:var(--dlg-portrait);
        opacity:.96;
    }}

    .dialogue-copy {{
        min-width:0;
        display:flex;
        flex-direction:column;
        justify-content:center;
        padding:.08rem .15rem;
    }}

    .dialogue-speaker {{
        color:var(--dlg-accent);
        font-family:var(--dlg-speaker-font);
        font-size:clamp(.84rem,1.2vw,.98rem);
        font-weight:800;
        letter-spacing:.08em;
        margin-bottom:.55rem;
    }}

    .dialogue-text {{
        color:var(--dlg-text);
        font-family:var(--dlg-font);
        font-size:clamp(1.32rem,2vw,1.78rem);
        line-height:1.58;
        font-weight:500;
        word-break:keep-all;
        text-wrap:pretty;
    }}

    .dialogue-narrator .dialogue-text {{
        font-size:clamp(1.34rem,1.95vw,1.76rem);
        line-height:1.62;
    }}

    @media (max-width:768px) {{
        .dialogue-scene-stage {{
            min-height:610px;
            border-radius:18px;
        }}

        .dialogue-scene-context {{
            display:none;
        }}

        .dialogue-scene-kicker {{
            top:.82rem;
            left:.82rem;
            font-size:.68rem;
            padding:.3rem .48rem;
        }}

        .dialogue-box {{
            grid-template-columns:1fr;
            gap:.72rem;
            min-height:285px;
            padding:.92rem;
            border-radius:17px;
        }}

        .dialogue-portrait {{
            width:82px;
            min-height:82px;
            max-height:82px;
            border-radius:14px;
        }}

        .dialogue-portrait img,
        .dialogue-portrait-fallback {{
            min-height:82px;
            height:82px;
            max-height:82px;
        }}

        .dialogue-portrait-fallback {{
            font-size:2.55rem;
        }}

        .dialogue-copy {{
            justify-content:flex-start;
            padding:.08rem .08rem .2rem;
        }}

        .dialogue-speaker {{
            margin-bottom:.42rem;
            font-size:.80rem;
        }}

        .dialogue-text,
        .dialogue-narrator .dialogue-text {{
            font-size:clamp(1.16rem,5vw,1.42rem);
            line-height:1.56;
        }}

        .dialogue-box.dialogue-narrator {{
            min-height:210px;
        }}

        .dialogue-box.dialogue-player {{
            grid-template-columns:1fr;
        }}

        .dialogue-box.dialogue-player .dialogue-copy,
        .dialogue-box.dialogue-player .dialogue-portrait {{
            order:initial;
        }}

        .dialogue-box.dialogue-player .dialogue-copy {{
            text-align:left;
            align-items:flex-start;
        }}

        .dialogue-box.dialogue-player .dialogue-portrait {{
            margin-left:auto;
        }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        .dialogue-scene-stage,
        .dialogue-scene-background,
        .dialogue-portrait {{
            animation:none !important;
            transform:none !important;
        }}
    }}
    </style>
    """



def render_dialogue_scene(
    *,
    theme: str,
    speaker_type: str,
    speaker_name: str,
    text: str,
    portrait_path: str | Path | None = None,
    background_path: str | Path | None = None,
    context_label: str | None = None,
    key: str | None = None,
    next_label: str | None = None,
    show_next_button: bool = True,
    show_scene_chrome: bool = False,
) -> bool:
    """RPG-style Dialogue Scene presentation component."""

    normalized_theme = _normalize_theme(theme)
    normalized_role = _normalize_speaker_type(speaker_type)
    style = _THEME_STYLE[normalized_theme]

    safe_name = html.escape(str(speaker_name or "").strip() or "이름 없는 인물")
    safe_text = html.escape(str(text or "").strip() or "...")
    safe_context = html.escape(str(context_label or "").strip())

    portrait_uri = _data_uri(portrait_path)
    background_uri = _data_uri(background_path)

    background_html = (
        (
            '<div class="dialogue-scene-background" '
            f'style="background-image:url(&quot;{background_uri}&quot;);">'
            '</div>'
        )
        if background_uri
        else ""
    )

    narrator = normalized_role == "narrator"

    if narrator:
        portrait_html = ""
        speaker_html = ""
        box_class = "dialogue-box dialogue-narrator"
    else:
        if portrait_uri:
            portrait_html = (
                '<div class="dialogue-portrait">'
                f'<img src="{portrait_uri}" alt="{safe_name} portrait">'
                '</div>'
            )
        else:
            fallback = html.escape(_ROLE_FALLBACK[normalized_role])
            portrait_html = (
                '<div class="dialogue-portrait">'
                f'<div class="dialogue-portrait-fallback">{fallback}</div>'
                '</div>'
            )

        speaker_html = (
            ""
            if normalized_role == "player"
            else f'<div class="dialogue-speaker">{safe_name}</div>'
        )
        box_class = (
            "dialogue-box dialogue-player"
            if normalized_role == "player"
            else "dialogue-box"
        )

    context_html = (
        f'<div class="dialogue-scene-context">{safe_context}</div>'
        if (show_scene_chrome and safe_context)
        else ""
    )

    if normalized_role == "narrator":
        scene_kicker = "STORY SCENE"
    elif normalized_role == "companion":
        scene_kicker = style["scene_label"]
    elif normalized_role == "player":
        scene_kicker = "PLAYER CHOICE"
    else:
        scene_kicker = "CHARACTER DIALOGUE"

    kicker_html = (
        f'<div class="dialogue-scene-kicker">{html.escape(scene_kicker)}</div>'
        if show_scene_chrome
        else ""
    )

    st.markdown(
        generated_text_readability_css()
        + _css(normalized_theme)
        + (
            '<section class="dialogue-scene-stage">'
            f'{background_html}'
            f'{kicker_html}'
            f'{context_html}'
            f'<div class="{box_class}">'
            f'{portrait_html}'
            '<div class="dialogue-copy">'
            f'{speaker_html}'
            f'<div class="dialogue-text">{safe_text}</div>'
            '</div>'
            '</div>'
            '</section>'
        ),
        unsafe_allow_html=True,
    )

    if not show_next_button:
        return False

    button_key = key or (
        "dialogue_scene_"
        + normalized_theme
        + "_"
        + normalized_role
        + "_next"
    )

    return bool(
        st.button(
            next_label or style["next_label"],
            key=button_key,
            use_container_width=True,
        )
    )

# CINEMATIC_STORY_SCENE_V2_20260906

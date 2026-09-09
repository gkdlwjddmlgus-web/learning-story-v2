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
# V3_STORY_AGENCY_STAGE_V1_20260908
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
        from {{ opacity:0; transform:translateY(5px); }}
        to {{ opacity:1; transform:translateY(0); }}
    }}

    @keyframes dialogueSceneKenBurns {{
        from {{ transform:scale(1.00); }}
        to {{ transform:scale(1.022); }}
    }}

    @keyframes dialoguePortraitEnter {{
        /*
        V3_STORY_VISUAL_CONTRACT_FIX_V3_1_20260908
        Opacity is deliberately NOT animated here.
        animation-fill-mode both previously kept the portrait at full opacity,
        overriding the narrator dim state after the enter animation finished.
        */
        from {{ transform:translateY(14px) scale(.98); }}
        to {{ transform:translateY(0) scale(1); }}
    }}

    .dialogue-scene-stage {{
        --dlg-accent:{style["accent"]};
        --dlg-font:{style["font"]};
        --dlg-speaker-font:{style["speaker_font"]};

        position:relative;
        isolation:isolate;
        width:min(100%, 1360px);
        height:clamp(500px,67dvh,700px);
        margin:.2rem auto 0;
        overflow:hidden;
        border-radius:22px;
        border:1px solid rgba(255,255,255,.14);
        background:{style["stage_bg"]};
        box-shadow:0 28px 80px rgba(0,0,0,.18);
        animation:dialogueSceneFadeIn .34s ease-out both;
    }}

    .dialogue-scene-background {{
        position:absolute;
        z-index:0;
        inset:-1.5%;
        background-size:cover;
        background-position:center;
        background-repeat:no-repeat;
        transform-origin:center;
        animation:dialogueSceneKenBurns 14s ease-out both;
    }}

    .dialogue-scene-stage::before {{
        content:"";
        position:absolute;
        z-index:1;
        inset:0;
        pointer-events:none;
        background:linear-gradient(to bottom,rgba(4,9,16,.34),rgba(4,9,16,.06) 45%,rgba(4,9,16,.42));
    }}

    .dialogue-scene-stage::after {{
        content:"";
        position:absolute;
        z-index:2;
        inset:auto 0 0;
        height:42%;
        pointer-events:none;
        background:linear-gradient(to top,rgba(3,8,15,.72),rgba(3,8,15,.16) 60%,transparent);
    }}

    .dialogue-scene-kicker,
    .dialogue-scene-context {{
        position:absolute;
        z-index:7;
        top:.9rem;
        padding:.3rem .56rem;
        border:1px solid rgba(255,255,255,.15);
        border-radius:999px;
        background:rgba(8,16,27,.58);
        color:#f7f7f4;
        backdrop-filter:blur(9px);
        -webkit-backdrop-filter:blur(9px);
        box-shadow:0 8px 22px rgba(0,0,0,.18);
        text-shadow:0 1px 3px rgba(0,0,0,.7);
    }}

    .dialogue-scene-kicker {{ left:.9rem; font-family:var(--dlg-speaker-font); font-size:.66rem; font-weight:850; letter-spacing:.13em; }}
    .dialogue-scene-context {{ right:.9rem; max-width:58%; font-size:.66rem; line-height:1.35; text-align:right; }}

    .dialogue-scene-character {{
        position:absolute;
        z-index:5;
        left:clamp(1.2rem,5vw,5.5rem);
        bottom:108px;
        width:clamp(140px,18vw,250px);
        height:clamp(185px,30vh,320px);
        display:flex;
        align-items:flex-end;
        justify-content:center;
        pointer-events:none;
        filter:drop-shadow(0 16px 24px rgba(0,0,0,.38));
        animation:dialoguePortraitEnter .38s cubic-bezier(.2,.8,.2,1) both;
        opacity:1;
        transition:opacity .22s ease, filter .22s ease;
    }}

    .dialogue-scene-character.companion.is-dim {{
        /*
        Dim the visual child instead of the animated positioning layer.
        This survives both CSS animation fill modes and Streamlit rerenders.
        */
        opacity:1;
        filter:drop-shadow(0 10px 18px rgba(0,0,0,.22));
    }}

    .dialogue-scene-character.companion.is-dim > img,
    .dialogue-scene-character.companion.is-dim
    > .dialogue-scene-character-fallback {{
        opacity:.26 !important;
        filter:saturate(.58) brightness(.72) !important;
    }}

    .dialogue-scene-character.companion.is-active {{
        opacity:1;
    }}

    .dialogue-scene-character.companion.is-active > img,
    .dialogue-scene-character.companion.is-active
    > .dialogue-scene-character-fallback {{
        opacity:1 !important;
        filter:none !important;
    }}

    .dialogue-scene-character.player {{
        left:auto;
        right:clamp(1.2rem,5vw,5.5rem);
        opacity:1;
    }}

    .dialogue-scene-character.npc {{
        left:auto;
        right:clamp(1.2rem,5vw,5.5rem);
        opacity:1;
    }}

    .dialogue-scene-character img {{
        width:100%;
        height:100%;
        object-fit:contain;
        object-position:center bottom;
        display:block;
        opacity:1;
        transition:opacity .22s ease,filter .22s ease;
    }}
    .dialogue-scene-character-fallback {{
        width:140px;
        height:140px;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius:999px;
        border:1px solid rgba(255,255,255,.18);
        background:rgba(8,16,27,.58);
        color:white;
        font-size:3.7rem;
        backdrop-filter:blur(9px);
        opacity:1;
        transition:opacity .22s ease,filter .22s ease;
    }}

    .dialogue-box {{
        position:absolute;
        z-index:6;
        left:clamp(.8rem,2.2vw,1.8rem);
        right:clamp(.8rem,2.2vw,1.8rem);
        bottom:clamp(.55rem,1.2vw,.9rem);
        min-height:100px;
        box-sizing:border-box;
        display:flex;
        flex-direction:column;
        justify-content:center;
        gap:.24rem;
        padding:.72rem 1rem .76rem;
        border:1px solid rgba(255,255,255,.20);
        border-radius:18px;
        background:linear-gradient(135deg,rgba(247,248,250,.96),rgba(236,239,245,.95));
        box-shadow:0 18px 46px rgba(0,0,0,.26),inset 0 1px 0 rgba(255,255,255,.75);
    }}

    .dialogue-speaker {{ align-self:flex-start; margin-top:-1.55rem; margin-bottom:.04rem; padding:.32rem .82rem; border-radius:10px 10px 5px 5px; background:#d7e9ff; color:#24558a; font-family:var(--dlg-speaker-font); font-size:.78rem; line-height:1.2; font-weight:900; box-shadow:0 6px 14px rgba(0,0,0,.10); }}
    .dialogue-copy {{ min-width:0; display:flex; flex-direction:column; justify-content:center; padding:0; }}
    .dialogue-text {{ color:#204b82; font-family:var(--dlg-font); font-size:clamp(.98rem,1.35vw,1.24rem); line-height:1.5; font-weight:650; word-break:keep-all; text-wrap:pretty; }}
    .dialogue-narrator .dialogue-text {{ color:#26394d; font-size:clamp(.94rem,1.28vw,1.16rem); }}

    @media (max-width:768px) {{
        .dialogue-scene-stage {{ height:590px; border-radius:16px; }}
        .dialogue-scene-context {{ display:none; }}
        .dialogue-scene-character.companion {{ left:24%; right:auto; transform:translateX(-50%); bottom:140px; width:138px; height:195px; }}
        .dialogue-scene-character.player,
        .dialogue-scene-character.npc {{ left:76%; right:auto; transform:translateX(-50%); bottom:140px; width:138px; height:195px; }}
        .dialogue-box {{ min-height:124px; padding:.76rem .86rem .82rem; }}
        .dialogue-text, .dialogue-narrator .dialogue-text {{ font-size:.98rem; line-height:1.46; }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        .dialogue-scene-stage, .dialogue-scene-background, .dialogue-scene-character {{ animation:none !important; transform:none !important; }}
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
    companion_portrait_path: str | Path | None = None,
    player_portrait_path: str | Path | None = None,
    background_path: str | Path | None = None,
    context_label: str | None = None,
    key: str | None = None,
    next_label: str | None = None,
    show_next_button: bool = True,
    show_scene_chrome: bool = False,
) -> bool:
    """Visual-novel style V3 Dialogue Scene presentation component."""
    normalized_theme = _normalize_theme(theme)
    normalized_role = _normalize_speaker_type(speaker_type)
    style = _THEME_STYLE[normalized_theme]

    safe_name = html.escape(str(speaker_name or "").strip() or "이름 없는 인물")
    safe_text = html.escape(str(text or "").strip() or "...")
    safe_context = html.escape(str(context_label or "").strip())

    portrait_uri = _data_uri(portrait_path)
    companion_uri = _data_uri(companion_portrait_path)
    player_uri = _data_uri(player_portrait_path)
    background_uri = _data_uri(background_path)

    background_html = (
        '<div class="dialogue-scene-background" ' + f'style="background-image:url(&quot;{background_uri}&quot;);"></div>'
        if background_uri
        else ""
    )

    narrator = normalized_role == "narrator"

    # V3_STORY_AGENCY_STAGE_V1_20260908
    # Companion occupies one fixed left slot. Narration only dims the same
    # companion sprite; Companion speech restores full opacity. Player is
    # rendered in the fixed right slot only when an explicit user-selected
    # dialogue choice is being replayed by the caller.
    companion_html = ""
    companion_source = (
        portrait_uri
        if normalized_role == "companion" and portrait_uri
        else companion_uri
    )
    if companion_source:
        companion_state = (
            "is-active"
            if normalized_role == "companion"
            else "is-dim"
        )
        companion_html = (
            f'<div class="dialogue-scene-character companion {companion_state}">'
            f'<img src="{companion_source}" alt="companion character">'
            '</div>'
        )
    elif normalized_role in {"companion", "narrator", "player"}:
        companion_state = (
            "is-active"
            if normalized_role == "companion"
            else "is-dim"
        )
        companion_html = (
            f'<div class="dialogue-scene-character companion {companion_state}">'
            '<div class="dialogue-scene-character-fallback">🐈</div>'
            '</div>'
        )

    active_character_html = ""
    if normalized_role == "player":
        active_player_uri = player_uri or portrait_uri
        if active_player_uri:
            active_character_html = (
                '<div class="dialogue-scene-character player">'
                f'<img src="{active_player_uri}" alt="{safe_name} character">'
                '</div>'
            )
        else:
            active_character_html = (
                '<div class="dialogue-scene-character player">'
                '<div class="dialogue-scene-character-fallback">👤</div>'
                '</div>'
            )
    elif normalized_role == "npc":
        if portrait_uri:
            active_character_html = (
                '<div class="dialogue-scene-character npc">'
                f'<img src="{portrait_uri}" alt="{safe_name} character">'
                '</div>'
            )
        else:
            active_character_html = (
                '<div class="dialogue-scene-character npc">'
                '<div class="dialogue-scene-character-fallback">◆</div>'
                '</div>'
            )

    character_html = companion_html + active_character_html

    speaker_html = (
        ""
        if narrator or normalized_role == "player"
        else f'<div class="dialogue-speaker">{safe_name}</div>'
    )
    context_html = (
        f'<div class="dialogue-scene-context">{safe_context}</div>'
        if show_scene_chrome and safe_context
        else ""
    )
    scene_kicker = (
        "STORY SCENE"
        if narrator
        else style["scene_label"]
        if normalized_role == "companion"
        else "PLAYER CHOICE"
        if normalized_role == "player"
        else "CHARACTER DIALOGUE"
    )
    kicker_html = (
        f'<div class="dialogue-scene-kicker">{html.escape(scene_kicker)}</div>'
        if show_scene_chrome
        else ""
    )
    box_class = (
        "dialogue-box dialogue-narrator"
        if narrator
        else "dialogue-box dialogue-player"
        if normalized_role == "player"
        else "dialogue-box"
    )

    st.markdown(
        generated_text_readability_css()
        + _css(normalized_theme)
        + (
            '<section class="dialogue-scene-stage">'
            f'{background_html}{kicker_html}{context_html}{character_html}'
            f'<div class="{box_class}"><div class="dialogue-copy">'
            f'{speaker_html}<div class="dialogue-text">{safe_text}</div>'
            '</div></div></section>'
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

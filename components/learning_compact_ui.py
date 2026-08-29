from __future__ import annotations

import html

import streamlit as st


# DAY5_COMPACT_LEARNING_UI_V1
_THEME_STYLE = {
    "미스터리": {
        "accent": "#8d2630",
        "track": "rgba(141,38,48,.12)",
        "surface": "rgba(255,255,255,.34)",
        "border": "rgba(141,38,48,.18)",
        "text": "#232321",
        "muted": "#696c67",
    },
    "SF": {
        "accent": "#3ed6f4",
        "track": "rgba(62,214,244,.14)",
        "surface": "rgba(11,36,53,.56)",
        "border": "rgba(62,214,244,.20)",
        "text": "#e9faff",
        "muted": "#9fc5d3",
    },
    "판타지": {
        "accent": "#caa55d",
        "track": "rgba(202,165,93,.14)",
        "surface": "rgba(36,33,30,.52)",
        "border": "rgba(202,165,93,.20)",
        "text": "#f4ead5",
        "muted": "#d6c5a5",
    },
    "무협": {
        "accent": "#9f3a32",
        "track": "rgba(159,58,50,.12)",
        "surface": "rgba(246,239,223,.55)",
        "border": "rgba(159,58,50,.18)",
        "text": "#2b2520",
        "muted": "#6f6257",
    },
    "동화": {
        "accent": "#d76a89",
        "track": "rgba(215,106,137,.12)",
        "surface": "rgba(255,250,248,.62)",
        "border": "rgba(215,106,137,.18)",
        "text": "#4d2834",
        "muted": "#7e5a66",
    },
}


def _inject_css(theme: str) -> None:
    style = _THEME_STYLE.get(theme, _THEME_STYLE["동화"])
    st.markdown(
        f"""
        <style>
        .stApp {{
            --learn-accent:{style['accent']};
            --learn-track:{style['track']};
            --learn-surface:{style['surface']};
            --learn-border:{style['border']};
            --learn-text:{style['text']};
            --learn-muted:{style['muted']};
        }}

        .learning-app-compact-head {{
            display:flex;
            align-items:baseline;
            justify-content:space-between;
            gap:1rem;
            margin:.1rem 0 .3rem;
            padding:.05rem 0 .28rem;
        }}
        .learning-app-compact-title {{
            color:var(--learn-text);
            font-size:1.18rem;
            line-height:1.15;
            font-weight:850;
            letter-spacing:-.02em;
        }}
        .learning-app-compact-identity {{
            color:var(--learn-muted);
            font-size:.78rem;
            line-height:1.35;
            text-align:right;
        }}

        .compact-chapter-shell {{
            margin:.28rem 0 .5rem;
            padding:.72rem .9rem .66rem;
            border:1px solid var(--learn-border);
            border-radius:14px;
            background:var(--learn-surface);
        }}
        .compact-chapter-topline {{
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:.7rem;
            margin-bottom:.18rem;
        }}
        .compact-chapter-kicker {{
            color:var(--learn-accent);
            font-size:.72rem;
            line-height:1.2;
            font-weight:850;
            letter-spacing:.12em;
            white-space:nowrap;
        }}
        .compact-chapter-progress-label {{
            color:var(--learn-muted);
            font-size:.72rem;
            line-height:1.2;
            white-space:nowrap;
        }}
        .compact-chapter-title {{
            color:var(--learn-text);
            font-size:1.26rem;
            line-height:1.35;
            font-weight:850;
            letter-spacing:-.02em;
            margin:.08rem 0 .16rem;
        }}
        .compact-chapter-meta {{
            color:var(--learn-muted);
            font-size:.78rem;
            line-height:1.4;
            margin-bottom:.5rem;
        }}
        .compact-chapter-progress {{
            width:100%;
            height:5px;
            border-radius:999px;
            background:var(--learn-track);
            overflow:hidden;
        }}
        .compact-chapter-progress > span {{
            display:block;
            height:100%;
            border-radius:999px;
            background:var(--learn-accent);
        }}

        .compact-learning-tools-marker {{display:none;}}

        /* DAY5_COMPACT_TOOL_ROW_ALIGN_V1:
           왼쪽 컬럼의 marker용 st.markdown wrapper가 레이아웃 높이를 차지하면서
           Story Review만 아래로 밀리던 현상을 제거한다.
           marker 자체는 HorizontalBlock 탐색용으로 DOM에 유지하되,
           그것을 감싼 Streamlit element container는 레이아웃에서 제외한다. */
        div[data-testid="stElementContainer"]:has(.compact-learning-tools-marker) {{
            display:none !important;
            height:0 !important;
            min-height:0 !important;
            margin:0 !important;
            padding:0 !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.compact-learning-tools-marker) {{
            gap:.55rem !important;
            margin:.12rem 0 .32rem !important;
            align-items:flex-start !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.compact-learning-tools-marker) details {{
            margin:0 !important;
        }}

        @media (max-width: 720px) {{
            .learning-app-compact-head {{
                align-items:flex-start;
                gap:.45rem;
            }}
            .learning-app-compact-title {{font-size:1.02rem;}}
            .learning-app-compact-identity {{font-size:.68rem; max-width:56%;}}
            .compact-chapter-shell {{padding:.62rem .7rem .58rem;}}
            .compact-chapter-title {{font-size:1.06rem;}}
            .compact-chapter-meta {{font-size:.71rem;}}
            .compact-chapter-kicker,
            .compact-chapter-progress-label {{font-size:.66rem;}}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_compact_app_header(
    *,
    theme: str,
    user_name: str,
    identity: str,
) -> None:
    _inject_css(theme)
    st.markdown(
        '<div class="learning-app-compact-head">'
        '<div class="learning-app-compact-title">Learning Story</div>'
        f'<div class="learning-app-compact-identity">{html.escape(user_name)} · {html.escape(identity)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_compact_chapter_header(
    *,
    theme: str,
    chapter_number: int,
    block_number: int,
    title: str,
    meta: str,
    progress_current: int | None,
    progress_total: int | None,
) -> None:
    _inject_css(theme)

    progress_label = ""
    progress_html = ""
    if progress_current and progress_total:
        ratio = max(0.0, min(1.0, progress_current / float(progress_total)))
        progress_label = f"{progress_current} / {progress_total}"
        progress_html = (
            '<div class="compact-chapter-progress">'
            f'<span style="width:{ratio * 100:.1f}%"></span>'
            '</div>'
        )

    st.markdown(
        '<section class="compact-chapter-shell">'
        '<div class="compact-chapter-topline">'
        f'<div class="compact-chapter-kicker">CHAPTER {chapter_number} · BLOCK {block_number}</div>'
        f'<div class="compact-chapter-progress-label">{html.escape(progress_label)}</div>'
        '</div>'
        f'<div class="compact-chapter-title">{html.escape(title)}</div>'
        f'<div class="compact-chapter-meta">{html.escape(meta)}</div>'
        f'{progress_html}'
        '</section>',
        unsafe_allow_html=True,
    )

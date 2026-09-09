from __future__ import annotations

import html

import streamlit as st


# DAY5_COMPACT_LEARNING_UI_V1
# V3_FULL_EXPECTED_PLAY_UI_V1_20260908
_THEME_STYLE = {
    "미스터리": {
        "accent": "#9a323b",
        "track": "rgba(154,50,59,.16)",
        "surface": "rgba(255,255,255,.76)",
        "border": "rgba(154,50,59,.24)",
        "text": "#232321",
        "muted": "#6c6b67",
    },
    "SF": {
        "accent": "#45d7ee",
        "track": "rgba(69,215,238,.16)",
        "surface": "rgba(8,29,43,.86)",
        "border": "rgba(69,215,238,.24)",
        "text": "#eefcff",
        "muted": "#a5c7d1",
    },
    "판타지": {
        "accent": "#d8b66c",
        "track": "rgba(216,182,108,.18)",
        "surface": "rgba(24,30,42,.86)",
        "border": "rgba(216,182,108,.24)",
        "text": "#f8edd6",
        "muted": "#d6c6a7",
    },
    "무협": {
        "accent": "#a14339",
        "track": "rgba(161,67,57,.15)",
        "surface": "rgba(249,242,226,.86)",
        "border": "rgba(161,67,57,.23)",
        "text": "#2d2924",
        "muted": "#706459",
    },
    "동화": {
        "accent": "#df7695",
        "track": "rgba(223,118,149,.15)",
        "surface": "rgba(255,250,248,.88)",
        "border": "rgba(223,118,149,.22)",
        "text": "#4d2834",
        "muted": "#7e5a66",
    },
}


def _inject_css(theme: str) -> None:
    style = _THEME_STYLE.get(
        theme,
        _THEME_STYLE["동화"],
    )

    st.markdown(
        f"""
        <style>
        .stApp {{
            --learn-accent:{style['accent']};
            --learn-track:{style['track']};
            --learn-border:{style['border']};
            --learn-text:#f4f7fb;
            --learn-muted:#b7c2cf;
            --learn-panel:rgba(9,24,39,.92);
            --learn-panel-alt:rgba(14,35,54,.90);
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
            font-size:1.05rem;
            line-height:1.15;
            font-weight:850;
            letter-spacing:-.02em;
        }}

        .learning-app-compact-identity {{
            color:var(--learn-muted);
            font-size:.72rem;
            line-height:1.35;
            text-align:right;
        }}

        .compact-chapter-shell {{
            display:grid;
            grid-template-columns:auto minmax(0,1fr) minmax(230px,.32fr);
            align-items:center;
            gap:.82rem;
            margin:0;
            padding:.56rem .72rem;
            border:1px solid color-mix(in srgb,var(--learn-accent) 32%,transparent);
            border-radius:15px;
            background:
                linear-gradient(135deg,var(--learn-panel),var(--learn-panel-alt));
            box-shadow:0 14px 38px rgba(0,0,0,.24);
            backdrop-filter:blur(14px) saturate(120%);
            -webkit-backdrop-filter:blur(14px) saturate(120%);
        }}

        .compact-chapter-book {{
            display:flex;
            align-items:center;
            justify-content:center;
            width:42px;
            height:42px;
            border-radius:11px;
            border:1px solid color-mix(in srgb,var(--learn-accent) 38%,transparent);
            background:color-mix(in srgb,var(--learn-accent) 16%,rgba(8,18,30,.8));
            color:var(--learn-accent);
            font-size:1.45rem;
        }}

        .compact-chapter-main {{ min-width:0; }}

        .compact-chapter-kicker {{
            color:var(--learn-accent);
            font-size:.62rem;
            line-height:1.15;
            font-weight:900;
            letter-spacing:.13em;
            margin-bottom:.1rem;
        }}

        .compact-chapter-title {{
            color:var(--learn-text);
            font-size:1.08rem;
            line-height:1.24;
            font-weight:900;
            letter-spacing:-.025em;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }}

        .compact-chapter-meta {{
            color:var(--learn-muted);
            font-size:.68rem;
            line-height:1.3;
            margin-top:.1rem;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }}

        .compact-chapter-side {{ min-width:0; }}

        .compact-chapter-progress-top {{
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:.5rem;
            margin-bottom:.26rem;
            color:var(--learn-muted);
            font-size:.65rem;
            font-weight:800;
        }}

        .compact-chapter-progress {{
            width:100%;
            height:5px;
            border-radius:999px;
            background:rgba(255,255,255,.10);
            overflow:hidden;
        }}

        .compact-chapter-progress > span {{
            display:block;
            height:100%;
            border-radius:inherit;
            background:linear-gradient(90deg,var(--learn-accent),color-mix(in srgb,var(--learn-accent) 65%,white));
            box-shadow:0 0 14px color-mix(in srgb,var(--learn-accent) 45%,transparent);
        }}

        .compact-chapter-pills {{
            display:flex;
            gap:.22rem;
            flex-wrap:wrap;
            justify-content:flex-end;
            margin-top:.3rem;
        }}

        .compact-chapter-pill {{
            padding:.12rem .38rem;
            border:1px solid rgba(255,255,255,.12);
            border-radius:999px;
            color:#d8e2ec;
            font-size:.57rem;
            line-height:1.2;
            background:rgba(255,255,255,.055);
            white-space:nowrap;
        }}

        .compact-learning-tools-marker {{ display:none; }}
        div[data-testid="stElementContainer"]:has(.compact-learning-tools-marker) {{
            display:none !important;
            height:0 !important;
            min-height:0 !important;
            margin:0 !important;
            padding:0 !important;
        }}

        @media (max-width:900px) {{
            .compact-chapter-shell {{ grid-template-columns:auto minmax(0,1fr); }}
            .compact-chapter-side {{ grid-column:1 / -1; padding-left:3.35rem; }}
            .compact-chapter-pills {{ justify-content:flex-start; }}
        }}

        @media (max-width:640px) {{
            .compact-chapter-shell {{ padding:.5rem .58rem; gap:.58rem; }}
            .compact-chapter-book {{ width:36px; height:36px; font-size:1.18rem; }}
            .compact-chapter-title {{ font-size:.95rem; }}
            .compact-chapter-meta {{ font-size:.62rem; }}
            .compact-chapter-side {{ padding-left:2.75rem; }}
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
        f'<div class="learning-app-compact-identity">'
        f'{html.escape(user_name)} · {html.escape(identity)}'
        '</div>'
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
    guide_name: str | None = None,
    learner_level: str | None = None,
    topic: str | None = None,
) -> None:
    _inject_css(theme)

    progress_label = ""
    progress_html = ""

    if progress_current and progress_total:
        ratio = max(
            0.0,
            min(
                1.0,
                progress_current
                / float(progress_total),
            ),
        )
        progress_label = (
            f"{progress_current} / {progress_total}"
        )
        progress_html = (
            '<div class="compact-chapter-progress">'
            f'<span style="width:{ratio * 100:.1f}%"></span>'
            '</div>'
        )

    pills = []
    for label, value in (
        ("테마", theme),
        ("동료", guide_name),
        ("학습", topic),
        ("수준", learner_level),
    ):
        clean = str(value or "").strip()
        if clean:
            pills.append(
                '<span class="compact-chapter-pill">'
                f'{html.escape(label)} · {html.escape(clean)}'
                '</span>'
            )

    st.markdown(
        '<section class="compact-chapter-shell">'
        '<div class="compact-chapter-book">📖</div>'
        '<div class="compact-chapter-main">'
        f'<div class="compact-chapter-kicker">CHAPTER {chapter_number} · BLOCK {block_number}</div>'
        f'<div class="compact-chapter-title">{html.escape(title)}</div>'
        f'<div class="compact-chapter-meta">{html.escape(meta)}</div>'
        '</div>'
        '<div class="compact-chapter-side">'
        '<div class="compact-chapter-progress-top">'
        '<span>진행도</span>'
        f'<span>{html.escape(progress_label)}</span>'
        '</div>'
        f'{progress_html}'
        '<div class="compact-chapter-pills">'
        f'{"".join(pills)}'
        '</div>'
        '</div>'
        '</section>',
        unsafe_allow_html=True,
    )

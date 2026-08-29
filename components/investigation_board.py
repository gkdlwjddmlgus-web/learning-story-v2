from __future__ import annotations

import html

import streamlit as st


# DAY5_INVESTIGATION_BOARD_V5_MOBILE_ACTION_ROW
# DAY5_INVESTIGATION_BOARD_V4_MOBILE_RESPONSIVE
# DAY5_INVESTIGATION_BOARD_V3_COMPACT_NAV
ACTION_CLUE = "clue"
ACTION_COMPANION = "companion"
ACTION_DEDUCE = "deduce"

_ACTION_ORDER = (
    ACTION_CLUE,
    ACTION_COMPANION,
    ACTION_DEDUCE,
)

_THEME_ACTIONS = {
    "미스터리": {
        ACTION_CLUE: ("🔎", "단서 조사", "단서 조사하기"),
        ACTION_COMPANION: ("🐈", "{guide_name}와 대화", "{guide_name}와 대화하기"),
        ACTION_DEDUCE: ("🧠", "추리하기", "추리 시작하기"),
    },
    "SF": {
        ACTION_CLUE: ("◉", "시스템 조사", "시스템 조사하기"),
        ACTION_COMPANION: ("🐈", "{guide_name}와 통신", "{guide_name}와 통신하기"),
        ACTION_DEDUCE: ("◇", "분석하기", "분석 시작하기"),
    },
    "판타지": {
        ACTION_CLUE: ("✦", "흔적 탐색", "흔적 탐색하기"),
        ACTION_COMPANION: ("🐈", "{guide_name}와 대화", "{guide_name}와 대화하기"),
        ACTION_DEDUCE: ("◈", "판단하기", "판단 시작하기"),
    },
    "무협": {
        ACTION_CLUE: ("🔎", "탐문하기", "탐문 시작하기"),
        ACTION_COMPANION: ("🐈", "{guide_name}와 대화", "{guide_name}와 대화하기"),
        ACTION_DEDUCE: ("◎", "판단하기", "판단 시작하기"),
    },
    "동화": {
        ACTION_CLUE: ("🔎", "주변 살펴보기", "주변 살펴보기"),
        ACTION_COMPANION: ("🐈", "{guide_name}와 이야기", "{guide_name}와 이야기하기"),
        ACTION_DEDUCE: ("✨", "답 찾아보기", "답 찾아보기"),
    },
}

_THEME_COMPACT_LABELS = {
    "미스터리": {
        ACTION_CLUE: "단서",
        ACTION_COMPANION: "{guide_name}",
        ACTION_DEDUCE: "추리",
    },
    "SF": {
        ACTION_CLUE: "조사",
        ACTION_COMPANION: "{guide_name}",
        ACTION_DEDUCE: "분석",
    },
    "판타지": {
        ACTION_CLUE: "탐색",
        ACTION_COMPANION: "{guide_name}",
        ACTION_DEDUCE: "판단",
    },
    "무협": {
        ACTION_CLUE: "탐문",
        ACTION_COMPANION: "{guide_name}",
        ACTION_DEDUCE: "판단",
    },
    "동화": {
        ACTION_CLUE: "탐색",
        ACTION_COMPANION: "{guide_name}",
        ACTION_DEDUCE: "답 찾기",
    },
}

_ACTION_DESCRIPTIONS = {
    ACTION_CLUE: "문제 해결에 필요한 기록과 증거를 확인합니다.",
    ACTION_COMPANION: "핵심 개념과 용어 도움을 동료와 함께 확인합니다.",
    ACTION_DEDUCE: "지금까지 확인한 내용을 바탕으로 결론을 내립니다.",
}

_THEME_STYLE = {
    "미스터리": {
        "accent": "#8d2630",
        "cta": "#8d2630",
        "cta_text": "#fffaf7",
        "surface": "#f7f4ef",
        "surface_alt": "#eee9e1",
        "text": "#232321",
        "muted": "#66645f",
        "border": "rgba(141,38,48,.34)",
    },
    "SF": {
        "accent": "#3ed6f4",
        "cta": "#0d7c8f",
        "cta_text": "#eaffff",
        "surface": "#0b2435",
        "surface_alt": "#12394e",
        "text": "#e9faff",
        "muted": "#9fc5d3",
        "border": "rgba(62,214,244,.42)",
    },
    "판타지": {
        "accent": "#caa55d",
        "cta": "#88652e",
        "cta_text": "#fff3d4",
        "surface": "#24211e",
        "surface_alt": "#3a3126",
        "text": "#f4ead5",
        "muted": "#d6c5a5",
        "border": "rgba(202,165,93,.42)",
    },
    "무협": {
        "accent": "#9f3a32",
        "cta": "#9f3a32",
        "cta_text": "#fffaf4",
        "surface": "#f6efdf",
        "surface_alt": "#eadfc8",
        "text": "#2b2520",
        "muted": "#6f6257",
        "border": "rgba(159,58,50,.32)",
    },
    "동화": {
        "accent": "#d76a89",
        "cta": "#f29ab0",
        "cta_text": "#4d2834",
        "surface": "#fffaf8",
        "surface_alt": "#f9e8ec",
        "text": "#4d2834",
        "muted": "#7e5a66",
        "border": "rgba(215,106,137,.34)",
    },
}


def get_investigation_selected_key(
    chapter_id: int,
    question_index: int,
) -> str:
    return f"investigation_selected_action_{chapter_id}_{question_index}"


def get_investigation_active_key(
    chapter_id: int,
    question_index: int,
) -> str:
    return f"investigation_active_action_{chapter_id}_{question_index}"


def get_investigation_visited_key(
    chapter_id: int,
    question_index: int,
) -> str:
    return f"investigation_visited_actions_{chapter_id}_{question_index}"


def _legacy_action_key(
    chapter_id: int,
    question_index: int,
) -> str:
    return f"investigation_action_{chapter_id}_{question_index}"


def clear_investigation_question_state(
    chapter_id: int,
    question_index: int,
) -> None:
    for key in (
        get_investigation_selected_key(chapter_id, question_index),
        get_investigation_active_key(chapter_id, question_index),
        get_investigation_visited_key(chapter_id, question_index),
        _legacy_action_key(chapter_id, question_index),
    ):
        st.session_state.pop(key, None)


def clear_investigation_state() -> None:
    prefixes = (
        "investigation_selected_action_",
        "investigation_active_action_",
        "investigation_visited_actions_",
        "investigation_action_",
    )
    for key in list(st.session_state.keys()):
        if str(key).startswith(prefixes):
            del st.session_state[key]


def set_investigation_action(
    *,
    chapter_id: int,
    question_index: int,
    action: str,
) -> None:
    if action not in _ACTION_ORDER:
        raise ValueError(f"Unsupported investigation action: {action}")

    st.session_state[
        get_investigation_selected_key(chapter_id, question_index)
    ] = action
    st.session_state[
        get_investigation_active_key(chapter_id, question_index)
    ] = action

    visited_key = get_investigation_visited_key(chapter_id, question_index)
    visited = set(st.session_state.get(visited_key, []))
    visited.add(action)
    st.session_state[visited_key] = list(visited)


def _action_meta(
    *,
    theme: str,
    guide_name: str,
    action: str,
) -> tuple[str, str, str]:
    mapping = _THEME_ACTIONS.get(
        theme,
        _THEME_ACTIONS["동화"],
    )
    icon, label, cta = mapping[action]
    safe_guide = guide_name or "고양이"
    return (
        icon,
        label.format(guide_name=safe_guide),
        cta.format(guide_name=safe_guide),
    )


def _compact_action_label(
    *,
    theme: str,
    guide_name: str,
    action: str,
) -> str:
    mapping = _THEME_COMPACT_LABELS.get(
        theme,
        _THEME_COMPACT_LABELS["동화"],
    )
    safe_guide = guide_name or "고양이"
    return mapping[action].format(guide_name=safe_guide)


def _inject_board_css(theme: str) -> None:
    style = _THEME_STYLE.get(
        theme,
        _THEME_STYLE["동화"],
    )
    st.markdown(
        f"""
        <style>
        .stApp {{
            --inv-accent:{style['accent']};
            --inv-cta:{style['cta']};
            --inv-cta-text:{style['cta_text']};
            --inv-surface:{style['surface']};
            --inv-surface-alt:{style['surface_alt']};
            --inv-text:{style['text']};
            --inv-muted:{style['muted']};
            --inv-border:{style['border']};
        }}

        .inv-board-heading {{
            text-align:center;
            margin:.15rem 0 .08rem;
            font-size:.76rem;
            letter-spacing:.18em;
            font-weight:800;
            color:var(--inv-muted);
        }}

        .inv-board-copy {{
            text-align:center;
            margin:0 0 .6rem;
            font-size:.84rem;
            color:var(--inv-muted);
        }}

        .inv-card-marker,
        .inv-action-cta-marker,
        .inv-question-title-marker {{ display:none; }}

        div[data-testid="stElementContainer"]:has(.inv-question-title-marker) {{
            display:none !important;
            height:0 !important;
            min-height:0 !important;
            margin:0 !important;
            padding:0 !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.inv-card-marker) {{
            align-items:center !important;
            gap:.7rem !important;
            margin:.15rem auto .35rem !important;
            max-width:820px;
        }}

        div[data-testid="stColumn"]:has(.inv-card-marker) .stButton {{
            display:flex;
            justify-content:center;
            align-items:center;
            width:100%;
        }}

        div[data-testid="stColumn"]:has(.inv-card-marker) .stButton > button {{
            width:100% !important;
            aspect-ratio:4 / 3 !important;
            height:auto !important;
            min-height:0 !important;
            white-space:normal !important;
            line-height:1.25 !important;
            font-weight:800 !important;
            padding:.8rem !important;
            border:1px solid var(--inv-border) !important;
            border-radius:18px !important;
            color:var(--inv-text) !important;
            background:var(--inv-surface) !important;
            box-shadow:none !important;
            transition:
                transform .24s ease,
                background .24s ease,
                border-color .24s ease,
                opacity .24s ease,
                box-shadow .24s ease !important;
        }}

        div[data-testid="stColumn"]:has(.inv-card-side) .stButton > button {{
            max-width:190px !important;
            opacity:.68;
            font-size:.86rem !important;
            transform:scale(.9);
        }}

        div[data-testid="stColumn"]:has(.inv-card-center) .stButton > button {{
            max-width:240px !important;
            background:var(--inv-surface-alt) !important;
            border:2px solid var(--inv-accent) !important;
            font-size:1rem !important;
            transform:translateY(-4px) scale(1.025);
            box-shadow:0 10px 24px rgba(0,0,0,.08) !important;
        }}

        div[data-testid="stColumn"]:has(.inv-card-marker) .stButton > button:hover {{
            border-color:var(--inv-accent) !important;
            opacity:1;
            transform:translateY(-2px) scale(.94);
        }}

        div[data-testid="stColumn"]:has(.inv-card-center) .stButton > button:hover {{
            transform:translateY(-6px) scale(1.04);
        }}

        .inv-selection-state {{
            max-width:820px;
            margin:.05rem auto .45rem;
            display:flex;
            align-items:center;
            justify-content:center;
            flex-wrap:wrap;
            gap:.28rem .7rem;
            color:var(--inv-muted);
            font-size:.82rem;
            text-align:center;
        }}

        .inv-selection-state strong {{
            color:var(--inv-text);
            font-weight:800;
        }}

        .inv-selection-description {{
            max-width:620px;
            margin:0 auto .45rem;
            text-align:center;
            color:var(--inv-muted);
            font-size:.84rem;
            line-height:1.55;
        }}

        div[data-testid="stElementContainer"]:has(.inv-action-cta-marker) + div[data-testid="stElementContainer"] .stButton,
        div[data-testid="stElementContainer"]:has(.inv-action-cta-marker) + div .stButton {{
            display:flex;
            justify-content:center;
        }}

        div[data-testid="stElementContainer"]:has(.inv-action-cta-marker) + div[data-testid="stElementContainer"] .stButton > button,
        div[data-testid="stElementContainer"]:has(.inv-action-cta-marker) + div .stButton > button {{
            width:min(100%, 430px) !important;
            min-height:44px !important;
            border-radius:12px !important;
            border:1px solid var(--inv-accent) !important;
            background:var(--inv-cta) !important;
            color:var(--inv-cta-text) !important;
            font-weight:850 !important;
        }}

        .inv-compact-marker {{display:none;}}
        .inv-compact-meta {{
            max-width:820px;
            margin:.08rem auto .38rem;
            color:var(--inv-muted);
            font-size:.76rem;
            line-height:1.4;
            text-align:center;
        }}
        div[data-testid="stHorizontalBlock"]:has(.inv-compact-marker) {{
            gap:.38rem !important;
            max-width:720px;
            margin:.05rem auto .28rem !important;
        }}
        div[data-testid="stColumn"]:has(.inv-compact-marker) .stButton > button {{
            width:100% !important;
            min-height:40px !important;
            padding:.45rem .55rem !important;
            border-radius:11px !important;
            border:1px solid var(--inv-border) !important;
            background:var(--inv-surface) !important;
            color:var(--inv-text) !important;
            font-size:.78rem !important;
            font-weight:760 !important;
            box-shadow:none !important;
        }}
        div[data-testid="stColumn"]:has(.inv-compact-active) .stButton > button {{
            border-color:var(--inv-accent) !important;
            background:var(--inv-surface-alt) !important;
            box-shadow:inset 0 -2px 0 var(--inv-accent) !important;
        }}
        div[data-testid="stColumn"]:has(.inv-compact-selected) .stButton > button {{
            border-color:var(--inv-accent) !important;
        }}
        .inv-active-badge {{
            width:max-content;
            max-width:100%;
            margin:.08rem auto .3rem;
            padding:.28rem .62rem;
            border-radius:999px;
            border:1px solid var(--inv-border);
            background:var(--inv-surface);
            color:var(--inv-muted);
            font-size:.74rem;
            line-height:1.3;
            text-align:center;
        }}
        .inv-active-badge strong {{color:var(--inv-text);}}

        @media (max-width: 720px) {{
            html,
            body,
            [data-testid="stAppViewContainer"],
            .stApp {{
                overflow-x:hidden !important;
            }}

            /* 첫 행동 carousel:
               중앙 카드는 충분히 넓게, 좌우 카드는 일부만 보이는 peek 형태로 유지한다. */
            div[data-testid="stHorizontalBlock"]:has(.inv-card-marker) {{
                flex-wrap:nowrap !important;
                gap:.28rem !important;
                width:116% !important;
                max-width:none !important;
                margin:.1rem -8% .3rem !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.inv-card-marker) > div[data-testid="stColumn"]:has(.inv-card-side) {{
                min-width:0 !important;
                width:20% !important;
                flex:0 0 20% !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.inv-card-marker) > div[data-testid="stColumn"]:has(.inv-card-center) {{
                min-width:0 !important;
                width:60% !important;
                flex:0 0 60% !important;
            }}

            div[data-testid="stColumn"]:has(.inv-card-side) .stButton > button {{
                max-width:none !important;
                padding:.35rem .18rem !important;
                font-size:.64rem !important;
                border-radius:13px !important;
                transform:scale(.94) !important;
            }}

            div[data-testid="stColumn"]:has(.inv-card-center) .stButton > button {{
                max-width:none !important;
                padding:.55rem !important;
                font-size:.84rem !important;
                border-radius:15px !important;
                transform:translateY(-2px) scale(1) !important;
            }}

            /* DAY5_INVESTIGATION_BOARD_V5_MOBILE_ACTION_ROW:
               Streamlit 모바일 기본 CSS가 st.columns를 세로로 collapse해도
               compact action nav는 명시적으로 row 방향을 유지한다. */
            div[data-testid="stHorizontalBlock"]:has(.inv-compact-marker) {{
                display:flex !important;
                flex-direction:row !important;
                flex-wrap:nowrap !important;
                align-items:stretch !important;
                justify-content:stretch !important;
                gap:.3rem !important;
                width:100% !important;
                max-width:100% !important;
                margin:.05rem auto .24rem !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.inv-compact-marker) > div[data-testid="stColumn"] {{
                display:block !important;
                min-width:0 !important;
                width:calc((100% - .6rem) / 3) !important;
                max-width:calc((100% - .6rem) / 3) !important;
                flex:0 0 calc((100% - .6rem) / 3) !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.inv-compact-marker)
            > div[data-testid="stColumn"] .stButton {{
                width:100% !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.inv-compact-marker)
            > div[data-testid="stColumn"] .stButton > button {{
                width:100% !important;
                min-width:0 !important;
                min-height:42px !important;
                padding:.4rem .12rem !important;
                font-size:.7rem !important;
                line-height:1.15 !important;
                white-space:nowrap !important;
                overflow:hidden !important;
                text-overflow:ellipsis !important;
            }}

            .inv-active-badge {{
                margin:.04rem auto .28rem;
                padding:.24rem .52rem;
                font-size:.7rem;
            }}

            /* 긴 Question 제목은 모바일에서 20~25% 줄여 선택지와 CTA를 더 빨리 보여준다. */
            div[data-testid="stElementContainer"]:has(.inv-question-title-marker)
            + div[data-testid="stElementContainer"] h3 {{
                font-size:1.34rem !important;
                line-height:1.28 !important;
                letter-spacing:-.025em !important;
                margin:.3rem 0 .48rem !important;
            }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            div[data-testid="stColumn"]:has(.inv-card-marker) .stButton > button {{
                transition:none !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_investigation_board(
    *,
    theme: str,
    guide_name: str,
    chapter_id: int,
    question_index: int,
    default_action: str = ACTION_CLUE,
    require_companion_before_deduce: bool = False,
    context_meta: str | None = None,
) -> str | None:
    """첫 행동 전에는 4:3 carousel, 실행 후에는 compact action navigation을 렌더한다."""
    if default_action not in _ACTION_ORDER:
        default_action = ACTION_CLUE

    selected_key = get_investigation_selected_key(chapter_id, question_index)
    active_key = get_investigation_active_key(chapter_id, question_index)
    visited_key = get_investigation_visited_key(chapter_id, question_index)

    st.session_state.pop(_legacy_action_key(chapter_id, question_index), None)

    selected_action = st.session_state.get(selected_key, default_action)
    if selected_action not in _ACTION_ORDER:
        selected_action = default_action
    st.session_state[selected_key] = selected_action

    active_action = st.session_state.get(active_key)
    if active_action not in _ACTION_ORDER:
        active_action = None
        st.session_state.pop(active_key, None)

    visited_actions = set(st.session_state.get(visited_key, []))
    _inject_board_css(theme)

    st.markdown('<div class="inv-board-heading">INVESTIGATION</div>', unsafe_allow_html=True)
    if context_meta:
        st.markdown(
            f'<div class="inv-compact-meta">{html.escape(context_meta)}</div>',
            unsafe_allow_html=True,
        )

    # 첫 행동을 실행하기 전까지만 큰 4:3 carousel을 보여준다.
    if active_action is None:
        st.markdown(
            '<div class="inv-board-copy">카드를 고른 뒤 행동 버튼을 눌러 실행합니다.</div>',
            unsafe_allow_html=True,
        )

        selected_index = _ACTION_ORDER.index(selected_action)
        ordered = (
            _ACTION_ORDER[(selected_index - 1) % len(_ACTION_ORDER)],
            selected_action,
            _ACTION_ORDER[(selected_index + 1) % len(_ACTION_ORDER)],
        )
        columns = st.columns([1, 1.22, 1], gap="small")

        for position, (column, action) in enumerate(zip(columns, ordered)):
            icon, label, _ = _action_meta(
                theme=theme,
                guide_name=guide_name,
                action=action,
            )
            is_center = position == 1
            slot_class = "inv-card-center" if is_center else "inv-card-side"
            with column:
                st.markdown(
                    f'<span class="inv-card-marker {slot_class}"></span>',
                    unsafe_allow_html=True,
                )
                pressed = st.button(
                    f"{icon}\n\n{label}",
                    key=f"investigation_select_{chapter_id}_{question_index}_{action}",
                    use_container_width=True,
                )
                if pressed and action != selected_action:
                    st.session_state[selected_key] = action
                    st.rerun()

        selected_icon, selected_label, selected_cta = _action_meta(
            theme=theme,
            guide_name=guide_name,
            action=selected_action,
        )
        st.markdown(
            '<div class="inv-selection-state">'
            f'<span>선택 · <strong>{html.escape(selected_icon)} {html.escape(selected_label)}</strong></span>'
            '</div>'
            f'<div class="inv-selection-description">{html.escape(_ACTION_DESCRIPTIONS[selected_action])}</div>',
            unsafe_allow_html=True,
        )
    else:
        # 실제 행동을 실행한 뒤에는 큰 carousel을 치우고 3개의 compact action nav만 유지한다.
        columns = st.columns(3, gap="small")
        for column, action in zip(columns, _ACTION_ORDER):
            icon, _, _ = _action_meta(
                theme=theme,
                guide_name=guide_name,
                action=action,
            )
            label = _compact_action_label(
                theme=theme,
                guide_name=guide_name,
                action=action,
            )
            marker_classes = ["inv-compact-marker"]
            if action == active_action:
                marker_classes.append("inv-compact-active")
            if action == selected_action:
                marker_classes.append("inv-compact-selected")

            with column:
                st.markdown(
                    f'<span class="{" ".join(marker_classes)}"></span>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"{icon} {label}",
                    key=f"investigation_compact_select_{chapter_id}_{question_index}_{action}",
                    use_container_width=True,
                ) and action != selected_action:
                    st.session_state[selected_key] = action
                    st.rerun()

        active_icon, active_label, _ = _action_meta(
            theme=theme,
            guide_name=guide_name,
            action=active_action,
        )
        st.markdown(
            '<div class="inv-active-badge">현재 · '
            f'<strong>{html.escape(active_icon)} {html.escape(active_label)}</strong>'
            '</div>',
            unsafe_allow_html=True,
        )

        selected_icon, selected_label, selected_cta = _action_meta(
            theme=theme,
            guide_name=guide_name,
            action=selected_action,
        )

    companion_required = (
        require_companion_before_deduce
        and selected_action == ACTION_DEDUCE
        and ACTION_COMPANION not in visited_actions
    )

    if active_action != selected_action:
        st.markdown('<span class="inv-action-cta-marker"></span>', unsafe_allow_html=True)
        if companion_required:
            st.button(
                "🐈 먼저 동료와 대화해 핵심 개념을 확인하세요",
                key=f"investigation_action_locked_{chapter_id}_{question_index}",
                disabled=True,
                use_container_width=True,
            )
        elif st.button(
            f"{selected_icon} {selected_cta}",
            key=f"investigation_execute_{chapter_id}_{question_index}_{selected_action}",
            use_container_width=True,
            type="primary",
        ):
            set_investigation_action(
                chapter_id=chapter_id,
                question_index=question_index,
                action=selected_action,
            )
            st.rerun()

    return active_action

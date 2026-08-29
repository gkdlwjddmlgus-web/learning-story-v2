from __future__ import annotations

import html
import time

import streamlit as st

from repositories.world_repository import (
    update_guide_name_for_world_intro,
)


# DAY5_WORLD_INTRO_CINEMATIC_V1_2_FINAL_SCENE_SPACING
# DAY5_WORLD_INTRO_CINEMATIC_V1_1_THEME_TYPOGRAPHY_POLISH
# DAY5_WORLD_INTRO_CINEMATIC_V1
_THEME_STYLE = {
    "동화": {
        "accent": "#d76a89",
        "surface": "rgba(255,250,248,.94)",
        "surface_alt": "rgba(249,232,236,.78)",
        "text": "#4d2834",
        "muted": "#7e5a66",
        "border": "rgba(215,106,137,.34)",
        "eyebrow": "STORY COMPANION",
        "registered_eyebrow": "이야기의 동료",
        "font_display": '"Segoe Print","Nanum Pen Script","Gulim","굴림","Malgun Gothic",sans-serif',
        "font_body": '"Gulim","굴림","Malgun Gothic",sans-serif',
    },
    "미스터리": {
        "accent": "#8d2630",
        "surface": "rgba(247,244,239,.96)",
        "surface_alt": "rgba(238,233,225,.80)",
        "text": "#232321",
        "muted": "#66645f",
        "border": "rgba(141,38,48,.34)",
        "eyebrow": "UNIDENTIFIED COMPANION",
        "registered_eyebrow": "CASE COMPANION",
        "font_display": '"Batang","바탕","Nanum Myeongjo","Times New Roman",serif',
        "font_body": '"Batang","바탕","Malgun Gothic",serif',
    },
    "무협": {
        "accent": "#9f3a32",
        "surface": "rgba(246,239,223,.95)",
        "surface_alt": "rgba(234,223,200,.78)",
        "text": "#2b2520",
        "muted": "#6f6257",
        "border": "rgba(159,58,50,.32)",
        "eyebrow": "강호의 인연",
        "registered_eyebrow": "동행인",
        "font_display": '"Gungsuh","궁서","Batang","바탕",serif',
        "font_body": '"Batang","바탕","Malgun Gothic",serif',
    },
    "SF": {
        "accent": "#3ed6f4",
        "surface": "rgba(11,36,53,.94)",
        "surface_alt": "rgba(18,57,78,.82)",
        "text": "#e9faff",
        "muted": "#9fc5d3",
        "border": "rgba(62,214,244,.42)",
        "eyebrow": "UNREGISTERED COMPANION",
        "registered_eyebrow": "COMPANION LINKED",
        "font_display": '"Cascadia Mono","Consolas","D2Coding","Malgun Gothic",monospace',
        "font_body": '"Cascadia Mono","Consolas","D2Coding","Malgun Gothic",sans-serif',
    },
    "판타지": {
        "accent": "#caa55d",
        "surface": "rgba(36,33,30,.94)",
        "surface_alt": "rgba(58,49,38,.80)",
        "text": "#f4ead5",
        "muted": "#d6c5a5",
        "border": "rgba(202,165,93,.42)",
        "eyebrow": "UNNAMED COMPANION",
        "registered_eyebrow": "BOUND COMPANION",
        "font_display": '"Georgia","Palatino Linotype","Batang","바탕",serif',
        "font_body": '"Batang","바탕","Malgun Gothic",serif',
    },
}

_THEME_SCRIPT = {
    "동화": {
        "encounter": [
            ("NARRATOR", "길모퉁이에서 작은 고양이 한 마리가 당신을 빤히 바라봅니다."),
            ("🐈", "어? 너도 이 길을 가는 거야? 나도 같이 가면 안 될까?"),
            ("🐈", "그런데 나 아직 이름이 없어! 네가 하나 지어줄래?"),
        ],
        "reaction": [
            ("🐈", "{name}...? 헤헤, 마음에 들어! 이제부터 나는 {name}이야."),
            ("🐈", "좋아! 그럼 우리 둘이서 이 이야기를 시작해보자!"),
            ("SYSTEM", "이야기의 문이 열리고 있습니다..."),
        ],
        "ready": ("🐈", "준비됐어! 우리 이야기 속으로 들어가자!"),
        "cta": "✨ 이야기를 시작한다",
    },
    "미스터리": {
        "encounter": [
            ("CASE NOTE", "기록에서 빠진 작은 발자국 하나가 당신 앞에서 멈췄다."),
            ("🐈", "계속 혼자 조사할 생각이야? ...나도 따라가도 될까."),
            ("🐈", "기록 어디에도 내 이름은 남아 있지 않아. 네가 부를 이름을 하나 정해줄래?"),
        ],
        "reaction": [
            ("🐈", "{name}. ...확인했어. 그 이름으로 기억하지."),
            ("🐈", "앞으로 보게 될 것들은 우연이 아닐지도 몰라. 천천히 확인하자."),
            ("CASE NOTE", "첫 사건 기록을 정리하고 있습니다..."),
        ],
        "ready": ("🐈", "준비됐어. 이제 기록의 첫 장을 열자."),
        "cta": "🔎 사건을 시작한다",
    },
    "무협": {
        "encounter": [
            ("기록", "객잔 처마 아래, 비를 피하던 고양이 한 마리가 당신을 바라본다."),
            ("🐈", "소협도 이 강호를 홀로 걷는 모양이구냥. 인연이라면 동행해도 괜찮겠냥?"),
            ("🐈", "강호를 떠돌다 보니 불릴 이름 하나 남지 않았구냥. 내 이름을 지어주겠냥?"),
        ],
        "reaction": [
            ("🐈", "{name}이라... 좋은 이름이구냥. 오늘부터 그 이름으로 강호를 걷겠냥."),
            ("🐈", "은원은 깊고 길은 멀다냥. 그래도 소협과 함께라면 가볼 만하겠구냥."),
            ("기록", "새로운 인연의 행로를 펼치고 있습니다..."),
        ],
        "ready": ("🐈", "자, 소협. 인연이 닿았으니 함께 길을 나서보자냥."),
        "cta": "◎ 함께 길을 나선다",
    },
    "SF": {
        "encounter": [
            ("SYSTEM LOG", "꺼진 시스템 옆에서 작은 생명 신호 하나가 감지됐다."),
            ("🐈", "생체 신호 확인. 개체 분류: 고양이. 상태: 정상이다냥. ...너도 여기 혼자인가?"),
            ("🐈", "식별자: 없음. 호출명 미등록 상태. 사용자, 내 호출명을 하나 지정해주겠냥?"),
        ],
        "reaction": [
            ("🐈", "CALLSIGN ACCEPTED: {name}. 호출명 등록 완료다냥. 이제부터 {name}로 응답하겠다."),
            ("🐈", "주변 시스템과 연결을 시도한다. 미확인 신호 하나가 잡히고 있다냥."),
            ("SYSTEM", "WORLD LINK / SYNCHRONIZING..."),
        ],
        "ready": ("🐈", "동기화 완료. 신호 경로 확보다냥. ...같이 이동하겠어?"),
        "cta": "◉ 신호를 따라간다",
    },
    "판타지": {
        "encounter": [
            ("CHRONICLE", "낯선 길목에서 작은 고양이 한 마리가 먼저 당신의 앞을 막아섰다."),
            ("🐈", "드디어 누군가 왔네! 위험한 길이어도 난 겁먹지 않아. 너와 같이 가도 될까?"),
            ("🐈", "이름은 아직 없지만 괜찮아. 네가 지어준 이름이라면 당당하게 들고 다닐게!"),
        ],
        "reaction": [
            ("🐈", "{name}! 좋아, 아주 멋진 이름이야. 이제부터 난 {name}이라고 불러줘!"),
            ("🐈", "앞길에 뭐가 있든 같이 가자. 내가 먼저 겁먹는 일은 없을 거야!"),
            ("CHRONICLE", "새로운 세계의 문이 열리고 있습니다..."),
        ],
        "ready": ("🐈", "준비됐어. 자, 우리 모험의 첫 장을 열자!"),
        "cta": "✦ 세계의 문을 연다",
    },
}


def _key(world_id: int, suffix: str) -> str:
    return f"world_intro_v1_{world_id}_{suffix}"


def _safe_theme(theme: str) -> str:
    return theme if theme in _THEME_SCRIPT else "동화"


def _inject_css(theme: str) -> None:
    style = _THEME_STYLE[_safe_theme(theme)]
    st.markdown(
        f"""
        <style>
        .block-container {{
            max-width:1120px !important;
            padding-top:8vh !important;
        }}

        .world-intro-shell {{
            --wi-accent:{style["accent"]};
            --wi-surface:{style["surface"]};
            --wi-surface-alt:{style["surface_alt"]};
            --wi-text:{style["text"]};
            --wi-muted:{style["muted"]};
            --wi-border:{style["border"]};
            --wi-font-display:{style["font_display"]};
            --wi-font-body:{style["font_body"]};
            min-height:68vh;
            display:flex;
            flex-direction:column;
            justify-content:center;
        }}

        .world-intro-scene {{
            max-width:920px;
            margin:0 auto;
            width:100%;
            padding:2.1rem 2.2rem;
            border:1px solid var(--wi-border);
            border-radius:22px;
            background:var(--wi-surface);
            color:var(--wi-text);
            box-shadow:0 22px 60px rgba(0,0,0,.12);
            animation:worldIntroFadeIn .62s ease both;
        }}

        .world-intro-eyebrow {{
            color:var(--wi-accent);
            font-family:var(--wi-font-display);
            font-size:.73rem;
            font-weight:850;
            letter-spacing:.18em;
            margin-bottom:1.15rem;
        }}

        .world-intro-speaker {{
            color:var(--wi-muted);
            font-family:var(--wi-font-display);
            font-size:.78rem;
            letter-spacing:.11em;
            font-weight:750;
            margin-bottom:.55rem;
        }}

        .world-intro-line {{
            color:var(--wi-text);
            font-family:var(--wi-font-body);
            font-size:clamp(1.22rem,2.25vw,1.8rem);
            line-height:1.72;
            font-weight:540;
            word-break:keep-all;
        }}

        .world-intro-counter {{
            text-align:right;
            color:var(--wi-muted);
            font-size:.74rem;
            letter-spacing:.12em;
            margin-top:1.25rem;
        }}

        .world-intro-name-head {{
            max-width:760px;
            font-family:var(--wi-font-body);
            margin:0 auto .7rem;
            color:var(--wi-text);
            text-align:center;
            animation:worldIntroFadeIn .7s ease both;
        }}

        .world-intro-name-head strong {{
            display:block;
            font-size:1.35rem;
            margin-bottom:.28rem;
        }}

        .world-intro-name-head span {{
            color:var(--wi-muted);
            font-size:.9rem;
        }}

        .world-intro-name-marker {{display:none;}}

        div[data-testid="stElementContainer"]:has(.world-intro-name-marker) + div {{
            animation:worldIntroFormIn .72s ease both;
        }}

        /* DAY5_WORLD_INTRO_CINEMATIC_V1_2_FINAL_SCENE_SPACING:
           마지막 장면은 카드+CTA가 하나의 결말 묶음처럼 보이도록
           일반 cinematic보다 세로 점유를 줄여 위쪽 과다 여백을 제거한다. */
        .world-intro-shell.world-intro-shell--ready {{
            min-height:52vh;
            justify-content:center;
        }}

        .world-intro-final-bottom-space {{
            height:clamp(3.75rem,7vh,5.5rem);
            width:100%;
            pointer-events:none;
        }}

        .world-intro-ready {{
            max-width:920px;
            min-height:300px;
            width:100%;
            margin:0 auto .85rem;
            padding:2.1rem 2.2rem;
            border:1px solid var(--wi-border);
            border-radius:22px;
            background:var(--wi-surface);
            color:var(--wi-text);
            box-shadow:0 22px 60px rgba(0,0,0,.12);
            display:flex;
            flex-direction:column;
            justify-content:center;
            text-align:left;
            animation:worldIntroFadeIn .72s ease both;
        }}

        .world-intro-ready .eyebrow {{
            color:var(--wi-accent);
            font-family:var(--wi-font-display);
            font-size:.73rem;
            font-weight:850;
            letter-spacing:.18em;
            margin-bottom:1.1rem;
        }}

        .world-intro-ready .speaker {{
            color:var(--wi-muted);
            font-family:var(--wi-font-display);
            font-size:.78rem;
            font-weight:800;
            letter-spacing:.13em;
            margin-bottom:.65rem;
        }}

        .world-intro-ready .line {{
            font-family:var(--wi-font-body);
            font-size:clamp(1.22rem,2.25vw,1.8rem);
            line-height:1.72;
            font-weight:540;
            word-break:keep-all;
        }}

        @keyframes worldIntroFadeIn {{
            from {{opacity:0; filter:blur(7px); transform:translateY(8px);}}
            to {{opacity:1; filter:blur(0); transform:translateY(0);}}
        }}

        @keyframes worldIntroFormIn {{
            from {{opacity:0; transform:translateY(14px);}}
            to {{opacity:1; transform:translateY(0);}}
        }}

        @media (max-width:640px) {{
            .block-container {{padding-top:4.2rem !important;}}
            .world-intro-shell {{min-height:74vh;}}
            .world-intro-shell.world-intro-shell--ready {{
                min-height:56vh;
            }}
            .world-intro-final-bottom-space {{
                height:calc(4.25rem + env(safe-area-inset-bottom, 0px));
            }}
            .world-intro-scene {{
                padding:1.45rem 1.25rem;
                border-radius:18px;
            }}
            .world-intro-line,
            .world-intro-ready .line {{
                font-size:1.16rem;
                line-height:1.68;
            }}
            .world-intro-ready {{
                min-height:270px;
                padding:1.45rem 1.25rem;
                border-radius:18px;
            }}
        }}

        @media (prefers-reduced-motion:reduce) {{
            .world-intro-scene,
            .world-intro-ready,
            div[data-testid="stElementContainer"]:has(.world-intro-name-marker) + div {{
                animation:none !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _registered_eyebrow(
    *,
    theme: str,
    guide_name: str,
) -> str:
    style = _THEME_STYLE[_safe_theme(theme)]
    base = str(style["registered_eyebrow"]).strip()
    safe_name = str(guide_name or "고양이").strip()
    return f"{base} · {safe_name}"


def _render_scene(
    *,
    theme: str,
    speaker: str,
    text: str,
    index: int,
    total: int,
    eyebrow: str | None = None,
) -> None:
    style = _THEME_STYLE[_safe_theme(theme)]
    resolved_eyebrow = eyebrow or str(style["eyebrow"])
    st.markdown(
        '<div class="world-intro-shell">'
        '<div class="world-intro-scene">'
        f'<div class="world-intro-eyebrow">{html.escape(resolved_eyebrow)}</div>'
        f'<div class="world-intro-speaker">{html.escape(speaker)}</div>'
        f'<div class="world-intro-line">{html.escape(text)}</div>'
        f'<div class="world-intro-counter">{index:02d} / {total:02d}</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _frame_duration(text: str) -> float:
    visible = len("".join(str(text or "").split()))
    return max(2.9, min(5.2, 2.0 + visible * 0.052))


def _current_frame(
    *,
    started_at: float,
    frames: list[tuple[str, str]],
) -> tuple[int, bool]:
    elapsed = max(0.0, time.monotonic() - started_at)
    cumulative = 0.0
    for index, (_, text) in enumerate(frames):
        cumulative += _frame_duration(text)
        if elapsed < cumulative:
            return index, False
    return max(0, len(frames) - 1), True


def _render_pre_auto(*, user, world) -> None:
    world_id = int(world[0])
    theme = _safe_theme(str(world[4]))
    frames = _THEME_SCRIPT[theme]["encounter"]
    started_key = _key(world_id, "pre_started")
    if started_key not in st.session_state:
        st.session_state[started_key] = time.monotonic()

    index, done = _current_frame(
        started_at=float(st.session_state[started_key]),
        frames=frames,
    )
    speaker, text = frames[index]
    _render_scene(
        theme=theme,
        speaker=speaker,
        text=text,
        index=index + 1,
        total=len(frames),
    )

    if done:
        st.session_state[_key(world_id, "name_ready")] = True
        st.rerun()


_fragment_factory = getattr(st, "fragment", None)
_AUTO_PRE = (
    _fragment_factory(run_every=0.25)(_render_pre_auto)
    if _fragment_factory is not None
    else None
)


def _render_pre_manual(*, user, world) -> None:
    world_id = int(world[0])
    theme = _safe_theme(str(world[4]))
    frames = _THEME_SCRIPT[theme]["encounter"]
    index_key = _key(world_id, "manual_pre_index")
    index = int(st.session_state.get(index_key, 0))
    index = max(0, min(index, len(frames) - 1))
    speaker, text = frames[index]

    _render_scene(
        theme=theme,
        speaker=speaker,
        text=text,
        index=index + 1,
        total=len(frames),
    )

    label = "이름을 지어준다" if index == len(frames) - 1 else "다음"
    if st.button(
        label,
        key=f"world_intro_manual_pre_{world_id}_{index}",
        use_container_width=True,
        type="primary" if index == len(frames) - 1 else "secondary",
    ):
        if index >= len(frames) - 1:
            st.session_state[_key(world_id, "name_ready")] = True
        else:
            st.session_state[index_key] = index + 1
        st.rerun()


def render_world_intro_naming(*, user, world) -> None:
    """Guide-name gate를 첫 만남 시네마틱 + naming interaction으로 렌더한다."""
    world_id = int(world[0])
    theme = _safe_theme(str(world[4]))
    _inject_css(theme)

    if not st.session_state.get(_key(world_id, "name_ready")):
        if _AUTO_PRE is not None:
            _AUTO_PRE(user=user, world=world)
        else:
            _render_pre_manual(user=user, world=world)
        return

    st.markdown(
        '<div class="world-intro-name-head">'
        '<strong>이제 이 고양이를 어떻게 부를까요?</strong>'
        '<span>정한 이름은 이 월드에서 계속 함께하는 동료의 이름이 됩니다.</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span class="world-intro-name-marker"></span>',
        unsafe_allow_html=True,
    )

    name = st.text_input(
        "고양이 이름",
        placeholder="예: 모카, 루루, 보리",
        max_chars=20,
        key=f"world_intro_name_input_{world_id}",
    )

    if st.button(
        "이 이름으로 부를게",
        key=f"world_intro_name_submit_{world_id}",
        type="primary",
        use_container_width=True,
    ):
        clean_name = str(name or "").strip()
        if not clean_name:
            st.error("고양이 이름을 입력해주세요.")
            return

        update_guide_name_for_world_intro(
            world_id=world_id,
            user_id=int(user["user_id"]),
            guide_name=clean_name,
        )
        st.session_state[_key(world_id, "saved_name")] = clean_name
        st.session_state[_key(world_id, "post_pending")] = True
        st.session_state[_key(world_id, "post_started")] = time.monotonic()
        st.rerun()


def should_render_world_intro_post(world) -> bool:
    if not world:
        return False
    return bool(
        st.session_state.get(
            _key(int(world[0]), "post_pending"),
            False,
        )
    )


def _render_post_auto(*, user, world) -> None:
    world_id = int(world[0])
    theme = _safe_theme(str(world[4]))
    guide_name = (
        str(world[9]).strip()
        if len(world) > 9 and world[9]
        else str(st.session_state.get(_key(world_id, "saved_name"), "고양이"))
    )
    frames = [
        (speaker, text.format(name=guide_name))
        for speaker, text in _THEME_SCRIPT[theme]["reaction"]
    ]
    started_key = _key(world_id, "post_started")
    if started_key not in st.session_state:
        st.session_state[started_key] = time.monotonic()

    index, done = _current_frame(
        started_at=float(st.session_state[started_key]),
        frames=frames,
    )
    speaker, text = frames[index]
    _render_scene(
        theme=theme,
        speaker=speaker,
        text=text,
        index=index + 1,
        total=len(frames),
        eyebrow=_registered_eyebrow(
            theme=theme,
            guide_name=guide_name,
        ),
    )

    if done:
        st.session_state[_key(world_id, "post_ready")] = True
        st.rerun()


_AUTO_POST = (
    _fragment_factory(run_every=0.25)(_render_post_auto)
    if _fragment_factory is not None
    else None
)


def _render_post_manual(*, user, world) -> None:
    world_id = int(world[0])
    theme = _safe_theme(str(world[4]))
    guide_name = (
        str(world[9]).strip()
        if len(world) > 9 and world[9]
        else str(st.session_state.get(_key(world_id, "saved_name"), "고양이"))
    )
    frames = [
        (speaker, text.format(name=guide_name))
        for speaker, text in _THEME_SCRIPT[theme]["reaction"]
    ]
    index_key = _key(world_id, "manual_post_index")
    index = int(st.session_state.get(index_key, 0))
    index = max(0, min(index, len(frames) - 1))
    speaker, text = frames[index]

    _render_scene(
        theme=theme,
        speaker=speaker,
        text=text,
        index=index + 1,
        total=len(frames),
        eyebrow=_registered_eyebrow(
            theme=theme,
            guide_name=guide_name,
        ),
    )

    label = "연결 확인" if index == len(frames) - 1 else "다음"
    if st.button(
        label,
        key=f"world_intro_manual_post_{world_id}_{index}",
        use_container_width=True,
    ):
        if index >= len(frames) - 1:
            st.session_state[_key(world_id, "post_ready")] = True
        else:
            st.session_state[index_key] = index + 1
        st.rerun()


def render_world_intro_post(*, user, world) -> None:
    """이름 확정 후 동료 반응 + 월드 진입 동기화 장면을 렌더한다."""
    world_id = int(world[0])
    theme = _safe_theme(str(world[4]))
    _inject_css(theme)

    if not st.session_state.get(_key(world_id, "post_ready")):
        if _AUTO_POST is not None:
            _AUTO_POST(user=user, world=world)
        else:
            _render_post_manual(user=user, world=world)
        return

    guide_name = (
        str(world[9]).strip()
        if len(world) > 9 and world[9]
        else str(st.session_state.get(_key(world_id, "saved_name"), "고양이"))
    )
    speaker, text = _THEME_SCRIPT[theme]["ready"]
    st.markdown(
        '<div class="world-intro-shell world-intro-shell--ready">'
        '<div class="world-intro-ready">'
        f'<div class="eyebrow">{html.escape(_registered_eyebrow(theme=theme, guide_name=guide_name))}</div>'
        f'<div class="speaker">{html.escape(speaker)}</div>'
        f'<div class="line">{html.escape(text.format(name=guide_name))}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        _THEME_SCRIPT[theme]["cta"],
        key=f"world_intro_enter_{world_id}",
        type="primary",
        use_container_width=True,
    ):
        st.session_state[_key(world_id, "post_pending")] = False
        st.session_state[_key(world_id, "complete")] = True
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="world-intro-final-bottom-space" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )

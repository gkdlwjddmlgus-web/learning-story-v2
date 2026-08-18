import html
import traceback

import streamlit as st

from services.dev_config import generation_mode_label, is_ai_mock_enabled

from components.theme_system import (
    apply_theme_styles,
    canonical_theme,
    get_theme_pack,
)
from repositories.chapter_repository import (
    get_chapter,
)
from repositories.world_repository import (
    update_current_chapter,
    update_guide_name,
)
from services.story_engine_service import (
    ensure_initial_story_block,
)


INTRO_COPY = {
    "동화": (
        "A NEW PAGE",
        "눈을 뜨자, 처음 보는 세계였다.",
        "낯선 바람 사이로 작은 발소리가 가까워졌다. "
        "조그마한 고양이가 책장 같은 문 옆에 앉아 당신을 기다리고 있었다.",
        "“드디어 일어났구냥. 그런데 나한테는 아직 이름이 없다냥. 네가 지어줄래?”",
    ),
    "판타지": (
        "A NEW WORLD",
        "낯선 세계의 길목에서 고양이와 마주쳤다.",
        "고대 문양이 새겨진 돌길 끝, 평범해 보이는 고양이 한 마리가 "
        "당신과 같은 방향으로 길을 바라보고 있었다.",
        "“나도 이 길을 가려던 참이야. 이름은 아직 없는데… 같이 갈 거라면 네가 불러줄래?”",
    ),
    "SF": (
        "UNREGISTERED COMPANION",
        "꺼진 시스템 옆에서 작은 생명 신호가 움직였다.",
        "차가운 시설의 비상등 아래에서 고양이 한 마리가 콘솔 뒤를 빠져나왔다. "
        "로봇도 장치도 아닌, 그냥 말을 할 수 있는 고양이였다.",
        "“여기서 혼자인 줄 알았어. 나한텐 등록된 이름이 없는데… 네가 하나 정해줄래?”",
    ),
    "무협": (
        "江湖初遇",
        "강호로 향하는 첫 길에서 작은 동행을 만났다.",
        "바람에 흔들리는 대숲 아래, 고양이 한 마리가 태연히 당신 옆에 앉았다. "
        "영물도 신수도 아닌 듯했지만 분명 사람의 말을 알아들었다.",
        "“계속 같은 길을 갈 것 같네. 아직 불리는 이름은 없는데, 네가 하나 지어줄래?”",
    ),
    "미스터리": (
        "FIRST WITNESS",
        "사건보다 먼저, 이름 없는 목격자를 만났다.",
        "낯선 장소를 살피던 중 고양이 한 마리가 조용히 당신을 따라왔다. "
        "작은 흔적을 유난히 잘 보는 듯했지만 정답을 알고 있는 탐정은 아니었다.",
        "“나도 뭘 봤는지는 천천히 생각해봐야겠어. 그 전에… 나를 뭐라고 부를래?”",
    ),
}


def _render_intro(
    theme: str,
) -> None:
    canonical = canonical_theme(
        theme
    )

    kicker, title, body, cat_line = (
        INTRO_COPY.get(
            canonical,
            INTRO_COPY["판타지"],
        )
    )

    st.markdown(
        f"""
        <div class="theme-intro-card">
            <div class="theme-kicker">{html.escape(kicker)}</div>
            <div class="theme-preview-title">{html.escape(title)}</div>
            <div class="theme-preview-copy">{html.escape(body)}</div>
            <div style="margin-top:1rem;font-weight:750;line-height:1.7;">
                {html.escape(cat_line)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_guide_naming(
    user,
    world,
) -> None:
    theme = world[4]

    apply_theme_styles(
        theme
    )

    pack = get_theme_pack(
        theme
    )

    _render_intro(
        theme
    )

    if is_ai_mock_enabled():
        st.caption(f"🧪 {generation_mode_label()} · Gemini 할당량을 사용하지 않습니다.")

    st.markdown(
        f"**{pack['cat_role']}에게 이름을 지어주세요.**"
    )

    guide_name = st.text_input(
        "고양이 이름",
        placeholder=(
            "예: 모카, 루루, 보리"
        ),
        max_chars=20,
        key=f"guide_name_{world[0]}",
    )

    if st.button(
        "이 이름으로 부를게",
        type="primary",
        use_container_width=True,
        key=f"save_guide_name_{world[0]}",
    ):
        cleaned_name = (
            guide_name.strip()
        )

        if not cleaned_name:
            st.error(
                "고양이의 이름을 하나 지어주세요."
            )
            return

        try:
            # 이름은 Critical Data이므로 Story AI보다 먼저 저장한다.
            update_guide_name(
                world_id=world[0],
                guide_name=(
                    cleaned_name
                ),
            )

            # 현재 render에 들어온 tuple은 아직 guide_name=None이므로
            # AI 생성에 새 이름이 즉시 반영되도록 로컬 복사본을 만든다.
            world_with_name = list(
                world
            )

            if len(
                world_with_name
            ) <= 9:
                world_with_name.extend(
                    [None]
                    * (
                        10
                        - len(
                            world_with_name
                        )
                    )
                )

            world_with_name[9] = (
                cleaned_name
            )
            world_with_name = tuple(
                world_with_name
            )

            chapter = get_chapter(
                world_id=world[0],
                chapter_number=1,
            )

            if chapter is None:
                with st.spinner(
                    f"{cleaned_name}와 함께할 Curriculum, Story Outline과 Chapter 1을 준비하고 있습니다..."
                ):
                    ensure_initial_story_block(
                        user=user,
                        world=(
                            world_with_name
                        ),
                    )

            update_current_chapter(
                world_id=world[0],
                chapter_number=1,
            )

            st.session_state.world_id = (
                world[0]
            )

            st.rerun()

        except Exception as exc:
            traceback.print_exc()
            st.error(
                "고양이의 이름은 저장했습니다. "
                "Curriculum / Story Blueprint / Story Outline / Chapter 1 중 "
                "아직 완료되지 않은 단계부터 다시 시도할 수 있습니다."
            )
            st.caption(
                f"개발용 오류 유형: {type(exc).__name__} · "
                "상세 내용은 터미널과 AI Generation Log에 기록됩니다."
            )

import streamlit as st

from components.theme_system import (
    THEME_ORDER,
    apply_theme_styles,
    get_theme_pack,
    render_theme_preview,
)
from services.world_bootstrap_service import (
    create_learning_world_with_story_context,
)


def render_world_create(
    user,
):
    theme = st.selectbox(
        "이야기 분위기",
        THEME_ORDER,
        index=None,
        placeholder=(
            "먼저 이야기의 분위기를 선택해주세요"
        ),
        key="world_create_theme",
    )

    # 아무 것도 고르지 않았을 때는 로그인과 이어지는 Portal,
    # 선택 직후에는 해당 Theme Pack을 같은 화면에서 바로 체험한다.
    apply_theme_styles(
        theme
    )

    pack = get_theme_pack(
        theme
    )

    st.title(
        "첫 학습 세계 만들기"
    )

    st.caption(
        "테마는 Story의 시각 언어와 분위기를 바꾸지만, "
        "학습 내용의 정확한 용어와 핵심 구조는 유지됩니다."
    )

    render_theme_preview(
        theme
    )

    if theme:
        st.markdown(
            f"""
            <div class="theme-panel">
                <div class="theme-kicker">CORE EXPERIENCE</div>
                <div class="theme-preview-copy">
                    {pack["identity"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    topic = st.text_input(
        "무엇을 배우고 싶나요?",
        placeholder=(
            "예: Python, SQL, 통계, 영어, "
            "산업안전기사, 경제학"
        ),
    )

    goal = st.text_area(
        "학습 목표",
        placeholder=(
            "예: 실무에서 직접 활용할 수 있을 정도로 "
            "기초부터 응용까지 배우고 싶다."
        ),
        height=120,
    )

    learner_level = st.selectbox(
        "현재 수준",
        [
            "입문",
            "초급",
            "중급",
            "고급",
        ],
    )

    if st.button(
        "세계 만들기",
        type="primary",
        use_container_width=True,
    ):
        if theme is None:
            st.error(
                "먼저 이야기 분위기를 선택해주세요."
            )
            return

        if not topic.strip():
            st.error(
                "학습 주제를 입력해주세요."
            )
            return

        with st.spinner(
            "이야기의 첫 장으로 향하는 문을 열고 있습니다..."
        ):
            try:
                bootstrap = (
                    create_learning_world_with_story_context(
                        user_id=user[
                            "user_id"
                        ],
                        topic=topic.strip(),
                        goal=goal.strip(),
                        learner_level=(
                            learner_level
                        ),
                        theme=theme,
                        guide_name=None,
                    )
                )

                st.session_state.world_id = (
                    bootstrap[
                        "world_id"
                    ]
                )

                st.rerun()

            except Exception:
                st.error(
                    "학습 세계를 만드는 중 문제가 발생했습니다. "
                    "잠시 후 다시 시도해주세요."
                )

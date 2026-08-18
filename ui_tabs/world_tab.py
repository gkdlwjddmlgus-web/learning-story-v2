import streamlit as st

from components.text_utils import (
    format_inline_text,
)
from components.theme_system import (
    get_phase_label,
    get_theme_pack,
)
from repositories.chapter_repository import (
    get_chapters_by_world,
)
from repositories.curriculum_repository import (
    get_curriculum,
)
from services.story_context_service import (
    get_story_context,
)


def render_world_tab(
    user,
    world,
):
    pack = get_theme_pack(
        world[4]
    )

    st.subheader(
        pack["archive_name"]
    )

    context = get_story_context(
        world[0]
    )

    arc = (
        context["arc"]
        if context
        else None
    )
    state = (
        context["state"]
        if context
        else None
    )

    with st.expander(
        "현재 이야기",
        expanded=True,
    ):
        col1, col2, col3 = (
            st.columns(3)
        )

        col1.metric(
            "학습 주제",
            world[1],
        )

        col2.metric(
            "현재 Chapter",
            world[7],
        )

        col3.metric(
            "동료 고양이",
            (
                world[9]
                if len(world) > 9
                and world[9]
                else "-"
            ),
        )

        st.caption(
            f"Theme · {world[4]}  |  "
            f"학습 수준 · {world[3]}"
        )

        if arc:
            total = (
                arc.get(
                    "target_chapter_count"
                )
                or "?"
            )

            phase = (
                get_phase_label(
                    world[4],
                    arc.get(
                        "current_phase"
                    ),
                )
            )

            st.markdown(
                f"**Story Arc {arc['arc_number']} · "
                f"{arc.get('title') or '제목 준비 중'}**"
            )

            st.caption(
                f"{phase} · Chapter {world[7]} / {total}"
            )

        if state and state.get(
            "story_summary"
        ):
            st.markdown(
                "**지금까지의 이야기**"
            )
            st.write(
                state[
                    "story_summary"
                ]
            )

        if state:
            open_threads = (
                state.get(
                    "open_threads"
                )
                or []
            )

            if open_threads:
                st.markdown(
                    "**아직 남아 있는 질문**"
                )

                for item in (
                    open_threads[:6]
                ):
                    st.write(
                        f"• {item}"
                    )

    curriculum_row = get_curriculum(
        world[0]
    )

    with st.expander(
        "학습 여정",
        expanded=False,
    ):
        if not curriculum_row:
            st.caption(
                "아직 Curriculum이 생성되지 않았습니다."
            )
        else:
            curriculum = (
                curriculum_row[
                    "curriculum"
                ]
            )

            st.write(
                curriculum.get(
                    "summary",
                    "",
                )
            )

            for category in (
                curriculum.get(
                    "categories",
                    [],
                )
            ):
                st.markdown(
                    f"**{category.get('order', '-')}. "
                    f"{category.get('name', '')}**"
                )
                st.caption(
                    category.get(
                        "description",
                        "",
                    )
                )

    st.markdown(
        "### 지난 Chapter"
    )

    chapters = get_chapters_by_world(
        world[0]
    )

    for chapter in chapters:
        phase = (
            chapter[10]
            if len(chapter) > 10
            else None
        )

        phase_label = (
            get_phase_label(
                world[4],
                phase,
            )
            if phase
            else ""
        )

        label = (
            f"Chapter {chapter[2]} · "
            f"{chapter[3]}"
        )

        if phase_label:
            label += (
                f" · {phase_label}"
            )

        with st.expander(
            label,
            expanded=False,
        ):
            st.markdown(
                '<div class="archive-chapter-card">',
                unsafe_allow_html=True,
            )

            st.write(
                chapter[4]
            )

            targets = (
                chapter[11]
                if len(chapter) > 11
                else []
            )

            if targets:
                st.caption(
                    "학습 Concept · "
                    + ", ".join(
                        targets
                    )
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

# DAY5_EVENT_FLUSH_FIX_V1
import streamlit as st

from components.world_intro_cinematic import (
    render_world_intro_naming,
    render_world_intro_post,
    should_render_world_intro_post,
)

from components.styles import (
    apply_global_styles,
)
from components.story_cinematic import (
    should_render_story_cinematic,
)
from components.learning_compact_ui import (
    render_compact_app_header,
)
from components.theme_system import (
    apply_theme_styles,
    get_theme_pack,
)
from repositories.chapter_repository import (
    get_chapter,
)
from services.event_service import (
    flush_events,
    queue_once,
)
from ui_tabs.learning_tab import (
    render_learning_tab,
)
from ui_tabs.record_tab import (
    render_record_tab,
)
from ui_tabs.world_tab import (
    render_world_tab,
)
from views.guide_naming_view import (
    render_guide_naming,
)


def render_main(
    user,
    world,
):
    apply_global_styles()
    apply_theme_styles(
        world[4]
    )

    # DAY5_WORLD_INTRO_CINEMATIC_V1_MAIN_GATE
    if (
        len(world) <= 9
        or not world[9]
    ):
        render_world_intro_naming(
            user=user,
            world=world,
        )
        return

    if should_render_world_intro_post(world):
        render_world_intro_post(
            user=user,
            world=world,
        )
        return

    queue_once(
        key=(
            f"session_{world[0]}"
        ),
        event_type="session_start",
        user_id=user["user_id"],
        world_id=world[0],
        metadata={
            "theme": world[4],
        },
        flush=True,
    )

    # DAY5_STORY_CINEMATIC_V2_MAIN_GATE
    # 최초 Story Cinematic은 Learning Story 제목/탭/로그아웃보다 먼저 전용 화면을 소유한다.
    chapter = get_chapter(
        world_id=world[0],
        chapter_number=world[7],
    )
    if (
        chapter is not None
        and should_render_story_cinematic(
            chapter_id=chapter[0],
            story_text=chapter[4],
        )
    ):
        render_learning_tab(
            user=user,
            world=world,
        )
        return

    pack = get_theme_pack(
        world[4]
    )

    # DAY5_COMPACT_LEARNING_UI_V1_MAIN
    render_compact_app_header(
        theme=world[4],
        user_name=f"{user['display_name']}님",
        identity=pack["identity"],
    )

    learn_tab, world_tab, record_tab = (
        st.tabs(
            [
                "학습",
                pack[
                    "archive_name"
                ],
                pack[
                    "report_name"
                ],
            ]
        )
    )

    with learn_tab:
        render_learning_tab(
            user=user,
            world=world,
        )

    with world_tab:
        render_world_tab(
            user=user,
            world=world,
        )

    with record_tab:
        render_record_tab(
            user=user,
            world=world,
        )

    st.divider()

    if st.button(
        "로그아웃"
    ):
        flush_events()
        st.session_state.clear()
        st.rerun()

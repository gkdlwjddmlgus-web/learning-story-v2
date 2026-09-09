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
from services.chapter_runtime_service import (
    get_runtime_chapter,
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

    chapter = get_runtime_chapter(
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

    section_options = [
        "학습",
        pack["archive_name"],
        pack["report_name"],
    ]
    section_key = (
        f"v3_main_section_{world[0]}"
    )

    active_section = st.session_state.get(
        section_key,
        section_options[0],
    )
    if active_section not in section_options:
        active_section = section_options[0]
        st.session_state[
            section_key
        ] = active_section

    # V3_FULL_EXPECTED_PLAY_UI_V1_20260908
    # Learning owns the full viewport. Its small navigation controls live
    # inside the play HUD, so the old app header/radio do not consume height.
    if active_section == section_options[0]:
        render_learning_tab(
            user=user,
            world=world,
        )
        return

    # Archive / Record retain the conventional Streamlit document layout.
    render_compact_app_header(
        theme=world[4],
        user_name=(
            f"{user['display_name']}님"
        ),
        identity=pack["identity"],
    )

    active_section = st.radio(
        "메인 화면",
        options=section_options,
        horizontal=True,
        key=section_key,
        label_visibility="collapsed",
    )

    if active_section == section_options[0]:
        st.rerun()
    elif active_section == section_options[1]:
        render_world_tab(
            user=user,
            world=world,
        )
    else:
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

import streamlit as st

from components.styles import (
    apply_global_styles,
)
from components.theme_system import (
    apply_theme_styles,
    get_theme_pack,
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
        render_guide_naming(
            user=user,
            world=world,
        )
        return

    pack = get_theme_pack(
        world[4]
    )

    st.title(
        "Learning Story"
    )
    st.caption(
        f"{user['display_name']}님 · {pack['identity']}"
    )

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

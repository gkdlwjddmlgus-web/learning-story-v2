import streamlit as st

from repositories.world_repository import (
    get_world_by_id_for_user,
    get_worlds_by_user,
)
from views.auth_view import render_auth
from views.main_view import render_main
from views.world_create_view import render_world_create


st.set_page_config(
    page_title="Learning Story",
    page_icon="📖",
    layout="wide",
)


def init_session():
    if "user" not in st.session_state:
        st.session_state.user = None


def render_app():
    user = st.session_state.user

    worlds = get_worlds_by_user(
        user["user_id"]
    )

    if not worlds:
        render_world_create(user)
        return

    # 월드 생성 직후 저장된 session_state.world_id를 우선 사용한다.
    # 잘못되었거나 다른 사용자의 ID라면 안전하게 fallback한다.
    active_world_id = st.session_state.get(
        "world_id"
    )

    world = None

    if active_world_id is not None:
        world = get_world_by_id_for_user(
            user_id=user["user_id"],
            world_id=active_world_id,
        )

    if world is None:
        # 재로그인처럼 session_state가 초기화된 경우에는
        # 현재 구조상 가장 최근에 만든 월드를 기본 월드로 사용한다.
        world = worlds[-1]
        st.session_state.world_id = world[0]

    render_main(
        user=user,
        world=world,
    )


init_session()

if st.session_state.user is None:
    render_auth()
else:
    render_app()

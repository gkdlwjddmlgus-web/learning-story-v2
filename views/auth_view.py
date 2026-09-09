from components.auth_styles import apply_auth_styles
import streamlit as st

from auth import (
    login_user,
    register_user,
)


def render_auth():
    apply_auth_styles()

    st.markdown(
        """
        <section class="v3-auth-hero">
            <h1 class="v3-auth-title">Learning Story</h1>
            <p class="v3-auth-subtitle">
                당신의 공부가 이야기를 만들어갑니다.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.container(
        key="v3_auth_card",
    ):
        login_tab, signup_tab = st.tabs(
            [
                "로그인",
                "회원가입",
            ]
        )

        with login_tab:
            login_username = st.text_input(
                "아이디",
                key="login_username",
                placeholder="아이디를 입력하세요",
            )
            login_password = st.text_input(
                "비밀번호",
                type="password",
                key="login_password",
                placeholder="비밀번호를 입력하세요",
            )

            if st.button(
                "로그인",
                type="primary",
                key="v3_login_submit",
                use_container_width=True,
            ):
                success, result = login_user(
                    login_username,
                    login_password,
                )

                if success:
                    st.session_state.user = result
                    st.rerun()
                else:
                    st.error(result)

        with signup_tab:
            signup_username = st.text_input(
                "아이디",
                key="signup_username",
                placeholder="사용할 아이디",
            )
            signup_display_name = st.text_input(
                "닉네임",
                key="signup_display_name",
                placeholder="이야기에서 사용할 이름",
            )
            signup_password = st.text_input(
                "비밀번호",
                type="password",
                key="signup_password",
                placeholder="비밀번호",
            )
            signup_password_confirm = st.text_input(
                "비밀번호 확인",
                type="password",
                key="signup_password_confirm",
                placeholder="비밀번호를 한 번 더 입력하세요",
            )

            if st.button(
                "회원가입",
                key="v3_signup_submit",
                use_container_width=True,
            ):
                if (
                    signup_password
                    != signup_password_confirm
                ):
                    st.error(
                        "비밀번호가 일치하지 않습니다."
                    )
                    return

                success, result = register_user(
                    signup_username,
                    signup_display_name,
                    signup_password,
                )

                if success:
                    st.success(
                        "회원가입이 완료되었습니다. 로그인해주세요."
                    )
                else:
                    st.error(result)

        st.markdown(
            '<div class="v3-auth-card-foot">'
            '공부를 이어가면 세계와 이야기도 함께 성장합니다.'
            '</div>',
            unsafe_allow_html=True,
        )

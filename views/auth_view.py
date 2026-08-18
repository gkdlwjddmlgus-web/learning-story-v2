from components.auth_styles import apply_auth_styles
import streamlit as st
from auth import login_user, register_user

def render_auth():
    apply_auth_styles()
    login_tab, signup_tab = st.tabs(['로그인', '회원가입'])
    with login_tab:
        login_username = st.text_input('아이디', key='login_username')
        login_password = st.text_input('비밀번호', type='password', key='login_password')
        if st.button('로그인', type='primary'):
            success, result = login_user(login_username, login_password)
            if success:
                st.session_state.user = result
                st.rerun()
            else:
                st.error(result)
    with signup_tab:
        signup_username = st.text_input('아이디', key='signup_username')
        signup_display_name = st.text_input('닉네임', key='signup_display_name')
        signup_password = st.text_input('비밀번호', type='password', key='signup_password')
        signup_password_confirm = st.text_input('비밀번호 확인', type='password', key='signup_password_confirm')
        if st.button('회원가입'):
            if signup_password != signup_password_confirm:
                st.error('비밀번호가 일치하지 않습니다.')
                return
            success, result = register_user(signup_username, signup_display_name, signup_password)
            if success:
                st.success('회원가입이 완료되었습니다. 로그인해주세요.')
            else:
                st.error(result)

import streamlit as st


def apply_auth_styles() -> None:
    st.markdown(
        '''
        <style>
        html { color-scheme: light !important; }
        .stApp {
            background:
                radial-gradient(circle at 12% 16%, rgba(64,113,175,.18), transparent 28%),
                radial-gradient(circle at 88% 82%, rgba(86,201,199,.10), transparent 30%),
                linear-gradient(145deg, #07111f 0%, #0d1c2d 46%, #10263a 100%) !important;
            color: #edf7ff !important;
        }
        [data-testid="stHeader"] { background: rgba(5,13,24,.92) !important; }
        [data-testid="stToolbar"] { color: #d9f6ff !important; }
        .main .block-container { max-width: 820px; padding-top: 5rem; }
        h1,h2,h3,h4,[data-testid="stMarkdownContainer"] { color: #edf7ff; }
        [data-testid="stCaptionContainer"], .stCaption { color:#9ab4c9 !important; }
        button[data-baseweb="tab"] { color:#afc8db !important; font-weight:700 !important; }
        button[data-baseweb="tab"][aria-selected="true"] { color:#74e8ff !important; }
        div[data-baseweb="tab-highlight"] { background-color:#5ce6ff !important; }
        .stTextInput input,.stTextArea textarea {
            background:rgba(8,23,39,.86) !important;
            color:#f4fbff !important;
            border:1px solid rgba(112,199,224,.28) !important;
            border-radius:14px !important;
        }
        .stButton > button {
            min-height:3rem; border-radius:14px !important; font-weight:800 !important;
            border:1px solid rgba(93,226,255,.55) !important;
            background:rgba(13,39,59,.88) !important;
            color:#dffaff !important;
        }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background:linear-gradient(135deg,#20a9d1 0%,#4bd6df 100%) !important;
            color:#041018 !important; border:none !important;
        }
        [data-testid="stAlert"] { border-radius:14px !important; }
        </style>
        ''',
        unsafe_allow_html=True,
    )
    st.markdown(
        '''
        <div style="margin:0 0 1.25rem 0;padding:1.15rem 1.25rem;border-radius:18px;
        border:1px solid rgba(95,226,255,.22);background:rgba(7,22,38,.58);">
          <div style="color:#65e6ff;font-size:.78rem;font-weight:900;letter-spacing:.16em;margin-bottom:.45rem;">LEARNING STORY</div>
          <div style="color:#f2fbff;font-size:1.7rem;font-weight:900;line-height:1.25;">Learning Story</div>
          <div style="color:#9fb9cc;margin-top:.45rem;line-height:1.65;">공부할수록 당신의 이야기가 진행됩니다.</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

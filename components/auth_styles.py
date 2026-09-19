from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTH_BACKGROUND = (
    PROJECT_ROOT
    / "assets"
    / "backgrounds"
    / "fantasy"
    / "map1.png"
)


@st.cache_data(show_spinner=False)
def _auth_background_data_url() -> str:
    if not AUTH_BACKGROUND.is_file():
        return ""

    mime = (
        mimetypes.guess_type(
            AUTH_BACKGROUND.name
        )[0]
        or "image/png"
    )

    encoded = base64.b64encode(
        AUTH_BACKGROUND.read_bytes()
    ).decode("ascii")

    return (
        f"data:{mime};base64,{encoded}"
    )


def apply_auth_styles() -> None:
    background = (
        _auth_background_data_url()
    )

    image_layer = (
        f'url("{background}")'
        if background
        else "none"
    )

    st.markdown(
        f"""
        <style>
        /* V3_FULL_EXPECTED_LOGIN_UI_V1_20260908 */

        html {{
            color-scheme: dark !important;
        }}

        body,
        .stApp,
        div[data-testid="stAppViewContainer"],
        section[data-testid="stMain"] {{
            min-height:100dvh !important;
            height:100dvh !important;
            overflow:hidden !important;
        }}

        .stApp {{
            background:
                linear-gradient(
                    180deg,
                    rgba(3,12,27,.18) 0%,
                    rgba(4,13,29,.08) 36%,
                    rgba(3,10,23,.52) 72%,
                    rgba(2,8,19,.82) 100%
                ),
                {image_layer},
                linear-gradient(
                    145deg,
                    #0a1730 0%,
                    #142c4c 50%,
                    #241d3d 100%
                ) !important;
            background-size:cover !important;
            background-position:center center !important;
            background-repeat:no-repeat !important;
            color:#f5f8ff !important;
        }}

        header[data-testid="stHeader"] {{
            background:transparent !important;
            height:2rem !important;
        }}

        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu,
        footer {{
            display:none !important;
        }}

        div[data-testid="stMainBlockContainer"],
        .main .block-container {{
            width:min(100%, 1180px) !important;
            max-width:1180px !important;
            min-height:100dvh !important;
            height:100dvh !important;
            box-sizing:border-box !important;
            padding:clamp(2rem,5vh,4rem) 1.25rem 1.5rem !important;
            display:flex !important;
            flex-direction:column !important;
            justify-content:space-between !important;
            overflow:hidden !important;
        }}

        .v3-auth-hero {{
            width:min(92vw, 780px);
            margin:0 auto;
            text-align:center;
            color:#fff;
            text-shadow:0 4px 18px rgba(0,0,0,.38);
        }}

        .v3-auth-title {{
            font-family:Georgia, "Times New Roman", serif;
            font-size:clamp(3rem,6.2vw,5.7rem);
            line-height:.98;
            font-weight:700;
            letter-spacing:.015em;
            margin:0;
        }}

        .v3-auth-subtitle {{
            margin:.9rem 0 0;
            color:rgba(244,249,255,.88);
            font-size:clamp(1rem,1.8vw,1.45rem);
            line-height:1.45;
            font-weight:500;
        }}

        .st-key-v3_auth_card {{
            width:min(92vw, 560px) !important;
            margin:0 auto !important;
            padding:1.05rem 1.25rem 1.25rem !important;
            border:1px solid rgba(176,208,242,.28) !important;
            border-radius:20px !important;
            background:
                linear-gradient(
                    145deg,
                    rgba(9,24,45,.88),
                    rgba(12,31,55,.80)
                ) !important;
            box-shadow:
                0 22px 70px rgba(0,0,0,.38),
                inset 0 1px 0 rgba(255,255,255,.07) !important;
            backdrop-filter:blur(18px) saturate(120%) !important;
            -webkit-backdrop-filter:blur(18px) saturate(120%) !important;
        }}

        .st-key-v3_auth_card [data-testid="stTabs"] {{
            margin-bottom:.65rem !important;
        }}

        .st-key-v3_auth_card button[data-baseweb="tab"] {{
            color:rgba(226,236,247,.72) !important;
            font-size:1rem !important;
            font-weight:800 !important;
            padding:.7rem 1rem !important;
        }}

        .st-key-v3_auth_card button[data-baseweb="tab"][aria-selected="true"] {{
            color:#f7fbff !important;
        }}

        .st-key-v3_auth_card div[data-baseweb="tab-highlight"] {{
            height:2px !important;
            background:
                linear-gradient(
                    90deg,
                    #72b6ff,
                    #87dcff
                ) !important;
        }}

        .st-key-v3_auth_card .stTextInput {{
            margin:.2rem 0 .45rem !important;
        }}

        .st-key-v3_auth_card .stTextInput label {{
            color:rgba(232,241,250,.86) !important;
            font-weight:700 !important;
        }}

        .st-key-v3_auth_card .stTextInput input {{
            min-height:3.25rem !important;
            padding:.65rem .9rem !important;
            border:1px solid rgba(161,196,231,.24) !important;
            border-radius:13px !important;
            background:rgba(19,42,68,.72) !important;
            color:#f8fbff !important;
            box-shadow:none !important;
        }}

        .st-key-v3_auth_card .stTextInput input::placeholder {{
            color:rgba(214,227,241,.48) !important;
        }}

        .st-key-v3_auth_card div[data-testid="stButton"] > button {{
            width:100% !important;
            min-height:3.25rem !important;
            border-radius:12px !important;
            font-weight:900 !important;
        }}

        .st-key-v3_auth_card .st-key-v3_login_submit button,
        .st-key-v3_auth_card .st-key-v3_signup_submit button,
        .st-key-v3_auth_card
        button[data-testid="stBaseButton-primary"] {{
            border:none !important;
            color:#fff !important;
            -webkit-text-fill-color:#fff !important;
            background:
                linear-gradient(
                    135deg,
                    #3f8df0 0%,
                    #579cf6 55%,
                    #3d84e3 100%
                ) !important;
            box-shadow:0 10px 24px rgba(38,112,211,.28) !important;
        }}

        .v3-auth-card-foot {{
            margin-top:.55rem;
            text-align:center;
            color:rgba(215,226,240,.55);
            font-size:.73rem;
        }}

        [data-testid="stAlert"] {{
            border-radius:12px !important;
        }}

        @media (max-height: 760px) {{
            div[data-testid="stMainBlockContainer"],
            .main .block-container {{
                padding-top:1rem !important;
                padding-bottom:.7rem !important;
            }}

            .v3-auth-title {{
                font-size:clamp(2.5rem,5.5vw,4rem);
            }}

            .v3-auth-subtitle {{
                margin-top:.45rem;
                font-size:.92rem;
            }}

            .st-key-v3_auth_card {{
                padding:.7rem 1rem .85rem !important;
            }}

            .st-key-v3_auth_card .stTextInput input,
            .st-key-v3_auth_card div[data-testid="stButton"] > button {{
                min-height:2.75rem !important;
            }}
        }}

        @media (max-width: 620px) {{
            div[data-testid="stMainBlockContainer"],
            .main .block-container {{
                padding-left:.75rem !important;
                padding-right:.75rem !important;
            }}

            .v3-auth-title {{
                font-size:2.7rem;
            }}

            .v3-auth-subtitle {{
                font-size:.94rem;
            }}

            .st-key-v3_auth_card {{
                width:100% !important;
            }}
        }}

        @media (max-width: 620px) and (max-height: 700px) {{
            div[data-testid="stMainBlockContainer"],
            .main .block-container {{
                padding-top:.35rem !important;
                padding-bottom:.35rem !important;
            }}

            .v3-auth-hero {{
                margin-bottom:.35rem !important;
            }}

            .v3-auth-title {{
                font-size:2rem !important;
                line-height:1.02 !important;
            }}

            .v3-auth-subtitle {{
                margin-top:.2rem !important;
                font-size:.76rem !important;
                line-height:1.25 !important;
            }}

            .st-key-v3_auth_card {{
                padding:.38rem .62rem .48rem !important;
            }}

            .st-key-v3_auth_card [data-testid="stTabs"] {{
                margin-bottom:.2rem !important;
            }}

            .st-key-v3_auth_card button[data-baseweb="tab"] {{
                padding:.4rem .65rem !important;
                font-size:.82rem !important;
            }}

            .st-key-v3_auth_card div[data-baseweb="tab-panel"] {{
                max-height:calc(100dvh - 9.6rem) !important;
                overflow-y:auto !important;
                overflow-x:hidden !important;
                padding-right:.18rem !important;
                scrollbar-width:thin !important;
                overscroll-behavior:contain !important;
            }}

            .st-key-v3_auth_card .stTextInput {{
                margin:.05rem 0 .18rem !important;
            }}

            .st-key-v3_auth_card .stTextInput label {{
                font-size:.72rem !important;
            }}

            .st-key-v3_auth_card .stTextInput input {{
                min-height:2.35rem !important;
                padding:.38rem .62rem !important;
                font-size:.78rem !important;
            }}

            .st-key-v3_auth_card .st-key-v3_signup_submit {{
                position:sticky !important;
                bottom:0 !important;
                z-index:5 !important;
                padding-top:.3rem !important;
                background:linear-gradient(180deg,transparent,rgba(9,24,45,.98) 30%) !important;
            }}

            .st-key-v3_auth_card .st-key-v3_signup_submit button,
            .st-key-v3_auth_card .st-key-v3_login_submit button {{
                min-height:2.55rem !important;
                color:#fff !important;
                -webkit-text-fill-color:#fff !important;
            }}

            .v3-auth-card-foot {{
                display:none !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

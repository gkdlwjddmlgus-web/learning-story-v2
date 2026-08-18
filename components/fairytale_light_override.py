import streamlit as st


def apply_fairytale_light_override() -> None:
    st.markdown(
        '''
        <style>
        html, body { color-scheme: light !important; }
        .stApp { color-scheme: light !important; }
        [data-testid="stHeader"] {
            background: rgba(255,249,242,.94) !important;
            border-bottom:1px solid rgba(215,184,172,.28) !important;
        }
        [data-testid="stToolbar"], [data-testid="stToolbar"] * {
            color:#5d4b43 !important;
        }
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] details > summary {
            background:rgba(255,252,248,.94) !important;
            color:#5b463e !important;
        }
        [data-testid="stExpander"] summary *,
        [data-testid="stExpander"] details > summary * {
            color:#5b463e !important;
        }
        [data-testid="stExpander"] details[open] > summary {
            border-bottom:1px solid rgba(212,184,173,.34) !important;
        }
        input, textarea, select, button { color-scheme: light !important; }
        [data-baseweb="select"] > div,
        [data-baseweb="popover"] *,
        [role="listbox"] { color-scheme:light !important; }
        </style>
        ''',
        unsafe_allow_html=True,
    )

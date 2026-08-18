import streamlit as st


def apply_global_styles():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1500px;
            padding-top: 2.2rem;
            padding-bottom: 3rem;
        }

        [data-testid="stTabs"] button {
            font-size: 1.02rem;
            font-weight: 700;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        [data-testid="stExpander"] {
            border-radius: 14px;
            overflow: hidden;
        }

        [data-testid="stExpander"] summary p {
            font-size: 1.12rem;
            font-weight: 800;
        }

        .chapter-meta {
            font-size: 0.92rem;
            opacity: 0.72;
            margin-bottom: 0.5rem;
        }

        .chapter-story {
            font-size: 1.05rem;
            line-height: 1.9;
        }

        .quest-number {
            font-size: 0.92rem;
            font-weight: 800;
            opacity: 0.72;
            margin-bottom: 0.45rem;
        }

        .quest-question {
            font-size: 1.25rem;
            font-weight: 800;
            line-height: 1.65;
            margin-bottom: 1rem;
        }

        [data-testid="stRadio"] label p {
            font-size: 1.02rem;
            line-height: 1.55;
        }

        [data-testid="stAlert"] {
            border-radius: 12px;
        }

        div[data-testid="stButton"] > button {
            min-height: 2.7rem;
            border-radius: 10px;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

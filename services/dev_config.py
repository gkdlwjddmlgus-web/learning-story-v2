from __future__ import annotations

import os

import streamlit as st


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {
        "1", "true", "yes", "y", "on",
    }


def _secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def is_ai_mock_enabled() -> bool:
    env = os.getenv("DEV_AI_MOCK")
    if env is not None:
        return _to_bool(env)
    return _to_bool(_secret("DEV_AI_MOCK", False))


def get_mock_delay() -> float:
    env = os.getenv("DEV_AI_MOCK_DELAY")
    raw = env if env is not None else _secret("DEV_AI_MOCK_DELAY", 0.25)
    try:
        return max(0.0, min(float(raw), 10.0))
    except (TypeError, ValueError):
        return 0.25


def generation_provider() -> str:
    return "mock" if is_ai_mock_enabled() else "gemini"


def generation_mode_label() -> str:
    if is_ai_mock_enabled():
        return "DEV AI MOCK"
    return "GEMINI LIVE"

# DAY6_DIALOGUE_RUNTIME_FEATURE_GATE_V1
def is_dialogue_runtime_enabled() -> bool:
    """
    Dialogue Scene Runtime v1 feature gate.

    Local Git Bash:
        DIALOGUE_SCENE_RUNTIME_V1=1 streamlit run app.py

    Streamlit secrets:
        DIALOGUE_SCENE_RUNTIME_V1 = true
    """
    env = os.getenv(
        "DIALOGUE_SCENE_RUNTIME_V1"
    )

    if env is not None:
        return _to_bool(env)

    # V3 game UI: dialogue story presentation is the default.
    # Set DIALOGUE_SCENE_RUNTIME_V1=0 only when explicitly testing
    # the legacy cinematic fallback.
    return _to_bool(
        _secret(
            "DIALOGUE_SCENE_RUNTIME_V1",
            True,
        )
    )

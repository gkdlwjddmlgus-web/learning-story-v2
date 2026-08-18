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

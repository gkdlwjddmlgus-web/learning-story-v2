"""Browser fixture for the production Story Choice renderer (no DB/AI access)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ui_tabs.learning_tab as learning_tab


CHAPTER_ID = 990_001
CHOICE = {
    "key": "dialogue_fixture",
    "text": "루미QA, 기록의 시간 순서부터 함께 확인하자.",
    "choice_type": "dialogue",
}


def _selected_choice(*, user_id: int, chapter_id: int) -> dict | None:
    del user_id
    if chapter_id != CHAPTER_ID:
        return None
    return st.session_state.get("fixture_selected_choice")


def _save_choice(**kwargs) -> None:
    st.session_state["fixture_selected_choice"] = {
        "choice_key": kwargs["choice_key"],
        "choice_text": kwargs["choice_text"],
    }


learning_tab.get_runtime_story_context = lambda world_id: {
    "arc": {"id": 990_101},
}
learning_tab.get_choice_for_chapter = _selected_choice
learning_tab.save_story_choice = _save_choice
learning_tab.queue_event = lambda *args, **kwargs: None

user = {
    "user_id": 990_201,
    "username": "fixture_player",
    "display_name": "테스트 플레이어",
}
world = (
    990_301,
    "SQL",
    "Story Choice contract",
    "입문",
    "SF",
    "Fixture World",
    "Fixture summary",
    3,
    None,
    "루미QA",
)
chapter = (
    CHAPTER_ID,
    world[0],
    3,
    "Dialogue Choice E2E Fixture",
    "Fixture story",
    [],
    [],
    True,
    None,
    [CHOICE],
)

st.set_page_config(page_title="Story Choice Dialogue E2E", layout="wide")
st.caption("TEST FIXTURE · production renderer · in-memory persistence")
learning_tab._render_story_choice(user=user, world=world, chapter=chapter)

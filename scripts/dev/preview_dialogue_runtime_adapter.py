from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from components.dialogue_scene import render_dialogue_scene
from services.dialogue_asset_service import (
    resolve_background,
    resolve_portrait,
)
from services.dialogue_runtime_service import build_dialogue_beats


# DAY6_DIALOGUE_RUNTIME_PREVIEW_V1

st.set_page_config(
    page_title="DAY6 Dialogue Runtime Adapter v1",
    layout="wide",
)

st.title("DAY6 · Dialogue Runtime Adapter v1")
st.caption(
    "기존 plain-text Story를 변경하지 않고 "
    "Dialogue Beat로 보수적으로 분해하는 QA 화면입니다."
)

with st.sidebar:
    theme = st.selectbox(
        "테마",
        ["동화", "판타지", "SF", "무협", "미스터리"],
    )

    guide_name = st.text_input(
        "고양이 이름",
        value="모카",
    )

    story_text = st.text_area(
        "Story",
        value=(
            "낡은 기록실 안쪽에서 종이가 넘어가는 소리가 들렸다.\n\n"
            f"“저 숫자들, 서로 다른 길을 가리키고 있어!” "
            f"{guide_name}가 기록지를 톡톡 두드리며 말했다.\n\n"
            "두 기록을 비교하려면 먼저 같은 단위로 맞춰야 한다는 사실을 "
            "확인하기 위해 우리는 세부 기록을 살펴보기로 했다."
        ),
        height=260,
    )

beats = build_dialogue_beats(
    story_text=story_text,
    guide_name=guide_name,
)

st.subheader(f"Parsed beats · {len(beats)}")

for index, beat in enumerate(beats):
    with st.expander(
        f"{index + 1:02d} · {beat.speaker_type} · {beat.speaker_name}",
        expanded=True,
    ):
        portrait = resolve_portrait(
            theme,
            beat.speaker_type,
            character_id="default",
        )
        background = resolve_background(
            theme,
            scene_id="default",
        )

        render_dialogue_scene(
            theme=theme,
            speaker_type=beat.speaker_type,
            speaker_name=beat.speaker_name,
            text=beat.text,
            portrait_path=portrait,
            background_path=background,
            context_label="ADAPTER PREVIEW",
            key=f"runtime_preview_{index}",
            show_next_button=False,
            show_scene_chrome=False,
        )

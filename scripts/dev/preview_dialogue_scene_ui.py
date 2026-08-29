from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from components.dialogue_scene import render_dialogue_scene


# DAY6_DIALOGUE_SCENE_UI_V1_PREVIEW
# DAY6_DIALOGUE_SCENE_UI_V1_1_POLISH_PREVIEW
st.set_page_config(
    page_title="DAY6 Dialogue Scene UI v1.1",
    layout="wide",
)

st.title("DAY6 · Dialogue Scene UI v1.1")
st.caption(
    "실제 Story/DB에는 연결하지 않은 Presentation QA입니다. "
    "왼쪽에서 값을 바꾸고 Scene만 바로 비교합니다."
)

with st.sidebar:
    st.header("Dialogue QA")

    theme = st.selectbox(
        "테마",
        ["동화", "미스터리", "무협", "SF", "판타지"],
    )

    speaker_type = st.selectbox(
        "화자 유형",
        ["companion", "npc", "player", "narrator"],
    )

    default_names = {
        "companion": "루루",
        "npc": "기록 관리인",
        "player": "나",
        "narrator": "NARRATOR",
    }

    speaker_name = st.text_input(
        "화자 이름",
        value=default_names[speaker_type],
    )

    sample_texts = {
        "동화": "저 종이 위 숫자들, 서로 다른 길을 가리키고 있어! 우리 같이 맞춰보자.",
        "미스터리": "잠깐. 기록된 수치와 현장 값이 맞지 않아. 누군가 단위를 바꿔 적은 흔적이 있어.",
        "무협": "소협, 이 장부의 수치가 서로 맞지 않는구냥. 먼저 단위의 흐름부터 살펴보세.",
        "SF": "데이터 불일치 감지. 변환 단위가 기준값과 다르다냥. 원본 로그 대조를 권장한다.",
        "판타지": "좋아, 이 흔적을 따라가자! 서로 다른 단위를 하나의 기준으로 맞추면 길이 열릴 거야.",
    }

    text = st.text_area(
        "대사",
        value=(
            "오래된 기록실 안쪽에서 종이가 넘어가는 소리가 들렸다."
            if speaker_type == "narrator"
            else sample_texts[theme]
        ),
        height=150,
    )

    portrait_path = st.text_input(
        "캐릭터 이미지 경로 (선택)",
        value="",
        placeholder="assets/dialogue/sf/companion.png",
    )

    background_path = st.text_input(
        "배경 이미지 경로 (선택)",
        value="",
        placeholder="assets/dialogue/backgrounds/sf_control_room.png",
    )

    show_scene_chrome = st.toggle(
        "Scene 개발 라벨 표시",
        value=False,
        help="STORY SCENE / prototype context 같은 QA용 라벨입니다.",
    )

    st.caption(
        "배치: Companion/NPC=좌측 초상 · Player=우측 초상 · "
        "Narrator=초상 없음"
    )

render_dialogue_scene(
    theme=theme,
    speaker_type=speaker_type,
    speaker_name=speaker_name,
    text=text,
    portrait_path=(portrait_path or None),
    background_path=(background_path or None),
    context_label="CHAPTER 1 · Dialogue Presentation Prototype",
    key=f"day6_preview_v11_{theme}_{speaker_type}",
    show_scene_chrome=show_scene_chrome,
)

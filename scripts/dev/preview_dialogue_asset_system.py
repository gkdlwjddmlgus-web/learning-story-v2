from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from components.dialogue_scene import render_dialogue_scene
from services.dialogue_asset_service import describe_resolution


# DAY6_DIALOGUE_ASSET_SYSTEM_V1_PREVIEW

st.set_page_config(
    page_title="DAY6 Dialogue Asset System v1",
    layout="wide",
)

st.title("DAY6 · Dialogue Asset System v1")
st.caption(
    "Story/DB에 연결하지 않은 Asset Resolver QA입니다. "
    "이미지가 없으면 기존 Dialogue Scene fallback이 그대로 표시됩니다."
)

with st.sidebar:
    st.header("Asset QA")

    theme = st.selectbox(
        "테마",
        [
            "동화",
            "미스터리",
            "무협",
            "SF",
            "판타지",
        ],
    )

    speaker_type = st.selectbox(
        "화자 유형",
        [
            "companion",
            "npc",
            "player",
            "narrator",
        ],
    )

    speaker_defaults = {
        "companion": "루루",
        "npc": "기록 관리인",
        "player": "나",
        "narrator": "NARRATOR",
    }

    character_defaults = {
        "companion": "lulu",
        "npc": "archive_keeper",
        "player": "player",
        "narrator": "narrator",
    }

    speaker_name = st.text_input(
        "화자 이름",
        value=speaker_defaults[speaker_type],
    )

    character_id = st.text_input(
        "캐릭터 ID",
        value=character_defaults[speaker_type],
        help=(
            "파일명 stem과 연결됩니다. "
            "예: lulu -> lulu.png / lulu.webp"
        ),
    )

    scene_id = st.text_input(
        "Scene ID",
        value="default",
        help=(
            "배경 파일명 stem과 연결됩니다. "
            "예: control_room -> control_room.png"
        ),
    )

    sample_text = {
        "동화": "저 숫자들, 서로 다른 길을 가리키고 있어! 우리 같이 맞춰보자.",
        "미스터리": "기록의 수치와 현장 값이 맞지 않아. 누군가 단위를 바꿔 적은 흔적이 있어.",
        "무협": "소협, 이 장부의 수치가 맞지 않는구냥. 단위의 흐름부터 살펴보세.",
        "SF": "데이터 불일치 감지. 변환 단위가 기준값과 다르다냥.",
        "판타지": "이 흔적을 따라가자! 단위를 하나의 기준으로 맞추면 길이 열릴 거야.",
    }

    dialogue_text = st.text_area(
        "대사",
        value=(
            "기록실 안쪽에서 종이가 넘어가는 소리가 들렸다."
            if speaker_type == "narrator"
            else sample_text[theme]
        ),
        height=140,
    )

resolution = describe_resolution(
    theme,
    speaker_type,
    character_id=character_id,
    scene_id=scene_id,
)

portrait_path = resolution["portrait_path"]
background_path = resolution["background_path"]

left, right = st.columns([1, 1])

with left:
    st.subheader("Resolver 결과")
    st.write(
        {
            "theme": resolution["theme"],
            "role": resolution["role"],
            "character_id": resolution["character_id"],
            "scene_id": resolution["scene_id"],
        }
    )

    st.caption(
        "Portrait directory: "
        + str(resolution["portrait_directory"])
    )
    st.caption(
        "Background directory: "
        + str(resolution["background_directory"])
    )

with right:
    if portrait_path:
        st.success(f"Portrait resolved: {portrait_path}")
    elif speaker_type == "narrator":
        st.info("Narrator는 portrait를 사용하지 않습니다.")
    else:
        st.warning(
            "Portrait 미발견 → 기존 placeholder fallback 사용"
        )

    if background_path:
        st.success(f"Background resolved: {background_path}")
    else:
        st.warning(
            "Background 미발견 → 테마 기본 배경 fallback 사용"
        )

render_dialogue_scene(
    theme=theme,
    speaker_type=speaker_type,
    speaker_name=speaker_name,
    text=dialogue_text,
    portrait_path=portrait_path,
    background_path=background_path,
    key=(
        "asset_preview_"
        + str(resolution["theme"])
        + "_"
        + str(resolution["role"])
    ),
)

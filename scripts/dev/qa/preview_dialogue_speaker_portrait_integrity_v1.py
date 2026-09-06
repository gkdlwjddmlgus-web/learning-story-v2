from __future__ import annotations

import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.dialogue_runtime_service import (
    MAX_SCENE_CHARS,
    build_dialogue_beats,
)


def _quote_beat(beats, fragment: str):
    for beat in beats:
        if fragment in beat.text:
            return beat
    raise AssertionError(f"quote beat not found: {fragment}")


def main() -> int:
    runtime_path = PROJECT_ROOT / "services" / "dialogue_runtime_service.py"
    experience_path = PROJECT_ROOT / "components" / "dialogue_story_experience.py"

    runtime = runtime_path.read_text(encoding="utf-8")
    experience = experience_path.read_text(encoding="utf-8")

    ast.parse(runtime, filename=str(runtime_path))
    ast.parse(experience, filename=str(experience_path))

    print("=" * 78)
    print("Dialogue Speaker / Portrait Integrity v1 - QA")
    print("=" * 78)

    beats = build_dialogue_beats(
        story_text=(
            '“저 숫자들, 서로 다른 길을 가리키고 있어!” '
            '루루가 기록지를 톡톡 두드리며 말했다.'
        ),
        guide_name="루루",
    )
    beat = _quote_beat(beats, "저 숫자들")
    if (beat.speaker_type, beat.speaker_name) != ("companion", "루루"):
        raise AssertionError("same-paragraph Companion attribution failed")
    print("[PASS] same-paragraph Companion attribution")

    beats = build_dialogue_beats(
        story_text=(
            "루루가 밸브 표면에 맺힌 차가운 김을 조심스레 들여다보며 "
            "고개를 갸웃했습니다.\n\n"
            "“이 유리관을 지나는 열량 흐름이 조금 묘해. "
            "우리가 계산해 둔 열에너지 수지보다 기체가 쥐고 있는 "
            "숨은 힘이 더 크게 요동치는 것 같지 않아?”"
        ),
        guide_name="루루",
    )
    beat = _quote_beat(beats, "이 유리관을 지나는 열량 흐름")
    if (beat.speaker_type, beat.speaker_name) != ("companion", "루루"):
        raise AssertionError(
            f"cross-paragraph Companion attribution failed: "
            f"{beat.speaker_type}/{beat.speaker_name}"
        )
    print("[PASS] screenshot-style cross-paragraph Companion attribution")

    beats = build_dialogue_beats(
        story_text=(
            "루루가 제어반 옆 기록지를 톡톡 치며 귀를 쫑긋거렸습니다."
        ),
        guide_name="루루",
    )
    if not beats or any(beat.speaker_type != "narrator" for beat in beats):
        raise AssertionError("plain Companion action should remain Narrator")
    print("[PASS] plain Companion action remains Narrator")

    beats = build_dialogue_beats(
        story_text='“이 기록은 이상하다.” 조명이 흔들렸다.',
        guide_name="루루",
    )
    beat = _quote_beat(beats, "이 기록은 이상하다")
    if beat.speaker_type != "narrator":
        raise AssertionError("uncertain quote should remain Narrator")
    print("[PASS] uncertain quote safely falls back to Narrator")

    beats = build_dialogue_beats(
        story_text='“루루, 저 문을 봐.”',
        guide_name="루루",
    )
    beat = _quote_beat(beats, "루루, 저 문을 봐")
    if beat.speaker_type == "player":
        raise AssertionError("guide vocative alone must not fabricate Player")
    print("[PASS] guide vocative alone no longer fabricates Player")

    beats = build_dialogue_beats(
        story_text='내가 물었다. “이 길이 맞을까?”',
        guide_name="루루",
    )
    beat = _quote_beat(beats, "이 길이 맞을까")
    if beat.speaker_type != "player":
        raise AssertionError("explicit legacy Player attribution compatibility failed")
    print("[PASS] explicit legacy Player attribution retained")

    beats = build_dialogue_beats(
        story_text='“잠깐 기다려.” 경비대장이 말했다.',
        guide_name="루루",
    )
    beat = _quote_beat(beats, "잠깐 기다려")
    if beat.speaker_type not in {"npc", "companion"}:
        raise AssertionError("explicit NPC attribution failed")
    if beat.speaker_type == "companion":
        raise AssertionError("NPC was misclassified as Companion")
    print("[PASS] explicit NPC attribution retained")

    long_story = " ".join(
        "공장 안쪽의 제어 기록에는 서로 다른 단위가 적혀 있었습니다."
        for _ in range(8)
    )
    beats = build_dialogue_beats(
        story_text=long_story,
        guide_name="루루",
    )
    if len(beats) < 2:
        raise AssertionError("long narration was not split")
    if any(len(beat.text) > MAX_SCENE_CHARS for beat in beats):
        raise AssertionError("scene max character limit exceeded")
    print(f"[PASS] scene max chars <= {MAX_SCENE_CHARS}")

    required_runtime = (
        "# DAY6_DIALOGUE_RUNTIME_SERVICE_V2",
        "# DIALOGUE_SPEAKER_PORTRAIT_INTEGRITY_V1_20260904",
        "def _previous_paragraph_guide_focus(",
        "previous_paragraph_text=",
    )
    for token in required_runtime:
        if token not in runtime:
            raise AssertionError("runtime marker missing: " + token)

    required_experience = (
        "portrait_path = resolve_portrait(",
        "beat.speaker_type",
        'character_id="default"',
        "portrait_path=portrait_path",
    )
    for token in required_experience:
        if token not in experience:
            raise AssertionError("portrait pipeline missing: " + token)

    print("[PASS] Dialogue Story Experience portrait pipeline retained")
    print()
    print("[SECURITY / COST]")
    print("- No Gemini API request was made.")
    print("- No DB query/write was made.")
    print("- Existing Story text / Chapter rows were not modified.")
    print()
    print("Dialogue Speaker / Portrait Integrity v1 QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

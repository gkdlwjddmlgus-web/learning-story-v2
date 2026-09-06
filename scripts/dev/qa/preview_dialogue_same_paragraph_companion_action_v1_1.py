from __future__ import annotations

import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.dialogue_runtime_service import build_dialogue_beats


def _beat_with(beats, fragment: str):
    for beat in beats:
        if fragment in beat.text:
            return beat
    raise AssertionError(f"beat not found: {fragment}")


def main() -> int:
    runtime_path = PROJECT_ROOT / "services" / "dialogue_runtime_service.py"
    runtime = runtime_path.read_text(encoding="utf-8")
    ast.parse(runtime, filename=str(runtime_path))

    print("=" * 78)
    print("Dialogue Same-Paragraph Companion Action v1.1 - QA")
    print("=" * 78)

    beats = build_dialogue_beats(
        story_text=(
            "소리 없이 다가온 무무가 수염을 미세하게 떨며 "
            "먹물이 번진 난을 꼬리로 가리켰다. "
            "“서첩과 장부의 기록이 군데군데 맞지 않네.”"
        ),
        guide_name="무무",
    )
    narration = _beat_with(beats, "소리 없이 다가온 무무가")
    quote = _beat_with(beats, "서첩과 장부의 기록이")

    if (narration.speaker_type, narration.speaker_name) != ("narrator", "NARRATOR"):
        raise AssertionError(
            "Companion action narration must remain Narrator: "
            f"{narration.speaker_type}/{narration.speaker_name}"
        )

    if (quote.speaker_type, quote.speaker_name) != ("companion", "무무"):
        raise AssertionError(
            "action-following quote must be Companion: "
            f"{quote.speaker_type}/{quote.speaker_name}"
        )

    if narration.text == quote.text:
        raise AssertionError("Narrator action and Companion quote were merged")

    print("[PASS] screenshot regression: Narrator action -> Companion quote split")

    beats = build_dialogue_beats(
        story_text=(
            "당신을 잠시 바라보던 무무가 장부를 톡톡 두드렸다. "
            "“여기부터 살펴보는 게 좋겠어.”"
        ),
        guide_name="무무",
    )
    quote = _beat_with(beats, "여기부터 살펴보는 게 좋겠어")
    if (quote.speaker_type, quote.speaker_name) != ("companion", "무무"):
        raise AssertionError("modified Companion subject attribution failed")
    print("[PASS] modified Companion subject attribution")

    beats = build_dialogue_beats(
        story_text=(
            "“저 숫자들, 서로 다른 길을 가리키고 있어!” "
            "무무가 기록지를 톡톡 두드리며 말했다."
        ),
        guide_name="무무",
    )
    quote = _beat_with(beats, "저 숫자들")
    if (quote.speaker_type, quote.speaker_name) != ("companion", "무무"):
        raise AssertionError("explicit same-paragraph Companion attribution regressed")
    print("[PASS] explicit same-paragraph Companion attribution retained")

    beats = build_dialogue_beats(
        story_text=(
            "무무가 장부 가장자리를 가볍게 짚고 고개를 갸웃했다.\n\n"
            "“이 기록 흐름이 조금 묘해.”"
        ),
        guide_name="무무",
    )
    quote = _beat_with(beats, "이 기록 흐름이 조금 묘해")
    if (quote.speaker_type, quote.speaker_name) != ("companion", "무무"):
        raise AssertionError("cross-paragraph Companion attribution regressed")
    print("[PASS] cross-paragraph Companion attribution retained")

    beats = build_dialogue_beats(
        story_text="무무가 장부 모서리를 꼬리로 가리켰다.",
        guide_name="무무",
    )
    if not beats or any(beat.speaker_type != "narrator" for beat in beats):
        raise AssertionError("plain Companion action narration must remain Narrator")
    print("[PASS] plain Companion action remains Narrator")

    beats = build_dialogue_beats(
        story_text='나는 무무가 가리킨 장부를 펼쳤다. “이상하군.”',
        guide_name="무무",
    )
    quote = _beat_with(beats, "이상하군")
    if quote.speaker_type == "companion":
        raise AssertionError("Player-context guide mention was misclassified as Companion")
    print("[PASS] Player-context guide mention does not fabricate Companion")

    beats = build_dialogue_beats(
        story_text='장부 가장자리에 먹물이 번져 있었다. “이 기록은 이상하다.”',
        guide_name="무무",
    )
    quote = _beat_with(beats, "이 기록은 이상하다")
    if quote.speaker_type != "narrator":
        raise AssertionError("uncertain quote fallback regressed")
    print("[PASS] uncertain quote still falls back to Narrator")

    required = (
        "# DIALOGUE_SPEAKER_PORTRAIT_INTEGRITY_V1_20260904",
        "# DIALOGUE_SAME_PARAGRAPH_COMPANION_ACTION_V1_1_20260906",
        "def _same_paragraph_guide_action_focus(",
        "_same_paragraph_guide_action_focus(",
        "_previous_paragraph_guide_focus(",
    )
    for token in required:
        if token not in runtime:
            raise AssertionError("runtime token missing: " + token)

    print("[PASS] v1 portrait integrity + v1.1 same-paragraph rule coexist")
    print()
    print("[SECURITY / COST]")
    print("- No Gemini API request was made.")
    print("- No DB query/write was made.")
    print("- Existing Story text / Chapter rows were not modified.")
    print()
    print("[PASS] Dialogue Same-Paragraph Companion Action v1.1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

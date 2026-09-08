from __future__ import annotations

import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.dialogue_runtime_service import build_dialogue_beats


def _find_quote_beat(beats, text_fragment: str):
    for beat in beats:
        if text_fragment in beat.text:
            return beat
    raise AssertionError(
        f"quote beat not found for fragment: {text_fragment!r}"
    )


def main() -> int:
    paths = {
        "runtime": PROJECT_ROOT / "services" / "dialogue_runtime_service.py",
        "experience": PROJECT_ROOT / "components" / "dialogue_story_experience.py",
        "scene": PROJECT_ROOT / "components" / "dialogue_scene.py",
    }

    sources = {}
    for name, path in paths.items():
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        sources[name] = source

    print("=" * 78)
    print("Story Scene Navigation & Speaker Integrity v1.2 - QA")
    print("=" * 78)

    story = (
        '이투가 살짝 꼬리를 세우며 말했다. '
        '“좋아, 이 기단 표면의 문양부터 보자.”'
    )
    beats = build_dialogue_beats(
        story_text=story,
        guide_name="이투",
    )
    quote = _find_quote_beat(
        beats,
        "이 기단 표면의 문양부터 보자",
    )
    if quote.speaker_type != "companion":
        raise AssertionError(
            f"guide quote misclassified: {quote}"
        )
    if quote.speaker_name != "이투":
        raise AssertionError(
            f"guide name lost: {quote}"
        )
    print("[PASS] guide-attributed quote renders as companion")

    contaminated_story = (
        '이투가 말했다. '
        '“빛을 받아들이던 자국부터 보자.” '
        '나는 기단을 살폈다.'
    )
    contaminated = build_dialogue_beats(
        story_text=contaminated_story,
        guide_name="이투",
    )
    quote = _find_quote_beat(
        contaminated,
        "빛을 받아들이던 자국부터 보자",
    )
    if quote.speaker_type != "companion":
        raise AssertionError(
            "player pronoun in neighboring narration contaminated "
            f"companion attribution: {quote}"
        )
    print("[PASS] neighboring player-like text cannot steal companion attribution")

    legacy_player_story = '나는 말했다. “가자.”'
    legacy = build_dialogue_beats(
        story_text=legacy_player_story,
        guide_name="이투",
    )
    if any(beat.speaker_type == "player" for beat in legacy):
        raise AssertionError(
            "Chapter Story runtime inferred a player speaker from raw Story text"
        )
    print("[PASS] Chapter Story runtime never infers Player portrait/speaker")

    experience = sources["experience"]
    required_nav_tokens = (
        '"← 이전"',
        '"다음 →"',
        "dialogue_runtime_v1_prev_",
        "dialogue_runtime_v1_next_",
        "disabled=(current_index <= 0)",
    )
    for token in required_nav_tokens:
        if token not in experience:
            raise AssertionError(
                "manual navigation token missing: " + token
            )

    if "clicked = st.button(" in experience:
        raise AssertionError(
            "legacy below-fold next button still exists"
        )
    print("[PASS] manual previous/next controls are always in the top control row")

    scene = sources["scene"]
    for token in (
        'scene_kicker = "STORY SCENE"',
        'scene_kicker = style["scene_label"]',
        'scene_kicker = "PLAYER CHOICE"',
        'scene_kicker = "CHARACTER DIALOGUE"',
    ):
        if token not in scene:
            raise AssertionError(
                "role-aware scene kicker missing: " + token
            )
    print("[PASS] Scene kicker follows actual speaker role")

    runtime = sources["runtime"]
    if '_PLAYER_HINT_PATTERN = re.compile(' in runtime:
        raise AssertionError(
            "legacy Player inference pattern still present in dialogue runtime"
        )
    if 'return "player", "나"' in runtime:
        raise AssertionError(
            "Chapter Story runtime still returns inferred Player speaker"
        )
    print("[PASS] legacy raw-text Player inference removed")

    print()
    print("[SCOPE]")
    print("- Fixes Dialogue Story Runtime presentation only.")
    print("- Player dialogue remains available in explicit choice/quiz interaction components.")
    print("- Existing Story text and DB rows are not rewritten.")
    print("- Story generation prompt and Story Dialogue Integrity Gate are unchanged.")
    print("- Curriculum / Semantic Contract / Question systems are unchanged.")
    print()
    print("[SECURITY / COST]")
    print("- QA makes no Gemini API request.")
    print("- QA makes no DB query/write.")
    print()
    print("[PASS] Story Scene Navigation & Speaker Integrity v1.2 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

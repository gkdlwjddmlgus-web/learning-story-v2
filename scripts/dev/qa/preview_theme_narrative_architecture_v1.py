from __future__ import annotations

import ast
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.theme_narrative_service import (
    THEME_NARRATIVE_PROFILES,
    build_theme_narrative_planner_rules,
    build_theme_narrative_writer_rules,
)


THEMES = ("동화", "판타지", "SF", "무협", "미스터리")


def main() -> int:
    story_path = PROJECT_ROOT / "services" / "story_service.py"
    story = story_path.read_text(encoding="utf-8")
    ast.parse(story, filename=str(story_path))

    print("=" * 78)
    print("Theme Narrative Architecture v1 - Config/Source QA")
    print("=" * 78)

    for theme in THEMES:
        profile = THEME_NARRATIVE_PROFILES[theme]
        archetypes = profile["narrative_archetypes"]

        if len(archetypes) < 8:
            raise AssertionError(
                f"{theme}: narrative archetype pool too small"
            )

        planner = build_theme_narrative_planner_rules(
            theme=theme,
            recent_interaction_modes=["sample_mode"],
        )
        writer = build_theme_narrative_writer_rules(
            theme=theme,
            chapter_outline={"interaction_mode": "sample_mode"},
            opening_choice=None,
        )

        if "Narrative Archetype" not in planner:
            raise AssertionError(f"{theme}: planner rules missing")
        if "Theme Narrative Director" not in writer:
            raise AssertionError(f"{theme}: writer rules missing")

        print(
            f"[PASS] {theme:<5} | "
            f"core={profile['core_experience']} | "
            f"archetypes={len(archetypes)}"
        )

    required_story_markers = (
        "# THEME_NARRATIVE_ARCHITECTURE_V1_20260904",
        "build_theme_narrative_planner_rules",
        "build_theme_narrative_writer_rules",
        "theme_narrative_planner_rules",
        "theme_narrative_writer_rules",
        "story_outline_v6_theme_narrative_architecture",
        "story_chapter_lazy_v14_theme_narrative_architecture",
        "[Story ↔ Question Reasoning 경계]",
        "[관찰 endpoint 고정]",
        "[단계 중립 표현]",
        "# DAY6_STORY_DIALOGUE_INTEGRITY_GATE_V1",
        "# DAY6_STORY_DIALOGUE_COHERENCE_V1",
        "# DAY6_CHARACTER_VOICE_STORY_DIALOGUE_PROMPT_V1",
    )
    for marker in required_story_markers:
        if marker not in story:
            raise AssertionError(
                "story regression/source marker missing: "
                + marker
            )

    forbidden_forced_defaults = (
        "이상 현상과 조사 필요성을 드러낸다",
        "로그·기록·조건을 조사하는 행동으로 끝낸다",
        "Story는 다음 조사 행동과 열린 질문을 남긴다",
        "Story 본문은 사건의 상황, 관찰 가능한 이상, 조사 동기와 다음 조사 행동까지만 제공한다",
        "미스터리의 긴장과 학습자의 판단 여지를 동시에 남긴다",
    )
    for phrase in forbidden_forced_defaults:
        if phrase in story:
            raise AssertionError(
                "old investigation-biased adapter phrase remains: "
                + phrase
            )

    print()
    print("[PASS] Story prompt versions")
    print("[PASS] Theme Narrative Planner/Writer injection")
    print("[PASS] Day4 reasoning/anchor/stage-neutral guards retained")
    print("[PASS] Day6 Dialogue Integrity/Character Voice markers retained")
    print("[PASS] investigation-default adapter/reasoning phrases removed")
    print("[PASS] stage-neutral guard is conditional, not a default plot generator")
    print()
    print("[SECURITY / COST]")
    print("- No Gemini API request was made.")
    print("- No DB query/write was made.")
    print("- Existing saved Chapters/Questions were not modified.")
    print()
    print("Theme Narrative Architecture v1 QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

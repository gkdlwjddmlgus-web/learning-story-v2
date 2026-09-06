from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import services.story_service as story_service
from services.character_voice_service import build_story_dialogue_distribution_rules


def main() -> int:
    story_path = PROJECT_ROOT / "services" / "story_service.py"
    voice_path = PROJECT_ROOT / "services" / "character_voice_service.py"

    story = story_path.read_text(encoding="utf-8")
    voice = voice_path.read_text(encoding="utf-8")
    ast.parse(story, filename=str(story_path))
    ast.parse(voice, filename=str(voice_path))

    print("=" * 78)
    print("Story Agency & Continuity Gate v1.2 - QA")
    print("=" * 78)

    check = story_service._story_dialogue_integrity_issues

    allowed = (
        "루루가 귀를 세우며 물었다. “저 문 너머로 가볼까?” "
        "바람이 불자 오래된 문틈에서 푸른 빛이 새어 나왔다."
    )
    if check(allowed, guide_name="루루"):
        raise AssertionError("NPC-only dialogue was rejected")
    print("[PASS] NPC/Companion dialogue without forced Player reply")

    bad_speech = (
        "루루가 물었다. “어디부터 볼까?” "
        "내가 기록표를 보며 말했다. “압력부터 확인해보자.”"
    )
    issues = check(bad_speech, guide_name="루루")
    if not any("player_speech" in item for item in issues):
        raise AssertionError("fabricated Player speech was not blocked")
    print("[PASS] fabricated Player speech blocked")

    bad_action = (
        "우리는 측정 기록지를 펼쳐 압력값을 비교했습니다."
    )
    issues = check(bad_action, guide_name="루루")
    if not any("player_action" in item for item in issues):
        raise AssertionError("fabricated Player action was not blocked")
    print("[PASS] fabricated first-person Player action blocked")

    neutral_choice_result = (
        "선택한 방향의 결과, 닫혀 있던 통로가 열리고 "
        "안쪽에서 낯선 빛이 새어 나왔다."
    )
    if check(neutral_choice_result, guide_name="루루"):
        raise AssertionError("neutral choice consequence was rejected")
    print("[PASS] neutral Story Choice consequence allowed")

    rules = build_story_dialogue_distribution_rules(
        theme="판타지",
        guide_name="루루",
    )
    for token in (
        "Player의 직접 발화는 AI가 만들지 않는다",
        "Story Choice",
        "Agency 보존",
    ):
        if token not in rules:
            raise AssertionError("voice rule missing: " + token)
    print("[PASS] Character Voice no longer forces Player dialogue")

    required = (
        "# THEME_NARRATIVE_ARCHITECTURE_V1_20260904",
        "# STORY_AGENCY_CONTINUITY_GATE_V1_2_20260904",
        "story_chapter_lazy_v15_agency_continuity_gate",
        "[Player Agency & Continuity Gate v1.2]",
        "Player는 AI가 조종하는 NPC가 아니다.",
        "이전 사건을 요약해서 다시 설명하지 않는다",
        "# DAY6_STORY_DIALOGUE_INTEGRITY_GATE_V1",
        "[Story ↔ Question Reasoning 경계]",
    )
    for token in required:
        if token not in story:
            raise AssertionError("story regression marker missing: " + token)

    forbidden = (
        "Player의 직접 발화를 Chapter 전체에 최소 1회 포함한다.",
        "가능하면 Companion의 직접 발화를 최소 2회, Player의 직접 발화를 최소 1회 포함한다.",
        "- Player 대사는 가까운 문맥에 '내가 말했다/물었다/대답했다'처럼 화자를 명확히 둔다.",
    )
    combined = story + "\n" + voice
    for token in forbidden:
        if token in combined:
            raise AssertionError("old forced Player-dialogue rule remains: " + token)

    print("[PASS] Theme Narrative Architecture retained")
    print("[PASS] Reasoning Boundary retained")
    print("[PASS] old forced Player-dialogue rules removed")
    print()
    print("[SECURITY / COST]")
    print("- No Gemini API request was made.")
    print("- No DB query/write was made.")
    print("- Existing saved Chapters/Questions were not modified.")
    print()
    print("Story Agency & Continuity Gate v1.2 QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

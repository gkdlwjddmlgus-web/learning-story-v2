from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.character_voice_service import build_companion_voice_rules
from services.experience_profile_service import get_learner_level_profile, get_reasoning_profile
from services.question_service import (
    QuestionDifficultyQualityError,
    REASONING_RULES,
    _is_obvious_throwaway_choice,
    _validate_choice_difficulty_quality,
)


def main() -> int:
    for rel in (
        Path("services/question_service.py"),
        Path("services/experience_profile_service.py"),
        Path("services/character_voice_service.py"),
    ):
        path = PROJECT_ROOT / rel
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    print("=" * 78)
    print("Question Difficulty & Companion Voice Quality Gate v1 - QA")
    print("=" * 78)

    intermediate = REASONING_RULES["intermediate"]
    for token in ("Evidence 사실/조건 2개 이상", "trade-off", "모두 삭제/무조건 0/그대로 방치"):
        if token not in intermediate:
            raise AssertionError("intermediate reasoning rule missing: " + token)
    print("[PASS] intermediate reasoning rule strengthened")

    level = get_learner_level_profile("중급")
    if "근거/조건 2개 이상" not in level["question_rule"]:
        raise AssertionError("중급 learner profile was not strengthened")
    print("[PASS] learner-level 중급 profile strengthened")

    reasoning = get_reasoning_profile("intermediate")
    if "독립된 근거 2개 이상" not in reasoning["rule"]:
        raise AssertionError("intermediate reasoning profile was not strengthened")
    print("[PASS] centralized intermediate reasoning profile strengthened")

    for text in (
        "수송 기록 전체 행을 장부에서 즉시 삭제한다.",
        "모든 결측치를 무조건 0으로 통일한다.",
        "검증 없이 그대로 최종 분석에 반영한다.",
        "값을 임의로 최대 수치로 변경한다.",
    ):
        if not _is_obvious_throwaway_choice(text):
            raise AssertionError("throwaway pattern not detected: " + text)
    print("[PASS] obvious throwaway distractor patterns detected")

    try:
        _validate_choice_difficulty_quality(
            choices=[
                "원본 기록과 주변 흐름을 대조한 뒤 보정 여부를 판단한다.",
                "전체 행을 즉시 삭제한다.",
                "모든 값을 무조건 0으로 통일한다.",
                "관련 시점의 다른 장부와 비교해 원인을 좁힌다.",
            ],
            correct_index=0,
            requested_difficulty="intermediate",
            index=1,
        )
    except QuestionDifficultyQualityError:
        pass
    else:
        raise AssertionError("intermediate quality gate did not reject 2 throwaways")
    print("[PASS] intermediate gate rejects >=2 throwaway distractors")

    _validate_choice_difficulty_quality(
        choices=[
            "원본 기록과 주변 흐름을 대조한 뒤 보정 여부를 판단한다.",
            "전체 행을 즉시 삭제한다.",
            "주변 시점의 중앙값과 보간값을 비교한다.",
            "원본 서첩을 재확인한 뒤 결측 원인을 분류한다.",
        ],
        correct_index=0,
        requested_difficulty="intermediate",
        index=2,
    )
    print("[PASS] intermediate gate allows one obvious distractor")

    _validate_choice_difficulty_quality(
        choices=[
            "원본 기록과 주변 흐름을 대조한다.",
            "전체 행을 즉시 삭제한다.",
            "모든 값을 무조건 0으로 통일한다.",
            "검증 없이 그대로 반영한다.",
        ],
        correct_index=0,
        requested_difficulty="basic",
        index=3,
    )
    print("[PASS] basic difficulty is not blocked by intermediate gate")

    wuxia = build_companion_voice_rules(theme="무협", guide_name="무무", scope="learning")
    for token in (
        "현대 분석 보고서를 그대로 낭독하지 않는다",
        "옮겨 적는 길목에서 빠졌는지",
        "뒤 판단까지 흐려질지",
    ):
        if token not in wuxia:
            raise AssertionError("wuxia learning voice rule missing: " + token)
    print("[PASS] wuxia learning companion register strengthened")

    story_voice = build_companion_voice_rules(theme="무협", guide_name="무무", scope="story")
    if "현대 분석 보고서를 그대로 낭독하지 않는다" in story_voice:
        raise AssertionError("learning-only register leaked into story scope")
    print("[PASS] learning-only voice rule does not leak into story scope")

    print()
    print("[SECURITY / COST]")
    print("- No Gemini API request was made.")
    print("- No DB query/write was made.")
    print("- Existing Question/Attempt/Mastery rows were not modified.")
    print()
    print("[PASS] Question Difficulty & Companion Voice Quality Gate v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

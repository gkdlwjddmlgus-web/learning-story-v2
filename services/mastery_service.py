from __future__ import annotations

from repositories.mastery_repository import (
    get_mastery_for_concept,
    get_mastery_profile,
    upsert_mastery,
)


DIFFICULTY_MULTIPLIER = {
    "intro": 0.80,
    "basic": 1.00,
    "intermediate": 1.12,
    "advanced": 1.25,
}

LEVEL_BASE_DIFFICULTY = {
    "입문": "intro",
    "초급": "basic",
    "중급": "intermediate",
    "고급": "advanced",
}


def _clamp(
    value: float,
    low: float = 0.05,
    high: float = 0.95,
) -> float:
    return max(
        low,
        min(high, value),
    )


def update_mastery_from_attempt(
    *,
    user_id: int,
    world_id: int,
    concept: str,
    is_correct: bool,
    difficulty: str | None,
) -> float:
    if not concept:
        return 0.5

    row = get_mastery_for_concept(
        user_id=user_id,
        world_id=world_id,
        concept=concept,
    )

    previous = (
        float(row[0])
        if row is not None
        else 0.5
    )

    multiplier = DIFFICULTY_MULTIPLIER.get(
        difficulty or "basic",
        1.0,
    )

    delta = (
        0.11 * multiplier
        if is_correct
        else -0.13 * multiplier
    )

    # 0/1 판정만 그대로 누적하기보다 기존 Mastery가 높을수록
    # 정답 상승폭은 조금 줄이고, 오답은 의미 있게 반영한다.
    if is_correct:
        delta *= max(
            0.45,
            1.0 - previous,
        )
    else:
        delta *= max(
            0.55,
            previous,
        )

    new_score = _clamp(
        previous + delta
    )

    review_needed = (
        not is_correct
        or new_score < 0.60
    )

    upsert_mastery(
        user_id=user_id,
        world_id=world_id,
        concept=concept,
        mastery_score=new_score,
        is_correct=is_correct,
        review_needed=review_needed,
    )

    return new_score


def get_mastery_summary(
    user_id: int,
    world_id: int,
) -> dict:
    rows = get_mastery_profile(
        user_id=user_id,
        world_id=world_id,
    )

    weak = [
        item["concept"]
        for item in rows
        if item["mastery_score"] < 0.45
    ]

    review = [
        item["concept"]
        for item in rows
        if (
            0.45
            <= item["mastery_score"]
            < 0.70
        )
        or item["review_needed"]
    ]

    strong = [
        item["concept"]
        for item in rows
        if item["mastery_score"] >= 0.70
    ]

    average = (
        sum(
            item["mastery_score"]
            for item in rows
        )
        / len(rows)
        if rows
        else None
    )

    return {
        "items": rows,
        "weak": list(dict.fromkeys(weak)),
        "review": list(dict.fromkeys(review)),
        "strong": list(dict.fromkeys(strong)),
        "average": average,
    }


def choose_requested_difficulty(
    *,
    learner_level: str,
    user_id: int,
    world_id: int,
    target_concepts: list[str],
) -> str:
    base = LEVEL_BASE_DIFFICULTY.get(
        learner_level,
        "basic",
    )

    profile = get_mastery_profile(
        user_id=user_id,
        world_id=world_id,
    )

    by_concept = {
        item["concept"]: item
        for item in profile
    }

    scores = [
        by_concept[name]["mastery_score"]
        for name in target_concepts
        if name in by_concept
    ]

    if not scores:
        return base

    average = sum(scores) / len(scores)

    if average < 0.45:
        return "intro"

    if average < 0.65:
        return "basic"

    if average >= 0.82:
        if base in {
            "intermediate",
            "advanced",
        }:
            return "advanced"

        return "intermediate"

    return base

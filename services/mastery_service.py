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

MASTERY_WEAK_THRESHOLD = 0.45
MASTERY_STRONG_THRESHOLD = 0.70
MASTERY_PROMOTION_THRESHOLD = 0.82

ADAPTIVE_SUPPORT_PROFILES = {
    "reinforce": {
        "label": "취약 Concept 복습 강화",
        "rule": (
            "필요한 핵심 개념을 쉬운 말로 짧게 다시 연결한 뒤, "
            "같은 정의를 반복하지 말고 새로운 Story 자료에서 다시 적용하게 한다. "
            "자료 이해를 돕되 정답을 먼저 노출하지 않는다."
        ),
    },
    "review": {
        "label": "복습 연결",
        "rule": (
            "긴 재설명 대신 이전에 배운 핵심을 떠올릴 수 있는 짧은 회상 단서를 제공하고, "
            "새 Concept 또는 새 상황과 연결해 적용하게 한다."
        ),
    },
    "challenge": {
        "label": "도전 확대",
        "rule": (
            "이미 안정적으로 익힌 Concept의 기초 정의 반복은 줄이고, "
            "자료 비교와 독립적인 판단 비중을 조금 높인다. "
            "단, 사용자가 선택한 선행지식 수준 자체를 높여 가정하지 않는다."
        ),
    },
    "standard": {
        "label": "기본 지원",
        "rule": "사용자가 선택한 학습 수준의 기본 설명량과 사고 난이도를 유지한다.",
    },
}


def _clamp(value: float, low: float = 0.05, high: float = 0.95) -> float:
    return max(low, min(high, value))


def classify_mastery_item(item: dict) -> str:
    """weak/review/strong을 상호 배타적으로 판정한다."""
    score = float(item.get("mastery_score", 0.5))
    review_needed = bool(item.get("review_needed"))
    if score < MASTERY_WEAK_THRESHOLD:
        return "weak"
    if score < MASTERY_STRONG_THRESHOLD or review_needed:
        return "review"
    return "strong"


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

    row = get_mastery_for_concept(user_id=user_id, world_id=world_id, concept=concept)
    previous = float(row[0]) if row is not None else 0.5
    multiplier = DIFFICULTY_MULTIPLIER.get(difficulty or "basic", 1.0)
    delta = 0.11 * multiplier if is_correct else -0.13 * multiplier

    if is_correct:
        delta *= max(0.45, 1.0 - previous)
    else:
        delta *= max(0.55, previous)

    new_score = _clamp(previous + delta)
    review_needed = (not is_correct) or new_score < 0.60

    upsert_mastery(
        user_id=user_id,
        world_id=world_id,
        concept=concept,
        mastery_score=new_score,
        is_correct=is_correct,
        review_needed=review_needed,
    )
    return new_score


def get_mastery_summary(user_id: int, world_id: int) -> dict:
    rows = get_mastery_profile(user_id=user_id, world_id=world_id)
    grouped = {"weak": [], "review": [], "strong": []}
    for item in rows:
        grouped[classify_mastery_item(item)].append(item["concept"])
    average = (
        sum(item["mastery_score"] for item in rows) / len(rows)
        if rows else None
    )
    return {
        "items": rows,
        "weak": list(dict.fromkeys(grouped["weak"])),
        "review": list(dict.fromkeys(grouped["review"])),
        "strong": list(dict.fromkeys(grouped["strong"])),
        "average": average,
    }


def _target_mastery_items(
    *, user_id: int, world_id: int, target_concepts: list[str]
) -> tuple[list[str], dict[str, dict]]:
    targets = [
        str(name).strip()
        for name in dict.fromkeys(target_concepts or [])
        if str(name).strip()
    ]
    profile = get_mastery_profile(user_id=user_id, world_id=world_id)
    return targets, {item["concept"]: item for item in profile}


def get_adaptive_support_profile(
    *, user_id: int, world_id: int, target_concepts: list[str]
) -> dict:
    """사고 난이도와 별개로 설명/발판의 강도를 결정한다."""
    targets, by_concept = _target_mastery_items(
        user_id=user_id, world_id=world_id, target_concepts=target_concepts
    )
    seen = [by_concept[name] for name in targets if name in by_concept]
    unseen = [name for name in targets if name not in by_concept]
    statuses = {item["concept"]: classify_mastery_item(item) for item in seen}

    if any(status == "weak" for status in statuses.values()):
        mode = "reinforce"
    elif any(status == "review" for status in statuses.values()):
        mode = "review"
    elif (
        targets and not unseen and seen
        and all(
            float(item["mastery_score"]) >= MASTERY_PROMOTION_THRESHOLD
            and not bool(item.get("review_needed"))
            for item in seen
        )
    ):
        mode = "challenge"
    else:
        mode = "standard"

    base = ADAPTIVE_SUPPORT_PROFILES[mode]
    return {
        "mode": mode,
        "label": base["label"],
        "rule": base["rule"],
        "target_statuses": statuses,
        "unseen_concepts": unseen,
    }


def choose_requested_difficulty(
    *,
    learner_level: str,
    user_id: int,
    world_id: int,
    target_concepts: list[str],
) -> str:
    base = LEVEL_BASE_DIFFICULTY.get(learner_level, "basic")
    targets, by_concept = _target_mastery_items(
        user_id=user_id, world_id=world_id, target_concepts=target_concepts
    )
    if not targets:
        return base

    seen = [by_concept[name] for name in targets if name in by_concept]
    unseen_exists = any(name not in by_concept for name in targets)
    order = ["intro", "basic", "intermediate", "advanced"]
    base_index = order.index(base)

    # 하나라도 weak이면 현재 수준보다 최대 한 단계 낮춘다.
    if any(float(item["mastery_score"]) < MASTERY_WEAK_THRESHOLD for item in seen):
        return order[max(0, base_index - 1)]

    # 미학습 Concept가 하나라도 있으면 승급하지 않는다.
    if unseen_exists:
        return base

    # 모든 target을 안정적으로 익힌 경우에만 최대 한 단계 승급한다.
    if seen and all(
        float(item["mastery_score"]) >= MASTERY_PROMOTION_THRESHOLD
        and not bool(item.get("review_needed"))
        for item in seen
    ):
        return order[min(len(order) - 1, base_index + 1)]

    return base

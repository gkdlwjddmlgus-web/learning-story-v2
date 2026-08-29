from repositories.attempt_repository import (
    get_concept_stats,
    get_concept_stats_for_chapter,
)
from repositories.mastery_repository import get_mastery_profile
from services.mastery_service import classify_mastery_item


def _accuracy_from_mastery(item: dict) -> float:
    attempts = int(item.get("attempts") or 0)
    correct = int(item.get("correct_count") or 0)
    return (correct / attempts) if attempts else 0.0


def classify_recent_stats(
    stats: list[dict],
    mastery_by_concept: dict[str, dict] | None = None,
) -> list[dict]:
    """최근 Chapter 결과와 장기 Mastery를 함께 사용한다."""
    mastery_by_concept = mastery_by_concept or {}
    result = []
    for stat in stats:
        concept = stat["concept"]
        accuracy = float(stat["accuracy"])
        mastery_item = mastery_by_concept.get(concept)
        mastery_status = (
            classify_mastery_item(mastery_item)
            if mastery_item is not None else None
        )

        if accuracy == 0 or mastery_status == "weak":
            status = "weak"
        elif mastery_status == "review" or accuracy < 1.0:
            status = "review"
        elif mastery_status == "strong":
            status = "strong"
        else:
            status = "strong" if accuracy == 1.0 else "review"

        result.append({
            **stat,
            "mastery_score": (
                float(mastery_item["mastery_score"])
                if mastery_item is not None else None
            ),
            "status": status,
        })
    return result


def classify_global_stats(stats: list[dict]) -> list[dict]:
    """Mastery row가 없는 legacy 상황을 위한 accuracy fallback."""
    result = []
    for stat in stats:
        attempts = stat["attempts"]
        accuracy = stat["accuracy"]
        if attempts >= 2 and accuracy <= 0.5:
            status = "weak"
        elif accuracy < 1.0:
            status = "review"
        else:
            status = "strong"
        result.append({**stat, "status": status})
    return result


def classify_stats(stats: list[dict]) -> list[dict]:
    return classify_global_stats(stats)


def _global_from_mastery(rows: list[dict]) -> list[dict]:
    return [
        {
            "concept": item["concept"],
            "attempts": item["attempts"],
            "correct_count": item["correct_count"],
            "accuracy": _accuracy_from_mastery(item),
            "mastery_score": item["mastery_score"],
            "review_needed": item["review_needed"],
            "status": classify_mastery_item(item),
        }
        for item in rows
    ]


def _names_by_status(classified: list[dict], status: str) -> list[str]:
    return [item["concept"] for item in classified if item["status"] == status]


def build_personalization_profile(
    user_id: int,
    world_id: int,
    chapter_id: int,
) -> dict:
    """Mastery를 장기 개인화의 Single Source of Truth로 사용한다."""
    recent_stats = get_concept_stats_for_chapter(
        user_id=user_id, world_id=world_id, chapter_id=chapter_id
    )
    mastery_rows = get_mastery_profile(user_id=user_id, world_id=world_id)
    mastery_by_concept = {item["concept"]: item for item in mastery_rows}

    recent = classify_recent_stats(
        recent_stats,
        mastery_by_concept=mastery_by_concept,
    )
    global_ = _global_from_mastery(mastery_rows)

    if not global_:
        global_ = classify_global_stats(
            get_concept_stats(user_id=user_id, world_id=world_id)
        )

    return {
        "recent": {
            "weak": _names_by_status(recent, "weak"),
            "review": _names_by_status(recent, "review"),
            "strong": _names_by_status(recent, "strong"),
        },
        "global": {
            "weak": _names_by_status(global_, "weak"),
            "review": _names_by_status(global_, "review"),
            "strong": _names_by_status(global_, "strong"),
        },
        "recent_details": recent,
        "global_details": global_,
    }


def get_latest_chapter_personalization_profile(
    user_id: int,
    world_id: int,
    chapter_id: int,
) -> dict:
    return build_personalization_profile(
        user_id=user_id,
        world_id=world_id,
        chapter_id=chapter_id,
    )

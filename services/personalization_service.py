from repositories.attempt_repository import (
    get_concept_stats,
    get_concept_stats_for_chapter,
)


def classify_recent_stats(
    stats: list[dict],
) -> list[dict]:
    """
    방금 끝낸 Chapter 결과를 판정한다.

    최근 결과는 즉시 다음 Chapter에 반영되어야 하므로
    누적 프로필보다 민감하게 판정한다.

    - 정답률 0%      -> weak
    - 0% 초과 100% 미만 -> review
    - 정답률 100%    -> strong
    """
    result = []

    for stat in stats:
        accuracy = stat["accuracy"]

        if accuracy == 0:
            status = "weak"
        elif accuracy < 1.0:
            status = "review"
        else:
            status = "strong"

        result.append(
            {
                **stat,
                "status": status,
            }
        )

    return result


def classify_global_stats(
    stats: list[dict],
) -> list[dict]:
    """
    월드 전체 누적 결과를 판정한다.

    누적 프로필은 한 번의 실수에 지나치게 흔들리지 않도록
    기존 MVP 기준을 유지한다.

    - 2회 이상 + 정답률 50% 이하 -> weak
    - 정답률 100% 미만          -> review
    - 정답률 100%               -> strong
    """
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

        result.append(
            {
                **stat,
                "status": status,
            }
        )

    return result


def classify_stats(
    stats: list[dict],
) -> list[dict]:
    """
    기존 코드 호환용.
    별도 구분이 없는 경우에는 누적 프로필 판정 규칙을 사용한다.
    """
    return classify_global_stats(stats)


def _names_by_status(
    classified: list[dict],
    status: str,
) -> list[str]:
    return [
        item["concept"]
        for item in classified
        if item["status"] == status
    ]


def build_personalization_profile(
    user_id: int,
    world_id: int,
    chapter_id: int,
) -> dict:
    """
    다음 Chapter 생성용 개인화 프로필.

    recent:
        방금 끝낸 Chapter 결과.
        최근 오답을 빠르게 반영하기 위해 민감한 기준을 사용한다.

    global:
        현재 월드 전체 누적 결과.
        장기적인 강점/약점을 보기 위해 보수적인 기준을 사용한다.
    """
    recent_stats = get_concept_stats_for_chapter(
        user_id=user_id,
        world_id=world_id,
        chapter_id=chapter_id,
    )

    global_stats = get_concept_stats(
        user_id=user_id,
        world_id=world_id,
    )

    recent = classify_recent_stats(
        recent_stats
    )

    global_ = classify_global_stats(
        global_stats
    )

    return {
        "recent": {
            "weak": _names_by_status(
                recent,
                "weak",
            ),
            "review": _names_by_status(
                recent,
                "review",
            ),
            "strong": _names_by_status(
                recent,
                "strong",
            ),
        },
        "global": {
            "weak": _names_by_status(
                global_,
                "weak",
            ),
            "review": _names_by_status(
                global_,
                "review",
            ),
            "strong": _names_by_status(
                global_,
                "strong",
            ),
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

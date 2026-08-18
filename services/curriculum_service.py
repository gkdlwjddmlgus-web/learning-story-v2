from __future__ import annotations

from typing import Any


def _sequence(
    curriculum: dict[str, Any] | None,
) -> list[dict]:
    if not curriculum:
        return []

    result = curriculum.get(
        "concept_sequence",
        [],
    )

    return sorted(
        [
            item
            for item in result
            if item.get("name")
        ],
        key=lambda item: item.get(
            "order",
            999,
        ),
    )


def plan_chapter_concepts(
    *,
    curriculum: dict[str, Any] | None,
    chapter_number: int,
    target_chapter_count: int,
    weak_concepts: list[str] | None = None,
    review_concepts: list[str] | None = None,
) -> list[str]:
    """
    Curriculum을 Story/Question이 함께 바라보게 하는 단순한 V1 planner.

    - 전체 Chapter 진행률에 따라 Curriculum의 기본 Concept을 선택
    - 최근 weak/review Concept은 다음 Chapter에 재노출
    - 한 Chapter에 1~2개 Concept만 집중
    """
    sequence = _sequence(
        curriculum
    )

    if not sequence:
        return []

    weak_concepts = (
        weak_concepts
        or []
    )
    review_concepts = (
        review_concepts
        or []
    )

    if target_chapter_count <= 1:
        progress = 0.0
    else:
        progress = (
            chapter_number - 1
        ) / (
            target_chapter_count - 1
        )

    base_index = round(
        progress
        * (
            len(sequence) - 1
        )
    )

    base_index = max(
        0,
        min(
            len(sequence) - 1,
            base_index,
        ),
    )

    base = sequence[
        base_index
    ]["name"]

    planned = []

    # 학습 결과는 처벌이 아니라 재노출 입력값이다.
    for concept in (
        list(weak_concepts)
        + list(review_concepts)
    ):
        if (
            concept
            and concept not in planned
        ):
            planned.append(
                concept
            )
            break

    if base not in planned:
        planned.append(
            base
        )

    # 다음 순서 Concept을 일부 Chapter에서 함께 연결한다.
    if (
        len(planned) < 2
        and base_index + 1
        < len(sequence)
        and chapter_number % 2 == 0
    ):
        planned.append(
            sequence[
                base_index + 1
            ]["name"]
        )

    return planned[:2]


def plan_story_block_concepts(
    *,
    curriculum: dict[str, Any] | None,
    start_chapter: int,
    block_size: int,
    target_chapter_count: int,
    weak_concepts: list[str] | None = None,
    review_concepts: list[str] | None = None,
) -> dict[int, list[str]]:
    result = {}

    for chapter_number in range(
        start_chapter,
        min(
            target_chapter_count,
            start_chapter
            + block_size
            - 1,
        )
        + 1,
    ):
        result[chapter_number] = (
            plan_chapter_concepts(
                curriculum=curriculum,
                chapter_number=(
                    chapter_number
                ),
                target_chapter_count=(
                    target_chapter_count
                ),
                # 취약 Concept은 Block 전체를 같은 내용으로 도배하지 않고
                # 첫 Chapter에 우선 재노출한다. 이후 Chapter는 Curriculum 진행을 따른다.
                weak_concepts=(
                    weak_concepts
                    if chapter_number == start_chapter
                    else []
                ),
                review_concepts=(
                    review_concepts
                    if chapter_number == start_chapter
                    else []
                ),
            )
        )

    return result

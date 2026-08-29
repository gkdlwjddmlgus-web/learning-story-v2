from __future__ import annotations

from typing import Any


def _sequence(curriculum: dict[str, Any] | None) -> list[dict]:
    if not curriculum:
        return []
    result = curriculum.get("concept_sequence", [])
    return sorted(
        [item for item in result if item.get("name")],
        key=lambda item: item.get("order", 999),
    )


def _dedupe_concepts(*groups: list[str] | None) -> list[str]:
    result: list[str] = []
    for group in groups:
        for concept in group or []:
            concept = str(concept or "").strip()
            if concept and concept not in result:
                result.append(concept)
    return result


def plan_chapter_concepts(
    *,
    curriculum: dict[str, Any] | None,
    chapter_number: int,
    target_chapter_count: int,
    weak_concepts: list[str] | None = None,
    review_concepts: list[str] | None = None,
) -> list[str]:
    sequence = _sequence(curriculum)
    if not sequence:
        return []

    weak_concepts = weak_concepts or []
    review_concepts = review_concepts or []
    progress = 0.0 if target_chapter_count <= 1 else (
        (chapter_number - 1) / (target_chapter_count - 1)
    )
    base_index = round(progress * (len(sequence) - 1))
    base_index = max(0, min(len(sequence) - 1, base_index))
    base = sequence[base_index]["name"]

    planned: list[str] = []
    for concept in _dedupe_concepts(weak_concepts, review_concepts):
        planned.append(concept)
        break

    if base not in planned:
        planned.append(base)

    if (
        len(planned) < 2
        and base_index + 1 < len(sequence)
        and chapter_number % 2 == 0
    ):
        planned.append(sequence[base_index + 1]["name"])

    return planned[:2]


def plan_story_block_concepts(
    *,
    curriculum: dict[str, Any] | None,
    start_chapter: int,
    block_size: int,
    target_chapter_count: int,
    weak_concepts: list[str] | None = None,
    review_concepts: list[str] | None = None,
    global_weak_concepts: list[str] | None = None,
    global_review_concepts: list[str] | None = None,
) -> dict[int, list[str]]:
    """새 Block 첫 Chapter에 recent weak -> global weak -> recent review -> global review 순으로 재노출한다."""
    prioritized_weak = _dedupe_concepts(weak_concepts, global_weak_concepts)
    prioritized_review = [
        concept
        for concept in _dedupe_concepts(review_concepts, global_review_concepts)
        if concept not in prioritized_weak
    ]

    result = {}
    for chapter_number in range(
        start_chapter,
        min(target_chapter_count, start_chapter + block_size - 1) + 1,
    ):
        result[chapter_number] = plan_chapter_concepts(
            curriculum=curriculum,
            chapter_number=chapter_number,
            target_chapter_count=target_chapter_count,
            weak_concepts=(prioritized_weak if chapter_number == start_chapter else []),
            review_concepts=(prioritized_review if chapter_number == start_chapter else []),
        )
    return result

from __future__ import annotations

from repositories.story_state_repository import (
    ensure_story_state,
    update_story_state,
)
from services.story_context_service import invalidate_runtime_story_context_all


def _dedupe(
    values: list,
) -> list:
    result = []

    for value in values:
        if value not in result:
            result.append(
                value
            )

    return result


def _merge_characters(
    current: list,
    updates: list,
) -> list:
    by_name = {}

    for item in current:
        if not isinstance(
            item,
            dict,
        ):
            continue

        name = item.get(
            "name"
        )

        if name:
            by_name[name] = dict(
                item
            )

    for item in updates:
        if not isinstance(
            item,
            dict,
        ):
            continue

        name = item.get(
            "name"
        )

        if not name:
            continue

        previous = by_name.get(
            name,
            {},
        )

        previous.update(
            {
                key: value
                for key, value
                in item.items()
                if value not in (
                    None,
                    "",
                )
            }
        )

        by_name[name] = previous

    return list(
        by_name.values()
    )


def initialize_companion_state(
    *,
    story_arc_id: int,
    guide_name: str,
) -> None:
    state = ensure_story_state(
        story_arc_id
    )

    characters = _merge_characters(
        state["characters"],
        [
            {
                "name": guide_name,
                "role": "동료 고양이",
                "relationship": (
                    "사용자가 직접 이름을 지어준 "
                    "첫 번째 동료"
                ),
                "status": "함께 여행 중",
                "note": (
                    "학습 분야의 전문가가 아니라 "
                    "관찰과 감정 반응을 담당한다."
                ),
            }
        ],
    )

    companion_state = dict(
        state["companion_state"]
        or {}
    )

    companion_state.update(
        {
            "name": guide_name,
            "relationship": (
                "사용자가 직접 이름을 지어줌"
            ),
            "role": (
                "Story와 학습 사이의 "
                "감정적 동료"
            ),
        }
    )

    update_story_state(
        story_arc_id,
        characters=characters,
        companion_state=(
            companion_state
        ),
    )
    invalidate_runtime_story_context_all()


def apply_state_update(
    *,
    story_arc_id: int,
    update: dict | None,
) -> None:
    if not update:
        return

    state = ensure_story_state(
        story_arc_id
    )

    current_facts = list(
        state["confirmed_facts"]
        or []
    )
    current_open = list(
        state["open_threads"]
        or []
    )
    current_resolved = list(
        state["resolved_events"]
        or []
    )

    add_facts = list(
        update.get(
            "confirmed_facts_add",
            [],
        )
        or []
    )
    add_open = list(
        update.get(
            "open_threads_add",
            [],
        )
        or []
    )
    resolved_threads = list(
        update.get(
            "resolved_threads",
            [],
        )
        or []
    )

    resolved_set = set(
        resolved_threads
    )

    new_open = [
        item
        for item in current_open
        if item not in resolved_set
    ]

    new_open.extend(
        add_open
    )

    new_resolved = (
        current_resolved
        + resolved_threads
    )

    characters = _merge_characters(
        state["characters"],
        update.get(
            "character_updates",
            [],
        )
        or [],
    )

    companion_state = dict(
        state["companion_state"]
        or {}
    )

    companion_update = (
        update.get(
            "companion_state",
            {},
        )
        or {}
    )

    companion_state.update(
        companion_update
    )

    latest_event_text = (
        update.get(
            "latest_event",
            ""
        )
        or ""
    )

    latest_event = (
        {
            "summary": (
                latest_event_text
            )
        }
        if latest_event_text
        else state["latest_event"]
    )

    update_story_state(
        story_arc_id,
        story_summary=(
            update.get(
                "story_summary"
            )
            or state[
                "story_summary"
            ]
        ),
        current_location=(
            update.get(
                "current_location"
            )
            or state[
                "current_location"
            ]
        ),
        characters=characters,
        companion_state=(
            companion_state
        ),
        confirmed_facts=_dedupe(
            current_facts
            + add_facts
        ),
        open_threads=_dedupe(
            new_open
        ),
        resolved_events=_dedupe(
            new_resolved
        ),
        latest_event=latest_event,
    )
    invalidate_runtime_story_context_all()

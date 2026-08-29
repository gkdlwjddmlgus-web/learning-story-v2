from __future__ import annotations

from repositories.chapter_repository import (
    create_chapter,
    get_chapter,
    mark_chapter_state_applied,
)
from repositories.story_block_repository import (
    get_outline_chapter,
    get_story_block_plan,
    upsert_story_block_plan,
)
from repositories.story_choice_repository import get_latest_choice_for_arc
from repositories.story_state_repository import update_story_state
from repositories.story_repository import (
    complete_story_arc,
    get_active_story_arc,
    update_story_arc_phase,
)
from services.ai_client import DEFAULT_MODEL
from services.curriculum_service import plan_story_block_concepts
from services.dev_config import generation_provider
from services.foundation_service import ensure_world_foundation
from services.story_context_service import ensure_story_context, get_story_context
from services.story_memory_service import apply_state_update, initialize_companion_state
from services.story_service import (
    BLOCK_SIZE,
    CHAPTER_PROMPT_VERSION,
    OUTLINE_PROMPT_VERSION,
    enrich_chapter_outline_interaction,
    generate_story_block_outline,
    generate_story_chapter,
    get_story_block_end_chapter,
    get_story_block_start_chapter,
    get_story_phase,
)


def get_story_runtime(world_id: int) -> dict | None:
    return get_story_context(world_id)


def _profiles_or_empty(personalization: dict | None) -> tuple[dict, dict]:
    empty = {"weak": [], "review": [], "strong": []}
    if not personalization:
        return empty, empty
    return personalization.get("recent", empty), personalization.get("global", empty)


def _prepare_context(
    *,
    user,
    world,
    chapter_number: int,
    personalization: dict | None,
) -> dict:
    ensure_story_context(world[0], link_existing_chapters=True)
    foundation = ensure_world_foundation(user_id=user["user_id"], world=world)
    context = ensure_story_context(world[0])
    guide_name = world[9] if len(world) > 9 else None
    if guide_name:
        initialize_companion_state(
            story_arc_id=context["arc"]["id"],
            guide_name=guide_name,
        )

    # legacy Story Memory fallback
    state = get_story_context(world[0])["state"]
    if chapter_number > 1 and not state.get("story_summary"):
        previous = get_chapter(
            world_id=world[0],
            chapter_number=chapter_number - 1,
        )
        if previous is not None:
            update_story_state(
                context["arc"]["id"],
                story_summary=(
                    f"Chapter {previous[2]} · {previous[3]}\n{previous[4]}"
                ),
                latest_event={
                    "summary": f"Chapter {previous[2]}까지 진행됨"
                },
            )
            state = get_story_context(world[0])["state"]

    recent, global_profile = _profiles_or_empty(personalization)
    return {
        "foundation": foundation,
        "context": context,
        "guide_name": guide_name,
        "state": state,
        "recent": recent,
        "global": global_profile,
    }


def _collect_recent_interaction_modes(
    *,
    story_arc_id: int,
    current_block_no: int,
    theme: str,
    target_chapter_count: int,
    max_modes: int = 6,
) -> list[str]:
    """이전 Block의 interaction mode를 모아 다음 Planner의 반복을 줄인다."""
    modes: list[str] = []

    for block_no in range(max(1, current_block_no - 2), current_block_no):
        plan = get_story_block_plan(story_arc_id, block_no)
        if not plan or not plan.get("outline"):
            continue

        for raw in plan["outline"].get("chapters", []):
            try:
                chapter_number = int(raw.get("chapter_number", -1))
            except (TypeError, ValueError):
                continue
            if chapter_number < 1:
                continue

            enriched = enrich_chapter_outline_interaction(
                raw,
                theme=theme,
                chapter_number=chapter_number,
                target_chapter_count=target_chapter_count,
                recent_modes=modes,
            )
            mode = str(enriched.get("interaction_mode") or "").strip()
            if mode:
                modes.append(mode)

    return modes[-max_modes:]


def _ensure_block_plan(
    *,
    user,
    world,
    chapter_number: int,
    personalization: dict | None,
) -> dict:
    prepared = _prepare_context(
        user=user,
        world=world,
        chapter_number=chapter_number,
        personalization=personalization,
    )
    foundation = prepared["foundation"]
    arc = foundation["arc"]
    blueprint = foundation["blueprint"]
    curriculum = foundation["curriculum"]
    target = int(blueprint["target_chapter_count"])
    block_start = get_story_block_start_chapter(chapter_number)
    block_end = get_story_block_end_chapter(
        start_chapter=block_start,
        target_chapter_count=target,
    )
    block_no = ((block_start - 1) // BLOCK_SIZE) + 1
    existing = get_story_block_plan(arc["id"], block_no)

    if existing and existing.get("outline"):
        return {
            **prepared,
            "plan": existing,
            "target": target,
            "block_start": block_start,
            "block_end": block_end,
        }

    size = block_end - block_start + 1
    concept_plan = plan_story_block_concepts(
        curriculum=curriculum,
        start_chapter=block_start,
        block_size=size,
        target_chapter_count=target,
        weak_concepts=prepared["recent"].get("weak", []),
        review_concepts=prepared["recent"].get("review", []),
        global_weak_concepts=prepared["global"].get("weak", []),
        global_review_concepts=prepared["global"].get("review", []),
    )
    latest_choice = None
    if block_start > 1:
        previous_chapter = get_chapter(
            world_id=world[0],
            chapter_number=block_start - 1,
        )
        candidate_choice = get_latest_choice_for_arc(
            user_id=user["user_id"],
            story_arc_id=arc["id"],
        )
        if (
            previous_chapter is not None
            and candidate_choice
            and candidate_choice.get("chapter_id") == previous_chapter[0]
        ):
            latest_choice = candidate_choice

    recent_modes = _collect_recent_interaction_modes(
        story_arc_id=arc["id"],
        current_block_no=block_no,
        theme=world[4],
        target_chapter_count=target,
    )

    outline = generate_story_block_outline(
        topic=world[1],
        goal=world[2] or "",
        learner_level=world[3],
        theme=world[4],
        guide_name=prepared["guide_name"],
        blueprint=blueprint,
        story_state=prepared["state"],
        chapter_concept_plan=concept_plan,
        start_chapter=block_start,
        target_chapter_count=target,
        recent_profile=prepared["recent"],
        global_profile=prepared["global"],
        latest_choice=latest_choice,
        recent_interaction_modes=recent_modes,
        user_id=user["user_id"],
        world_id=world[0],
        story_arc_id=arc["id"],
    )
    provider = generation_provider()
    upsert_story_block_plan(
        story_arc_id=arc["id"],
        block_number=block_no,
        start_chapter=block_start,
        end_chapter=block_end,
        outline=outline,
        provider=provider,
        model="mock-local" if provider == "mock" else DEFAULT_MODEL,
        prompt_version=OUTLINE_PROMPT_VERSION,
    )
    plan = get_story_block_plan(arc["id"], block_no)
    return {
        **prepared,
        "plan": plan,
        "target": target,
        "block_start": block_start,
        "block_end": block_end,
    }


def get_chapter_interaction_context(
    *,
    world_id: int,
    chapter_number: int,
    theme: str,
) -> dict:
    """현재 Chapter의 Story-integrated 학습 행동 정보를 반환한다.

    과거 v1 Outline에는 interaction_mode가 없어도 deterministic fallback을 사용한다.
    """
    context = get_story_context(world_id)
    target = chapter_number
    story_arc_id = None

    if context:
        story_arc_id = context["arc"]["id"]
        try:
            target = int(
                context["arc"].get("target_chapter_count")
                or chapter_number
            )
        except (TypeError, ValueError):
            target = chapter_number

    raw: dict = {}
    if story_arc_id is not None:
        block_no = ((chapter_number - 1) // BLOCK_SIZE) + 1
        plan = get_story_block_plan(story_arc_id, block_no)
        if plan and plan.get("outline"):
            raw = get_outline_chapter(
                plan["outline"],
                chapter_number,
            ) or {}

    enriched = enrich_chapter_outline_interaction(
        raw,
        theme=theme,
        chapter_number=chapter_number,
        target_chapter_count=max(target, chapter_number),
    )
    return {
        "mode": enriched.get("interaction_mode"),
        "label": enriched.get("interaction_label"),
        "goal": enriched.get("interaction_goal"),
        "question_style": enriched.get("interaction_question_style"),
    }


def ensure_story_chapter(
    *,
    user,
    world,
    chapter_number: int,
    personalization: dict | None = None,
) -> int:
    existing = get_chapter(
        world_id=world[0],
        chapter_number=chapter_number,
    )
    if existing is not None:
        return existing[0]

    data = _ensure_block_plan(
        user=user,
        world=world,
        chapter_number=chapter_number,
        personalization=personalization,
    )
    outline = data["plan"]["outline"]
    chapter_outline = get_outline_chapter(outline, chapter_number)
    if chapter_outline is None:
        raise RuntimeError(
            f"Story Block Outline에서 Chapter {chapter_number} 계획을 찾지 못했습니다."
        )

    chapter_outline = enrich_chapter_outline_interaction(
        chapter_outline,
        theme=world[4],
        chapter_number=chapter_number,
        target_chapter_count=data["target"],
    )

    foundation = data["foundation"]
    arc = foundation["arc"]

    # Story Choice는 다음 Block의 첫 Chapter 첫 장면에만 직접 연결한다.
    opening_choice = None
    if chapter_number == data["block_start"] and chapter_number > 1:
        previous_chapter = get_chapter(
            world_id=world[0],
            chapter_number=chapter_number - 1,
        )
        candidate_choice = get_latest_choice_for_arc(
            user_id=user["user_id"],
            story_arc_id=arc["id"],
        )
        if (
            previous_chapter is not None
            and candidate_choice
            and candidate_choice.get("chapter_id") == previous_chapter[0]
        ):
            opening_choice = candidate_choice

    generated = generate_story_chapter(
        topic=world[1],
        goal=world[2] or "",
        learner_level=world[3],
        theme=world[4],
        guide_name=data["guide_name"],
        blueprint=foundation["blueprint"],
        story_state=data["state"],
        block_outline=outline,
        chapter_outline=chapter_outline,
        chapter_number=chapter_number,
        target_chapter_count=data["target"],
        recent_profile=data["recent"],
        global_profile=data["global"],
        opening_choice=opening_choice,
        user_id=user["user_id"],
        world_id=world[0],
        story_arc_id=arc["id"],
    )
    chapter_id = create_chapter(
        world_id=world[0],
        chapter_number=chapter_number,
        title=generated["title"],
        story=generated["story"],
        learning_objectives=generated["learning_objectives"],
        questions=[],
        story_arc_id=arc["id"],
        story_choices=generated.get("story_choices", []),
        story_phase=generated.get("story_phase"),
        target_concepts=generated.get("target_concepts", []),
        pending_state_update=generated.get("state_update", {}),
    )
    update_story_arc_phase(
        story_arc_id=arc["id"],
        current_phase=(
            generated.get("story_phase")
            or get_story_phase(
                chapter_number=chapter_number,
                target_chapter_count=data["target"],
            )
        ),
    )
    return chapter_id


def ensure_initial_story_block(*, user, world) -> None:
    """호환 이름 유지. 실제 동작은 첫 Block Outline + Chapter 1만 Lazy 생성한다."""
    ensure_story_chapter(
        user=user,
        world=world,
        chapter_number=1,
        personalization=None,
    )


def generate_next_story_block(
    *,
    user,
    world,
    start_chapter: int,
    personalization: dict,
) -> list[int]:
    """호환 이름 유지. 다음 Block 전체가 아니라 필요한 다음 Chapter 1개만 생성한다."""
    return [
        ensure_story_chapter(
            user=user,
            world=world,
            chapter_number=start_chapter,
            personalization=personalization,
        )
    ]


def apply_completed_chapter_state(*, world_id: int, chapter) -> None:
    if len(chapter) <= 13 or chapter[13]:
        return
    context = get_story_context(world_id)
    if context is None:
        return
    update = dict(chapter[12] or {})

    # 문제에서 누적한 단서는 Chapter 완료 시 Story State에도 반영한다.
    # 다섯 단서를 모두 장기 메모리에 넣으면 context가 빠르게 비대해지므로,
    # 마지막 학습 행동의 story_progress를 이번 Chapter의 진행 결론으로 보존한다.
    questions = chapter[6] if len(chapter) > 6 else []
    if isinstance(questions, list):
        progress = [
            str(item.get("story_progress") or "").strip()
            for item in questions
            if isinstance(item, dict)
            and str(item.get("story_progress") or "").strip()
        ]
        if progress:
            conclusion = progress[-1]
            confirmed = list(update.get("confirmed_facts_add") or [])
            if conclusion not in confirmed:
                confirmed.append(conclusion)
            update["confirmed_facts_add"] = confirmed

            # 마지막 문제는 현재 Story State의 open_threads 중 실제 해결된 원문만 돌려준다.
            # 정확한 문자열만 사용하므로 모호한 유사도 휴리스틱으로 잘못 닫는 일을 피한다.
            last_question = questions[-1] if questions and isinstance(questions[-1], dict) else {}
            requested_resolved = list(last_question.get("resolved_threads") or [])
            current_open = set((context.get("state") or {}).get("open_threads") or [])
            resolved = list(update.get("resolved_threads") or [])
            for thread in requested_resolved:
                if thread in current_open and thread not in resolved:
                    resolved.append(thread)
            update["resolved_threads"] = resolved

            # 같은 Chapter state_update가 열려고 한 thread를 학습 결론이 즉시 해결했다면
            # add와 resolved가 동시에 남아 다시 open되는 일을 막는다.
            if resolved:
                update["open_threads_add"] = [
                    thread
                    for thread in list(update.get("open_threads_add") or [])
                    if thread not in set(resolved)
                ]

            previous_event = str(update.get("latest_event") or "").strip()
            update["latest_event"] = (
                f"{previous_event} Chapter 진행 결과: {conclusion}".strip()
                if previous_event
                else f"Chapter 진행 결과: {conclusion}"
            )

    apply_state_update(
        story_arc_id=context["arc"]["id"],
        update=update,
    )
    mark_chapter_state_applied(chapter_id=chapter[0])
    phase = chapter[10] if len(chapter) > 10 else None
    if phase:
        update_story_arc_phase(
            story_arc_id=context["arc"]["id"],
            current_phase=phase,
        )


def get_target_chapter_count(world_id: int) -> int | None:
    context = get_story_context(world_id)
    return None if context is None else context["arc"].get("target_chapter_count")


def is_story_complete(*, world_id: int, chapter_number: int) -> bool:
    total = get_target_chapter_count(world_id)
    return bool(total and chapter_number >= total)


def is_story_block_end(*, world_id: int, chapter_number: int) -> bool:
    total = get_target_chapter_count(world_id)
    return True if total and chapter_number >= total else chapter_number % BLOCK_SIZE == 0


def complete_current_story_arc(world_id: int) -> None:
    arc = get_active_story_arc(world_id)
    if arc:
        complete_story_arc(arc["id"])

from __future__ import annotations

import json
from typing import Any

from components.theme_system import get_theme_prompt_rules
from services.ai_client import DEFAULT_MODEL
from services.generation_gateway import generate_json
from services.experience_profile_service import (
    build_story_pedagogy_rules,
    build_theme_planner_rules,
    build_theme_writer_rules,
    enrich_interaction_outline,
)


BLOCK_SIZE = 3
OUTLINE_PROMPT_VERSION = "story_outline_v5_day3_personalization"
CHAPTER_PROMPT_VERSION = "story_chapter_lazy_v10_day4_stage_neutral_boundary"



def _dedupe_profile_names(*groups) -> list[str]:
    result: list[str] = []
    for group in groups:
        for concept in group or []:
            concept = str(concept or "").strip()
            if concept and concept not in result:
                result.append(concept)
    return result


def _build_personalization_story_rules(
    *,
    target_concepts: list[str],
    recent_profile: dict | None,
    global_profile: dict | None,
) -> str:
    recent = recent_profile or {}
    global_ = global_profile or {}
    weak = _dedupe_profile_names(recent.get("weak"), global_.get("weak"))
    review = [
        name
        for name in _dedupe_profile_names(recent.get("review"), global_.get("review"))
        if name not in weak
    ]
    strong = [
        name
        for name in _dedupe_profile_names(global_.get("strong"), recent.get("strong"))
        if name not in weak and name not in review
    ]
    targets = _dedupe_profile_names(target_concepts)
    target_weak = [name for name in targets if name in weak]
    target_review = [name for name in targets if name in review]
    target_strong = [name for name in targets if name in strong]

    return f"""
[개인화 학습 행동 규칙]
이번 target 중 weak: {target_weak or '없음'}
이번 target 중 review: {target_review or '없음'}
이번 target 중 strong: {target_strong or '없음'}
장기 weak 전체: {weak or '없음'}
- target이 weak이면 앞서 배운 쉬운 표현을 짧게 다시 연결한 뒤, 같은 정의를 복사하지 말고 새로운 Story 상황에서 다시 사용하게 한다.
- target이 review이면 긴 재설명 대신 짧은 회상 단서와 이전 Concept-새 Concept의 연결을 제공한다.
- target이 strong이면 이미 배운 개념처럼 활용하고 기초 정의 반복을 줄인다.
- 현재 target이 아닌 weak Concept은 Curriculum을 가로막으며 억지로 끼우지 않는다. 자연스러운 연결점이 있을 때만 짧게 재사용한다.
- 개인화 지원은 정답을 Story에서 먼저 말하는 것이 아니다. 이해 발판만 조절한다.
"""


MYSTERY_INTERACTION_MODES: dict[str, dict[str, str]] = {
    "scene_reconstruction": {
        "label": "현장 재구성",
        "goal": "흩어진 기록과 기술적 사실을 이용해 사건 직전의 흐름을 재구성한다.",
        "question_style": "시간순서, 데이터 흐름, 원인-결과를 기술적으로 복원하는 조사",
    },
    "witness_verification": {
        "label": "진술 검증",
        "goal": "등장인물의 기술적 진술을 비교해 사실과 모순을 가려낸다.",
        "question_style": "여러 인물의 그럴듯한 기술 진술 중 성립하는 설명/모순된 설명을 판별하는 조사",
    },
    "log_forensics": {
        "label": "로그 포렌식",
        "goal": "로그와 운영 기록을 해석해 이상이 시작된 지점과 의미를 좁힌다.",
        "question_style": "로그, 메트릭, 실행 기록, 오류 흔적을 해석하는 조사",
    },
    "alibi_check": {
        "label": "알리바이 검증",
        "goal": "용의자의 작업 주장이 실제 시스템 구조와 기술적으로 가능한지 검증한다.",
        "question_style": "각 인물의 작업 주장/행동이 시스템 구조상 가능한지 기술 지식으로 검증하는 조사",
    },
    "evidence_comparison": {
        "label": "증거 대조",
        "goal": "서로 다른 데이터·기록·설정을 비교해 어느 증거가 가설을 지지하거나 반박하는지 판단한다.",
        "question_style": "같은 사건을 가리키는 여러 기술 증거를 대조하는 조사",
    },
    "route_trace": {
        "label": "경로 추적",
        "goal": "데이터나 요청이 이동한 경로를 따라가며 우회·누락·변조 지점을 찾는다.",
        "question_style": "파이프라인, 네트워크, 처리 단계의 이동 경로를 추론하는 조사",
    },
    "hypothesis_test": {
        "label": "가설 검증",
        "goal": "현재 사건 가설을 확인하거나 반박할 수 있는 가장 적절한 기술 검증을 선택한다.",
        "question_style": "가설마다 어떤 테스트/쿼리/검증이 필요한지 판단하는 조사",
    },
    "contradiction_hunt": {
        "label": "모순 추적",
        "goal": "이미 확보한 사실들 사이의 기술적 모순을 찾아 새로운 방향을 연다.",
        "question_style": "서로 함께 참일 수 없는 기술 주장이나 기록을 찾는 조사",
    },
    "trap_design": {
        "label": "검증 장치 설계",
        "goal": "의심되는 행동이나 시스템 문제를 드러내기 위한 안전한 검증 조건을 설계한다.",
        "question_style": "특정 가설을 드러낼 모니터링·테스트·격리·검증 절차를 선택하는 조사",
    },
    "case_synthesis": {
        "label": "사건 종합",
        "goal": "누적된 기술 증거를 종합해 사건의 원인·수법·책임 가설을 가장 강한 근거와 함께 정리한다.",
        "question_style": "여러 Concept과 누적 증거를 종합하는 결론형 조사. 단, 전체 마지막에만 최종 범인/원인 지목을 허용",
    },
}


_PHASE_MODE_POOL: dict[str, tuple[str, ...]] = {
    "setup": (
        "scene_reconstruction",
        "witness_verification",
        "evidence_comparison",
    ),
    "development": (
        "log_forensics",
        "alibi_check",
        "route_trace",
        "hypothesis_test",
    ),
    "turn": (
        "contradiction_hunt",
        "hypothesis_test",
        "trap_design",
        "route_trace",
    ),
    "resolution": (
        "evidence_comparison",
        "contradiction_hunt",
        "case_synthesis",
    ),
}


def get_story_block_start_chapter(chapter_number: int) -> int:
    return ((chapter_number - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1


def get_story_block_end_chapter(*, start_chapter: int, target_chapter_count: int) -> int:
    return min(
        target_chapter_count,
        get_story_block_start_chapter(start_chapter) + BLOCK_SIZE - 1,
    )


def get_story_phase(*, chapter_number: int, target_chapter_count: int) -> str:
    if target_chapter_count <= 1:
        return "resolution"
    progress = chapter_number / target_chapter_count
    if progress <= 0.22:
        return "setup"
    if progress <= 0.52:
        return "development"
    if progress <= 0.80:
        return "turn"
    return "resolution"


def _mystery_mode_label(mode: str) -> str:
    return MYSTERY_INTERACTION_MODES.get(mode, {}).get("label", "조사")


def _pick_mystery_mode(
    *,
    chapter_number: int,
    target_chapter_count: int,
    phase: str,
    avoid: set[str] | None = None,
) -> str:
    avoid = avoid or set()

    if chapter_number >= target_chapter_count:
        return "case_synthesis"

    pool = list(_PHASE_MODE_POOL.get(phase, _PHASE_MODE_POOL["development"]))
    # 전체 마지막 전에는 결론형을 남발하지 않는다.
    pool = [mode for mode in pool if mode != "case_synthesis"] or pool

    start_index = (chapter_number - 1) % len(pool)
    ordered = pool[start_index:] + pool[:start_index]

    for mode in ordered:
        if mode not in avoid:
            return mode

    return ordered[0]


def enrich_chapter_outline_interaction(
    chapter_outline: dict[str, Any] | None,
    *,
    theme: str,
    chapter_number: int,
    target_chapter_count: int,
    recent_modes: list[str] | None = None,
) -> dict[str, Any]:
    """모든 Theme에 공통 인터페이스를 사용해 interaction metadata를 보완한다."""
    return enrich_interaction_outline(
        chapter_outline,
        theme=theme,
        chapter_number=chapter_number,
        target_chapter_count=target_chapter_count,
        recent_modes=recent_modes,
    )


def _mystery_planner_rules(recent_modes: list[str] | None) -> str:
    catalog = "\n".join(
        f"- {mode}: {info['label']} · {info['goal']}"
        for mode, info in MYSTERY_INTERACTION_MODES.items()
    )
    return f"""
[미스터리 Chapter 조사 방식 설계]
각 Chapter에는 interaction_mode와 interaction_goal을 반드시 지정한다.
허용 조사 방식:
{catalog}

최근 사용 조사 방식: {recent_modes or []}
규칙:
- 같은 Block 안에서는 가능한 한 서로 다른 조사 방식을 사용한다.
- 직전 Chapter와 같은 interaction_mode를 반복하지 않는다.
- 최근 사용 방식만 기계적으로 반복하지 않는다.
- 모든 Chapter를 '용의자 4명 중 범인 찾기'로 만들지 않는다.
- 초반은 사건 파악/진술/증거, 중반은 로그·알리바이·경로·가설, 후반은 모순·검증 장치·종합처럼 흐름을 변주한다.
- case_synthesis와 최종 범인/원인 지목은 전체 Story의 resolution 또는 마지막 Chapter에 가깝게 사용한다.
- interaction_goal에는 사용자가 이번 Chapter에서 '무엇을 조사/판단/복원하는지'를 쓴다. 정답 자체는 쓰지 않는다.
"""


OUTLINE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "block_number",
        "block_title",
        "block_goal",
        "chapters",
        "block_resolution",
    ],
    "properties": {
        "block_number": {"type": "integer"},
        "block_title": {"type": "string"},
        "block_goal": {"type": "string"},
        "chapters": {
            "type": "array",
            "minItems": 1,
            "maxItems": BLOCK_SIZE,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "chapter_number",
                    "phase",
                    "title_seed",
                    "narrative_goal",
                    "learning_bridge",
                    "ending_hook",
                    "target_concepts",
                    "interaction_mode",
                    "interaction_goal",
                ],
                "properties": {
                    "chapter_number": {"type": "integer"},
                    "phase": {"type": "string"},
                    "title_seed": {"type": "string"},
                    "narrative_goal": {"type": "string"},
                    "learning_bridge": {"type": "string"},
                    "ending_hook": {"type": "string"},
                    "target_concepts": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 2,
                        "items": {"type": "string"},
                    },
                    "interaction_mode": {"type": "string"},
                    "interaction_goal": {"type": "string"},
                },
            },
        },
        "block_resolution": {"type": "string"},
    },
}


CHAPTER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "chapter_number",
        "title",
        "story",
        "learning_objectives",
        "story_choices",
        "story_summary",
        "current_location",
        "character_updates",
        "companion_mood",
        "companion_relationship_note",
        "companion_latest_reaction",
        "confirmed_facts_add",
        "open_threads_add",
        "resolved_threads",
        "latest_event",
    ],
    "properties": {
        "chapter_number": {"type": "integer"},
        "title": {"type": "string"},
        "story": {"type": "string"},
        "learning_objectives": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {"type": "string"},
        },
        "story_choices": {
            "type": "array",
            "maxItems": 2,
            "items": {"type": "string"},
        },
        "story_summary": {"type": "string"},
        "current_location": {"type": "string"},
        "character_updates": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "role",
                    "relationship",
                    "status",
                    "important_info",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "relationship": {"type": "string"},
                    "status": {"type": "string"},
                    "important_info": {"type": "string"},
                },
            },
        },
        "companion_mood": {"type": "string"},
        "companion_relationship_note": {"type": "string"},
        "companion_latest_reaction": {"type": "string"},
        "confirmed_facts_add": {
            "type": "array",
            "maxItems": 8,
            "items": {"type": "string"},
        },
        "open_threads_add": {
            "type": "array",
            "maxItems": 6,
            "items": {"type": "string"},
        },
        "resolved_threads": {
            "type": "array",
            "maxItems": 6,
            "items": {"type": "string"},
        },
        "latest_event": {"type": "string"},
    },
}


def _guide_rules(guide_name: str | None) -> str:
    if not guide_name:
        return "고양이 이름은 아직 정해지지 않았다. 새 이름을 임의로 만들지 않는다."
    return f"""사용자가 직접 이름 붙인 동료 고양이는 '{guide_name}'이다.
- 모든 Chapter에서 같은 고양이다.
- 처음 만나는 장면을 반복하지 않는다.
- 전문 교사가 아니라 관찰/반응/가벼운 힌트를 담당한다.
- Story에서 '{guide_name}'이라는 이름을 자연스럽게 사용한다."""


def _normalize_outline(
    result: dict,
    *,
    start: int,
    end: int,
    concept_plan: dict[int, list[str]],
    target_count: int,
    theme: str,
    recent_modes: list[str] | None = None,
) -> dict:
    chapters = result.get("chapters") or []
    expected = list(range(start, end + 1))
    by = {int(x.get("chapter_number", -1)): dict(x) for x in chapters}
    if any(n not in by for n in expected):
        raise ValueError("Story Block Outline의 Chapter 번호가 요청과 일치하지 않습니다.")

    normalized: list[dict[str, Any]] = []
    used_modes = set(recent_modes[-1:] if recent_modes else [])

    for n in expected:
        item = by[n]
        item["phase"] = get_story_phase(
            chapter_number=n,
            target_chapter_count=target_count,
        )
        item["target_concepts"] = list(
            concept_plan.get(n) or item.get("target_concepts") or []
        )[:2]
        if not item["target_concepts"]:
            raise ValueError(f"Chapter {n} Outline에 target concept이 없습니다.")

        item = enrich_chapter_outline_interaction(
            item,
            theme=theme,
            chapter_number=n,
            target_chapter_count=target_count,
            recent_modes=list(used_modes),
        )
        used_modes.add(item["interaction_mode"])

        normalized.append(item)

    result = dict(result)
    result["chapters"] = normalized
    result["block_number"] = ((start - 1) // BLOCK_SIZE) + 1
    return result


def generate_story_block_outline(
    *,
    topic: str,
    goal: str,
    learner_level: str,
    theme: str,
    guide_name: str | None,
    blueprint: dict[str, Any],
    story_state: dict[str, Any] | None,
    chapter_concept_plan: dict[int, list[str]],
    start_chapter: int,
    target_chapter_count: int,
    recent_profile: dict | None = None,
    global_profile: dict | None = None,
    latest_choice: dict | None = None,
    recent_interaction_modes: list[str] | None = None,
    user_id: int | None = None,
    world_id: int | None = None,
    story_arc_id: int | None = None,
) -> dict:
    end = get_story_block_end_chapter(
        start_chapter=start_chapter,
        target_chapter_count=target_chapter_count,
    )
    phase_map = {
        n: get_story_phase(
            chapter_number=n,
            target_chapter_count=target_chapter_count,
        )
        for n in range(start_chapter, end + 1)
    }
    theme_rules = get_theme_prompt_rules(theme)
    interaction_rules = build_theme_planner_rules(
        theme=theme,
        recent_modes=recent_interaction_modes,
    )
    pedagogy_rules = build_story_pedagogy_rules(learner_level)
    planned_concepts = [
        concept
        for chapter_concepts in chapter_concept_plan.values()
        for concept in chapter_concepts
    ]
    personalization_rules = _build_personalization_story_rules(
        target_concepts=planned_concepts,
        recent_profile=recent_profile,
        global_profile=global_profile,
    )

    prompt = f"""너는 Story Block Planner다. 긴 본문을 쓰지 말고 Chapter {start_chapter}~{end}의 방향만 짧은 JSON으로 설계한다.
학습 주제: {topic}
목표: {goal}
수준: {learner_level}
Theme 규칙:
{theme_rules}

{pedagogy_rules}

고양이:
{_guide_rules(guide_name)}
Blueprint:
{json.dumps(blueprint, ensure_ascii=False)}
현재 Story State:
{json.dumps(story_state or {}, ensure_ascii=False, default=str)}
최근 Story Choice: {(latest_choice or {}).get('choice_text', '없음')}
최근 학습: {json.dumps(recent_profile or {}, ensure_ascii=False)}
장기 학습: {json.dumps(global_profile or {}, ensure_ascii=False)}
{personalization_rules}
Chapter별 확정 Concept: {json.dumps(chapter_concept_plan, ensure_ascii=False)}
{interaction_rules}
규칙:
- 본문을 쓰지 않는다.
- 각 Chapter는 title_seed/narrative_goal/learning_bridge/ending_hook/interaction_mode/interaction_goal을 계획한다.
- 최근 Story Choice가 존재하고 이번 Block이 새로 시작된다면, 첫 Chapter의 narrative_goal은 반드시 그 선택 행동을 실제로 수행하는 장면에서 시작한다.
- 선택한 방향을 단순 언급/복사하지 말고, 그 행동의 결과로 이번 Chapter의 새 증거·인물·시스템 이상 중 하나가 발견되게 한다.
- 새 학습 Concept 때문에 사용자의 선택을 무시하고 갑자기 다른 행동으로 점프하지 않는다. Concept는 선택을 따라가다가 발견되는 문제를 해석하는 도구로 연결한다.
- Story는 독립적으로 재미있어야 하고 실제 Concept을 마법 이름으로 바꾸지 않는다.
- 같은 Story 흐름을 이어가더라도 Chapter마다 사용자가 하는 행동/판단 방식은 변주한다.
- Block 마지막은 한 단계 정리하되 전체 Arc가 끝나지 않았다면 메인 갈등은 남긴다.
JSON만 반환한다."""

    result = generate_json(
        feature="story_block_outline",
        prompt_version=OUTLINE_PROMPT_VERSION,
        prompt=prompt,
        schema=OUTLINE_SCHEMA,
        model=DEFAULT_MODEL,
        user_id=user_id,
        world_id=world_id,
        story_arc_id=story_arc_id,
        mock_context={
            "topic": topic,
            "goal": goal,
            "learner_level": learner_level,
            "theme": theme,
            "guide_name": guide_name,
            "start_chapter": start_chapter,
            "end_chapter": end,
            "target_chapter_count": target_chapter_count,
            "chapter_concept_plan": chapter_concept_plan,
            "phase_map": phase_map,
            "recent_interaction_modes": recent_interaction_modes or [],
        },
    )
    return _normalize_outline(
        result,
        start=start_chapter,
        end=end,
        concept_plan=chapter_concept_plan,
        target_count=target_chapter_count,
        theme=theme,
        recent_modes=recent_interaction_modes,
    )


def _normalize_chapter(
    item: dict,
    *,
    chapter_number: int,
    target_concepts: list[str],
    phase: str,
    block_end: int,
    target_count: int,
) -> dict:
    if int(item.get("chapter_number", -1)) != chapter_number:
        raise ValueError("생성 Chapter 번호가 요청과 다릅니다.")
    if not str(item.get("title") or "").strip() or not str(item.get("story") or "").strip():
        raise ValueError("Chapter title/story가 비어 있습니다.")

    choices = [str(x).strip() for x in item.get("story_choices", []) if str(x).strip()]
    if chapter_number != block_end or chapter_number >= target_count:
        choices = []

    item = dict(item)
    item["story_choices"] = [
        {"key": chr(ord("A") + i), "text": text}
        for i, text in enumerate(choices[:2])
    ]
    item["target_concepts"] = list(target_concepts[:2])
    item["story_phase"] = phase
    item["state_update"] = {
        "story_summary": item.pop("story_summary", ""),
        "current_location": item.pop("current_location", ""),
        "character_updates": item.pop("character_updates", []),
        "companion_state": {
            "mood": item.pop("companion_mood", ""),
            "relationship_note": item.pop("companion_relationship_note", ""),
            "latest_reaction": item.pop("companion_latest_reaction", ""),
        },
        "confirmed_facts_add": item.pop("confirmed_facts_add", []),
        "open_threads_add": item.pop("open_threads_add", []),
        "resolved_threads": item.pop("resolved_threads", []),
        "latest_event": item.pop("latest_event", ""),
    }
    return item



def _build_reasoning_safe_writer_outlines(
    *,
    block_outline: dict[str, Any],
    chapter_outline: dict[str, Any],
    chapter_number: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Story Writer용 Outline에서 Question reasoning 결론만 제거한다.

    DB에 저장된 Curriculum/Story Outline 자체는 변경하지 않는다. Writer에게는
    title/phase/target Concept/interaction mode 같은 계획 구조는 유지하되,
    narrative_goal/learning_bridge/ending_hook/interaction_goal처럼 원인·단계·
    가설 결과를 선공개할 수 있는 자유서술 필드를 관찰형 지시로 치환한다.
    """
    concepts = [
        str(value).strip()
        for value in (chapter_outline.get("target_concepts") or [])[:2]
        if str(value).strip()
    ]
    concept_text = ", ".join(concepts) if concepts else "이번 target Concept"
    interaction_label = str(
        chapter_outline.get("interaction_label")
        or chapter_outline.get("interaction_mode")
        or "조사"
    ).strip()
    observation_anchor = str(chapter_outline.get("narrative_goal") or "").strip()
    if not observation_anchor:
        observation_anchor = (
            "현재 Story State와 직전 Choice에 이미 등장한 관찰 대상과 위치만 사용한다."
        )

    safe_chapter = {
        "chapter_number": int(chapter_outline.get("chapter_number") or chapter_number),
        "phase": chapter_outline.get("phase"),
        "title_seed": chapter_outline.get("title_seed"),
        "target_concepts": concepts,
        "interaction_mode": chapter_outline.get("interaction_mode"),
        "interaction_label": chapter_outline.get("interaction_label"),
        "observation_anchor": observation_anchor,
        "observation_anchor_rule": (
            "observation_anchor에서 이미 제시된 관찰 대상·저장소·시점·처리 전후 endpoint의 위치 관계는 유지한다. "
            "원인이나 문제 단계는 숨기되, 불일치가 발생한 위치를 앞/뒤 단계로 옮기거나 새로운 중간 checkpoint를 만들어내지 않는다. "
            "Story State/직전 결과/observation_anchor에 없는 수량·시각·파일 상태·중간 저장소를 사실처럼 새로 만들지 않는다. "
            "두 endpoint가 다르다는 사실은 말할 수 있지만, 아직 단계가 확정되지 않았다면 'X를 거친 직후', 'X를 거치는 동안', "
            "'X 과정에서 사라졌다'처럼 특정 중간 구간을 발생 위치로 고정하지 않는다. '두 endpoint 사이 어디선가 차이가 생겼다' 수준으로 유지한다."
        ),
        "stage_neutral_rule": (
            "Question이 문제 발생 단계를 판단하기 전에는 Story와 state_update 모두 endpoint 간 차이만 기록한다. "
            "open_threads_add도 '두 endpoint 사이의 불일치가 어느 처리 지점에서 왜 발생했는가?'처럼 중립적으로 남기고, "
            "아직 확인하지 않은 특정 단계·스크립트·구간을 이미 누락이 발생한 위치로 전제하지 않는다."
        ),
        "narrative_goal": (
            "직전 Choice와 현재 Story State를 이어 받아, 이번 Chapter에서 관찰할 수 있는 "
            "이상 현상과 조사 필요성을 드러낸다. 어느 처리 단계가 문제인지, 직접 원인이 "
            "무엇인지, 가설이 맞는지는 아직 확정하지 않는다."
        ),
        "learning_bridge": (
            f"{concept_text}을(를) Story의 관찰 자료를 해석하는 도구로 연결한다. "
            "정의·정답·원인·조치 결론을 먼저 설명하지 않고 이후 Evidence/Question에서 적용하게 한다."
        ),
        "ending_hook": (
            "서로 맞지 않는 기록이나 결과 차이를 확인한 뒤, 어디서 왜 어긋났는지 "
            "다음 Evidence/Question에서 판단하도록 로그·기록·조건을 조사하는 행동으로 끝낸다."
        ),
        "interaction_goal": (
            f"{interaction_label} 방식으로 관찰 가능한 사실과 불일치를 제시하되, "
            "문제 발생 단계·직접 원인·가설 결론은 학습자의 판단 영역으로 남긴다."
        ),
        "interaction_question_style": (
            "Story는 판단에 필요한 맥락만 열어 둔다. 구체 Evidence를 읽은 뒤 단계·원인·가설 결과를 "
            "학습자가 Question에서 판단한다."
        ),
    }

    safe_chapters: list[dict[str, Any]] = []
    active_found = False
    for raw in block_outline.get("chapters") or []:
        raw_number = int(raw.get("chapter_number") or -1)
        if raw_number == chapter_number:
            safe_chapters.append(dict(safe_chapter))
            active_found = True
            continue

        # 다른 Chapter의 내부 결론까지 현재 Writer에게 노출하지 않는다.
        safe_chapters.append(
            {
                "chapter_number": raw_number,
                "phase": raw.get("phase"),
                "title_seed": raw.get("title_seed"),
                "target_concepts": list(raw.get("target_concepts") or [])[:2],
                "interaction_mode": raw.get("interaction_mode"),
                "interaction_label": raw.get("interaction_label"),
            }
        )

    if not active_found:
        safe_chapters.append(dict(safe_chapter))
        safe_chapters.sort(key=lambda item: int(item.get("chapter_number") or 0))

    safe_block = {
        "block_number": block_outline.get("block_number"),
        "block_title": block_outline.get("block_title"),
        "block_goal": (
            "기존 Block의 진행 방향과 Chapter 순서는 유지한다. 다만 현재 Chapter에서 이후 Question이 "
            "판단할 단계·원인·가설 결과를 Story 내부 결론으로 선공개하지 않는다."
        ),
        "chapters": safe_chapters,
        "block_resolution": (
            "기존 Block의 계획된 진행을 유지하되, 현재 Chapter의 학습 판단은 Evidence/Question 이후에 "
            "확정한다. Story는 다음 조사 행동과 열린 질문을 남긴다."
        ),
    }
    return safe_block, safe_chapter

def generate_story_chapter(
    *,
    topic: str,
    goal: str,
    learner_level: str,
    theme: str,
    guide_name: str | None,
    blueprint: dict[str, Any],
    story_state: dict[str, Any] | None,
    block_outline: dict[str, Any],
    chapter_outline: dict[str, Any],
    chapter_number: int,
    target_chapter_count: int,
    recent_profile: dict | None = None,
    global_profile: dict | None = None,
    opening_choice: dict | None = None,
    user_id: int | None = None,
    world_id: int | None = None,
    story_arc_id: int | None = None,
) -> dict:
    block_end = int(
        max(x["chapter_number"] for x in block_outline.get("chapters", [chapter_outline]))
    )
    phase = get_story_phase(
        chapter_number=chapter_number,
        target_chapter_count=target_chapter_count,
    )
    chapter_outline = enrich_chapter_outline_interaction(
        chapter_outline,
        theme=theme,
        chapter_number=chapter_number,
        target_chapter_count=target_chapter_count,
    )
    concepts = list(chapter_outline.get("target_concepts") or [])[:2]
    writer_block_outline, writer_chapter_outline = _build_reasoning_safe_writer_outlines(
        block_outline=block_outline,
        chapter_outline=chapter_outline,
        chapter_number=chapter_number,
    )

    interaction_section = f"""
이번 Chapter 학습 상호작용:
- mode: {writer_chapter_outline.get('interaction_mode')}
- label: {writer_chapter_outline.get('interaction_label')}
- goal: {writer_chapter_outline.get('interaction_goal')}
- question style: {writer_chapter_outline.get('interaction_question_style')}
- observation anchor: {writer_chapter_outline.get('observation_anchor')}
- anchor rule: {writer_chapter_outline.get('observation_anchor_rule')}
- stage-neutral rule: {writer_chapter_outline.get('stage_neutral_rule')}
"""

    choice_bridge_section = ""
    if opening_choice and opening_choice.get("choice_text"):
        choice_bridge_section = f"""
[직전 Story Choice - 이번 Chapter 첫 장면에 반드시 반영]
사용자가 선택한 방향: {opening_choice.get('choice_text')}
- 첫 1~2문장에서 사용자가 이 선택을 실제로 수행하고 있음을 행동/결과로 보여준다.
- 선택을 수행한 결과 이번 Chapter의 핵심 증거·이상·인물 반응 중 하나가 발견되어야 한다.
- 선택 문장을 그대로 복사해 '선택했다'고 설명만 하지 않는다.
- 선택과 무관한 새 학습 Concept로 갑자기 점프하지 않는다. 새 Concept는 선택의 결과로 발견된 문제를 해석하는 도구로 등장시킨다.
"""

    theme_writer_rules = build_theme_writer_rules(theme)
    pedagogy_rules = build_story_pedagogy_rules(learner_level)
    personalization_rules = _build_personalization_story_rules(
        target_concepts=concepts,
        recent_profile=recent_profile,
        global_profile=global_profile,
    )

    latest_event = (story_state or {}).get("latest_event") or {}
    previous_result = (
        latest_event.get("summary", "")
        if isinstance(latest_event, dict)
        else str(latest_event or "")
    )
    open_threads = list((story_state or {}).get("open_threads") or [])
    is_final_chapter = chapter_number >= target_chapter_count

    continuity_section = f"""
[직전 Chapter 진행 결과 - 다음 Chapter 연결]
{previous_result or '명시적 직전 결과 없음'}
- 직전 결과가 있다면 첫 문단 1~2문장 안에서 그 결과가 이번 행동/발견의 직접적인 이유가 되게 한다.
- 이미 해결한 사실을 다시 처음 발견하거나 미해결처럼 되풀이하지 않는다.
- 후속 문제가 생긴다면 '앞 단계를 정리한 뒤 새로 드러난 문제'로 연결한다.
- 현재 open_threads: {json.dumps(open_threads, ensure_ascii=False)}
"""

    reasoning_boundary_section = f"""
[Story ↔ Question Reasoning 경계]
- Story 본문은 사건의 상황, 관찰 가능한 이상, 조사 동기와 다음 조사 행동까지만 제공한다.
- 이후 Question에서 학습자가 판단해야 할 '문제 발생 단계', '직접 원인', '정답 Concept', '가설의 확정/기각', '복구/조치 결론'을 Story에서 먼저 확정하지 않는다.
- opening_choice에 Concept 이름이 들어가더라도 그것은 이번 Chapter에서 검증할 가설/행동 방향으로 취급한다. 아직 확인하지 않은 가설을 Story에서 사실로 승격시키지 않는다.
- 허용 예: 'ELT 방식이라는 가설을 확인하기 위해 원본과 처리 기록을 대조한다.'
- 금지 예: Question에서 아직 판단해야 하는데 '이 시스템은 ELT다', '가공 과정에서 데이터가 빠졌다', '스크립트가 원인이다', '외부 도난이 아니다'처럼 진단을 먼저 확정한다.
- 원본과 결과가 다르다는 관찰, 기록의 불일치, 이상 징후는 Story에 보여줄 수 있다. 다만 그 차이가 어느 단계에서 왜 발생했는지는 학습자가 Evidence와 Question을 통해 판단하게 남겨둔다.
- [관찰 endpoint 고정] writer_chapter_outline.observation_anchor에 등장한 비교 대상·저장소·시점·처리 전후 위치를 Story의 관찰 기준으로 유지한다. 원인을 숨기기 위해 endpoint 자체를 다른 단계로 옮기지 않는다.
- 예를 들어 계획이 '원본 저장소와 최종 결과를 비교'하는 구조라면, Story에서 임의로 '수집 기록과 가공 직전 로그 사이에서 이미 수량이 달랐다' 같은 새로운 중간 불일치를 만들지 않는다.
- Story State, 직전 Chapter 결과, observation_anchor에 명시되지 않은 수량·시각·파일 상태·중간 checkpoint를 새 사실처럼 생성하지 않는다. 구체 값이 필요하면 정성적 불일치만 보여주고 실제 수치/조건은 Evidence/Question에 남긴다.
- [단계 중립 표현] 두 endpoint 사이의 차이는 관찰할 수 있지만, Question이 발생 단계를 판단하기 전에는 특정 중간 구간을 이미 원인 위치로 묘사하지 않는다.
- 'X를 거친 직후 사라졌다', 'X를 거치는 동안 누락됐다', 'X 과정에서 없어졌다', 'X 이후부터 문제가 생겼다'처럼 시간 순서를 곧바로 인과/발생 단계로 확정하는 문장을 피한다. 이전 Story State에서 이미 확정된 사실인 경우에만 예외다.
- 단계가 아직 미확정이면 '원본 endpoint에는 존재하지만 최종 endpoint에서는 확인되지 않는다', '두 결과 사이에 불일치가 있다', '어느 처리 지점에서 차이가 생겼는지 확인해야 한다'처럼 endpoint 차이와 열린 질문만 서술한다.
- state_update의 confirmed_facts_add/story_summary/latest_event도 같은 endpoint만 기록한다. 관찰 위치를 바꾸거나 아직 보지 않은 중간 단계의 사실을 새로 확정하지 않는다.
- open_threads_add는 미확정 단계명을 원인 구간으로 전제하지 않는다. '가공 스크립트를 거치는 동안 왜 누락됐는가?'보다 '원본과 최종 결과 사이의 불일치가 어느 처리 지점에서 왜 발생했는가?'처럼 단계 중립 질문을 남긴다.
- Story 끝은 '어디서/왜 어긋났는지 확인해야 한다'는 open question 또는 다음 조사 행동으로 이어지게 한다. 미스터리의 긴장과 학습자의 판단 여지를 동시에 남긴다.
- Concept는 Story를 해석하는 도구로 자연스럽게 등장시키되, 정의를 강의하거나 정답 문장으로 사용하지 않는다.
- 현재 Story State의 confirmed_facts/resolved_events에 이미 확정된 사실은 숨기지 않는다. 이 규칙은 이번 Chapter에서 새로 판단해야 하는 정보만 미확정으로 남기기 위한 것이다.
- Block/Chapter Outline에 원인이나 결론이 내부 계획으로 적혀 있더라도, 그것이 이후 Question의 판단 대상이면 Story 사용자 본문에 확정 사실로 복사하지 않는다. Reasoning 경계를 Outline 문구보다 우선한다.
- story_summary/latest_event/confirmed_facts_add도 Story 본문보다 앞서 더 강한 원인/결론을 확정하지 않는다. 아직 Question에서 판단해야 할 내용은 중립적 관찰이나 open_threads_add로 남긴다.
"""

    prompt = f"""너는 개인화 학습 Story의 단일 Chapter Writer다. 지금 필요한 Chapter {chapter_number} 하나만 작성한다.
학습: {topic} / {goal} / {learner_level}
Theme:
{get_theme_prompt_rules(theme)}
고양이:
{_guide_rules(guide_name)}
Blueprint:
{json.dumps(blueprint, ensure_ascii=False)}
현재 Story State(이미 완료한 Chapter까지만 반영):
{json.dumps(story_state or {}, ensure_ascii=False, default=str)}
이번 Block Outline(Story Writer용 reasoning-safe adapter 적용):
{json.dumps(writer_block_outline, ensure_ascii=False)}
이번 Chapter Outline(Story Writer용 reasoning-safe adapter 적용):
{json.dumps(writer_chapter_outline, ensure_ascii=False)}
{interaction_section}
{choice_bridge_section}
{continuity_section}
{reasoning_boundary_section}
최근 학습: {json.dumps(recent_profile or {}, ensure_ascii=False)}
장기 학습: {json.dumps(global_profile or {}, ensure_ascii=False)}
{personalization_rules}
{theme_writer_rules}
{pedagogy_rules}
규칙:
- 한국어 250~450자, 짧은 3문단. 입문/초급은 짧은 문장과 쉬운 연결어를 우선한다.
- Story 상황→이번 Theme 행동이 필요한 이유→다음 행동의 기대/긴장으로 이어진다.
- Concept는 현실 용어를 유지한다.
- 고양이는 교사가 아니며 정답을 강의하지 않는다.
- 사용자가 이름 붙인 고양이와 이미 만난 상태를 유지한다.
- Block 마지막 Chapter이고 전체 마지막이 아니면 0~2 Story Choice 가능. 그 외 story_choices는 빈 배열.
- Story State update는 이 Chapter에서 실제 발생한 변화만 반환한다.
- resolved_threads는 현재 open_threads 중 이번 Chapter에서 실제로 해결된 문장을 정확히 그대로 넣는다. 해결되지 않았으면 빈 배열이다.
- open_threads_add에는 앞으로 확인해야 할 새 질문만 넣고 이미 해결된 질문을 다시 추가하지 않는다.
- 전체 마지막 Chapter가 아니라면 story_summary/latest_event/confirmed_facts에서 '완벽히 해결', '완전히 해결', '사건 종결', '최종 원인 확정'처럼 Story 전체를 닫는 표현을 사용하지 않는다. 이번 Chapter에서 확인된 범위만 정리한다.
- 전체 마지막 Chapter 여부: {is_final_chapter}
JSON만 반환한다."""

    result = generate_json(
        feature="story_chapter",
        prompt_version=CHAPTER_PROMPT_VERSION,
        prompt=prompt,
        schema=CHAPTER_SCHEMA,
        model=DEFAULT_MODEL,
        user_id=user_id,
        world_id=world_id,
        story_arc_id=story_arc_id,
        mock_context={
            "topic": topic,
            "goal": goal,
            "learner_level": learner_level,
            "theme": theme,
            "guide_name": guide_name,
            "chapter_number": chapter_number,
            "chapter_outline": writer_chapter_outline,
            "target_concepts": concepts,
            "block_end_chapter": block_end,
            "target_chapter_count": target_chapter_count,
            "opening_choice": (opening_choice or {}).get("choice_text"),
        },
    )
    return _normalize_chapter(
        result,
        chapter_number=chapter_number,
        target_concepts=concepts,
        phase=phase,
        block_end=block_end,
        target_count=target_chapter_count,
    )


def generate_first_chapter(*args, **kwargs):
    raise RuntimeError(
        "Lazy Story Engine에서는 story_engine_service.ensure_initial_story_block()을 사용해주세요."
    )


def generate_next_chapter(*args, **kwargs):
    raise RuntimeError(
        "Lazy Story Engine에서는 story_engine_service.generate_next_story_block()을 사용해주세요."
    )

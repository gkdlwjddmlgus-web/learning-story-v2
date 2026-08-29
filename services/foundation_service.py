from __future__ import annotations

import json
from typing import Any

from components.theme_system import get_theme_prompt_rules
from repositories.curriculum_repository import (
    get_curriculum,
    upsert_curriculum,
)
from repositories.story_repository import (
    get_active_story_arc,
    update_story_arc_blueprint,
)
from services.ai_client import DEFAULT_MODEL
from services.dev_config import generation_provider
from services.generation_gateway import generate_json
from services.experience_profile_service import (
    build_curriculum_pedagogy_rules,
    build_story_pedagogy_rules,
    get_theme_experience_profile,
)


CURRICULUM_PROMPT_VERSION = "curriculum_v3_pedagogy"
BLUEPRINT_PROMPT_VERSION = "blueprint_v3_theme_arc"

CURRICULUM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "categories", "concept_sequence"],
    "properties": {
        "summary": {"type": "string"},
        "categories": {
            "type": "array",
            "minItems": 2,
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "order", "description"],
                "properties": {
                    "name": {"type": "string"},
                    "order": {"type": "integer"},
                    "description": {"type": "string"},
                },
            },
        },
        "concept_sequence": {
            "type": "array",
            "minItems": 5,
            "maxItems": 24,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "category",
                    "order",
                    "initial_difficulty",
                    "reviewable",
                    "description",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "order": {"type": "integer"},
                    "initial_difficulty": {
                        "type": "string",
                        "enum": [
                            "intro",
                            "basic",
                            "intermediate",
                            "advanced",
                        ],
                    },
                    "reviewable": {"type": "boolean"},
                    "description": {"type": "string"},
                },
            },
        },
    },
}

BLUEPRINT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title",
        "premise",
        "main_conflict",
        "ending_rule",
        "target_chapter_count",
        "tone",
        "world_rules",
        "forbidden_rules",
        "phase_goals",
        "hidden_truth",
    ],
    "properties": {
        "title": {"type": "string"},
        "premise": {"type": "string"},
        "main_conflict": {"type": "string"},
        "ending_rule": {"type": "string"},
        "target_chapter_count": {
            "type": "integer",
            "minimum": 9,
            "maximum": 15,
        },
        "tone": {"type": "string"},
        "world_rules": {
            "type": "array",
            "minItems": 3,
            "maxItems": 8,
            "items": {"type": "string"},
        },
        "forbidden_rules": {
            "type": "array",
            "minItems": 3,
            "maxItems": 8,
            "items": {"type": "string"},
        },
        "phase_goals": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "setup",
                "development",
                "turn",
                "resolution",
            ],
            "properties": {
                "setup": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 5,
                    "items": {"type": "string"},
                },
                "development": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 5,
                    "items": {"type": "string"},
                },
                "turn": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 5,
                    "items": {"type": "string"},
                },
                "resolution": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 5,
                    "items": {"type": "string"},
                },
            },
        },
        "hidden_truth": {"type": "string"},
    },
}


def get_world_foundation(
    world_id: int,
) -> dict[str, Any] | None:
    arc = get_active_story_arc(world_id)
    curriculum_row = get_curriculum(world_id)

    if (
        arc is None
        or curriculum_row is None
        or not curriculum_row.get("curriculum")
        or not arc.get("blueprint")
    ):
        return None

    return {
        "arc": arc,
        "curriculum": curriculum_row["curriculum"],
        "curriculum_meta": curriculum_row,
        "blueprint": arc["blueprint"],
    }


def _ensure_curriculum(
    *,
    user_id: int,
    world,
) -> dict:
    curriculum_row = get_curriculum(world[0])

    if (
        curriculum_row is not None
        and curriculum_row.get("curriculum")
    ):
        return curriculum_row["curriculum"]

    curriculum_pedagogy = build_curriculum_pedagogy_rules(world[3])

    prompt = f"""
너는 범용 학습 서비스의 Curriculum Architect다.

학습 주제: {world[1]}
학습 목표: {world[2] or "별도 목표 없음"}
현재 수준: {world[3]}

{curriculum_pedagogy}

다음 기준으로 실제 학습 Curriculum을 설계한다.
- 특정 분야에 종속된 고정 템플릿을 쓰지 않는다.
- 학습 대분류와 실제 Concept을 정확한 현실 용어로 작성한다.
- 권장 순서와 초기 난이도를 제공한다.
- Concept는 Story Generator, Question Generator, Learning Analyzer가 함께 사용할 기준이다.
- Story 세계관 용어로 Concept 이름을 바꾸지 않는다.
- 사용자의 현재 수준과 목표를 Concept 순서와 출발점에 직접 반영한다.
- 각 Concept description에는 "무엇을 배우는지"를 현재 수준에서 이해할 수 있는 말로 쓴다.
- 앞 Concept를 배우지 않고 뒤 Concept를 알아야만 이해되는 역전된 순서를 만들지 않는다.
- 기초부터 응용까지 이어지는 5~24개의 Concept sequence를 만든다.

JSON만 반환한다.
"""

    curriculum = generate_json(
        feature="curriculum",
        prompt_version=CURRICULUM_PROMPT_VERSION,
        prompt=prompt,
        schema=CURRICULUM_SCHEMA,
        model=DEFAULT_MODEL,
        user_id=user_id,
        world_id=world[0],
        mock_context={
            "topic": world[1],
            "goal": world[2] or "",
            "learner_level": world[3],
            "theme": world[4],
            "guide_name": world[9] if len(world) > 9 else None,
        },
    )

    upsert_curriculum(
        world_id=world[0],
        curriculum=curriculum,
        model=("mock-local" if generation_provider() == "mock" else DEFAULT_MODEL),
        prompt_version=CURRICULUM_PROMPT_VERSION,
    )
    return curriculum


def _ensure_blueprint(
    *,
    user_id: int,
    world,
    curriculum: dict,
) -> dict:
    arc = get_active_story_arc(world[0])

    if arc is None:
        raise RuntimeError("활성 Story Arc를 찾지 못했습니다.")

    if arc.get("blueprint"):
        return arc["blueprint"]

    theme_rules = get_theme_prompt_rules(world[4])
    theme_profile = get_theme_experience_profile(world[4])
    story_pedagogy = build_story_pedagogy_rules(world[3])

    prompt = f"""
너는 완결형 Story Blueprint Designer다.

학습 주제: {world[1]}
학습 목표: {world[2] or "별도 목표 없음"}
현재 수준: {world[3]}
Theme: {world[4]}

Theme 규칙:
{theme_rules}

Theme Story 전개 가이드:
{theme_profile['arc_guidance']}
{theme_profile['writer_rules']}

{story_pedagogy}

Curriculum 요약:
{json.dumps(curriculum, ensure_ascii=False)}

규칙:
- Story Arc는 기(setup) → 승(development) → 전(turn) → 결(resolution)로 완결한다.
- 목표 Chapter 수는 9~15 사이에서 결정한다.
- Chapter별 사건을 전부 미리 고정하지 않는다.
- premise, main conflict, world rules, ending rule, phase goals만 고정한다.
- 구체적인 사건/장소/조연/대화는 이후 Story Block Generator가 만든다.
- 결 단계에서는 새로운 메인 갈등/최종 악역/갑작스러운 세계 규칙을 추가하지 않는다.
- 학습 성적이 낮다고 Bad Ending이나 Story 실패로 연결하지 않는다.
- Story는 교재가 아니라 학습이 필요해지는 상황을 제공한다.
- 실제 학습 Concept을 마법/주문/게임 자원으로 억지 치환하지 않는다.
- 동료 고양이는 전문 교사가 아니라 사용자의 고정 동료다.
- 미스터리라면 hidden_truth에 사건의 핵심 진실/원인/동기를 처음부터 고정한다.
- 다른 Theme은 hidden_truth를 빈 문자열로 두되, 위 Theme Story 전개 가이드에 맞는 장기 목표와 결말 규칙을 phase_goals에 반영한다.
- Theme이 달라도 모든 Chapter가 "증거 조사"처럼 보이지 않게 한다.

JSON만 반환한다.
"""

    blueprint = generate_json(
        feature="story_blueprint",
        prompt_version=BLUEPRINT_PROMPT_VERSION,
        prompt=prompt,
        schema=BLUEPRINT_SCHEMA,
        model=DEFAULT_MODEL,
        user_id=user_id,
        world_id=world[0],
        story_arc_id=arc["id"],
        mock_context={
            "topic": world[1],
            "goal": world[2] or "",
            "learner_level": world[3],
            "theme": world[4],
            "guide_name": world[9] if len(world) > 9 else None,
            "curriculum": curriculum,
        },
    )

    update_story_arc_blueprint(
        story_arc_id=arc["id"],
        blueprint=blueprint,
        title=blueprint["title"],
        target_chapter_count=blueprint["target_chapter_count"],
    )
    return blueprint


def ensure_world_foundation(
    *,
    user_id: int,
    world,
) -> dict[str, Any]:
    """
    Curriculum → Blueprint를 분리 저장한다.

    중간 실패 시 이미 성공한 단계는 DB에 남기므로
    다음 재시도에서는 실패한 단계부터 이어간다.
    """
    existing = get_world_foundation(world[0])
    if existing is not None:
        return existing

    arc = get_active_story_arc(world[0])
    if arc is None:
        raise RuntimeError("활성 Story Arc를 찾지 못했습니다.")

    curriculum = _ensure_curriculum(
        user_id=user_id,
        world=world,
    )

    _ensure_blueprint(
        user_id=user_id,
        world=world,
        curriculum=curriculum,
    )

    result = get_world_foundation(world[0])
    if result is None:
        raise RuntimeError(
            "Curriculum/Story Blueprint 저장 상태를 확인하지 못했습니다."
        )
    return result

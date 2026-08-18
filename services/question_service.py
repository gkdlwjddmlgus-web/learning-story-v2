from __future__ import annotations

from components.theme_system import (
    get_theme_prompt_rules,
)
from services.ai_client import DEFAULT_MODEL
from services.generation_gateway import generate_json


QUESTION_COUNT = 5
PROMPT_VERSION = "question_curriculum_v1"


class QuestionGenerationError(
    RuntimeError
):
    """사용자에게 노출 가능한 문제 생성 오류."""


QUESTION_SCHEMA = {
    "type": "array",
    "minItems": QUESTION_COUNT,
    "maxItems": QUESTION_COUNT,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "concept",
            "difficulty",
            "question",
            "choices",
            "correct_index",
            "correct_feedback",
            "wrong_feedback",
            "explanation",
        ],
        "properties": {
            "concept": {
                "type": "string",
            },
            "difficulty": {
                "type": "string",
                "enum": [
                    "intro",
                    "basic",
                    "intermediate",
                    "advanced",
                ],
            },
            "question": {
                "type": "string",
            },
            "choices": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {
                    "type": "string",
                },
            },
            "correct_index": {
                "type": "integer",
                "minimum": 0,
                "maximum": 3,
            },
            "correct_feedback": {
                "type": "string",
                "description": (
                    "고양이가 정답에 감정적으로 반응하는 1문장. "
                    "전문 개념 강의 금지."
                ),
            },
            "wrong_feedback": {
                "type": "string",
                "description": (
                    "고양이가 오답에 격려/관찰을 전달하는 1문장. "
                    "전문 개념 강의와 정답 직접 제공 금지."
                ),
            },
            "explanation": {
                "type": "string",
                "description": (
                    "고양이 대사가 아닌 중립적 학습 노트. "
                    "현실의 정확한 학습 용어를 사용한 2~4문장 설명."
                ),
            },
        },
    },
}


def _validate_questions(
    questions: list,
    target_concepts: list[str],
    requested_difficulty: str,
) -> list:
    if not isinstance(
        questions,
        list,
    ):
        raise ValueError(
            "문제 생성 결과가 배열이 아닙니다."
        )

    if len(questions) != QUESTION_COUNT:
        raise ValueError(
            f"문제가 {QUESTION_COUNT}개 생성되지 않았습니다."
        )

    allowed = set(
        target_concepts
    )

    for index, item in enumerate(
        questions,
        start=1,
    ):
        choices = item.get(
            "choices"
        )

        if (
            not isinstance(
                choices,
                list,
            )
            or len(choices) != 4
        ):
            raise ValueError(
                f"{index}번 문제의 보기 수가 올바르지 않습니다."
            )

        correct_index = item.get(
            "correct_index"
        )

        if (
            not isinstance(
                correct_index,
                int,
            )
            or not (
                0 <= correct_index <= 3
            )
        ):
            raise ValueError(
                f"{index}번 문제의 정답 인덱스가 올바르지 않습니다."
            )

        concept = (
            item.get(
                "concept",
                ""
            )
            or ""
        ).strip()

        # Curriculum과 다른 개념명이 튀어나오면 가장 가까운
        # 현재 target concept으로 저장 기준을 보정한다.
        if (
            allowed
            and concept not in allowed
        ):
            item["concept"] = (
                target_concepts[
                    (index - 1)
                    % len(target_concepts)
                ]
            )

        item["difficulty"] = (
            requested_difficulty
        )

    return questions


def generate_chapter_questions(
    topic: str,
    learner_level: str,
    theme: str,
    chapter_title: str,
    chapter_story: str,
    learning_objectives: list[str],
    *,
    target_concepts: list[str] | None = None,
    requested_difficulty: str = "basic",
    guide_name: str | None = None,
    user_id: int | None = None,
    world_id: int | None = None,
    story_arc_id: int | None = None,
) -> list:
    target_concepts = (
        target_concepts
        or [
            objective
            for objective
            in learning_objectives[:2]
        ]
    )

    if not target_concepts:
        raise QuestionGenerationError(
            "이번 Chapter에서 평가할 학습 개념을 찾지 못했습니다."
        )

    theme_rules = (
        get_theme_prompt_rules(
            theme
        )
    )

    cat_tone = (
        """
동화 Theme의 고양이 반응은 자연스러운 냥체를 사용한다.
예: '좋은 선택이다냥!', '조금 헷갈렸던 것 같다냥.'
'무엇일냥?'처럼 문법이 어색한 억지 냥체는 사용하지 않는다.
"""
        if theme == "동화"
        else """
고양이 반응은 짧고 친근한 동료 말투로 쓴다.
필요하면 아주 가볍게 고양이다운 표현을 넣을 수 있지만
Theme 역할극 때문에 학습 문장을 왜곡하지 않는다.
"""
    )

    prompt = f"""
너는 범용 개인화 학습 서비스의 Question Generator다.

학습 주제:
{topic}

학습자 수준:
{learner_level}

Theme:
{theme}

Theme 규칙:
{theme_rules}

현재 Chapter:
{chapter_title}

현재 Story:
{chapter_story}

이번 Chapter의 학습 목표:
{learning_objectives}

Curriculum에서 확정한 평가 Concept:
{target_concepts}

요청 난이도:
{requested_difficulty}

동료 고양이 이름:
{guide_name or "이름 미지정"}

문제 {QUESTION_COUNT}개를 한 번에 생성한다.

[가장 중요한 규칙]
1. 문제는 반드시 target_concepts 안의 실제 학습 개념만 평가한다.
2. Story 상황은 문제의 맥락으로 활용하되 실제 학습 용어를 판타지/마법 용어로 바꾸지 않는다.
3. Story를 몰라도 학습적으로 정답이 명확해야 한다.
4. 객관식 보기 4개, 정답 1개.
5. 같은 질문 구조를 5번 반복하지 않는다.
6. 단순 암기, 비교, 적용, 해석을 적절히 섞는다.
7. requested_difficulty에 맞추되 억지 함정 문제를 만들지 않는다.
8. correct_feedback / wrong_feedback는 고양이의 짧은 감정 반응이다.
9. 고양이는 정답을 직접 가르치거나 전문 개념을 강의하지 않는다.
10. explanation은 고양이 대사가 아니라 중립적인 학습 노트다.
11. explanation은 정확한 현실 용어로 왜 정답인지 2~4문장으로 설명한다.
12. wrong_feedback에 정답을 먼저 말하지 않는다. 정답은 UI와 학습 노트에서 확인한다.

[고양이 말투]
{cat_tone}

반드시 JSON만 반환한다.
"""

    try:
        result = generate_json(
            feature="question_generation",
            prompt_version=(
                PROMPT_VERSION
            ),
            prompt=prompt,
            schema=QUESTION_SCHEMA,
            model=DEFAULT_MODEL,
            user_id=user_id,
            world_id=world_id,
            story_arc_id=story_arc_id,
            mock_context={
                "topic": topic,
                "learner_level": learner_level,
                "theme": theme,
                "guide_name": guide_name,
                "chapter_title": chapter_title,
                "chapter_story": chapter_story,
                "target_concepts": target_concepts,
                "requested_difficulty": requested_difficulty,
                "world_id": world_id,
            },
        )

        return _validate_questions(
            result,
            target_concepts=(
                target_concepts
            ),
            requested_difficulty=(
                requested_difficulty
            ),
        )

    except QuestionGenerationError:
        raise

    except Exception as exc:
        raise QuestionGenerationError(
            "문제를 생성하는 중 AI 요청 또는 형식 오류가 발생했습니다. "
            "잠시 후 다시 시도해주세요."
        ) from exc

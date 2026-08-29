from __future__ import annotations

import json
import re

from components.theme_system import get_theme_prompt_rules
from services.ai_client import AIQuotaExhausted, DEFAULT_MODEL, is_timeout_error
from services.experience_profile_service import (
    build_question_pedagogy_rules,
    get_action_plan,
    get_learner_level_profile,
    get_theme_experience_profile,
)
from services.generation_gateway import generate_json


QUESTION_COUNT = 5
PROMPT_VERSION = "question_curriculum_v12_day4_strong_scaffolding_hotfix"

# 문제 5개는 Story 1개보다 출력량이 크므로 전역 60초보다 약간 긴 제한을 둔다.
# ReadTimeout 이후 자동 재시도는 하지 않아 사용자가 2~3분 묶이는 것을 방지한다.
QUESTION_TIMEOUT_MS = 90_000
QUESTION_MAX_RETRIES = 1
QUESTION_THINKING_LEVEL = "low"
QUESTION_MAX_OUTPUT_TOKENS = 3072


class QuestionGenerationError(RuntimeError):
    """사용자에게 노출 가능한 문제 생성 오류."""


class EvidenceAnswerLeakError(ValueError):
    """생성된 Evidence가 정답 보기를 직접 노출했을 때 사용."""


class ConceptTargetMismatchError(ValueError):
    """생성된 문제의 concept가 현재 Chapter target_concepts 밖일 때 사용."""


class DefinitionRecallQuestionError(ValueError):
    """Q1~Q4가 단순 용어/명칭 회상형 질문으로 되돌아갔을 때 사용."""


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
            "task_label",
            "concept_brief",
            "evidence_summary",
            "evidence_context",
            "evidence_help",
            "question",
            "choices",
            "correct_index",
            "story_progress",
            "resolved_threads",
            "correct_feedback",
            "wrong_feedback",
            "explanation",
        ],
        "properties": {
            "concept": {"type": "string"},
            "difficulty": {
                "type": "string",
                "enum": ["intro", "basic", "intermediate", "advanced"],
            },
            "task_label": {
                "type": "string",
                "description": "Story 안에서 사용자가 지금 수행하는 행동을 짧게 표시.",
            },
            "concept_brief": {
                "type": "string",
                "description": (
                    "문제 전에 필요한 핵심 개념을 가르치는 1~2문장. "
                    "입문/초급은 쉬운 말로 먼저 설명하고 실제 용어를 연결한다. "
                    "가르친 정의를 질문에서 그대로 반복해 용어명만 맞히게 만들지 않는다."
                ),
            },
            "evidence_summary": {
                "type": "string",
                "description": (
                    "사용자가 먼저 읽을 쉬운 상황/자료 요약 1~2문장. "
                    "특히 입문/초급은 원본 로그보다 이해하기 쉬워야 한다. "
                    "관찰할 차이와 확인할 지점만 안내하고 원인/분류/정답/결론을 대신 해석하지 않는다."
                ),
            },
            "evidence_context": {
                "type": "string",
                "description": (
                    "실제형 상세 자료 1~3문장. 로그, 진술, 기록, 설정, 메트릭, 규칙 등. "
                    "입문/초급에서는 요약 뒤에 확인할 수 있는 보조 자료로 사용한다. "
                    "값/상태/순서/조건식 같은 원자료를 제시하고 그 자료가 뜻하는 원인이나 결론은 대신 말하지 않는다."
                ),
            },
            "evidence_help": {
                "type": "string",
                "description": (
                    "생소한 용어/약어 도움말. 필요 없으면 빈 문자열. "
                    "예: DAG: 여러 작업의 실행 순서를 묶은 흐름."
                ),
            },
            "question": {
                "type": "string",
                "description": (
                    "Evidence의 새로운 사례/값/상태/순서/조건을 실제로 적용해야 답할 수 있는 질문. "
                    "Q1~Q4는 '무엇이라고 부릅니까?', '용어/명칭은 무엇입니까?' 같은 단순 명칭 회상형을 사용하지 않는다."
                ),
            },
            "choices": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {"type": "string"},
                "description": (
                    "네 보기는 모두 같은 판단 축과 비슷한 추상화 수준이어야 한다. "
                    "동급 실재 용어 4개가 없으면 다른 범주 용어를 채우지 말고, 같은 축의 흐름/행동/설명 문장 4개로 구성한다."
                ),
            },
            "correct_index": {
                "type": "integer",
                "minimum": 0,
                "maximum": 3,
            },
            "story_progress": {
                "type": "string",
                "description": (
                    "답 제출 후 학습 검토를 거쳐 확정되는 Story 진행 결과 1문장. "
                    "오답이어도 Learning Note를 확인한 뒤 얻을 수 있는 객관적 사실. "
                    "전체 마지막 Chapter가 아니라면 이번 Chapter에서 확인된 범위만 표현한다."
                ),
            },
            "resolved_threads": {
                "type": "array",
                "maxItems": 6,
                "items": {"type": "string"},
                "description": (
                    "이번 문제 결과로 실제 해결된 기존 open thread의 정확한 원문 목록. "
                    "1~4번은 반드시 빈 배열이며, 5번에서만 필요 시 사용한다."
                ),
            },
            "correct_feedback": {
                "type": "string",
                "description": "고양이의 짧은 정답 반응 1문장. 전문 강의 금지.",
            },
            "wrong_feedback": {
                "type": "string",
                "description": "고양이의 짧은 오답 격려/관찰 1문장. 정답 직접 제공 금지.",
            },
            "explanation": {
                "type": "string",
                "description": "중립적인 학습 노트. 정확한 용어로 핵심 이유를 1~2문장 설명.",
            },
        },
    },
}


REASONING_RULES = {
    "intro": """
- 방금 concept_brief에서 배운 핵심 역할·흐름을 한 단계 적용하면 풀 수 있게 한다.
- 복잡한 예외나 여러 선행개념을 동시에 요구하지 않는다.
""",
    "basic": """
- 핵심 개념을 간단한 상황에 적용하거나 두 선택을 비교하게 한다.
- 단순 암기만 반복하지 않되 숨은 선행지식을 요구하지 않는다.
""",
    "intermediate": """
- 원인, 적절한 조치, 흐름, 관측 결과를 연결해 분석하게 한다.
- 5개 중 최소 3개는 적용/진단형으로 만든다.
""",
    "advanced": """
- 아키텍처 선택, failure mode, trade-off, 운영 리스크를 종합 판단하게 한다.
- 단순 정의 문제는 최대 1개만 허용한다.
""",
}


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _strip_choice_prefix(value: object) -> str:
    """AI가 보기 문자열 안에 다시 번호를 넣어 UI에 2. 2. ...가 되는 현상을 제거한다."""
    text = _normalize_text(value)
    return re.sub(
        r"^\s*(?:[①②③④]|\(?[1-4]\)?[.)]|[1-4]\s*번[.)]?)\s*",
        "",
        text,
    ).strip()


def _sanitize_evidence_labels(value: object) -> str:
    """관찰 자료 안의 정답 역할 라벨만 제거한다. 실제 값/순서/로그는 유지한다."""
    text = _normalize_text(value)
    if not text:
        return text

    # [출발지 태그: A] / [이동 통로: B] / 목적지: C 같이 역할을 직접 써주는 라벨 제거
    text = re.sub(
        r"(?i)(출발지(?:\s*태그)?|이동\s*통로|목적지|정답|원인|결론)\s*[:：]\s*",
        "",
        text,
    )
    # (표 형태), (규격 없음), (정형), (비정형)처럼 분류 답을 괄호로 직접 제공하는 표현 제거
    text = re.sub(
        r"\s*[（(]\s*(?:표\s*형태|규격\s*없음|정형\s*데이터?|비정형\s*데이터?|정상|비정상|정답)\s*[)）]",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return _normalize_text(text)


def _compact_match_text(value: object) -> str:
    """공백/구두점/따옴표 차이를 무시하고 직접 문자열 노출을 비교한다."""
    text = _normalize_text(value).casefold()
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE)


def _has_direct_answer_leak(
    evidence: object,
    correct_choice: object,
) -> bool:
    """정답 보기 전체가 Evidence 안에 사실상 그대로 들어가면 True."""
    evidence_key = _compact_match_text(evidence)
    answer_key = _compact_match_text(correct_choice)

    # 한 글자 답은 우연 일치 위험이 커서 자동 차단하지 않는다.
    if len(answer_key) < 2 or not evidence_key:
        return False

    return answer_key in evidence_key


_DEFINITION_RECALL_PATTERNS = (
    re.compile(
        r"(?:무엇이라고|무엇이라)\s*(?:부릅니까|부르나요|부르는가요|합니까|하나요|말합니까)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:용어|명칭)(?:은|는|이|가|을|를)?\s*무엇(?:입니까|인가요|인가|일까요)",
        re.IGNORECASE,
    ),
)


def _is_definition_recall_question(value: object) -> bool:
    """Q1~Q4에서 차단할 전형적인 '용어 이름 맞히기' 표면형을 감지한다."""
    text = _normalize_text(value)
    if not text:
        return False
    return any(pattern.search(text) for pattern in _DEFINITION_RECALL_PATTERNS)


def _build_mastery_question_rules(adaptive_support: dict) -> str:
    """각 target Concept의 mastery 상태를 문제 설명량/적용 방식에 직접 연결한다."""
    statuses = adaptive_support.get("target_statuses") or {}
    unseen = set(adaptive_support.get("unseen_concepts") or [])

    if not statuses and not unseen:
        return "- 상태 정보가 없으면 learner_level의 기본 pedagogy를 적용한다."

    lines: list[str] = []
    ordered_concepts = list(statuses)
    for concept in unseen:
        if concept not in ordered_concepts:
            ordered_concepts.append(concept)

    for concept in ordered_concepts:
        status = "unseen" if concept in unseen else str(statuses.get(concept) or "unknown")
        if status == "weak":
            rule = (
                "짧고 쉬운 재연결 1~2문장만 제공한다. 정식 정의를 그대로 다시 외우게 하지 말고, "
                "새 Story Evidence에 한 단계 적용하게 한다. Q1 우선 후보로 사용할 수 있다."
            )
        elif status == "review":
            rule = (
                "완전한 재강의 대신 1문장 회상 단서/비교 기준만 제공하고, 이전 개념과 현재 Evidence를 연결하게 한다."
            )
        elif status == "strong":
            rule = (
                "이미 아는 개념처럼 사용한다. concept_brief에는 정의·원리·정답 인과를 다시 설명하지 말고, "
                "'앞서 배운 기준을 이번 자료에 적용해보자' 수준의 중립적인 적용 지시 1문장만 둔다. "
                "특히 Q5에서는 복구 가능성, 해결 방법, 최종 결론을 concept_brief에서 먼저 말하지 않는다."
            )
        elif status == "unseen":
            rule = (
                "쉬운 말로 핵심 뜻을 먼저 가르치되, 바로 뒤에서 그 정의의 명칭을 회상시키지 않는다. "
                "새 Evidence 사례에 적용하도록 한다."
            )
        else:
            rule = "learner_level의 기본 설명량을 유지하되 Evidence 적용형으로 만든다."
        lines.append(f"- {concept}: {status} → {rule}")

    return "\n".join(lines)


def _build_strong_concept_brief(index: int, concept: str) -> str:
    """Strong Concept는 재강의 대신 중립적인 적용/종합 지시만 노출한다."""
    if index == QUESTION_COUNT:
        return (
            f"앞선 조사에서 확인한 서로 다른 근거를 함께 놓고 '{concept}'의 관점에서 "
            "이번 단계의 결론이나 다음 조치를 판단해봅니다."
        )
    return (
        f"앞서 배운 '{concept}'의 기준을 이번 Story 자료에 적용해 "
        "비교하거나 판단해봅니다."
    )


def _format_action_plan(plan: list[tuple[str, str, str]]) -> str:
    return "\n".join(
        f"{index}. task_role={role} | 권장 라벨={label} | {instruction}"
        for index, (role, label, instruction) in enumerate(plan, start=1)
    )


def _theme_integration_rules(
    *,
    theme: str,
    interaction_mode: str | None,
    interaction_goal: str | None,
    action_plan: list[tuple[str, str, str]],
) -> str:
    profile = get_theme_experience_profile(theme)
    return f"""
[{theme} Story-integrated Learning Task]
이번 행동 방식: {interaction_mode or '상황 적용'}
이번 행동 목표: {interaction_goal or '현재 Story의 문제를 학습 Concept로 한 단계 해결한다.'}

Theme 경험 규칙:
{profile['writer_rules']}

[이번 Chapter의 5단계 행동 - 순서와 task_role을 지킨다]
{_format_action_plan(action_plan)}

중요:
- 다섯 문제를 '교과서 문제 5개'가 아니라 위 다섯 행동으로 느끼게 만든다.
- 같은 4지선다여도 사용자가 하는 인지 행동은 관찰/비교/추적/검증/설계/정리처럼 달라야 한다.
- task_label은 Theme 세계에서 실제로 하는 행동처럼 짧게 쓴다.
- evidence_summary에는 사용자가 먼저 이해할 쉬운 상황 요약을 쓴다.
- evidence_context에는 Story 속 실제 자료를 쓴다.
- story_progress는 Theme에 맞는 진행 결과다. 학습 설명이 아니라 Story에서 새로 확인된 사실/변화다.
- 1~4번은 서로 다른 중간 진행을 만들고, 5번은 앞의 결과와 새 자료를 합쳐 Chapter 결론으로 수렴한다.
- 마지막 문제를 매번 '범인 찾기'나 '최종 해결'로 만들지 않는다. 전체 Story 결말에 가까울 때만 최종 결론을 허용한다.
"""


def _validate_questions(
    questions: list,
    target_concepts: list[str],
    requested_difficulty: str,
    *,
    expected_roles: list[str] | None = None,
    current_open_threads: list[str] | None = None,
    adaptive_support: dict | None = None,
) -> list:
    if not isinstance(questions, list):
        raise ValueError("문제 생성 결과가 배열이 아닙니다.")

    if len(questions) != QUESTION_COUNT:
        raise ValueError(f"문제가 {QUESTION_COUNT}개 생성되지 않았습니다.")

    allowed = set(target_concepts)
    support = adaptive_support or {}
    target_statuses = support.get("target_statuses") or {}
    strong_concepts = {
        concept
        for concept, status in target_statuses.items()
        if str(status).casefold() == "strong"
    }
    seen_questions: set[str] = set()
    seen_task_labels: set[str] = set()
    seen_summaries: set[str] = set()

    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{index}번 문제가 객체 형식이 아닙니다.")

        question = _normalize_text(item.get("question"))
        if not question:
            raise ValueError(f"{index}번 문제의 질문이 비어 있습니다.")
        if question.casefold() in seen_questions:
            raise ValueError(f"{index}번 문제가 이전 문제와 중복됩니다.")
        if index < QUESTION_COUNT and _is_definition_recall_question(question):
            raise DefinitionRecallQuestionError(
                f"{index}번 문제가 단순 용어/명칭 회상형 질문입니다: {question}"
            )
        seen_questions.add(question.casefold())
        item["question"] = question

        choices = item.get("choices")
        if not isinstance(choices, list) or len(choices) != 4:
            raise ValueError(f"{index}번 문제의 보기 수가 올바르지 않습니다.")

        cleaned_choices = [_strip_choice_prefix(choice) for choice in choices]
        if any(not choice for choice in cleaned_choices):
            raise ValueError(f"{index}번 문제에 빈 보기가 있습니다.")
        if len({choice.casefold() for choice in cleaned_choices}) != 4:
            raise ValueError(f"{index}번 문제에 중복 보기가 있습니다.")
        item["choices"] = cleaned_choices

        correct_index = item.get("correct_index")
        if not isinstance(correct_index, int) or not 0 <= correct_index <= 3:
            raise ValueError(f"{index}번 문제의 정답 인덱스가 올바르지 않습니다.")

        concept = _normalize_text(item.get("concept"))
        if allowed and concept not in allowed:
            raise ConceptTargetMismatchError(
                f"{index}번 문제의 concept '{concept}'가 "
                f"현재 Chapter target_concepts {target_concepts}에 없습니다."
            )
        item["concept"] = concept

        item["difficulty"] = requested_difficulty

        task_label = _normalize_text(item.get("task_label"))
        concept_brief = _normalize_text(item.get("concept_brief"))
        if concept in strong_concepts:
            concept_brief = _build_strong_concept_brief(index, concept)
        evidence_summary = _sanitize_evidence_labels(item.get("evidence_summary"))
        evidence_context = _sanitize_evidence_labels(item.get("evidence_context"))
        evidence_help = _normalize_text(item.get("evidence_help"))
        story_progress = _normalize_text(item.get("story_progress"))
        raw_resolved = item.get("resolved_threads") or []
        if not isinstance(raw_resolved, list):
            raw_resolved = []

        correct_choice = cleaned_choices[correct_index]
        for evidence_name, evidence_value in (
            ("evidence_summary", evidence_summary),
            ("evidence_context", evidence_context),
        ):
            if _has_direct_answer_leak(evidence_value, correct_choice):
                raise EvidenceAnswerLeakError(
                    f"{index}번 문제의 {evidence_name}가 "
                    f"정답 보기 '{correct_choice}'를 직접 노출합니다."
                )

        if not task_label:
            raise ValueError(f"{index}번 문제의 행동 라벨이 비어 있습니다.")
        if not concept_brief:
            raise ValueError(f"{index}번 문제의 개념 브리핑이 비어 있습니다.")
        if not evidence_summary:
            raise ValueError(f"{index}번 문제의 쉬운 자료 요약이 비어 있습니다.")
        if not evidence_context:
            raise ValueError(f"{index}번 문제의 상세 자료가 비어 있습니다.")
        if not story_progress:
            raise ValueError(f"{index}번 문제의 Story 진행 결과가 비어 있습니다.")

        task_key = task_label.casefold()
        summary_key = evidence_summary.casefold()
        if task_key in seen_task_labels:
            raise ValueError(f"{index}번 문제의 행동이 이전 문제와 중복됩니다.")
        if summary_key in seen_summaries:
            raise ValueError(f"{index}번 문제의 자료 요약이 이전 문제와 중복됩니다.")
        seen_task_labels.add(task_key)
        seen_summaries.add(summary_key)

        item["task_role"] = (
            expected_roles[index - 1]
            if expected_roles and index <= len(expected_roles)
            else f"step_{index}"
        )
        item["task_label"] = task_label
        item["concept_brief"] = concept_brief
        item["evidence_summary"] = evidence_summary
        item["evidence_context"] = evidence_context
        item["evidence_help"] = evidence_help
        item["story_progress"] = story_progress

        allowed_threads = set(current_open_threads or [])
        if index < QUESTION_COUNT:
            item["resolved_threads"] = []
        else:
            item["resolved_threads"] = [
                _normalize_text(thread)
                for thread in raw_resolved
                if _normalize_text(thread) in allowed_threads
            ]

        explanation = _normalize_text(item.get("explanation"))
        if not explanation:
            raise ValueError(f"{index}번 문제의 학습 노트가 비어 있습니다.")
        item["explanation"] = explanation
        item["correct_feedback"] = _normalize_text(item.get("correct_feedback"))
        item["wrong_feedback"] = _normalize_text(item.get("wrong_feedback"))

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
    adaptive_support: dict | None = None,
    guide_name: str | None = None,
    interaction_mode: str | None = None,
    interaction_goal: str | None = None,
    chapter_number: int | None = None,
    target_chapter_count: int | None = None,
    current_open_threads: list[str] | None = None,
    user_id: int | None = None,
    world_id: int | None = None,
    story_arc_id: int | None = None,
) -> list:
    target_concepts = target_concepts or [
        objective for objective in learning_objectives[:2]
    ]

    if not target_concepts:
        raise QuestionGenerationError(
            "이번 Chapter에서 평가할 학습 개념을 찾지 못했습니다."
        )

    theme_rules = get_theme_prompt_rules(theme)
    theme_profile = get_theme_experience_profile(theme)
    support_profile = get_learner_level_profile(learner_level)
    adaptive_support = adaptive_support or {
        "mode": "standard",
        "label": "기본 지원",
        "rule": "사용자가 선택한 학습 수준의 기본 설명량을 유지한다.",
        "target_statuses": {},
        "unseen_concepts": [],
    }
    pedagogy_rules = build_question_pedagogy_rules(
        learner_level=learner_level,
        requested_difficulty=requested_difficulty,
    )
    action_plan = get_action_plan(
        theme=theme,
        interaction_mode=interaction_mode,
    )
    expected_roles = [role for role, _, _ in action_plan]

    cat_tone = (
        """
동화 Theme의 고양이 반응은 자연스러운 귀여운 말투를 사용할 수 있다.
문장마다 억지로 '냥'을 붙이지 않는다.
"""
        if theme == "동화"
        else """
고양이 반응은 짧고 친근한 동료 말투로 쓴다.
고양이는 학습 개념을 강의하지 않는다.
"""
    )

    theme_integration = _theme_integration_rules(
        theme=theme,
        interaction_mode=interaction_mode,
        interaction_goal=interaction_goal,
        action_plan=action_plan,
    )
    reasoning_rules = REASONING_RULES.get(
        requested_difficulty,
        REASONING_RULES["basic"],
    )
    mastery_question_rules = _build_mastery_question_rules(adaptive_support)
    is_final_chapter = bool(
        chapter_number
        and target_chapter_count
        and chapter_number >= target_chapter_count
    )
    open_threads_json = json.dumps(
        current_open_threads or [],
        ensure_ascii=False,
    )

    prompt = f"""
너는 개인화 학습 Story 서비스의 Story-integrated Question Generator다.

최우선 목표:
1) 사용자가 새로운 지식을 실제로 배운다.
2) 방금 배운 지식을 Story 속 행동에 사용한다.
3) 문제를 맞히면 Story가 한 단계 진행된다.

'이미 아는 사람만 풀 수 있는 복습 퀴즈'도 실패고,
'Story를 읽기만 하면 지식 없이 맞히는 문제'도 실패다.

[학습 정보]
학습 주제: {topic}
사용자가 선택한 현재 수준: {learner_level}
Theme: {theme}
현재 Chapter: {chapter_title}
학습 목표: {learning_objectives}
평가 Concept: {target_concepts}
적응형 사고 난이도: {requested_difficulty}
현재 Chapter 번호: {chapter_number or "미상"}
전체 Chapter 수: {target_chapter_count or "미상"}
전체 마지막 Chapter 여부: {is_final_chapter}

[현재 미해결 Story Thread - 정확한 원문]
{open_threads_json}

[현재 Chapter Story]
{chapter_story}

[Theme 규칙]
{theme_rules}

{theme_integration}

{pedagogy_rules}

[Mastery 기반 Adaptive Scaffolding]
모드: {adaptive_support.get('mode')}
표시: {adaptive_support.get('label')}
이번 target 상태: {json.dumps(adaptive_support.get('target_statuses') or {}, ensure_ascii=False)}
미학습 target: {json.dumps(adaptive_support.get('unseen_concepts') or [], ensure_ascii=False)}
규칙: {adaptive_support.get('rule')}

Concept별 실제 문제 작성 규칙:
{mastery_question_rules}

- 각 question의 concept를 정한 뒤 위 상태 규칙을 그 문제의 concept_brief와 질문 방식에 직접 적용한다.
- weak는 '쉬운 보기'가 아니라 '짧은 재연결 + 새로운 Evidence 적용'으로 지원한다.
- strong은 concept_brief에서 개념 지식 자체를 다시 설명하지 않는다. 중립적인 적용/비교 지시만 1문장으로 두고 이미 아는 개념을 Story 판단 도구로 사용한다.
- strong이 Q5에 배치되면 concept_brief에서 복구 가능성, 해결 방법, 원인-결과, 종합 결론을 선공개하지 않는다.
- scaffolding은 '얼마나 도와줄지'를 조절하고 requested_difficulty는 '얼마나 깊게 생각할지'를 조절한다.
- weak라고 오답을 우스꽝스럽게 만들거나 정답을 evidence에 써주지 않는다.
- challenge여도 learner_level의 선행지식 가정은 유지한다.

[동료 고양이]
이름: {guide_name or '이름 미지정'}
{cat_tone}

문제 {QUESTION_COUNT}개를 한 번에 생성한다.

[가르친 뒤 적용하기]
배우기 전에 시험부터 보게 하지 않는다.
1. concept_brief의 설명량은 위 Mastery 상태 규칙을 우선한다. weak/unseen은 필요한 만큼 먼저 가르치고, strong은 정의·원리·정답 인과를 다시 설명하지 않고 중립적인 적용 지시만 둔다.
2. concept_brief는 정답 번호나 현재 evidence의 결론을 직접 말하지 않는다.
2-1. concept_brief에서 용어의 정의/역할을 가르쳤다면 question에서 그 정의를 거의 그대로 다시 적고 '이 용어는 무엇인가?'라고 묻지 않는다.
2-2. Q1~Q4에서는 '무엇이라고 부릅니까?', '무엇이라 합니까?', '용어/명칭은 무엇입니까?' 같은 이름 회상형 질문을 사용하지 않는다. 배운 용어는 보기의 이름을 맞히는 대상이 아니라 Evidence를 해석하는 도구로 사용한다.
2-3. concept_brief와 question만 읽고 Evidence를 보지 않아도 정답이 확정된다면 실패다. 정답 판단에는 evidence_summary/evidence_context의 사례, 값, 상태, 순서, 조건 중 최소 하나를 실제로 적용하게 한다.
2-4. teach-before-test의 목적은 답을 미리 알려주는 것이 아니라, 배운 개념을 새로운 Story 자료에 적용할 수 있게 만드는 것이다.
3. 입문 사용자는 해당 분야를 처음 본다고 가정한다. 새 용어를 알아야만 풀 수 있다면 반드시 먼저 뜻을 알려주되 바로 그 용어 이름을 묻지 않는다.
4. 초급도 생소한 약어/운영 용어를 설명 없이 전제로 두지 않는다.
5. evidence_help에는 이번 자료를 읽는 데 필요한 새 용어만 짧게 설명한다.
6. learner_level={learner_level}의 지원 수준은 적응형 난이도가 올라가도 유지한다.

[자료 제시 - 답안지가 아닌 실제 관찰 자료]
7. evidence_summary는 먼저 읽는 쉬운 한국어 브리핑이다. 관찰된 상황만 요약하고 분류/원인/정답을 대신 판정하지 않는다.
7-1. evidence_summary의 역할은 '무엇을 비교/확인할지' 안내하는 것이다. '때문에', '따라서', '원인은', '오류로', '걸러져서', '제거되어', '확인되었다/밝혀졌다'처럼 질문의 결론을 대신 완성하는 표현은 그 문장이 정답 판단을 직접 제공한다면 쓰지 않는다.
7-2. 나쁜 요약: '필터 조건 오류 때문에 A가 누락되었다.' 좋은 요약: '원본에는 A가 있지만 결과에는 없습니다. A의 상태 값과 처리 조건을 비교해보세요.'
8. evidence_context는 실제형 상세 자료다. {theme_profile['source_label']}의 느낌으로 Story에 자연스럽게 배치한다.
8-1. evidence_context에는 로그, 값, 상태, 시각, 입력/출력, 처리 순서, 조건식처럼 관찰 가능한 원자료를 우선 제시한다.
8-2. '조건 미충족 → 제거됨', '이 설정 때문에 실패함'처럼 원자료와 해석을 한 문장에 합쳐 질문의 원인/결론을 대신 말하지 않는다. 예: 'WHERE status = COMPLETED'와 'A102 status = PENDING'은 허용하지만, 'PENDING이라 필터에서 제거됨'은 질문이 그 원인을 묻는다면 금지한다.
9. evidence_summary/evidence_context에 '출발지:', '목적지:', '이동 통로:', '정답:', '원인:'처럼 문제에서 찾아야 할 역할 라벨을 직접 붙이지 않는다.
10. '(표 형태)', '(규격 없음)', '(정형)', '(비정형)', '(정상)', '(비정상)'처럼 정답 분류를 괄호로 써주지 않는다. 값, 순서, 문장, 로그 등 관찰 가능한 사실만 제시한다.
10-1. 질문이 장소/방식/개념/단계/원인 중 하나를 식별하게 한다면, evidence_summary/evidence_context에 정답 보기 전체 문자열이나 정답 보기의 핵심 명칭/약어를 그대로 쓰지 않는다.
10-2. 정답의 이름 대신 사용자가 그 답을 추론할 수 있는 관찰 특성, 입력/출력, 처리 순서, 시각, 형태, 동작 결과를 제시한다.
10-3. 예를 들어 정답이 '데이터 웨어하우스'라면 Evidence에 '데이터 웨어하우스'라고 쓰지 말고, '정제·규격화된 데이터를 분석용으로 보관하는 영역'처럼 특징을 보여준다.
10-4. 문자열 정답명이 없더라도 Evidence가 사실상 '그래서 정답은 이것'이라고 의미상 결론까지 설명하면 실패다. 관찰 사실과 최종 판단 사이에 사용자가 직접 수행할 추론 한 단계를 남긴다.
11. 입문/초급에서는 원본 로그 한 줄만 던지고 알아서 해석하라고 하지 않는다. 다만 쉬운 설명이 정답 자체를 말해서도 안 된다.
12. 중급/고급에서는 실제형 로그·설정·메트릭을 적극 활용할 수 있다.
13. Story 설정을 장황하게 다시 쓰지 않는다. 문제에 필요한 자료만 제시한다.

[평가 타당성]
14. 각 문제는 target_concepts 중 하나의 실제 이해/적용을 요구한다.
14-1. JSON의 concept 필드는 반드시 target_concepts에 있는 문자열 하나를 철자/괄호/영문 표기까지 그대로 복사한다. 동의어, 축약, 재표현으로 바꾸지 않는다.
15. 문제에 필요한 선행지식은 현재 수준에 맞게 concept_brief/evidence_help에서 제공한다.
16. 학습 주제를 모르는 사람이 단순 국어적 소거만으로 정답을 고를 수 없게 한다.
17. 정답은 Story 문장을 그대로 복사한 보기여서는 안 된다.
18. 동시에 입문 사용자가 아직 가르쳐주지 않은 전문지식을 알아야만 맞히는 문제도 금지한다.

[보기 - 먼저 판단 축을 정한 뒤 4개를 만든다]
19. 보기를 쓰기 전에 내부적으로 이번 문제의 '판단 축(choice axis)'을 하나 정한다. 예: 처리 순서, 문제 발생 단계, 원인 후보, 복구 조치, 설계 선택. 출력에는 axis 이름을 쓰지 않는다.
19-1. 네 보기는 모두 그 한 문장의 같은 빈칸에 들어갈 수 있어야 하며, 같은 기술 범주/역할/추상화 수준이어야 한다.
19-2. '관련 있는 기술 용어'라는 이유만으로 경쟁 후보가 아닌 개념을 섞지 않는다. ETL/ELT 판단에 FTP/API를 넣거나, Ingestion 판단에 Visualization/Modeling/Encryption을 넣는 것은 실패다.
19-3. 같은 범주의 실재 명칭이 4개 없으면 '용어 이름 맞히기' 문제 자체를 만들지 않는다. 대신 질문을 '어떤 흐름/해석/행동/설계가 Evidence와 가장 맞는가?'로 바꾸고 네 보기를 모두 같은 축의 완결된 설명 문장으로 만든다.
19-4. 정답 1개 + 완전히 다른 범주의 용어 3개로 숫자만 채우는 방식을 금지한다.
20. '출발지/목적지/입구' 세 개와 '중간 처리 장치' 하나처럼 역할 자체가 다른 보기를 섞지 않는다.
21. 오답도 실제 초보자가 Evidence의 한 값/순서/조건을 잘못 읽으면 고를 수 있는 그럴듯한 후보로 만든다.
21-1. Story/Evidence에 근거가 없는 물리적 파괴, 외부 침입, 전면 삭제, 전원 차단 같은 극단적 사건을 편의상 오답으로 만들지 않는다.
22. '모두 삭제', '오류를 무시', '그대로 방치', '무조건 강제로 넣기'처럼 정답과 비교 가치가 없는 극단적 오답을 남발하지 않는다.
23. 농담성/분야 밖 보기를 금지한다.
24. 정답만 유독 길거나 전문적인 형태를 금지한다. 네 보기 길이와 전문 용어 밀도를 비슷하게 맞춘다.
25. choices 문자열 안에는 '1.', '2번.', '③' 같은 번호를 직접 쓰지 않는다. UI가 번호를 붙인다.
26. 정답 번호는 1~4번에 분산하고 같은 번호를 3회 이상 사용하지 않는다.

[Q1~Q5 인지 Blueprint - action_plan의 Story 행동과 동시에 지킨다]
22. task_label/Theme 행동은 위 action_plan을 따르되, 학습 인지 기능은 아래 Blueprint를 우선한다.
22-1. Q1 = 적용 시작. weak/review Concept가 있으면 우선 사용한다. 정의 이름을 묻지 말고, concept_brief의 짧은 재연결을 새로운 Evidence 사례에 적용해 첫 판단을 하게 한다.
22-2. Q2 = 비교/구분. 다른 target Concept가 있으면 가능하면 활용한다. 두 방식/흐름/규칙/사례의 차이를 Evidence 기준으로 구분하게 한다. 이름 회상 문제가 아니다.
22-3. Q3 = 범위/단계 좁히기. 이상·차이·문제가 '어디/언제/어느 단계/어느 조건 범위'에서 시작되는지 찾게 하되, 아직 세부 root cause를 확정하지 않는다.
22-4. Q4 = 구체 검증. 실제 값/규칙/조건/기록을 대조해 Q3에서 좁힌 범위 안의 구체 원인·조건·가설을 검증한다.
22-5. Q5 = 종합/의미/조치. 최소 두 개의 독립된 관찰 사실 또는 앞 문제에서 확보한 서로 다른 결과를 연결해 이번 Chapter 범위의 결론, 복구 가능성, 다음 조치, 의미 중 하나를 판단하게 한다.
22-6. 한 target Concept만 있어도 다섯 문제를 정의 반복으로 채우지 않는다. 같은 Concept의 서로 다른 적용·비교·진단·검증·종합 행동으로 변주한다.
22-7. 여러 target Concept가 있다면 한 Concept만 4~5문제 연속 사용하지 않는다. weak/review를 우선하되 다른 target도 자연스럽게 연결한다.
22-8. 앞 문제가 뒤 문제의 정답 문장을 이미 완성해버리면 실패다. Q3에서 범위를 좁히고 Q4에서 구체 원인을 검증하는 식으로 정보 공개 깊이를 단계적으로 조절한다.
23. 같은 '가장 올바른 설명은?' 문장만 5번 반복하지 않는다.
24. task_label은 사용자가 지금 Story에서 하는 행동을 보여준다.
25. 1~4번 story_progress는 서로 다른 중간 진행을 만든다. story_progress가 다음 문제의 정답을 직접 선공개하지 않게 한다.
26. 5번 story_progress는 앞 결과와 새 자료를 종합한 이번 Chapter 결론이다.
26-1. Q5는 Q3/Q4에서 이미 완성된 결론 문장을 다시 고르는 문제가 아니다. 최소 두 개의 독립된 관찰 사실을 연결해 이번 Chapter에서 얻은 의미/결론을 종합하게 한다.
26-2. Q5의 concept_brief/evidence_summary/evidence_context도 그 종합 결론을 먼저 문장으로 말하지 않는다. 사용자가 앞선 결과와 현재 자료를 결합할 여지를 남긴다.
26-3. Q5의 concept가 strong이면 concept_brief는 개념 설명이 아니라 '앞선 근거를 함께 놓고 판단해보자' 수준의 중립적인 종합 지시만 사용한다. 복구 가능성/해결 방법/정답 인과를 먼저 설명하면 실패다.
27. story_progress는 학습 해설 문장이 아니라 Story에서 확인된 사실/변화다.
28. 전체 마지막 Chapter가 아니라면 5번 story_progress도 '이번 단계에서 확인/좁힌/정리한 범위'까지만 말한다. '완벽히 해결', '완전히 해결', '사건 종결', '최종 원인 확정' 같은 과도한 종결 표현을 금지한다.
29. 1~4번 resolved_threads는 반드시 []다. 5번에서 실제로 해결한 기존 open thread가 있다면 위 [현재 미해결 Story Thread]의 문자열을 한 글자도 바꾸지 않고 resolved_threads에 넣는다. 해결하지 못했다면 []다.
30. 새로 알아낸 후속 문제는 기존 thread를 억지로 해결 처리하지 말고 story_progress/open thread 흐름으로 남긴다.

[사고 난이도]
{reasoning_rules}

[설명/피드백]
28. correct_feedback / wrong_feedback는 고양이의 짧은 감정 반응 1문장이다.
29. 고양이는 전문 개념을 강의하지 않는다.
30. wrong_feedback에서 정답을 먼저 알려주지 않는다.
31. explanation은 중립적인 학습 노트로 정확한 용어를 사용해 1~2문장으로 정리한다.
32. 입문/초급 explanation은 쉬운 설명 뒤 실제 용어를 연결한다.

[출력 전 내부 점검 - 출력에는 쓰지 말 것]
- 각 question의 concept 상태가 weak/review/strong/unseen 중 무엇인지 확인했고, 그 상태에 맞게 concept_brief 설명량을 실제로 바꿨는가?
- strong Concept를 처음 배우는 사람처럼 'X란 ~이다'로 다시 강의하고 있지 않은가? strong의 concept_brief는 개념 사실이 아니라 중립적인 적용/비교/종합 지시 1문장인가?
- Q5가 strong Concept라면 concept_brief에서 '원본이 보존되므로 복구 가능', '규칙을 수정하면 해결'처럼 정답 결론을 먼저 말하고 있지 않은가?
- weak Concept를 정의 이름 맞히기로 쉽게 만든 것이 아니라 짧게 재연결한 뒤 새로운 Evidence에 적용하게 했는가?
- Q1~Q4 질문에 '무엇이라고 부릅니까/합니까', '용어/명칭은 무엇입니까'가 남아 있지 않은가?
- concept_brief와 question만 읽고 Evidence 없이 정답을 확정할 수 있는가? 그렇다면 적용형으로 다시 쓴다.
- evidence_summary만 읽어도 상황 자체는 이해되는가? 단, 원인/분류/결론까지 대신 말하고 있지는 않은가?
- 상세 자료의 생소한 용어가 evidence_help에 설명되어 있는가?
- evidence_summary/evidence_context가 문제의 정답 역할이나 분류를 직접 써주고 있지 않은가? 있다면 관찰 사실만 남기고 다시 쓴다.
- 정답 보기 문자열 또는 정답의 핵심 고유명사/약어가 Evidence에 그대로 등장하지 않는가? 등장한다면 그 명칭을 삭제하고 관찰 특징으로 바꾼다.
- 문자열 정답명이 없어도 '필터 때문에 제거됨', '오류로 누락됨', '따라서 X다'처럼 질문의 추론을 Evidence가 대신 끝내고 있지 않은가?
- 보기를 만들기 전에 하나의 판단 축을 정했는가? 네 보기가 같은 문장 슬롯과 같은 추상화 수준에서 경쟁하는가?
- 동급 실재 용어가 4개 없는데 FTP/API 같은 다른 범주를 숫자 채우기로 넣지 않았는가? 그 경우 4개의 흐름/행동/설명 문장으로 바꿨는가?
- 오답이 Evidence의 현실적인 오독에서 나오나, 아니면 침입/파괴/전면 삭제 같은 터무니없는 사건인가?
- Q1은 적용, Q2는 비교/구분, Q3는 범위/단계 좁히기, Q4는 구체 검증, Q5는 두 근거 이상 종합이라는 인지 역할이 실제로 분리됐는가?
- Q3의 story_progress나 정답이 Q4의 구체 원인을 미리 확정하고 있지 않은가?
- Q5는 concept_brief나 Evidence에서 이미 말한 결론을 복사하는 문제가 아닌가?
- Story를 빼도 완전히 똑같은 교과서 문제인가? 그렇다면 Story 자료/행동과 더 직접 연결한다.
- Story만 읽고 지식 없이 맞힐 수 있는가? 그렇다면 Concept 적용이 필요하도록 다시 쓴다.
- 마지막 story_progress가 이번 Chapter의 자연스러운 결론인가? 아직 전체 마지막이 아니라면 과도하게 '완전 해결'이라고 끝내지 않았는가?
- resolved_threads는 실제로 이번 Chapter에서 해결한 기존 open thread의 정확한 원문만 포함하는가?

반드시 JSON만 반환한다.
"""

    try:
        result = generate_json(
            feature="question_generation",
            prompt_version=PROMPT_VERSION,
            prompt=prompt,
            schema=QUESTION_SCHEMA,
            model=DEFAULT_MODEL,
            user_id=user_id,
            world_id=world_id,
            story_arc_id=story_arc_id,
            timeout_ms=QUESTION_TIMEOUT_MS,
            thinking_level=QUESTION_THINKING_LEVEL,
            max_retries=QUESTION_MAX_RETRIES,
            max_output_tokens=QUESTION_MAX_OUTPUT_TOKENS,
            retry_on_timeout=False,
            mock_context={
                "topic": topic,
                "learner_level": learner_level,
                "theme": theme,
                "guide_name": guide_name,
                "chapter_title": chapter_title,
                "chapter_story": chapter_story,
                "target_concepts": target_concepts,
                "requested_difficulty": requested_difficulty,
                "adaptive_support_mode": adaptive_support.get("mode"),
                "adaptive_support_label": adaptive_support.get("label"),
                "interaction_mode": interaction_mode,
                "interaction_goal": interaction_goal,
                "task_roles": expected_roles,
                "support_mode": support_profile["ui_mode"],
                "world_id": world_id,
                "current_open_threads": current_open_threads or [],
            },
        )

        return _validate_questions(
            result,
            target_concepts=target_concepts,
            requested_difficulty=requested_difficulty,
            expected_roles=expected_roles,
            current_open_threads=current_open_threads or [],
            adaptive_support=adaptive_support,
        )

    except QuestionGenerationError:
        raise

    except ConceptTargetMismatchError as exc:
        raise QuestionGenerationError(
            "생성된 문제의 학습 Concept가 현재 Chapter의 평가 대상과 일치하지 않아 "
            "해당 결과를 폐기했습니다. "
            "잘못된 Concept로 Attempt/Mastery가 기록되는 것을 막기 위한 검증입니다. "
            "일일 AI 요청량을 불필요하게 쓰지 않도록 자동 재생성은 하지 않았습니다. "
            "문제 준비를 다시 눌러 새로 생성해주세요."
        ) from exc

    except DefinitionRecallQuestionError as exc:
        raise QuestionGenerationError(
            "생성된 문제에 단순 용어/명칭 회상형 질문이 포함되어 해당 결과를 폐기했습니다. "
            "DAY 4에서는 배운 개념을 새로운 Evidence에 적용하는 문제를 우선합니다. "
            "일일 AI 요청량을 불필요하게 쓰지 않도록 자동 재생성은 하지 않았습니다. "
            "문제 준비를 다시 눌러 새로 생성해주세요."
        ) from exc

    except EvidenceAnswerLeakError as exc:
        raise QuestionGenerationError(
            "생성된 문제의 증거 자료가 정답을 직접 노출해 해당 결과를 폐기했습니다. "
            "일일 AI 요청량을 불필요하게 쓰지 않도록 자동 재생성은 하지 않았습니다. "
            "문제 준비를 다시 눌러 새로 생성해주세요."
        ) from exc

    except AIQuotaExhausted as exc:
        raise QuestionGenerationError(
            "Gemini의 일일 무료 요청 할당량이 소진되었습니다. "
            "이 경우 자동 재시도는 하지 않습니다. 할당량이 갱신된 뒤 다시 시도해주세요."
        ) from exc

    except Exception as exc:
        if is_timeout_error(exc):
            raise QuestionGenerationError(
                "문제 생성이 90초 안에 완료되지 않았습니다. "
                "자동 재시도는 중단했으니 잠시 후 다시 시도해주세요."
            ) from exc

        raise QuestionGenerationError(
            "문제를 생성하는 중 AI 요청 또는 형식 오류가 발생했습니다. "
            "잠시 후 다시 시도해주세요."
        ) from exc

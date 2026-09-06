from __future__ import annotations

# CURRICULUM_SEMANTIC_CONTRACT_V1_20260906

import hashlib
from typing import Any

from services.experience_profile_service import (
    get_action_plan,
    get_interaction_info,
    pick_interaction_mode,
)


def _seed(*parts: object) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _concepts_for_topic(topic: str) -> list[str]:
    key = topic.lower().strip()
    maps = [
        (("streamlit", "스트림릿"), [
            "Streamlit 실행 구조", "위젯과 rerun", "Session State",
            "레이아웃과 컴포넌트", "캐시와 리소스 관리", "배포와 상태 관리",
        ]),
        (("python", "파이썬"), [
            "변수와 자료형", "조건문", "반복문", "함수", "자료구조", "예외 처리",
        ]),
        (("sql",), [
            "SELECT와 FROM", "WHERE", "GROUP BY", "HAVING", "JOIN", "서브쿼리",
        ]),
        (("통계", "statistics"), [
            "평균과 중앙값", "분산과 표준편차", "확률분포", "표본과 추정", "가설검정", "상관과 회귀",
        ]),
        (("영어", "english"), [
            "기본 인사", "be동사", "일반동사", "의문문", "시제", "일상 회화",
        ]),
    ]
    for needles, concepts in maps:
        if any(needle in key for needle in needles):
            return concepts
    clean = topic.strip() or "학습 주제"
    return [
        f"{clean} 기초 개념", f"{clean} 핵심 용어", f"{clean} 기본 원리",
        f"{clean} 적용 방법", f"{clean} 문제 해결", f"{clean} 종합 응용",
    ]


def _theme_story_bits(theme: str, guide_name: str) -> tuple[str, str, str]:
    table = {
        "동화": ("별빛 서고", "잠겨 있던 이야기 페이지", "포근한 빛이 번지는 서가"),
        "판타지": ("고대 기록탑", "봉인된 길의 기록", "낡은 석문과 별 문양"),
        "SF": ("궤도 연구시설", "응답하지 않는 시스템", "청록 신호가 흐르는 관제실"),
        "무협": ("강호의 객잔", "주인을 잃은 서찰", "먹향이 남은 조용한 방"),
        "미스터리": ("오래된 기록실", "서로 맞지 않는 사건 기록", "희미한 조명 아래의 파일 캐비닛"),
    }
    return table.get(theme, table["판타지"])


def mock_curriculum(context: dict[str, Any]) -> dict:
    topic = context.get("topic", "학습")
    concepts = _concepts_for_topic(topic)
    midpoint = max(1, len(concepts)//2)
    categories = [
        {"name": "기초 이해", "order": 1, "description": f"{topic}의 기본 구조와 핵심 개념을 이해한다."},
        {"name": "적용과 응용", "order": 2, "description": f"{topic}의 개념을 실제 문제에 적용한다."},
    ]
    seq=[]
    for i, concept in enumerate(concepts, 1):
        seq.append({
            "name": concept,
            "category": "기초 이해" if i<=midpoint else "적용과 응용",
            "order": i,
            "initial_difficulty": "intro" if i<=2 else ("basic" if i<=4 else "intermediate"),
            "reviewable": True,
            "description": f"{concept}의 의미와 활용을 학습한다.",
            "semantic_contract": {
                "core_rule": f"{concept}의 핵심 원리와 적용 기준을 정확히 사용한다.",
                "common_misconception": f"{concept}을 이름만 보고 단순화하거나 다른 개념과 혼동하는 것.",
                "reasoning_boundary": f"주어진 근거가 뒷받침하는 범위를 넘어 {concept}에 대한 결론을 단정하지 않는다.",
            },
        })
    return {"summary": f"{topic}을 기초에서 응용까지 단계적으로 익히는 개발용 Curriculum이다.", "categories": categories, "concept_sequence": seq}


def mock_blueprint(context: dict[str, Any]) -> dict:
    theme=context.get("theme","동화")
    topic=context.get("topic","학습")
    guide=context.get("guide_name") or "고양이"
    place, conflict, visual=_theme_story_bits(theme, guide)
    title_map={"동화":"별빛 서고의 빈 페이지","판타지":"기록탑 너머의 길","SF":"사라진 신호의 좌표","무협":"바람이 남긴 서찰","미스터리":"기록되지 않은 밤"}
    return {
        "title": title_map.get(theme, "함께 걷는 첫 이야기"),
        "premise": f"사용자와 {guide}가 {place}에서 {conflict}을 발견하고 원인을 추적한다.",
        "main_conflict": f"{visual} 속에서 드러난 문제를 해결하려면 {topic}에 관한 실제 지식을 차근차근 활용해야 한다.",
        "ending_rule": "마지막 Chapter에서 처음 제시된 핵심 문제를 해결하고 현재 Story Arc를 완결한다.",
        "target_chapter_count": 9,
        "tone": f"{theme} 테마의 차분한 모험과 동료 관계 중심",
        "world_rules": ["학습 개념을 마법 이름으로 바꾸지 않는다.", f"{guide}는 전문 교사가 아닌 고정 동료다.", "해결은 학습과 관찰의 결과로 이루어진다."],
        "forbidden_rules": ["갑작스러운 최종 악역 추가 금지", "학습 실패를 Bad Ending으로 연결 금지", "고양이가 정답을 대신 말하는 전개 금지"],
        "phase_goals": {
            "setup": ["핵심 문제 발견", "사용자와 고양이의 공동 목표 형성"],
            "development": ["문제의 범위 확대", "새 단서와 관계 축적"],
            "turn": ["기존 단서의 의미 재해석", "핵심 진실에 접근"],
            "resolution": ["열린 사건 회수", "처음의 핵심 문제 해결"],
        },
        "hidden_truth": "초기에 보인 기록 누락은 서로 다른 기록 기준이 섞여 발생했다." if theme=="미스터리" else "",
    }


def mock_block_outline(context: dict[str, Any]) -> dict:
    start=int(context.get("start_chapter",1)); end=int(context.get("end_chapter",start+2))
    theme=context.get("theme","동화"); guide=context.get("guide_name") or "고양이"
    concept_plan=context.get("chapter_concept_plan") or {}
    block_no=((start-1)//3)+1
    target_count=int(context.get("target_chapter_count", max(end, 9)))
    recent=set(context.get("recent_interaction_modes") or [])
    chapters=[]

    for n in range(start,end+1):
        concepts=concept_plan.get(n) or concept_plan.get(str(n)) or [f"학습 개념 {n}"]
        phase=context.get("phase_map",{}).get(n) or context.get("phase_map",{}).get(str(n)) or "setup"
        mode=pick_interaction_mode(
            theme=theme,
            chapter_number=n,
            target_chapter_count=target_count,
            phase=phase,
            avoid=recent,
        )
        info=get_interaction_info(theme, mode)
        recent.add(mode)

        chapters.append({
            "chapter_number": n,
            "phase": phase,
            "title_seed": f"{guide}와 함께하는 {info['label']} {n}",
            "narrative_goal": f"{info['label']} 행동을 통해 {concepts[0]}과 연결된 다음 상황을 연다.",
            "learning_bridge": f"Story 행동 속에서 {', '.join(concepts[:2])}을 이해하고 적용한다.",
            "ending_hook": "다음 행동으로 이어지는 작은 변화를 남긴다." if n<end else "이번 이야기 묶음의 진행을 한 단계 정리한다.",
            "target_concepts": list(concepts[:2]),
            "interaction_mode": mode,
            "interaction_goal": info["goal"],
        })

    return {
        "block_number": block_no,
        "block_title": f"{theme} 이야기 묶음 {block_no}",
        "block_goal": f"{guide}와 함께 Theme에 맞는 서로 다른 행동으로 학습 개념을 사용한다.",
        "chapters": chapters,
        "block_resolution": "마지막 Chapter에서 이번 Block의 직접적인 문제를 정리하되 전체 Story Arc의 핵심 갈등은 남긴다.",
    }


def mock_story_chapter(context: dict[str, Any]) -> dict:
    n=int(context.get("chapter_number",1)); theme=context.get("theme","동화"); guide=context.get("guide_name") or "고양이"
    outline=context.get("chapter_outline") or {}
    concepts=outline.get("target_concepts") or context.get("target_concepts") or ["핵심 개념"]
    place, conflict, visual=_theme_story_bits(theme, guide)
    title=outline.get("title_seed") or f"{place}의 {n}번째 기록"
    concept=concepts[0]
    story=(
        f"{visual}을 지나던 당신과 {guide}는 {conflict}과 연결된 작은 이상을 발견했다. "
        f"{guide}는 먼저 답을 내놓기보다 주변을 살피며, 지금까지 보지 못했던 표시 하나를 가리켰다.\n\n"
        f"표시 옆에는 현실의 용어로 '{concept}'을 확인하라는 짧은 기록이 남아 있었다. "
        f"이 지식을 이해해야 다음 장치를 안전하게 다룰 수 있다는 사실만은 분명했다.\n\n"
        f"당신이 기록을 펼치자 멈춰 있던 상황이 조금씩 움직이기 시작했다. "
        f"{guide}는 곁에 앉아 다음 선택을 기다렸고, 이제 실제 개념을 확인할 차례가 되었다."
    )
    end_chapter=int(context.get("block_end_chapter", n))
    total=int(context.get("target_chapter_count",9))
    choices=[]
    if n==end_chapter and n<total:
        choices=["조금 더 기록을 조사한다.", "고양이와 주변 장소를 먼저 살펴본다."]
    return {
        "chapter_number": n,
        "title": title,
        "story": story,
        "learning_objectives": [f"{concept}의 핵심 의미를 설명할 수 있다.", f"{concept}을 간단한 상황에 적용할 수 있다."],
        "story_choices": choices,
        "story_summary": f"Chapter {n}에서 사용자와 {guide}는 {place}의 이상을 발견하고 {concept}을 알아야 다음 단계로 갈 수 있음을 확인했다.",
        "current_location": place,
        "character_updates": [],
        "companion_mood": "호기심",
        "companion_relationship_note": "사용자와 함께 단서를 살피며 신뢰가 조금 쌓였다.",
        "companion_latest_reaction": "사용자가 직접 답을 찾도록 곁에서 기다린다.",
        "confirmed_facts_add": [f"현재 문제를 진행하려면 {concept}을 이해해야 한다."],
        "open_threads_add": ["처음 발견한 이상 현상의 근본 원인은 아직 남아 있다."],
        "resolved_threads": [],
        "latest_event": f"{place}에서 {concept}과 연결된 단서를 발견했다.",
    }


def mock_questions(context: dict[str, Any]) -> list[dict]:
    concepts=context.get("target_concepts") or ["핵심 개념"]
    difficulty=context.get("requested_difficulty","basic")
    seed=_seed(context.get("world_id"),context.get("chapter_title"),','.join(concepts))
    theme=context.get("theme") or "동화"
    mode=context.get("interaction_mode")
    plan=get_action_plan(theme=theme, interaction_mode=mode)
    out=[]

    for i in range(5):
        concept=concepts[i%len(concepts)]
        correct=(seed+i)%4
        choices=[
            f"{concept}의 핵심 조건을 확인한 뒤 상황에 적용한다.",
            f"{concept}과 비슷하지만 현재 조건에는 맞지 않는 방법을 적용한다.",
            f"현재 자료와 맞지 않는 다른 조건을 전제로 판단한다.",
            f"핵심 조건 하나를 놓친 채 일부 결과만 보고 결정한다.",
        ]
        answer=choices[0]
        choices[0],choices[correct]=choices[correct],answer

        role,label,instruction=plan[i] if i < len(plan) else (f"step_{i+1}", f"Mock 단계 {i+1}", "상황을 판단한다.")

        out.append({
            "concept": concept,
            "difficulty": difficulty,
            "task_role": role,
            "task_label": label,
            "concept_brief": f"{concept}은(는) 이번 테스트에서 상황을 판단하기 위한 핵심 개념이다. 먼저 기본 역할을 확인한다.",
            "evidence_summary": f"Mock 요약 {i+1}: {concept}을 적용해야 다음 상황을 이해할 수 있다.",
            "evidence_context": f"Mock 상세 자료 {i+1}: {instruction}",
            "evidence_help": "Mock: 실제 AI 대신 기능 흐름을 확인하기 위한 개발용 자료.",
            "question": f"개발용 Mock 문제 {i+1}. 방금 확인한 '{concept}'을 현재 상황에 적용할 때 가장 적절한 접근은 무엇인가요?",
            "choices": choices,
            "correct_index": correct,
            "story_progress": (
                f"{mode or 'story'} 흐름의 Mock Chapter 결과로 {concept} 관련 핵심 방향을 정리했다."
                if i == 4
                else f"{mode or 'story'} 흐름에서 {concept}과 연결된 Mock 진행을 확인했다."
            ),
            "resolved_threads": (
                list(context.get("current_open_threads") or [])[:1]
                if i == 4
                else []
            ),
            "correct_feedback": "좋아, 배운 기준을 잘 적용했어!",
            "wrong_feedback": "조금 헷갈렸던 것 같아. 방금 배운 기준을 다시 같이 보자.",
            "explanation": f"{concept}을 적용할 때는 문제의 조건과 개념의 핵심 역할을 연결해야 한다. 이 문제는 기능 흐름 테스트를 위한 Mock 데이터다.",
        })
    return out


def generate_mock(feature: str, context: dict[str, Any] | None = None) -> Any:
    context=context or {}
    if feature=="curriculum": return mock_curriculum(context)
    if feature=="story_blueprint": return mock_blueprint(context)
    if feature=="story_block_outline": return mock_block_outline(context)
    if feature=="story_chapter": return mock_story_chapter(context)
    if feature in {"question_generation","questions"}: return mock_questions(context)
    raise ValueError(f"지원하지 않는 Mock feature입니다: {feature}")

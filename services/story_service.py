from __future__ import annotations

import json
from typing import Any

from components.theme_system import get_theme_prompt_rules
from services.ai_client import DEFAULT_MODEL
from services.generation_gateway import generate_json


BLOCK_SIZE = 3
OUTLINE_PROMPT_VERSION = "story_outline_v1"
CHAPTER_PROMPT_VERSION = "story_chapter_lazy_v1"


def get_story_block_start_chapter(chapter_number:int) -> int:
    return ((chapter_number-1)//BLOCK_SIZE)*BLOCK_SIZE+1


def get_story_block_end_chapter(*,start_chapter:int,target_chapter_count:int)->int:
    return min(target_chapter_count, get_story_block_start_chapter(start_chapter)+BLOCK_SIZE-1)


def get_story_phase(*,chapter_number:int,target_chapter_count:int)->str:
    if target_chapter_count<=1: return "resolution"
    progress=chapter_number/target_chapter_count
    if progress<=0.22: return "setup"
    if progress<=0.52: return "development"
    if progress<=0.80: return "turn"
    return "resolution"


OUTLINE_SCHEMA={
    "type":"object","additionalProperties":False,
    "required":["block_number","block_title","block_goal","chapters","block_resolution"],
    "properties":{
        "block_number":{"type":"integer"},"block_title":{"type":"string"},"block_goal":{"type":"string"},
        "chapters":{"type":"array","minItems":1,"maxItems":BLOCK_SIZE,"items":{
            "type":"object","additionalProperties":False,
            "required":["chapter_number","phase","title_seed","narrative_goal","learning_bridge","ending_hook","target_concepts"],
            "properties":{
                "chapter_number":{"type":"integer"},"phase":{"type":"string"},"title_seed":{"type":"string"},
                "narrative_goal":{"type":"string"},"learning_bridge":{"type":"string"},"ending_hook":{"type":"string"},
                "target_concepts":{"type":"array","minItems":1,"maxItems":2,"items":{"type":"string"}},
            },
        }},
        "block_resolution":{"type":"string"},
    },
}

CHAPTER_SCHEMA={
    "type":"object","additionalProperties":False,
    "required":["chapter_number","title","story","learning_objectives","story_choices","story_summary","current_location","character_updates","companion_mood","companion_relationship_note","companion_latest_reaction","confirmed_facts_add","open_threads_add","resolved_threads","latest_event"],
    "properties":{
        "chapter_number":{"type":"integer"},"title":{"type":"string"},"story":{"type":"string"},
        "learning_objectives":{"type":"array","minItems":2,"maxItems":4,"items":{"type":"string"}},
        "story_choices":{"type":"array","maxItems":2,"items":{"type":"string"}},
        "story_summary":{"type":"string"},"current_location":{"type":"string"},
        "character_updates":{"type":"array","maxItems":5,"items":{"type":"object","additionalProperties":False,"required":["name","role","relationship","status","important_info"],"properties":{"name":{"type":"string"},"role":{"type":"string"},"relationship":{"type":"string"},"status":{"type":"string"},"important_info":{"type":"string"}}}},
        "companion_mood":{"type":"string"},"companion_relationship_note":{"type":"string"},"companion_latest_reaction":{"type":"string"},
        "confirmed_facts_add":{"type":"array","maxItems":8,"items":{"type":"string"}},
        "open_threads_add":{"type":"array","maxItems":6,"items":{"type":"string"}},
        "resolved_threads":{"type":"array","maxItems":6,"items":{"type":"string"}},
        "latest_event":{"type":"string"},
    },
}


def _guide_rules(guide_name:str|None)->str:
    if not guide_name:
        return "고양이 이름은 아직 정해지지 않았다. 새 이름을 임의로 만들지 않는다."
    return f"""사용자가 직접 이름 붙인 동료 고양이는 '{guide_name}'이다.
- 모든 Chapter에서 같은 고양이다.
- 처음 만나는 장면을 반복하지 않는다.
- 전문 교사가 아니라 관찰/반응/가벼운 힌트를 담당한다.
- Story에서 '{guide_name}'이라는 이름을 자연스럽게 사용한다."""


def _normalize_outline(result:dict,*,start:int,end:int,concept_plan:dict[int,list[str]],target_count:int)->dict:
    chapters=result.get("chapters") or []
    expected=list(range(start,end+1))
    by={int(x.get("chapter_number",-1)):dict(x) for x in chapters}
    if any(n not in by for n in expected):
        raise ValueError("Story Block Outline의 Chapter 번호가 요청과 일치하지 않습니다.")
    normalized=[]
    for n in expected:
        item=by[n]
        item["phase"]=get_story_phase(chapter_number=n,target_chapter_count=target_count)
        item["target_concepts"]=list(concept_plan.get(n) or item.get("target_concepts") or [])[:2]
        if not item["target_concepts"]:
            raise ValueError(f"Chapter {n} Outline에 target concept이 없습니다.")
        normalized.append(item)
    result=dict(result); result["chapters"]=normalized; result["block_number"]=((start-1)//BLOCK_SIZE)+1
    return result


def generate_story_block_outline(
    *,topic:str,goal:str,learner_level:str,theme:str,guide_name:str|None,
    blueprint:dict[str,Any],story_state:dict[str,Any]|None,chapter_concept_plan:dict[int,list[str]],
    start_chapter:int,target_chapter_count:int,recent_profile:dict|None=None,global_profile:dict|None=None,
    latest_choice:dict|None=None,user_id:int|None=None,world_id:int|None=None,story_arc_id:int|None=None,
)->dict:
    end=get_story_block_end_chapter(start_chapter=start_chapter,target_chapter_count=target_chapter_count)
    phase_map={n:get_story_phase(chapter_number=n,target_chapter_count=target_chapter_count) for n in range(start_chapter,end+1)}
    theme_rules=get_theme_prompt_rules(theme)
    prompt=f"""너는 Story Block Planner다. 긴 본문을 쓰지 말고 Chapter {start_chapter}~{end}의 방향만 짧은 JSON으로 설계한다.
학습 주제: {topic}\n목표: {goal}\n수준: {learner_level}\nTheme 규칙:\n{theme_rules}\n고양이:\n{_guide_rules(guide_name)}
Blueprint:\n{json.dumps(blueprint,ensure_ascii=False)}\n현재 Story State:\n{json.dumps(story_state or {},ensure_ascii=False,default=str)}
최근 Story Choice: {(latest_choice or {}).get('choice_text','없음')}
최근 학습: {json.dumps(recent_profile or {},ensure_ascii=False)}\n장기 학습: {json.dumps(global_profile or {},ensure_ascii=False)}
Chapter별 확정 Concept: {json.dumps(chapter_concept_plan,ensure_ascii=False)}
규칙: 본문을 쓰지 않는다. 각 Chapter는 title_seed/narrative_goal/learning_bridge/ending_hook만 계획한다. Story는 독립적으로 재미있어야 하고 실제 Concept을 마법 이름으로 바꾸지 않는다. Block 마지막은 한 단계 정리하되 전체 Arc가 끝나지 않았다면 메인 갈등은 남긴다. JSON만 반환한다."""
    result=generate_json(
        feature="story_block_outline",prompt_version=OUTLINE_PROMPT_VERSION,prompt=prompt,schema=OUTLINE_SCHEMA,model=DEFAULT_MODEL,
        user_id=user_id,world_id=world_id,story_arc_id=story_arc_id,
        mock_context={"topic":topic,"goal":goal,"learner_level":learner_level,"theme":theme,"guide_name":guide_name,"start_chapter":start_chapter,"end_chapter":end,"target_chapter_count":target_chapter_count,"chapter_concept_plan":chapter_concept_plan,"phase_map":phase_map},
    )
    return _normalize_outline(result,start=start_chapter,end=end,concept_plan=chapter_concept_plan,target_count=target_chapter_count)


def _normalize_chapter(item:dict,*,chapter_number:int,target_concepts:list[str],phase:str,block_end:int,target_count:int)->dict:
    if int(item.get("chapter_number",-1))!=chapter_number: raise ValueError("생성 Chapter 번호가 요청과 다릅니다.")
    if not str(item.get("title") or "").strip() or not str(item.get("story") or "").strip(): raise ValueError("Chapter title/story가 비어 있습니다.")
    choices=[str(x).strip() for x in item.get("story_choices",[]) if str(x).strip()]
    if chapter_number!=block_end or chapter_number>=target_count: choices=[]
    item=dict(item)
    item["story_choices"]=[{"key":chr(ord('A')+i),"text":text} for i,text in enumerate(choices[:2])]
    item["target_concepts"]=list(target_concepts[:2])
    item["story_phase"]=phase
    item["state_update"]={
        "story_summary":item.pop("story_summary",""),"current_location":item.pop("current_location",""),
        "character_updates":item.pop("character_updates",[]),
        "companion_state":{"mood":item.pop("companion_mood",""),"relationship_note":item.pop("companion_relationship_note",""),"latest_reaction":item.pop("companion_latest_reaction","")},
        "confirmed_facts_add":item.pop("confirmed_facts_add",[]),"open_threads_add":item.pop("open_threads_add",[]),
        "resolved_threads":item.pop("resolved_threads",[]),"latest_event":item.pop("latest_event",""),
    }
    return item


def generate_story_chapter(
    *,topic:str,goal:str,learner_level:str,theme:str,guide_name:str|None,blueprint:dict[str,Any],story_state:dict[str,Any]|None,
    block_outline:dict[str,Any],chapter_outline:dict[str,Any],chapter_number:int,target_chapter_count:int,
    recent_profile:dict|None=None,global_profile:dict|None=None,user_id:int|None=None,world_id:int|None=None,story_arc_id:int|None=None,
)->dict:
    block_end=int(max(x["chapter_number"] for x in block_outline.get("chapters",[chapter_outline])))
    phase=get_story_phase(chapter_number=chapter_number,target_chapter_count=target_chapter_count)
    concepts=list(chapter_outline.get("target_concepts") or [])[:2]
    prompt=f"""너는 개인화 학습 Story의 단일 Chapter Writer다. 지금 필요한 Chapter {chapter_number} 하나만 작성한다.
학습: {topic} / {goal} / {learner_level}\nTheme:\n{get_theme_prompt_rules(theme)}\n고양이:\n{_guide_rules(guide_name)}
Blueprint:\n{json.dumps(blueprint,ensure_ascii=False)}\n현재 Story State(이미 완료한 Chapter까지만 반영):\n{json.dumps(story_state or {},ensure_ascii=False,default=str)}
이번 Block Outline:\n{json.dumps(block_outline,ensure_ascii=False)}\n이번 Chapter Outline:\n{json.dumps(chapter_outline,ensure_ascii=False)}
최근 학습: {json.dumps(recent_profile or {},ensure_ascii=False)}\n장기 학습: {json.dumps(global_profile or {},ensure_ascii=False)}
규칙: 한국어 250~450자, 짧은 3문단. 사건→단서/정보→학습 필요성→다음 행동. Concept는 현실 용어 유지. 고양이는 교사가 아니며 정답을 강의하지 않는다. 사용자가 이름 붙인 고양이와 이미 만난 상태를 유지한다. Block 마지막 Chapter이고 전체 마지막이 아니면 0~2 Story Choice 가능. 그 외 story_choices는 빈 배열. Story State update는 이 Chapter에서 실제 발생한 변화만 반환. JSON만 반환."""
    result=generate_json(
        feature="story_chapter",prompt_version=CHAPTER_PROMPT_VERSION,prompt=prompt,schema=CHAPTER_SCHEMA,model=DEFAULT_MODEL,
        user_id=user_id,world_id=world_id,story_arc_id=story_arc_id,
        mock_context={"topic":topic,"goal":goal,"learner_level":learner_level,"theme":theme,"guide_name":guide_name,"chapter_number":chapter_number,"chapter_outline":chapter_outline,"target_concepts":concepts,"block_end_chapter":block_end,"target_chapter_count":target_chapter_count},
    )
    return _normalize_chapter(result,chapter_number=chapter_number,target_concepts=concepts,phase=phase,block_end=block_end,target_count=target_chapter_count)


def generate_first_chapter(*args,**kwargs):
    raise RuntimeError("Lazy Story Engine에서는 story_engine_service.ensure_initial_story_block()을 사용해주세요.")

def generate_next_chapter(*args,**kwargs):
    raise RuntimeError("Lazy Story Engine에서는 story_engine_service.generate_next_story_block()을 사용해주세요.")

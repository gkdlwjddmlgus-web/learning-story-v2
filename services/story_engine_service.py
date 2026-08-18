from __future__ import annotations

from repositories.chapter_repository import create_chapter, get_chapter, mark_chapter_state_applied
from repositories.story_block_repository import get_outline_chapter, get_story_block_plan, upsert_story_block_plan
from repositories.story_choice_repository import get_latest_choice_for_arc
from repositories.story_state_repository import update_story_state
from repositories.story_repository import complete_story_arc, get_active_story_arc, update_story_arc_phase
from services.curriculum_service import plan_story_block_concepts
from services.dev_config import generation_provider
from services.foundation_service import ensure_world_foundation
from services.story_context_service import ensure_story_context, get_story_context
from services.story_memory_service import apply_state_update, initialize_companion_state
from services.story_service import BLOCK_SIZE, CHAPTER_PROMPT_VERSION, OUTLINE_PROMPT_VERSION, generate_story_block_outline, generate_story_chapter, get_story_block_end_chapter, get_story_block_start_chapter, get_story_phase


def get_story_runtime(world_id:int)->dict|None: return get_story_context(world_id)


def _profiles_or_empty(personalization:dict|None)->tuple[dict,dict]:
    empty={"weak":[],"review":[],"strong":[]}
    if not personalization: return empty,empty
    return personalization.get("recent",empty),personalization.get("global",empty)


def _prepare_context(*,user,world,chapter_number:int,personalization:dict|None)->dict:
    ensure_story_context(world[0],link_existing_chapters=True)
    foundation=ensure_world_foundation(user_id=user["user_id"],world=world)
    context=ensure_story_context(world[0])
    guide_name=world[9] if len(world)>9 else None
    if guide_name: initialize_companion_state(story_arc_id=context["arc"]["id"],guide_name=guide_name)
    # legacy Story Memory fallback
    state=get_story_context(world[0])["state"]
    if chapter_number>1 and not state.get("story_summary"):
        previous=get_chapter(world_id=world[0],chapter_number=chapter_number-1)
        if previous is not None:
            update_story_state(context["arc"]["id"],story_summary=f"Chapter {previous[2]} · {previous[3]}\n{previous[4]}",latest_event={"summary":f"Chapter {previous[2]}까지 진행됨"})
            state=get_story_context(world[0])["state"]
    recent,global_profile=_profiles_or_empty(personalization)
    return {"foundation":foundation,"context":context,"guide_name":guide_name,"state":state,"recent":recent,"global":global_profile}


def _ensure_block_plan(*,user,world,chapter_number:int,personalization:dict|None)->dict:
    prepared=_prepare_context(user=user,world=world,chapter_number=chapter_number,personalization=personalization)
    foundation=prepared["foundation"]; arc=foundation["arc"]; blueprint=foundation["blueprint"]; curriculum=foundation["curriculum"]
    target=int(blueprint["target_chapter_count"])
    block_start=get_story_block_start_chapter(chapter_number); block_end=get_story_block_end_chapter(start_chapter=block_start,target_chapter_count=target); block_no=((block_start-1)//BLOCK_SIZE)+1
    existing=get_story_block_plan(arc["id"],block_no)
    if existing and existing.get("outline"): return {**prepared,"plan":existing,"target":target,"block_start":block_start,"block_end":block_end}
    size=block_end-block_start+1
    concept_plan=plan_story_block_concepts(curriculum=curriculum,start_chapter=block_start,block_size=size,target_chapter_count=target,weak_concepts=prepared["recent"].get("weak",[]),review_concepts=prepared["recent"].get("review",[]))
    latest_choice=get_latest_choice_for_arc(user_id=user["user_id"],story_arc_id=arc["id"])
    outline=generate_story_block_outline(
        topic=world[1],goal=world[2] or "",learner_level=world[3],theme=world[4],guide_name=prepared["guide_name"],blueprint=blueprint,story_state=prepared["state"],chapter_concept_plan=concept_plan,
        start_chapter=block_start,target_chapter_count=target,recent_profile=prepared["recent"],global_profile=prepared["global"],latest_choice=latest_choice,user_id=user["user_id"],world_id=world[0],story_arc_id=arc["id"],
    )
    provider=generation_provider()
    upsert_story_block_plan(story_arc_id=arc["id"],block_number=block_no,start_chapter=block_start,end_chapter=block_end,outline=outline,provider=provider,model="mock-local" if provider=="mock" else "gemini-flash-latest",prompt_version=OUTLINE_PROMPT_VERSION)
    plan=get_story_block_plan(arc["id"],block_no)
    return {**prepared,"plan":plan,"target":target,"block_start":block_start,"block_end":block_end}


def ensure_story_chapter(*,user,world,chapter_number:int,personalization:dict|None=None)->int:
    existing=get_chapter(world_id=world[0],chapter_number=chapter_number)
    if existing is not None: return existing[0]
    data=_ensure_block_plan(user=user,world=world,chapter_number=chapter_number,personalization=personalization)
    outline=data["plan"]["outline"]; chapter_outline=get_outline_chapter(outline,chapter_number)
    if chapter_outline is None: raise RuntimeError(f"Story Block Outline에서 Chapter {chapter_number} 계획을 찾지 못했습니다.")
    foundation=data["foundation"]; arc=foundation["arc"]
    generated=generate_story_chapter(
        topic=world[1],goal=world[2] or "",learner_level=world[3],theme=world[4],guide_name=data["guide_name"],blueprint=foundation["blueprint"],story_state=data["state"],block_outline=outline,chapter_outline=chapter_outline,chapter_number=chapter_number,target_chapter_count=data["target"],recent_profile=data["recent"],global_profile=data["global"],user_id=user["user_id"],world_id=world[0],story_arc_id=arc["id"],
    )
    chapter_id=create_chapter(world_id=world[0],chapter_number=chapter_number,title=generated["title"],story=generated["story"],learning_objectives=generated["learning_objectives"],questions=[],story_arc_id=arc["id"],story_choices=generated.get("story_choices",[]),story_phase=generated.get("story_phase"),target_concepts=generated.get("target_concepts",[]),pending_state_update=generated.get("state_update",{}))
    update_story_arc_phase(story_arc_id=arc["id"],current_phase=generated.get("story_phase") or get_story_phase(chapter_number=chapter_number,target_chapter_count=data["target"]))
    return chapter_id


def ensure_initial_story_block(*,user,world)->None:
    """호환 이름 유지. 실제 동작은 첫 Block Outline + Chapter 1만 Lazy 생성한다."""
    ensure_story_chapter(user=user,world=world,chapter_number=1,personalization=None)


def generate_next_story_block(*,user,world,start_chapter:int,personalization:dict)->list[int]:
    """호환 이름 유지. 다음 Block 전체가 아니라 필요한 다음 Chapter 1개만 생성한다."""
    return [ensure_story_chapter(user=user,world=world,chapter_number=start_chapter,personalization=personalization)]


def apply_completed_chapter_state(*,world_id:int,chapter)->None:
    if len(chapter)<=13 or chapter[13]: return
    context=get_story_context(world_id)
    if context is None: return
    apply_state_update(story_arc_id=context["arc"]["id"],update=chapter[12] or {})
    mark_chapter_state_applied(chapter_id=chapter[0])
    phase=chapter[10] if len(chapter)>10 else None
    if phase: update_story_arc_phase(story_arc_id=context["arc"]["id"],current_phase=phase)


def get_target_chapter_count(world_id:int)->int|None:
    context=get_story_context(world_id); return None if context is None else context["arc"].get("target_chapter_count")

def is_story_complete(*,world_id:int,chapter_number:int)->bool:
    total=get_target_chapter_count(world_id); return bool(total and chapter_number>=total)

def is_story_block_end(*,world_id:int,chapter_number:int)->bool:
    total=get_target_chapter_count(world_id)
    return True if total and chapter_number>=total else chapter_number%BLOCK_SIZE==0

def complete_current_story_arc(world_id:int)->None:
    arc=get_active_story_arc(world_id)
    if arc: complete_story_arc(arc["id"])

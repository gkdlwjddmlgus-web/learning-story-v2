from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import psycopg
import streamlit as st

from repositories.story_block_repository import (
    get_outline_chapter,
    get_story_block_plan,
)
from repositories.story_choice_repository import get_latest_choice_for_arc
from services.foundation_service import get_world_foundation
from services.personalization_service import build_personalization_profile
from services.story_context_service import get_story_context
from services.story_service import generate_story_chapter


USERNAME = "ptest1"
DISPLAY_NAME = "p_test_0819"
TOPIC = "데이터 엔지니어링 입문"
THEME = "미스터리"
CHAPTER_NUMBER = 7
PREVIOUS_CHAPTER_NUMBER = 6
BLOCK_NUMBER = 3


def _jsonable(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _snapshot(conn, *, world_id: int, story_arc_id: int, chapter_id: int) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
                id,
                title,
                story,
                learning_objectives,
                questions,
                completed,
                story_choices,
                story_phase,
                target_concepts,
                pending_state_update,
                state_applied
            from public.v2_chapters
            where id = %s
            """,
            (chapter_id,),
        )
        chapter = cur.fetchone()
        if not chapter:
            raise RuntimeError("snapshot에서 Chapter 7을 찾지 못했습니다.")

        cur.execute(
            """
            select
                story_summary,
                current_location,
                characters,
                companion_state,
                confirmed_facts,
                open_threads,
                resolved_events,
                latest_event
            from public.v2_story_states
            where story_arc_id = %s
            """,
            (story_arc_id,),
        )
        state = cur.fetchone()
        if not state:
            raise RuntimeError("snapshot에서 Story State를 찾지 못했습니다.")

        cur.execute(
            """
            select current_phase, blueprint
            from public.v2_story_arcs
            where id = %s
            """,
            (story_arc_id,),
        )
        arc = cur.fetchone()
        if not arc:
            raise RuntimeError("snapshot에서 Story Arc를 찾지 못했습니다.")

        cur.execute(
            """
            select count(*)
            from public.v2_story_choice_selections
            where world_id = %s
            """,
            (world_id,),
        )
        choice_count = cur.fetchone()[0]

    return _jsonable(
        {
            "chapter": {
                "id": chapter[0],
                "title": chapter[1],
                "story": chapter[2],
                "learning_objectives": chapter[3] or [],
                "questions": chapter[4] or [],
                "completed": bool(chapter[5]),
                "story_choices": chapter[6] or [],
                "story_phase": chapter[7],
                "target_concepts": chapter[8] or [],
                "pending_state_update": chapter[9] or {},
                "state_applied": bool(chapter[10]),
            },
            "story_state": {
                "story_summary": state[0],
                "current_location": state[1],
                "characters": state[2] or [],
                "companion_state": state[3] or {},
                "confirmed_facts": state[4] or [],
                "open_threads": state[5] or [],
                "resolved_events": state[6] or [],
                "latest_event": state[7] or {},
            },
            "arc": {
                "current_phase": arc[0],
                "blueprint": arc[1] or {},
            },
            "choice_count": choice_count,
        }
    )


def main() -> None:
    database_url = st.secrets["DATABASE_URL"]

    print("[INFO] DAY 4 Ch7 non-destructive Story preview")
    print("[INFO] 기존 Chapter / Story State / Choice / Question / Mastery는 수정하지 않습니다.")

    with psycopg.connect(database_url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, username, display_name
                from public.v2_app_users
                where username = %s
                """,
                (USERNAME,),
            )
            user_row = cur.fetchone()

            if not user_row:
                raise RuntimeError(f"username={USERNAME!r} 사용자를 찾지 못했습니다.")

            user_id, username, display_name = user_row

            if display_name != DISPLAY_NAME:
                raise RuntimeError(
                    f"display_name 불일치: actual={display_name!r}, "
                    f"expected={DISPLAY_NAME!r}"
                )

            cur.execute(
                """
                select
                    id,
                    topic,
                    goal,
                    learner_level,
                    theme,
                    title,
                    world_summary,
                    current_chapter,
                    created_at,
                    guide_name
                from public.v2_learning_worlds
                where user_id = %s
                  and topic = %s
                  and theme = %s
                order by created_at desc
                """,
                (user_id, TOPIC, THEME),
            )
            worlds = cur.fetchall()

            if len(worlds) != 1:
                raise RuntimeError(
                    "대상 World를 정확히 1개로 식별하지 못했습니다. "
                    f"candidate_count={len(worlds)}"
                )

            world = worlds[0]
            world_id = world[0]

            cur.execute(
                """
                select
                    id,
                    title,
                    story,
                    completed,
                    target_concepts,
                    pending_state_update,
                    state_applied
                from public.v2_chapters
                where world_id = %s
                  and chapter_number = %s
                """,
                (world_id, CHAPTER_NUMBER),
            )
            ch7 = cur.fetchone()

            if not ch7:
                raise RuntimeError("Chapter 7을 찾지 못했습니다.")

            chapter_id = ch7[0]

            cur.execute(
                """
                select id, completed, state_applied
                from public.v2_chapters
                where world_id = %s
                  and chapter_number = %s
                """,
                (world_id, PREVIOUS_CHAPTER_NUMBER),
            )
            ch6 = cur.fetchone()

            if not ch6:
                raise RuntimeError("Chapter 6을 찾지 못했습니다.")

            if not bool(ch6[1]) or not bool(ch6[2]):
                raise RuntimeError(
                    "Chapter 6 완료/State 적용 상태가 예상과 달라 "
                    "Ch7 생성 당시 Context를 안전하게 재현할 수 없습니다."
                )

            if bool(ch7[6]):
                raise RuntimeError(
                    "Chapter 7 state_applied=true 입니다. "
                    "현재 Story State에 Ch7 결과가 이미 반영되었을 수 있어 "
                    "비파괴 Preview를 중단합니다."
                )

    context = get_story_context(world_id)
    if context is None:
        raise RuntimeError("Story Context를 찾지 못했습니다.")

    arc = context["arc"]
    story_state = context["state"] or {}

    foundation = get_world_foundation(world_id)
    if foundation is None:
        raise RuntimeError("기존 World Foundation을 찾지 못했습니다.")

    plan = get_story_block_plan(arc["id"], BLOCK_NUMBER)
    if not plan or not plan.get("outline"):
        raise RuntimeError("Block 3 Story Outline을 찾지 못했습니다.")

    chapter_outline = get_outline_chapter(
        plan["outline"],
        CHAPTER_NUMBER,
    )
    if chapter_outline is None:
        raise RuntimeError("Block 3 Outline에서 Chapter 7 계획을 찾지 못했습니다.")

    personalization = build_personalization_profile(
        user_id=user_id,
        world_id=world_id,
        chapter_id=ch6[0],
    )

    opening_choice = get_latest_choice_for_arc(
        user_id=user_id,
        story_arc_id=arc["id"],
    )
    if (
        opening_choice is None
        or opening_choice.get("chapter_id") != ch6[0]
    ):
        raise RuntimeError(
            "Chapter 6의 Story Choice를 정확히 찾지 못했습니다. "
            f"latest_choice={opening_choice}"
        )

    with psycopg.connect(database_url, connect_timeout=10) as conn:
        before = _snapshot(
            conn,
            world_id=world_id,
            story_arc_id=arc["id"],
            chapter_id=chapter_id,
        )

    print(f"[PASS] account: username={username!r}, display_name={display_name!r}")
    print(f"[PASS] world_id={world_id}, story_arc_id={arc['id']}")
    print(f"[PASS] Ch6 completed/state_applied=True")
    print(f"[PASS] Ch7 state_applied=False")
    print(f"[PASS] opening choice: {opening_choice.get('choice_text')}")
    print(
        "[INFO] personalization recent="
        f"{personalization.get('recent')} / global={personalization.get('global')}"
    )
    print("[INFO] Gemini를 1회 호출해 Hotfix 적용 Story를 Preview 생성합니다.")
    print("[INFO] 생성 Story는 DB Chapter에 저장하지 않고 로컬 JSON으로만 저장합니다.")

    generated = generate_story_chapter(
        topic=world[1],
        goal=world[2] or "",
        learner_level=world[3],
        theme=world[4],
        guide_name=world[9],
        blueprint=foundation["blueprint"],
        story_state=story_state,
        block_outline=plan["outline"],
        chapter_outline=chapter_outline,
        chapter_number=CHAPTER_NUMBER,
        target_chapter_count=int(arc["target_chapter_count"]),
        recent_profile=personalization.get("recent"),
        global_profile=personalization.get("global"),
        opening_choice=opening_choice,
        user_id=user_id,
        world_id=world_id,
        story_arc_id=arc["id"],
    )

    if not isinstance(generated, dict):
        raise RuntimeError(
            f"예상과 다른 생성 결과 type={type(generated).__name__}"
        )

    if int(generated.get("chapter_number", -1)) != CHAPTER_NUMBER:
        raise RuntimeError(
            f"생성 Chapter 번호 불일치: {generated.get('chapter_number')}"
        )

    if not str(generated.get("story") or "").strip():
        raise RuntimeError("생성 Story가 비어 있습니다.")

    with psycopg.connect(database_url, connect_timeout=10) as conn:
        after = _snapshot(
            conn,
            world_id=world_id,
            story_arc_id=arc["id"],
            chapter_id=chapter_id,
        )

    if before != after:
        raise RuntimeError(
            "비파괴 검증 실패: Chapter/Story State/Arc/Choice 중 "
            "예상하지 못한 DB 변경이 감지되었습니다."
        )

    out_dir = Path("qa_previews")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"day4_ch7_story_preview_{stamp}.json"

    payload = {
        "qa_only": True,
        "saved_to_db": False,
        "username": username,
        "display_name": display_name,
        "world_id": world_id,
        "story_arc_id": arc["id"],
        "chapter_id": chapter_id,
        "chapter_number": CHAPTER_NUMBER,
        "previous_chapter_id": ch6[0],
        "opening_choice": opening_choice,
        "personalization": personalization,
        "existing_ch7": {
            "title": ch7[1],
            "story": ch7[2],
            "target_concepts": ch7[4] or [],
            "pending_state_update": ch7[5] or {},
            "state_applied": bool(ch7[6]),
        },
        "chapter_outline": chapter_outline,
        "generated_preview": generated,
    }

    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    print("[PASS] generated Story non-empty")
    print("[PASS] 기존 Ch7 Chapter row 유지")
    print("[PASS] Story State 유지")
    print("[PASS] Arc/Choice 유지")
    print("[PASS] Question/Attempt/Mastery 직접 변경 없음")
    print(f"[DONE] preview JSON: {out_path}")
    print("[NOTE] v2_ai_generation_logs에는 기존 generate_json 정책에 따라 로그가 남을 수 있습니다.")


if __name__ == "__main__":
    main()

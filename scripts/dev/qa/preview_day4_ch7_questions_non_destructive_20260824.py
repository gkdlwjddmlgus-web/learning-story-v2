from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import psycopg
import streamlit as st

from services.mastery_service import (
    choose_requested_difficulty,
    get_adaptive_support_profile,
)
from services.question_service import generate_chapter_questions
from services.story_context_service import get_story_context
from services.story_engine_service import get_chapter_interaction_context


USERNAME = "ptest1"
DISPLAY_NAME = "p_test_0819"
TOPIC = "데이터 엔지니어링 입문"
THEME = "미스터리"
CHAPTER_NUMBER = 7


def main() -> None:
    database_url = st.secrets["DATABASE_URL"]

    print("[INFO] DAY 4 Ch7 non-destructive Question preview")
    print("[INFO] 기존 v2_chapters.questions / Attempt / Mastery는 수정하지 않습니다.")

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
                    f"display_name 불일치: actual={display_name!r}, expected={DISPLAY_NAME!r}"
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
                    f"대상 World를 정확히 1개로 식별하지 못했습니다. count={len(worlds)}"
                )

            world = worlds[0]
            world_id = world[0]

            cur.execute(
                """
                select
                    id,
                    world_id,
                    chapter_number,
                    title,
                    story,
                    learning_objectives,
                    questions,
                    completed,
                    created_at,
                    story_choices,
                    story_phase,
                    target_concepts,
                    pending_state_update,
                    state_applied
                from public.v2_chapters
                where world_id = %s
                  and chapter_number = %s
                """,
                (world_id, CHAPTER_NUMBER),
            )
            chapter = cur.fetchone()
            if not chapter:
                raise RuntimeError("Chapter 7을 찾지 못했습니다.")

            cur.execute(
                """
                select count(*)
                from public.v2_question_attempts
                where user_id = %s
                  and world_id = %s
                  and chapter_id = %s
                """,
                (user_id, world_id, chapter[0]),
            )
            attempt_count = cur.fetchone()[0]

    targets = chapter[11] or []
    if not isinstance(targets, list):
        raise RuntimeError(f"target_concepts 형식이 예상과 다릅니다: {type(targets).__name__}")

    requested_difficulty = choose_requested_difficulty(
        learner_level=world[3],
        user_id=user_id,
        world_id=world_id,
        target_concepts=targets,
    )
    adaptive_support = get_adaptive_support_profile(
        user_id=user_id,
        world_id=world_id,
        target_concepts=targets,
    )
    interaction_context = get_chapter_interaction_context(
        world_id=world_id,
        chapter_number=chapter[2],
        theme=world[4],
    )
    context = get_story_context(world_id)

    print(f"[PASS] account: username={username!r}, display_name={display_name!r}")
    print(f"[PASS] world_id={world_id}, chapter_id={chapter[0]}, chapter={chapter[2]}")
    print(f"[INFO] existing saved questions={len(chapter[6] or [])}")
    print(f"[INFO] existing attempts={attempt_count}")
    print(f"[INFO] target_concepts={targets}")
    print(f"[INFO] requested_difficulty={requested_difficulty}")
    print(f"[INFO] adaptive_support={adaptive_support.get('label')}")
    print("[INFO] Gemini를 1회 호출해 새 Prompt 결과를 생성합니다.")
    print("[INFO] 생성 결과는 DB에 저장하지 않고 로컬 JSON으로만 저장합니다.")

    generated = generate_chapter_questions(
        topic=world[1],
        learner_level=world[3],
        theme=world[4],
        chapter_title=chapter[3],
        chapter_story=chapter[4],
        learning_objectives=chapter[5] or [],
        target_concepts=targets,
        requested_difficulty=requested_difficulty,
        adaptive_support=adaptive_support,
        guide_name=world[9],
        interaction_mode=interaction_context.get("mode"),
        interaction_goal=interaction_context.get("goal"),
        chapter_number=chapter[2],
        target_chapter_count=(
            context["arc"].get("target_chapter_count")
            if context
            else None
        ),
        current_open_threads=(
            (context.get("state") or {}).get("open_threads", [])
            if context
            else []
        ),
        user_id=user_id,
        world_id=world_id,
        story_arc_id=(context["arc"]["id"] if context else None),
    )

    if not isinstance(generated, list) or len(generated) != 5:
        raise RuntimeError(
            f"예상과 다른 생성 결과: type={type(generated).__name__}, count="
            f"{len(generated) if isinstance(generated, list) else 'n/a'}"
        )

    out_dir = Path("qa_previews")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"day4_ch7_questions_preview_{stamp}.json"

    payload = {
        "qa_only": True,
        "saved_to_db": False,
        "username": username,
        "display_name": display_name,
        "world_id": world_id,
        "chapter_id": chapter[0],
        "chapter_number": chapter[2],
        "chapter_title": chapter[3],
        "target_concepts": targets,
        "requested_difficulty": requested_difficulty,
        "adaptive_support": adaptive_support,
        "questions": generated,
    }

    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # DB가 그대로인지 재확인
    with psycopg.connect(database_url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select questions
                from public.v2_chapters
                where id = %s
                """,
                (chapter[0],),
            )
            stored_questions = (cur.fetchone() or [None])[0] or []

            cur.execute(
                """
                select count(*)
                from public.v2_question_attempts
                where user_id = %s
                  and world_id = %s
                  and chapter_id = %s
                """,
                (user_id, world_id, chapter[0]),
            )
            post_attempt_count = cur.fetchone()[0]

    if stored_questions != (chapter[6] or []):
        raise RuntimeError("DB questions가 변경되었습니다. 예상하지 못한 write가 발생했습니다.")
    if post_attempt_count != attempt_count:
        raise RuntimeError("Attempt 수가 변경되었습니다. 예상하지 못한 write가 발생했습니다.")

    print(f"[PASS] generated question count={len(generated)}")
    print("[PASS] 기존 chapter.questions 유지")
    print(f"[PASS] Attempt count 유지={post_attempt_count}")
    print("[PASS] Mastery/Story/DB schema 직접 변경 없음")
    print(f"[DONE] preview JSON: {out_path}")
    print("[NOTE] generation log는 기존 generate_json 경로에 따라 기록될 수 있습니다.")


if __name__ == "__main__":
    main()

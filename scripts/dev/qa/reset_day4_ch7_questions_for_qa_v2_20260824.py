from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import psycopg
import streamlit as st


USERNAME = "ptest1"
DISPLAY_NAME = "p_test_0819"
TOPIC = "데이터 엔지니어링 입문"
THEME = "미스터리"
CHAPTER_NUMBER = 7


def _question_count(value) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DAY 4 QA용 Ch7 기존 문제만 안전하게 비웁니다."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="조회/검증만 하고 DB는 수정하지 않습니다.",
    )
    args = parser.parse_args()

    database_url = st.secrets["DATABASE_URL"]

    print("[INFO] DAY 4 Ch7 Question QA reset")
    print(
        f"[INFO] target username={USERNAME!r}, display_name={DISPLAY_NAME!r}, "
        f"topic={TOPIC!r}, theme={THEME!r}, chapter={CHAPTER_NUMBER}"
    )

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
                raise RuntimeError(f"사용자 username={USERNAME!r}를 찾지 못했습니다.")

            user_id, actual_username, actual_display_name = user_row

            if actual_display_name != DISPLAY_NAME:
                raise RuntimeError(
                    "대상 계정 검증 실패: "
                    f"username={actual_username!r}, display_name={actual_display_name!r}, "
                    f"expected display_name={DISPLAY_NAME!r}"
                )

            print(
                f"[PASS] account verified: "
                f"username={actual_username!r}, display_name={actual_display_name!r}"
            )

            cur.execute(
                """
                select
                    id,
                    topic,
                    theme,
                    current_chapter
                from public.v2_learning_worlds
                where user_id = %s
                  and topic = %s
                  and theme = %s
                  and current_chapter = %s
                order by created_at desc
                """,
                (
                    user_id,
                    TOPIC,
                    THEME,
                    CHAPTER_NUMBER,
                ),
            )
            worlds = cur.fetchall()

            if len(worlds) != 1:
                raise RuntimeError(
                    "대상 World를 정확히 1개로 식별하지 못했습니다. "
                    f"candidate_count={len(worlds)} / candidates={worlds}"
                )

            world_id, topic, theme, current_chapter = worlds[0]

            cur.execute(
                """
                select
                    id,
                    title,
                    questions,
                    completed
                from public.v2_chapters
                where world_id = %s
                  and chapter_number = %s
                """,
                (
                    world_id,
                    CHAPTER_NUMBER,
                ),
            )
            chapter_row = cur.fetchone()

            if not chapter_row:
                raise RuntimeError("대상 Chapter 7을 찾지 못했습니다.")

            chapter_id, title, questions, completed = chapter_row
            questions = questions or []

            cur.execute(
                """
                select count(*)
                from public.v2_question_attempts
                where user_id = %s
                  and world_id = %s
                  and chapter_id = %s
                """,
                (
                    user_id,
                    world_id,
                    chapter_id,
                ),
            )
            attempt_count = cur.fetchone()[0]

            print(f"[PASS] user_id={user_id}")
            print(f"[PASS] world_id={world_id} / current_chapter={current_chapter}")
            print(f"[PASS] chapter_id={chapter_id} / title={title!r}")
            print(f"[INFO] existing question count={_question_count(questions)}")
            print(f"[INFO] existing attempt count={attempt_count}")
            print(f"[INFO] chapter completed={completed}")

            if attempt_count != 0:
                raise RuntimeError(
                    "Ch7에 이미 제출된 Attempt가 있어 questions만 비우면 "
                    "Resume/Attempt 정합성이 깨질 수 있습니다. DB 수정 없이 중단합니다."
                )

            if not questions:
                print("[DONE] 이미 questions가 비어 있습니다. 수정할 내용이 없습니다.")
                return

            if args.dry_run:
                print("[PASS] Ch7 Attempt 0건 확인")
                print("[DRY-RUN] public.v2_chapters.questions만 []로 초기화 예정")
                print("[DRY-RUN] Story / target_concepts / Mastery / Attempt / DB schema 변경 없음")
                print("[DRY-RUN] DB를 수정하지 않았습니다.")
                return

            backup_dir = Path("migration_backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"day4_ch7_questions_before_reset_{stamp}.json"

            backup_payload = {
                "username": USERNAME,
                "user_id": user_id,
                "world_id": world_id,
                "chapter_id": chapter_id,
                "chapter_number": CHAPTER_NUMBER,
                "title": title,
                "completed": completed,
                "questions": questions,
            }
            backup_path.write_text(
                json.dumps(
                    backup_payload,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            print(f"[PASS] backup: {backup_path}")

            cur.execute(
                """
                update public.v2_chapters
                set questions = '[]'::jsonb
                where id = %s
                """,
                (chapter_id,),
            )

            if cur.rowcount != 1:
                raise RuntimeError(
                    f"예상과 다른 update rowcount={cur.rowcount}; rollback합니다."
                )

        conn.commit()

    # post-write verification은 새 connection으로 재확인
    with psycopg.connect(database_url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select questions
                from public.v2_chapters
                where id = %s
                """,
                (chapter_id,),
            )
            row = cur.fetchone()

            if not row:
                raise RuntimeError("post-write verification에서 Chapter를 찾지 못했습니다.")

            stored_questions = row[0] or []

            if stored_questions != []:
                raise RuntimeError(
                    "post-write verification 실패: questions가 []가 아닙니다."
                )

            cur.execute(
                """
                select count(*)
                from public.v2_question_attempts
                where user_id = %s
                  and world_id = %s
                  and chapter_id = %s
                """,
                (
                    user_id,
                    world_id,
                    chapter_id,
                ),
            )
            post_attempt_count = cur.fetchone()[0]

            if post_attempt_count != 0:
                raise RuntimeError(
                    "post-write verification 실패: Attempt 수가 변경되었습니다."
                )

    print("[PASS] post-write verification: questions=[]")
    print("[PASS] Attempt 0건 유지")
    print("[INFO] Story / target_concepts / Mastery / DB schema 변경 없음")
    print("[DONE] Ch7 기존 Question set 초기화 완료 → 앱에서 새 문제 생성 가능")


if __name__ == "__main__":
    main()

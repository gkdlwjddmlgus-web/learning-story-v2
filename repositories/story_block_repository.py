from __future__ import annotations

import json
from typing import Any

from db import get_pool


def get_story_block_plan(story_arc_id: int, block_number: int) -> dict[str, Any] | None:
    pool=get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, story_arc_id, block_number, start_chapter, end_chapter,
                       outline, provider, model, prompt_version, created_at, updated_at
                from public.v2_story_block_plans
                where story_arc_id=%s and block_number=%s
                """,
                (story_arc_id,block_number),
            )
            row=cur.fetchone()
    if row is None: return None
    return {
        "id":row[0],"story_arc_id":row[1],"block_number":row[2],
        "start_chapter":row[3],"end_chapter":row[4],"outline":row[5] or {},
        "provider":row[6],"model":row[7],"prompt_version":row[8],
        "created_at":row[9],"updated_at":row[10],
    }


def upsert_story_block_plan(
    *, story_arc_id:int, block_number:int, start_chapter:int, end_chapter:int,
    outline:dict, provider:str, model:str|None, prompt_version:str|None,
) -> None:
    pool=get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_story_block_plans (
                    story_arc_id,block_number,start_chapter,end_chapter,outline,provider,model,prompt_version
                ) values (%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                on conflict (story_arc_id,block_number)
                do update set start_chapter=excluded.start_chapter,
                              end_chapter=excluded.end_chapter,
                              outline=excluded.outline,
                              provider=excluded.provider,
                              model=excluded.model,
                              prompt_version=excluded.prompt_version,
                              updated_at=now()
                """,
                (story_arc_id,block_number,start_chapter,end_chapter,
                 json.dumps(outline,ensure_ascii=False),provider,model,prompt_version),
            )
        conn.commit()


def get_outline_chapter(outline:dict, chapter_number:int) -> dict|None:
    for item in outline.get("chapters",[]):
        if int(item.get("chapter_number",-1))==int(chapter_number):
            return item
    return None

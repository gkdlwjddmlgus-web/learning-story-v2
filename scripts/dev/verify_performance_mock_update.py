from __future__ import annotations

from db import get_pool
from services.dev_config import generation_mode_label, get_mock_delay, is_ai_mock_enabled


def main():
    print("="*82)
    print("Learning Story V2 - Performance / Mock Update Verification")
    print("="*82)
    print(f"Generation Mode: {generation_mode_label()}")
    print(f"DEV_AI_MOCK: {is_ai_mock_enabled()}")
    print(f"Mock Delay: {get_mock_delay()} sec")
    pool=get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select count(*) from public.v2_story_block_plans")
            plans=cur.fetchone()[0]
            cur.execute("select count(*) from public.v2_ai_generation_logs where provider='mock'")
            mock_logs=cur.fetchone()[0]
            cur.execute("select count(*) from public.v2_ai_generation_logs where provider='gemini'")
            live_logs=cur.fetchone()[0]
            cur.execute("""
                select feature,provider,success,retry_count,latency_ms,error_type,created_at
                from public.v2_ai_generation_logs
                order by created_at desc limit 15
            """)
            logs=cur.fetchall()
            cur.execute("""
                select w.id,w.topic,w.theme,w.guide_name,a.id,a.target_chapter_count,
                       (select count(*) from public.v2_story_block_plans p where p.story_arc_id=a.id),
                       (select count(*) from public.v2_chapters c where c.story_arc_id=a.id)
                from public.v2_learning_worlds w
                left join public.v2_story_arcs a on a.world_id=w.id and a.status='active'
                order by w.created_at desc limit 1
            """)
            latest=cur.fetchone()
    print("\n[Stored data]")
    print(f"Story Block Plans: {plans}")
    print(f"Mock Generation Logs: {mock_logs}")
    print(f"Gemini Generation Logs: {live_logs}")
    print("\n[Recent Generation Logs]")
    for row in logs:
        print(f"- {row[6]} | {row[0]} | {row[1]} | {'OK' if row[2] else 'FAIL'} | retry={row[3]} | {row[4] or '-'}ms | {row[5] or '-'}")
    print("\n[Latest World]")
    print(latest or "- World 없음")
    print("\n[판정]")
    print("- Mock Mode에서는 새 World 생성 시 curriculum / story_blueprint / story_block_outline / story_chapter가 provider=mock으로 기록되면 정상")
    print("- 최초 진입 시 Block 전체 Chapter가 아니라 Chapter 1만 저장되는 것이 정상")
    print("- Ch1 완료 후 다음 Chapter 준비 시 Ch2 하나만 추가되는 것이 정상")

if __name__=='__main__': main()

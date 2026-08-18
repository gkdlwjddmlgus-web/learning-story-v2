begin;

create table if not exists public.v2_story_block_plans (
    id bigserial primary key,
    story_arc_id bigint not null,
    block_number integer not null,
    start_chapter integer not null,
    end_chapter integer not null,
    outline jsonb not null default '{}'::jsonb,
    provider text not null default 'gemini',
    model text,
    prompt_version text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint v2_story_block_plans_arc_fkey foreign key (story_arc_id) references public.v2_story_arcs(id) on delete cascade,
    constraint v2_story_block_plans_arc_block_unique unique (story_arc_id, block_number),
    constraint v2_story_block_plans_block_positive check (block_number > 0),
    constraint v2_story_block_plans_range_check check (start_chapter > 0 and end_chapter >= start_chapter)
);
create index if not exists idx_v2_story_block_plans_arc on public.v2_story_block_plans(story_arc_id, block_number);

alter table public.v2_ai_generation_logs add column if not exists provider text not null default 'gemini';

commit;

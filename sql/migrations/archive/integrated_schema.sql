-- ============================================================
-- Learning Story V2 Integrated Foundation
-- 기존 Phase 2 Story Arc / Story State 위에 확장합니다.
-- 데이터 삭제 없음 / 기존 컬럼 유지 / 신규 컬럼은 nullable 또는 default 사용
-- ============================================================

begin;

-- 1. Curriculum ------------------------------------------------
create table if not exists public.v2_curricula (
    id bigserial primary key,
    world_id bigint not null unique,
    curriculum jsonb not null default '{}'::jsonb,
    model text,
    prompt_version text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint v2_curricula_world_id_fkey
        foreign key (world_id)
        references public.v2_learning_worlds(id)
        on delete cascade
);

-- 2. Concept Mastery -------------------------------------------
create table if not exists public.v2_concept_mastery (
    id bigserial primary key,
    user_id bigint not null,
    world_id bigint not null,
    concept text not null,
    mastery_score double precision not null default 0.5,
    attempts integer not null default 0,
    correct_count integer not null default 0,
    last_result boolean,
    review_needed boolean not null default false,
    last_seen_at timestamptz,
    updated_at timestamptz not null default now(),

    constraint v2_concept_mastery_user_id_fkey
        foreign key (user_id)
        references public.v2_app_users(id)
        on delete cascade,

    constraint v2_concept_mastery_world_id_fkey
        foreign key (world_id)
        references public.v2_learning_worlds(id)
        on delete cascade,

    constraint v2_concept_mastery_user_world_concept_unique
        unique (user_id, world_id, concept),

    constraint v2_concept_mastery_score_check
        check (mastery_score >= 0.0 and mastery_score <= 1.0)
);

create index if not exists idx_v2_mastery_user_world
    on public.v2_concept_mastery(user_id, world_id);

create index if not exists idx_v2_mastery_review
    on public.v2_concept_mastery(user_id, world_id, review_needed);

-- 3. User Event Log --------------------------------------------
create table if not exists public.v2_user_events (
    id bigserial primary key,
    user_id bigint,
    world_id bigint,
    story_arc_id bigint,
    chapter_id bigint,
    session_id text,
    event_type text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),

    constraint v2_user_events_user_id_fkey
        foreign key (user_id)
        references public.v2_app_users(id)
        on delete set null,

    constraint v2_user_events_world_id_fkey
        foreign key (world_id)
        references public.v2_learning_worlds(id)
        on delete set null,

    constraint v2_user_events_story_arc_id_fkey
        foreign key (story_arc_id)
        references public.v2_story_arcs(id)
        on delete set null,

    constraint v2_user_events_chapter_id_fkey
        foreign key (chapter_id)
        references public.v2_chapters(id)
        on delete set null
);

create index if not exists idx_v2_user_events_user_time
    on public.v2_user_events(user_id, created_at desc);

create index if not exists idx_v2_user_events_world_type
    on public.v2_user_events(world_id, event_type, created_at desc);

-- 4. AI Generation Log -----------------------------------------
create table if not exists public.v2_ai_generation_logs (
    id bigserial primary key,
    user_id bigint,
    world_id bigint,
    story_arc_id bigint,
    feature text not null,
    model text not null,
    prompt_version text,
    latency_ms integer,
    success boolean not null,
    retry_count integer not null default 0,
    error_type text,
    created_at timestamptz not null default now(),

    constraint v2_ai_generation_logs_user_id_fkey
        foreign key (user_id)
        references public.v2_app_users(id)
        on delete set null,

    constraint v2_ai_generation_logs_world_id_fkey
        foreign key (world_id)
        references public.v2_learning_worlds(id)
        on delete set null,

    constraint v2_ai_generation_logs_story_arc_id_fkey
        foreign key (story_arc_id)
        references public.v2_story_arcs(id)
        on delete set null
);

create index if not exists idx_v2_ai_logs_feature_time
    on public.v2_ai_generation_logs(feature, created_at desc);

-- 5. Story Choice ----------------------------------------------
create table if not exists public.v2_story_choice_selections (
    id bigserial primary key,
    user_id bigint not null,
    world_id bigint not null,
    story_arc_id bigint not null,
    chapter_id bigint not null,
    choice_key text not null,
    choice_text text not null,
    created_at timestamptz not null default now(),

    constraint v2_story_choice_user_id_fkey
        foreign key (user_id)
        references public.v2_app_users(id)
        on delete cascade,

    constraint v2_story_choice_world_id_fkey
        foreign key (world_id)
        references public.v2_learning_worlds(id)
        on delete cascade,

    constraint v2_story_choice_arc_id_fkey
        foreign key (story_arc_id)
        references public.v2_story_arcs(id)
        on delete cascade,

    constraint v2_story_choice_chapter_id_fkey
        foreign key (chapter_id)
        references public.v2_chapters(id)
        on delete cascade,

    constraint v2_story_choice_user_chapter_unique
        unique (user_id, chapter_id)
);

create index if not exists idx_v2_story_choice_arc
    on public.v2_story_choice_selections(story_arc_id, created_at desc);

-- 6. Chapter Story Engine metadata -----------------------------
alter table public.v2_chapters
    add column if not exists story_choices jsonb not null default '[]'::jsonb;

alter table public.v2_chapters
    add column if not exists story_phase text;

alter table public.v2_chapters
    add column if not exists target_concepts jsonb not null default '[]'::jsonb;

alter table public.v2_chapters
    add column if not exists pending_state_update jsonb not null default '{}'::jsonb;

alter table public.v2_chapters
    add column if not exists state_applied boolean not null default false;

-- 7. Attempt analytics fields ---------------------------------
alter table public.v2_question_attempts
    add column if not exists difficulty text;

alter table public.v2_question_attempts
    add column if not exists response_time_ms integer;

create index if not exists idx_v2_attempts_concept
    on public.v2_question_attempts(user_id, world_id, concept);

commit;

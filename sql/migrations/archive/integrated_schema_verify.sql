-- Learning Story V2 Integrated Update - schema verify

select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
      'v2_curricula',
      'v2_concept_mastery',
      'v2_user_events',
      'v2_ai_generation_logs',
      'v2_story_choice_selections'
  )
order by table_name;

select column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public'
  and table_name = 'v2_chapters'
  and column_name in (
      'story_arc_id',
      'story_choices',
      'story_phase',
      'target_concepts',
      'pending_state_update',
      'state_applied'
  )
order by ordinal_position;

select column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name = 'v2_question_attempts'
  and column_name in ('difficulty', 'response_time_ms')
order by ordinal_position;

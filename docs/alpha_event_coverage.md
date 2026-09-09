# Closed Alpha event coverage

## Product events (`v2_user_events`)

| Event | Trigger | Closed-alpha use |
| --- | --- | --- |
| `session_start` | authenticated main view opens, once per session | active sessions |
| `story_open` | Chapter Story is opened, once per Chapter/session | Story reach |
| `story_choice` | Story Choice is persisted | agency/branch selection |
| `question_start` | a question becomes active, once per question/session | quiz starts |
| `question_answered` | an answer attempt is saved | completion and correctness |
| `chapter_complete` | all Chapter questions are completed | Chapter funnel |
| `story_block_complete` | a non-final Story Block completes | block retention |
| `story_complete` | the final Story Arc completes | end-to-end completion |

The queue is best-effort: analytics insertion failure is logged and does not block the learning flow. Identifiers available at the call site (`user_id`, `world_id`, `story_arc_id`, `chapter_id`, and session ID) are carried with events, while event-specific details are stored as metadata.

## AI generation logs (`v2_ai_generation_logs`)

The generation gateway records both mock and Gemini attempts with:

- feature, provider, model, and prompt version
- success/failure, latency, retry and attempt counts
- error type/message for failed generation
- timeout, thinking level, and output-token limit
- prompt/response character counts and retry reasons
- user, World, and Story Arc context when available

This is sufficient for the first closed-alpha cost/reliability baseline without duplicating AI generation as a product event.

## Recommended queries for alpha review

- Funnel: distinct users by `session_start` → `story_open` → `question_start` → `question_answered` → `chapter_complete`.
- Agency: Story Choice count and `choice_key` distribution by Story Arc and Chapter.
- Reliability: AI success rate and p50/p95 latency by provider, feature, and model.
- Retry pressure: average retry count and top retry reasons by feature.
- Content cost proxy: prompt/response character totals by feature and successful generation.

## Known gaps (non-blocking for a small closed alpha)

- Login failure/success and logout are not explicit product events.
- World creation started/completed/failed is not represented in `v2_user_events`; generation logs cover only the AI side.
- Review/Companion/Quiz mode switches are not tracked.
- Retry CTA clicks, Story skip/manual-next/autoplay changes, abandonment, and UI error exposure are not tracked.
- There is no explicit deployment/release version attached to each event.

Add these only after the closed-alpha funnel proves they answer a concrete product or operational question. Any new columns or schema/index changes require a separately reviewed migration.

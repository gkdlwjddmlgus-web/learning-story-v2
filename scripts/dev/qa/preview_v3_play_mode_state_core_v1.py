from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import play_runtime_service as runtime


def _assert(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(
            message
        )


def main() -> int:
    learning_path = (
        ROOT
        / "ui_tabs"
        / "learning_tab.py"
    )
    service_path = (
        ROOT
        / "services"
        / "play_runtime_service.py"
    )

    learning_source = learning_path.read_text(
        encoding="utf-8"
    )
    service_source = service_path.read_text(
        encoding="utf-8"
    )

    ast.parse(
        learning_source,
        filename=str(
            learning_path
        ),
    )
    ast.parse(
        service_source,
        filename=str(
            service_path
        ),
    )

    print("=" * 78)
    print("V3 Play Mode State Core v1 - QA")
    print("=" * 78)

    _assert(
        runtime.PLAY_MODES
        == (
            "story",
            "review",
            "companion",
            "quiz",
        ),
        "play-mode contract changed",
    )

    original_state = (
        runtime.st.session_state
    )

    try:
        runtime.st.session_state = {}

        first = runtime.resolve_play_mode(
            world_id=7,
            chapter_id=101,
            story_pending=True,
        )
        _assert(
            first
            == runtime.PLAY_MODE_STORY,
            "pending Story must own play mode",
        )

        after_story = runtime.resolve_play_mode(
            world_id=7,
            chapter_id=101,
            story_pending=False,
        )
        _assert(
            after_story
            == runtime.PLAY_MODE_QUIZ,
            "seen Story must advance stale story mode to quiz",
        )

        runtime.set_play_mode(
            world_id=7,
            chapter_id=101,
            mode=runtime.PLAY_MODE_REVIEW,
        )
        _assert(
            runtime.resolve_play_mode(
                world_id=7,
                chapter_id=101,
                story_pending=False,
            )
            == runtime.PLAY_MODE_REVIEW,
            "review mode did not persist",
        )

        runtime.set_play_mode(
            world_id=7,
            chapter_id=101,
            mode=runtime.PLAY_MODE_COMPANION,
        )
        _assert(
            runtime.resolve_play_mode(
                world_id=7,
                chapter_id=101,
                story_pending=False,
            )
            == runtime.PLAY_MODE_COMPANION,
            "companion mode did not persist",
        )

        runtime.set_play_mode(
            world_id=7,
            chapter_id=101,
            mode=runtime.PLAY_MODE_QUIZ,
        )
        _assert(
            runtime.resolve_play_mode(
                world_id=7,
                chapter_id=101,
                story_pending=False,
            )
            == runtime.PLAY_MODE_QUIZ,
            "quiz mode did not persist",
        )

        other_chapter = (
            runtime.resolve_play_mode(
                world_id=7,
                chapter_id=102,
                story_pending=False,
            )
        )
        _assert(
            other_chapter
            == runtime.PLAY_MODE_QUIZ,
            "new Chapter must have independent default mode",
        )

        runtime.set_play_mode(
            world_id=8,
            chapter_id=201,
            mode=runtime.PLAY_MODE_REVIEW,
        )
        runtime.clear_world_play_modes(
            7
        )

        keys = list(
            runtime.st.session_state.keys()
        )
        _assert(
            not any(
                str(key).startswith(
                    "_v3_play_mode:7:"
                )
                for key in keys
            ),
            "World-7 play modes were not cleared",
        )
        _assert(
            any(
                str(key).startswith(
                    "_v3_play_mode:8:"
                )
                for key in keys
            ),
            "clearing one World removed another World's mode",
        )

        try:
            runtime.set_play_mode(
                world_id=8,
                chapter_id=201,
                mode="invalid",
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "invalid play mode must raise ValueError"
            )
    finally:
        runtime.st.session_state = (
            original_state
        )

    _assert(
        "story_pending = (" in learning_source
        and "play_mode = resolve_play_mode(" in learning_source,
        "learning_tab does not resolve V3 play mode",
    )
    _assert(
        "if play_mode == PLAY_MODE_STORY:"
        in learning_source,
        "Story render gate is not controlled by play mode",
    )
    _assert(
        "PLAY_MODE_REVIEW" in learning_source
        and "PLAY_MODE_COMPANION" in learning_source
        and "PLAY_MODE_QUIZ" in learning_source,
        "future Action Hub modes are not registered in learning_tab",
    )

    forbidden = (
        "repositories.",
        "generate_",
        "Gemini",
        "get_chapter(",
    )
    for token in forbidden:
        _assert(
            token not in service_source,
            "play runtime service must remain local-only: "
            + token,
        )

    print("[PASS] play-mode contract = story/review/companion/quiz")
    print("[PASS] pending Story force-enters story mode")
    print("[PASS] Story completion reconciles story -> quiz locally")
    print("[PASS] review/companion/quiz persist per World + Chapter")
    print("[PASS] Chapter mode state is isolated from another Chapter")
    print("[PASS] World cleanup does not clear another World's state")
    print("[PASS] invalid mode is rejected")
    print("[PASS] learning Story gate now resolves through play-mode state")

    print()
    print("[PERFORMANCE]")
    print("- Mode resolution uses session_state only.")
    print("- Mode transitions require no DB read/write.")
    print("- Mode transitions require no Gemini call.")
    print("- No timer, polling, TTL, or background refresh is introduced.")

    print()
    print("[SCOPE]")
    print("- This migration establishes state ownership only.")
    print("- Existing visible Story -> Quiz flow is preserved.")
    print("- Review/Companion are registered for the next Action Hub migration.")
    print("- No new Review/Companion button is rendered yet.")

    print()
    print("[NO CHANGE]")
    print("- DB schema/data unchanged.")
    print("- Chapter Runtime Cache contract unchanged.")
    print("- Story/Question/Curriculum/Mastery semantics unchanged.")
    print("- Existing Quiz session-state keys unchanged.")

    print()
    print("[SECURITY / COST]")
    print("- QA uses an in-memory session_state replacement.")
    print("- QA makes no DB query/write.")
    print("- QA makes no Gemini API request.")

    print()
    print("[PASS] V3 Play Mode State Core v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

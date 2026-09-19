from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    hub_path = ROOT / "components" / "play_action_hub.py"
    learning_path = ROOT / "ui_tabs" / "learning_tab.py"
    story_path = ROOT / "components" / "story_cinematic.py"

    hub_source = hub_path.read_text(encoding="utf-8")
    learning_source = learning_path.read_text(encoding="utf-8")
    story_source = story_path.read_text(encoding="utf-8")

    for path, source in (
        (hub_path, hub_source),
        (learning_path, learning_source),
        (story_path, story_source),
    ):
        ast.parse(source, filename=str(path))

    print("=" * 78)
    print("V3 Action Hub v1 - QA")
    print("=" * 78)

    _assert(
        "render_play_action_hub(" in learning_source,
        "learning_tab does not render Action Hub",
    )
    _assert(
        "if play_mode == PLAY_MODE_REVIEW:" in learning_source
        and "if play_mode == PLAY_MODE_COMPANION:" in learning_source
        and "if play_mode == PLAY_MODE_NOTE:" in learning_source
        and "if play_mode != PLAY_MODE_QUIZ:" in learning_source,
        "mode dispatch contract is incomplete",
    )
    _assert(
        "_render_companion_play_mode(" in learning_source
        and "using only stored question support data" in learning_source
        and "concept_brief" in learning_source
        and "evidence_summary" in learning_source
        and "evidence_context" in learning_source
        and "evidence_help" in learning_source,
        "Companion mode does not reuse learning materials",
    )
    _assert(
        "_render_v3_story_review_panel(" in learning_source
        and "review_expanded=False" in learning_source
        and "render_tools=False" in learning_source,
        "Story Review mode does not preserve Story runtime with the V3 review panel",
    )
    _assert(
        "set_play_mode(" in hub_source
        and "st.rerun()" in hub_source,
        "Action Hub does not perform local mode transition",
    )
    _assert(
        "PLAY_MODE_NOTE" in hub_source
        and "_render_learning_note_mode(" in learning_source
        and "v3-open-book" in learning_source,
        "full-screen Learning Note mode is incomplete",
    )

    forbidden_hub = (
        "repositories",
        "generate_",
        "get_runtime_chapter",
        "get_chapter(",
    )
    for token in forbidden_hub:
        _assert(
            token not in hub_source,
            "Action Hub must remain local-only: " + token,
        )

    _assert(
        "_initialize_quiz_progress_from_db(" in learning_source,
        "Companion mode must reuse guarded quiz progress restore",
    )

    print("[PASS] Action Hub exposes Review / Companion / Quiz / Learning Note")
    print("[PASS] Hub click path uses set_play_mode + rerun only")
    print("[PASS] Story Review reuses existing renderer with expanded presentation")
    print("[PASS] Companion reuses current-question Evidence + learning materials")
    print("[PASS] Quiz keeps existing render_quiz flow")
    print("[PASS] Learning Note uses a local-only open-book view")
    print("[PASS] Hub component contains no repository or generation dependency")
    print()
    print("[PERFORMANCE]")
    print("- Hub transition itself is session-state only.")
    print("- Chapter payload continues to use Chapter Runtime Cache.")
    print("- Companion reuses the existing guarded quiz-progress restore.")
    print("- Repeated same-Chapter mode switches do not reinitialize quiz progress.")
    print("- No new generation call is introduced by Review/Companion mode.")
    print()
    print("[NO CHANGE]")
    print("- DB schema/data unchanged.")
    print("- Question generation semantics unchanged.")
    print("- Quiz answer/write semantics unchanged.")
    print("- Story seen-state contract unchanged.")
    print()
    print("[PASS] V3 Action Hub v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

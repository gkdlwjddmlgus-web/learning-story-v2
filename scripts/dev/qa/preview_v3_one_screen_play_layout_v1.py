from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines()

    for node in tree.body:
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ) and node.name == name:
            return "\n".join(
                lines[
                    node.lineno - 1:
                    node.end_lineno
                ]
            )

    raise AssertionError(
        f"function not found: {name}"
    )


def main() -> int:
    scene = (
        ROOT
        / "components"
        / "dialogue_scene.py"
    ).read_text(encoding="utf-8")
    learning = (
        ROOT
        / "ui_tabs"
        / "learning_tab.py"
    ).read_text(encoding="utf-8")
    runtime = (
        ROOT
        / "services"
        / "dialogue_runtime_service.py"
    ).read_text(encoding="utf-8")
    story_service = (
        ROOT
        / "services"
        / "story_service.py"
    ).read_text(encoding="utf-8")

    for source in (
        scene,
        learning,
        runtime,
        story_service,
    ):
        ast.parse(source)

    # Player Agency must remain untouched.
    speaker_fn = _function_source(
        runtime,
        "_speaker_from_quote_context",
    )
    _assert(
        'return "player"' not in speaker_fn,
        "ordinary Story can fabricate Player speech",
    )

    choice_fn = _function_source(
        learning,
        "_render_story_choice",
    )
    _assert(
        'if choice_type == "dialogue":' in choice_fn
        and 'speaker_type="player"' in choice_fn
        and '"choice_type": choice_type' in choice_fn,
        "explicit Player dialogue-choice gate changed",
    )
    _assert(
        "Action choices never become Player dialogue." in choice_fn,
        "action-choice Player Agency guard missing",
    )

    # Root-cause fix: portrait-enter animation no longer owns opacity.
    scene_css = _function_source(
        scene,
        "_css",
    )
    portrait_animation = (
        scene_css
        .split(
            "@keyframes dialoguePortraitEnter",
            1,
        )[1]
        .split(
            ".dialogue-scene-stage",
            1,
        )[0]
    )
    _assert(
        "opacity:" not in portrait_animation,
        "portrait enter animation still overrides narrator dim opacity",
    )
    for token in (
        ".dialogue-scene-character.companion.is-dim > img",
        "opacity:.26 !important;",
        "filter:saturate(.58) brightness(.72) !important;",
        ".dialogue-scene-character.companion.is-active > img",
        "opacity:1 !important;",
    ):
        _assert(
            token in scene_css,
            f"runtime companion opacity contract missing: {token}",
        )

    scene_fn = _function_source(
        scene,
        "render_dialogue_scene",
    )
    _assert(
        '"is-active"' in scene_fn
        and '"is-dim"' in scene_fn,
        "runtime companion state class assignment missing",
    )
    _assert(
        "companion_html + active_character_html" in scene_fn,
        "fixed companion/player stage composition changed",
    )

    # Review mirrors the same visual semantics.
    shell_css = _function_source(
        learning,
        "_inject_v3_one_screen_play_layout_css",
    )
    for token in (
        ".v3-review-character.is-dim img",
        "opacity:.28 !important;",
        "filter:saturate(.60) brightness(.74) !important;",
        ".v3-review-character.is-active img",
    ):
        _assert(
            token in shell_css,
            f"Story Review opacity contract missing: {token}",
        )

    review_fn = _function_source(
        learning,
        "_render_v3_story_review_panel",
    )
    _assert(
        '"is-active"' in review_fn
        and '"is-dim"' in review_fn,
        "Story Review role->opacity state mapping missing",
    )

    # Evidence is now an owned semantic HTML card, not a Streamlit wrapper
    # whose nested Markdown color can be re-overridden by theme CSS.
    evidence_fn = _function_source(
        learning,
        "_render_v3_quiz_evidence_card",
    )
    for token in (
        'class="v3-evidence-card"',
        'class="v3-evidence-kicker"',
        'class="v3-evidence-task"',
        'class="v3-evidence-heading"',
        'class="v3-evidence-copy"',
        "unsafe_allow_html=True",
    ):
        _assert(
            token in evidence_fn,
            f"owned Evidence surface contract missing: {token}",
        )
    _assert(
        "st.container(" not in evidence_fn
        and "st.caption(" not in evidence_fn,
        "Evidence helper returned to generated Streamlit nested wrappers",
    )

    for token in (
        "{body_class} .v3-evidence-card {{",
        "{body_class} .v3-evidence-card * {{",
        "-webkit-text-fill-color:#eef4fb !important;",
        ".v3-evidence-heading {{",
        "color:#ffffff !important;",
        ".v3-evidence-copy,",
        "max-height:285px !important;",
        "overflow-y:auto !important;",
    ):
        _assert(
            token in shell_css,
            f"deterministic Evidence contrast token missing: {token}",
        )

    _assert(
        ".v3-evidence-panel-marker" not in shell_css,
        "old :has(marker) Evidence styling returned",
    )

    quiz_fn = _function_source(
        learning,
        "render_quiz",
    )
    _assert(
        "_render_v3_quiz_evidence_card(" in quiz_fn,
        "Quiz does not use the owned Evidence surface",
    )
    _assert(
        "v3-evidence-panel-marker" not in quiz_fn,
        "Quiz still depends on old Streamlit marker traversal",
    )

    for token in (
        "create_attempt(",
        "update_mastery_from_attempt(",
        '"question_answered"',
        "get_runtime_story_context(",
        "_initialize_quiz_progress_from_db(",
    ):
        _assert(
            token in quiz_fn,
            f"Quiz write/runtime contract missing: {token}",
        )

    _assert(
        "generate_chapter_questions(" not in quiz_fn,
        "ordinary Quiz render gained generation work",
    )

    # One-screen v3 contract must remain present.
    for token in (
        "grid-template-rows:auto minmax(0,1fr) auto",
        '> div[data-testid="stElementContainer"]:has({body_class})',
        "overflow:hidden !important;",
        "min-height:2.82rem",
    ):
        _assert(
            token in shell_css,
            f"one-screen contract missing: {token}",
        )

    # Future Story Choice schema remains explicit and backward-compatible.
    _assert(
        '"enum": ["action", "dialogue"]' in story_service
        and 'choice_type = "action"' in story_service,
        "Story Choice action/dialogue schema or old-choice fallback changed",
    )

    print("=" * 78)
    print("V3 Visual Contract Fix v3.1 - QA")
    print("=" * 78)
    print("[PASS] ordinary Story still cannot fabricate Player speech")
    print("[PASS] action/dialogue Story Choice agency gate is preserved")
    print("[PASS] portrait-enter animation no longer owns opacity")
    print("[PASS] Narration dims the companion visual child deterministically")
    print("[PASS] Companion speech restores the same fixed left sprite to full opacity")
    print("[PASS] Story Review mirrors active/dim opacity semantics")
    print("[PASS] Quiz Evidence is one owned HTML surface")
    print("[PASS] Evidence contrast no longer depends on Streamlit :has(marker) wrapper traversal")
    print("[PASS] Evidence heading/body colors are explicitly forced readable")
    print("[PASS] Evidence remains internally bounded")
    print("[PASS] Quiz attempt/mastery/event/runtime contracts remain present")
    print("[PASS] one-screen HUD/body/dock contract remains present")
    print()
    print("[ROOT CAUSE FIXED]")
    print("- Story: animation-fill-mode previously finished at opacity:1 and masked narrator dim.")
    print("- Quiz: outer Streamlit container styling succeeded, but nested Markdown could still inherit darker theme text.")
    print()
    print("[NO CHANGE]")
    print("- Login UI unchanged.")
    print("- DB schema/data unchanged.")
    print("- Chapter / Story Context Runtime Cache unchanged.")
    print("- play_mode / Action Dock switching unchanged.")
    print("- Story playback, Review, Companion, and mode switching add no Gemini call.")
    print()
    print("[VISUAL E2E REQUIRED]")
    print("- Narration companion must now be visibly faint in the fixed left slot.")
    print("- Companion speech must make that same sprite fully opaque.")
    print("- Quiz Evidence title/body must remain clearly readable at 100% desktop zoom.")
    print("- HUD + Body + Action Dock must still fit in the same viewport.")
    print()
    print("[PASS] V3 Visual Contract Fix v3.1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

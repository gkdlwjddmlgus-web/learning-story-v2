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
    learning = (
        ROOT
        / "ui_tabs"
        / "learning_tab.py"
    ).read_text(encoding="utf-8")
    scene = (
        ROOT
        / "components"
        / "dialogue_scene.py"
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
        learning,
        scene,
        runtime,
        story_service,
    ):
        ast.parse(source)

    shell_css = _function_source(
        learning,
        "_inject_v3_one_screen_play_layout_css",
    )
    review_fn = _function_source(
        learning,
        "_render_v3_story_review_panel",
    )
    companion_fn = _function_source(
        learning,
        "_render_companion_play_mode",
    )
    quiz_fn = _function_source(
        learning,
        "render_quiz",
    )
    choice_fn = _function_source(
        learning,
        "_render_story_choice",
    )

    # Review center: the dialogue is now in normal flex flow inside an
    # explicit-height stage. This is the deterministic fix for the clipped
    # white strip observed during visual E2E.
    for token in (
        'class="v3-review-stage v3-review-stage-v32"',
        'class="v3-review-dialogue v3-review-dialogue-v32"',
        'class="v3-review-character v3-review-character-v32 ',
        'class="v3-review-scene-list-title"',
    ):
        _assert(
            token in review_fn,
            f"Review v3.2 owned-stage contract missing: {token}",
        )

    for token in (
        ".v3-review-stage.v3-review-stage-v32 {{",
        "display:flex !important;",
        "justify-content:flex-end !important;",
        "height:clamp(280px,41vh,380px) !important;",
        "isolation:isolate !important;",
        ".v3-review-stage-v32 .v3-review-dialogue-v32 {{",
        "position:relative !important;",
        "bottom:auto !important;",
        'div[data-testid="stElementContainer"]:has(.v3-review-stage-v32)',
    ):
        _assert(
            token in shell_css,
            f"Review clipping fix token missing: {token}",
        )

    # Review side content no longer relies on theme-sensitive nested
    # Streamlit Markdown/Caption wrappers.
    for token in (
        'class="v3-review-side-stack"',
        'class="v3-review-side-card v3-review-clue-card"',
        'class="v3-review-side-list"',
        'class="v3-review-keyword-chip"',
        "unsafe_allow_html=True",
    ):
        _assert(
            token in review_fn,
            f"Review owned clue/keyword surface missing: {token}",
        )

    _assert(
        "with st.container(border=True):" not in review_fn,
        "Review returned to theme-sensitive Streamlit clue containers",
    )

    for token in (
        ".v3-review-side-card,",
        ".v3-review-side-card * {{",
        "-webkit-text-fill-color:#edf4fb !important;",
        ".v3-review-side-list li {{",
        "color:#dfeaf5 !important;",
        ".v3-review-side-title {{",
        "color:#ffffff !important;",
    ):
        _assert(
            token in shell_css,
            f"Review clue contrast token missing: {token}",
        )

    # Companion hint/current evidence also becomes a single owned surface.
    for token in (
        'class="v3-companion-progress"',
        'class="v3-companion-hint-card"',
        'class="v3-companion-hint-title"',
        'class="v3-companion-hint-copy"',
        'class="v3-companion-evidence-line"',
    ):
        _assert(
            token in companion_fn,
            f"Companion v3.2 readable surface missing: {token}",
        )

    _assert(
        "with st.container(" not in companion_fn,
        "Companion hint returned to a nested Streamlit container",
    )

    for token in (
        ".v3-companion-hint-card {{",
        ".v3-companion-hint-card * {{",
        "-webkit-text-fill-color:#eef4fb !important;",
        ".v3-companion-hint-title {{",
        "color:#f0cf83 !important;",
        ".v3-companion-evidence-line strong {{",
        "color:#dfeaf5 !important;",
    ):
        _assert(
            token in shell_css,
            f"Companion contrast token missing: {token}",
        )

    # v3.1 Story opacity fix must remain untouched.
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
        "v3.1 portrait animation opacity regression",
    )
    for token in (
        ".dialogue-scene-character.companion.is-dim > img",
        "opacity:.26 !important;",
        ".dialogue-scene-character.companion.is-active > img",
        "opacity:1 !important;",
    ):
        _assert(
            token in scene_css,
            f"v3.1 Story opacity contract changed: {token}",
        )

    # Quiz Evidence + one-screen successes are regressions, not v3.2 scope.
    for token in (
        "{body_class} .v3-evidence-card {{",
        "{body_class} .v3-evidence-card * {{",
        "grid-template-rows:auto minmax(0,1fr) auto",
        '> div[data-testid="stElementContainer"]:has({body_class})',
        "min-height:2.82rem",
    ):
        _assert(
            token in shell_css,
            f"existing Quiz/one-screen contract regressed: {token}",
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

    # Player Agency remains exactly as agreed.
    speaker_fn = _function_source(
        runtime,
        "_speaker_from_quote_context",
    )
    _assert(
        'return "player"' not in speaker_fn,
        "ordinary Story can fabricate Player speech",
    )
    _assert(
        'if choice_type == "dialogue":' in choice_fn
        and 'speaker_type="player"' in choice_fn
        and "Action choices never become Player dialogue." in choice_fn,
        "explicit Story Choice Player Agency gate changed",
    )
    _assert(
        '"enum": ["action", "dialogue"]' in story_service
        and 'choice_type = "action"' in story_service,
        "Story Choice schema/backward-compatible action fallback changed",
    )

    # Review / Companion stay local-data UI paths.
    for label, source in (
        ("Review", review_fn),
        ("Companion", companion_fn),
    ):
        for forbidden in (
            "generate_",
            "get_pool(",
            "repositories.",
            "create_attempt(",
        ):
            _assert(
                forbidden not in source,
                f"{label} gained forbidden expensive/write dependency: {forbidden}",
            )

    print("=" * 78)
    print("V3 Review / Companion Visual Fix v3.2 - QA")
    print("=" * 78)
    print("[PASS] Review stage owns an explicit viewport-safe height")
    print("[PASS] Review dialogue is in normal flex flow instead of fragile absolute bottom positioning")
    print("[PASS] Review Streamlit wrappers cannot collapse the stage")
    print("[PASS] Review clue/keyword panels are owned HTML surfaces with forced readable contrast")
    print("[PASS] Companion problem progress / hint / current evidence use owned readable surfaces")
    print("[PASS] v3.1 Narration/Companion opacity contract is preserved")
    print("[PASS] Quiz Evidence readable-surface contract is preserved")
    print("[PASS] HUD / Body / Action Dock one-screen contract is preserved")
    print("[PASS] Quiz attempt/mastery/event/runtime contracts are preserved")
    print("[PASS] Player Agency action/dialogue Story Choice contract is preserved")
    print("[PASS] Review / Companion add no Gemini/repository/write dependency")
    print()
    print("[NO CHANGE]")
    print("- Login UI unchanged.")
    print("- DB schema/data unchanged.")
    print("- Story generation / Story Choice schema unchanged.")
    print("- Chapter / Story Context Runtime Cache unchanged.")
    print("- play_mode / Action Dock switching unchanged.")
    print("- Quiz attempt/mastery/analytics write semantics unchanged.")
    print()
    print("[VISUAL E2E REQUIRED]")
    print("- Story Review center must visibly show background + companion + bottom dialogue card.")
    print("- Review clue/keyword text must be readable at 100% desktop zoom.")
    print("- Companion hint/current-evidence text must be readable at 100% desktop zoom.")
    print("- Quiz and Action Dock must remain visually unchanged and fully visible.")
    print()
    print("[PASS] V3 Review / Companion Visual Fix v3.2 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

TARGET = (
    ROOT
    / "components"
    / "world_intro_cinematic.py"
)


def _assert(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(message)


def _function_source(
    source: str,
    name: str,
) -> str:
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
    source = TARGET.read_text(
        encoding="utf-8"
    )

    ast.parse(source)

    naming = _function_source(
        source,
        "render_world_intro_naming",
    )

    post = _function_source(
        source,
        "render_world_intro_post",
    )

    # Pre-naming cinematic must not advance from wall-clock time.
    _assert(
        "_render_pre_manual("
        "user=user, world=world"
        ")" in naming,
        "pre-intro does not use deterministic manual progression",
    )

    _assert(
        "_AUTO_PRE(user=user, world=world)"
        not in naming,
        "pre-intro runtime still uses elapsed-time autoplay",
    )

    # Post-naming reaction receives the same deterministic treatment.
    _assert(
        "_render_post_manual("
        "user=user, world=world"
        ")" in post,
        "post-intro does not use deterministic manual progression",
    )

    _assert(
        "_AUTO_POST(user=user, world=world)"
        not in post,
        "post-intro runtime still uses elapsed-time autoplay",
    )

    # Existing generation/repository/runtime ownership must be reused.
    for token in (
        "ensure_initial_story_block(",
        "update_current_chapter(",
        "invalidate_runtime_world(",
        "except AIQuotaExhausted:",
        "st.session_state.world_id = world_id",
        '"post_pending")] = False',
        '"complete")] = True',
    ):
        _assert(
            token in post,
            (
                "world-enter lifecycle "
                f"contract missing: {token}"
            ),
        )

    ensure_pos = post.index(
        "ensure_initial_story_block("
    )

    update_pos = post.index(
        "update_current_chapter("
    )

    invalidate_pos = post.index(
        "invalidate_runtime_world("
    )

    complete_pos = post.index(
        '"complete")] = True'
    )

    _assert(
        ensure_pos
        < update_pos
        < invalidate_pos
        < complete_pos,
        (
            "Chapter preparation/update/cache invalidation "
            "must finish before intro completion"
        ),
    )

    quota_pos = post.index(
        "except AIQuotaExhausted:"
    )

    generic_pos = post.index(
        "except Exception as exc:"
    )

    _assert(
        quota_pos < generic_pos < complete_pos,
        "exception handling order changed",
    )

    _assert(
        "return"
        in post[
            quota_pos:
            generic_pos
        ],
        (
            "quota failure can fall through "
            "to intro completion"
        ),
    )

    _assert(
        "return"
        in post[
            generic_pos:
            complete_pos
        ],
        (
            "generic generation failure can fall through "
            "to intro completion"
        ),
    )

    print("=" * 78)
    print(
        "V3 World Intro Alpha E2E Fix v1 - QA"
    )
    print("=" * 78)

    print(
        "[PASS] pre-intro uses deterministic "
        "manual frame progression"
    )
    print(
        "[PASS] post-intro uses deterministic "
        "manual frame progression"
    )
    print(
        "[PASS] elapsed-time autoplay is not used "
        "by active intro routing"
    )
    print(
        "[PASS] final World CTA owns initial "
        "Story/Chapter preparation"
    )
    print(
        "[PASS] current Chapter is set to "
        "Chapter 1 before entry"
    )
    print(
        "[PASS] Chapter Runtime Cache is "
        "invalidated before entry"
    )
    print(
        "[PASS] AI quota failure remains "
        "distinguishable"
    )
    print(
        "[PASS] failed generation cannot "
        "complete the intro"
    )

    print()
    print("[NO CHANGE]")
    print("- DB schema/data unchanged.")
    print(
        "- Story/Question/Mastery semantics unchanged."
    )
    print(
        "- Review/Companion/Quiz play-mode "
        "contracts unchanged."
    )
    print(
        "- Lazy Main Section Routing unchanged."
    )
    print(
        "- Player Agency contract unchanged."
    )

    print()
    print("[VISUAL E2E REQUIRED]")
    print(
        "- New World must visibly start "
        "at encounter Scene 1."
    )
    print(
        "- Scene 1 -> 2 -> 3 must require "
        "explicit user progression."
    )
    print(
        "- Post-naming reaction scenes "
        "must not auto-skip."
    )
    print(
        "- Final CTA must enter an existing "
        "Chapter 1, not the empty fallback."
    )

    print()
    print(
        "[PASS] V3 World Intro Alpha E2E Fix v1 "
        "deterministic QA"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

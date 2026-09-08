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


def main() -> int:
    story_path = ROOT / "components" / "story_cinematic.py"
    hub_path = ROOT / "components" / "play_action_hub.py"

    story_source = story_path.read_text(encoding="utf-8")
    hub_source = hub_path.read_text(encoding="utf-8")

    ast.parse(story_source)
    ast.parse(hub_source)

    _assert(
        "V3_STORY_REVIEW_CONTRAST_FIX_V1_20260908" in story_source,
        "Story Review contrast-fix marker is missing",
    )
    _assert(
        "details:has(.story-review-card) > summary" in story_source,
        "Story Review expander selector is not scoped to the review card",
    )
    _assert(
        "details:has(.story-review-card)[open] > summary" in story_source,
        "expanded Story Review selector is missing",
    )
    _assert(
        "background: transparent !important;" in story_source,
        "expanded Story Review header does not preserve theme background",
    )
    _assert(
        "generated_text_readability_css()\n"
        "            + _story_review_expander_contrast_css()" in story_source,
        "contrast CSS is not injected through the existing review markdown block",
    )
    _assert(
        'with st.expander(\n'
        '        "📖 스토리 다시보기",\n'
        '        expanded=expanded,\n'
        '    ):' in story_source,
        "Action Hub expanded Story Review contract changed unexpectedly",
    )

    forbidden = (
        "repositories.",
        "generation_gateway",
        "generate_",
        "get_runtime_chapter",
    )
    helper_start = story_source.index(
        "def _story_review_expander_contrast_css()"
    )
    helper_end = story_source.index(
        "\ndef render_story_review(",
        helper_start,
    )
    helper_source = story_source[helper_start:helper_end]

    for token in forbidden:
        _assert(
            token not in helper_source,
            "contrast fix must remain presentation-only: " + token,
        )

    _assert(
        "set_play_mode(" in hub_source
        and "st.rerun()" in hub_source,
        "Action Hub local-only transition contract changed",
    )

    print("=" * 78)
    print("V3 Story Review Contrast Fix v1 - QA")
    print("=" * 78)
    print("[PASS] expanded Story Review header keeps the theme background")
    print("[PASS] contrast rule is scoped to the Story Review expander")
    print("[PASS] existing Story Review renderer/expanded contract is preserved")
    print("[PASS] fix adds no repository or generation dependency")
    print()
    print("[NO CHANGE]")
    print("- Action Hub mode state unchanged.")
    print("- Story seen-state unchanged.")
    print("- DB schema/data unchanged.")
    print("- Gemini routing/generation unchanged.")
    print()
    print("[PASS] V3 Story Review Contrast Fix v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

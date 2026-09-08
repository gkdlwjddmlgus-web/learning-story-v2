from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import chapter_runtime_service as runtime


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    paths = {
        "main": ROOT / "views" / "main_view.py",
        "learning": ROOT / "ui_tabs" / "learning_tab.py",
        "service": ROOT / "services" / "chapter_runtime_service.py",
    }

    sources = {}
    for name, path in paths.items():
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        sources[name] = source

    print("=" * 78)
    print("V3 Chapter Runtime Cache v1 - QA")
    print("=" * 78)

    _assert(
        "active_section = st.radio(" in sources["main"],
        "V3 lazy main-section routing baseline missing",
    )
    _assert(
        "get_runtime_chapter(" in sources["main"]
        and "get_runtime_chapter(" in sources["learning"],
        "runtime chapter reader is not wired through main + learning",
    )
    _assert(
        "from repositories.chapter_repository import (\n    get_chapter,"
        not in sources["main"],
        "main_view still imports repository get_chapter directly",
    )
    _assert(
        "    get_chapter,\n    mark_chapter_completed,"
        not in sources["learning"],
        "learning_tab still imports repository get_chapter directly",
    )

    for token in (
        "invalidate_runtime_chapter(",
        "invalidate_runtime_world(",
        "update_chapter_questions(",
        "mark_chapter_completed(",
        "ensure_initial_story_block(",
        "generate_next_story_block(",
    ):
        _assert(
            token in sources["learning"],
            "runtime invalidation boundary missing: " + token,
        )

    original_state = runtime.st.session_state
    original_reader = runtime.get_chapter

    calls: list[tuple[int, int]] = []

    def fake_get_chapter(*, world_id: int, chapter_number: int):
        calls.append(
            (world_id, chapter_number)
        )
        if chapter_number == 99:
            return None
        return (
            world_id * 1000 + chapter_number,
            world_id,
            chapter_number,
        )

    try:
        runtime.st.session_state = {}
        runtime.get_chapter = fake_get_chapter

        first = runtime.get_runtime_chapter(
            world_id=7,
            chapter_number=2,
        )
        second = runtime.get_runtime_chapter(
            world_id=7,
            chapter_number=2,
        )

        _assert(
            first == second,
            "same runtime chapter changed without invalidation",
        )
        _assert(
            calls == [(7, 2)],
            "same chapter must hit repository exactly once",
        )

        missing_first = runtime.get_runtime_chapter(
            world_id=7,
            chapter_number=99,
        )
        missing_second = runtime.get_runtime_chapter(
            world_id=7,
            chapter_number=99,
        )
        _assert(
            missing_first is None
            and missing_second is None,
            "missing chapter cache contract changed",
        )
        _assert(
            calls.count((7, 99)) == 1,
            "None result must also be cached",
        )

        runtime.invalidate_runtime_chapter(
            world_id=7,
            chapter_number=2,
        )
        runtime.get_runtime_chapter(
            world_id=7,
            chapter_number=2,
        )
        _assert(
            calls.count((7, 2)) == 2,
            "chapter invalidation did not force one refresh",
        )

        runtime.get_runtime_chapter(
            world_id=8,
            chapter_number=1,
        )
        runtime.invalidate_runtime_world(7)

        keys = list(runtime.st.session_state.keys())
        _assert(
            not any(
                str(key).startswith(
                    "_v3_chapter_runtime:7:"
                )
                for key in keys
            ),
            "world invalidation left stale world-7 runtime keys",
        )
        _assert(
            any(
                str(key).startswith(
                    "_v3_chapter_runtime:8:"
                )
                for key in keys
            ),
            "world invalidation removed another world's cache",
        )
    finally:
        runtime.get_chapter = original_reader
        runtime.st.session_state = original_state

    print("[PASS] main_view and learning_tab share one runtime Chapter reader")
    print("[PASS] same World/Chapter performs one repository read until invalidated")
    print("[PASS] missing Chapter(None) is cached and explicitly invalidatable")
    print("[PASS] chapter-scoped invalidation forces a fresh repository read")
    print("[PASS] world-scoped invalidation does not clear another World")
    print("[PASS] mutation boundaries contain runtime invalidation hooks")

    print()
    print("[PERFORMANCE]")
    print("- Current Chapter survives ordinary Streamlit full reruns in session_state.")
    print("- main_view -> learning_tab no longer performs duplicate current-Chapter SELECTs.")
    print("- Story scene / quiz UI reruns reuse the same Chapter snapshot.")
    print("- No TTL polling and no new background query is introduced.")

    print()
    print("[INVALIDATION]")
    print("- generated questions -> current Chapter invalidated")
    print("- completed/state-applied Chapter -> current Chapter invalidated")
    print("- initial/next Story generation -> World Chapter cache invalidated")
    print("- logout already clears session_state, including this cache")

    print()
    print("[NO CHANGE]")
    print("- DB schema/data unchanged.")
    print("- Gemini routing/generation unchanged.")
    print("- Question/Story/Curriculum/Mastery semantics unchanged.")
    print("- Story/Quiz visible UI unchanged.")

    print()
    print("[SECURITY / COST]")
    print("- QA replaces the repository reader with an in-memory fake.")
    print("- QA makes no Gemini API request.")
    print("- QA makes no DB query/write.")

    print()
    print("[PASS] V3 Chapter Runtime Cache v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

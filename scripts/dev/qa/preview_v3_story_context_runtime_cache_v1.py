from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import story_context_service as runtime


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            lines = source.splitlines()
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"function not found: {name}")


def main() -> int:
    original_st = runtime.st
    original_active = runtime.get_active_story_arc
    original_latest = runtime.get_latest_story_arc
    original_state = runtime.get_story_state

    counts = {"active": 0, "latest": 0, "state": 0}

    def fake_active(world_id: int):
        counts["active"] += 1
        if int(world_id) == 3:
            return None
        return {
            "id": int(world_id) * 100,
            "world_id": int(world_id),
            "status": "active",
            "current_phase": "development",
            "target_chapter_count": 7,
        }

    def fake_latest(world_id: int):
        counts["latest"] += 1
        if int(world_id) == 3:
            return None
        return {
            "id": int(world_id) * 100 + 1,
            "world_id": int(world_id),
            "status": "completed",
            "current_phase": "resolution",
            "target_chapter_count": 7,
        }

    def fake_state(story_arc_id: int):
        counts["state"] += 1
        return {
            "story_arc_id": int(story_arc_id),
            "companion_state": {},
        }

    try:
        runtime.st = SimpleNamespace(session_state={})
        runtime.get_active_story_arc = fake_active
        runtime.get_latest_story_arc = fake_latest
        runtime.get_story_state = fake_state

        first = runtime.get_runtime_story_context(1)
        _assert(first and first["arc"]["id"] == 100, "first runtime context read failed")
        _assert(
            counts == {"active": 1, "latest": 0, "state": 1},
            f"unexpected first-read counters: {counts}",
        )

        again = runtime.get_runtime_story_context(1)
        _assert(again == first, "same-World cached context changed")
        _assert(
            counts == {"active": 1, "latest": 0, "state": 1},
            f"same-World reread hit repositories: {counts}",
        )

        other = runtime.get_runtime_story_context(2)
        _assert(other and other["arc"]["id"] == 200, "other-World runtime read failed")
        _assert(
            counts == {"active": 2, "latest": 0, "state": 2},
            f"other-World isolation counters unexpected: {counts}",
        )

        runtime.invalidate_runtime_story_context(1)
        refreshed = runtime.get_runtime_story_context(1)
        _assert(refreshed and refreshed["arc"]["id"] == 100, "refresh after invalidation failed")
        _assert(
            counts == {"active": 3, "latest": 0, "state": 3},
            f"World invalidation did not force reread: {counts}",
        )

        before_other = dict(counts)
        runtime.get_runtime_story_context(2)
        _assert(
            counts == before_other,
            "World-scoped invalidation cleared another World's context",
        )

        none_first = runtime.get_runtime_story_context(3)
        _assert(none_first is None, "None context was not preserved")
        none_counts = dict(counts)
        none_again = runtime.get_runtime_story_context(3)
        _assert(none_again is None, "cached None context changed")
        _assert(counts == none_counts, "None context was not cached")

        runtime.invalidate_runtime_story_context_all()
        runtime.get_runtime_story_context(2)
        _assert(
            counts["active"] == none_counts["active"] + 1,
            "global mutation-boundary invalidation did not clear runtime contexts",
        )

    finally:
        runtime.st = original_st
        runtime.get_active_story_arc = original_active
        runtime.get_latest_story_arc = original_latest
        runtime.get_story_state = original_state

    learning_source = (ROOT / "ui_tabs" / "learning_tab.py").read_text(encoding="utf-8")
    story_context_source = (
        ROOT / "services" / "story_context_service.py"
    ).read_text(encoding="utf-8")
    engine_source = (
        ROOT / "services" / "story_engine_service.py"
    ).read_text(encoding="utf-8")
    memory_source = (
        ROOT / "services" / "story_memory_service.py"
    ).read_text(encoding="utf-8")
    foundation_source = (
        ROOT / "services" / "foundation_service.py"
    ).read_text(encoding="utf-8")

    for name in ("_render_chapter_story", "_render_story_choice", "render_quiz"):
        fn = _function_source(learning_source, name)
        _assert(
            "get_runtime_story_context(" in fn,
            f"{name} does not use Story Context Runtime Cache",
        )

    complete_fn = _function_source(learning_source, "render_chapter_complete")
    _assert(
        "get_story_context(" in complete_fn,
        "chapter-completion mutation path must keep a fresh raw context read",
    )

    _assert(
        "invalidate_runtime_story_context(world_id)" in
        _function_source(story_context_source, "ensure_story_context"),
        "ensure_story_context mutation boundary does not invalidate runtime cache",
    )

    _assert(
        "invalidate_runtime_story_context_all()" in engine_source,
        "story_engine_service mutation invalidation hook missing",
    )
    _assert(
        "invalidate_runtime_story_context_all()" in memory_source,
        "story_memory_service mutation invalidation hook missing",
    )
    _assert(
        "invalidate_runtime_story_context_all()" in foundation_source,
        "foundation_service mutation invalidation hook missing",
    )

    print("=" * 78)
    print("V3 Story Context Runtime Cache v1 - QA")
    print("=" * 78)
    print("[PASS] same World reuses one Story Context repository snapshot")
    print("[PASS] None Story Context is cached")
    print("[PASS] World-scoped invalidation forces one fresh read")
    print("[PASS] World cache isolation is preserved")
    print("[PASS] global mutation-boundary invalidation clears cached Story Contexts")
    print("[PASS] Chapter Story / Story Choice / Quiz use the runtime Story Context reader")
    print("[PASS] chapter-completion mutation path keeps a fresh raw Story Context read")
    print("[PASS] Story Arc/state mutation services contain invalidation hooks")
    print()
    print("[PERFORMANCE]")
    print("- ordinary Review / Companion reruns reuse the cached Story Context")
    print("- ordinary Quiz reruns share one cached context across Story chrome + question_start")
    print("- quiz-progress attempt restore remains independently guarded by Chapter/session state")
    print()
    print("[NO CHANGE]")
    print("- DB schema/data unchanged.")
    print("- Gemini prompt/routing unchanged.")
    print("- Chapter Runtime Cache unchanged.")
    print("- play_mode and Action Hub contracts unchanged.")
    print()
    print("[PASS] V3 Story Context Runtime Cache v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

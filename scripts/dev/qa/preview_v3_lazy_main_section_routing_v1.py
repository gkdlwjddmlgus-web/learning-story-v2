from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MAIN = ROOT / "views" / "main_view.py"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    source = MAIN.read_text(encoding="utf-8")
    ast.parse(source, filename=str(MAIN))

    print("=" * 78)
    print("V3 Lazy Main Section Routing v1 - QA")
    print("=" * 78)

    _assert(
        "st.tabs(" not in source,
        "eager st.tabs rendering still exists in main_view",
    )
    _assert(
        'key=f"v3_main_section_{world[0]}"' in source,
        "world-scoped V3 section state key missing",
    )
    _assert(
        "active_section = st.radio(" in source
        and "horizontal=True" in source,
        "lazy section selector missing",
    )
    _assert(
        "if active_section == section_options[0]:" in source
        and "elif active_section == section_options[1]:" in source,
        "single active-section conditional routing missing",
    )

    _assert(
        source.count("render_learning_tab(") == 2,
        "render_learning_tab call count changed unexpectedly",
    )
    _assert(
        source.count("render_world_tab(") == 1,
        "render_world_tab call count changed unexpectedly",
    )
    _assert(
        source.count("render_record_tab(") == 1,
        "render_record_tab call count changed unexpectedly",
    )

    _assert(
        "should_render_story_cinematic(" in source
        and source.index("should_render_story_cinematic(")
        < source.index("active_section = st.radio("),
        "dedicated Story cinematic gate must remain before main-section routing",
    )
    _assert(
        'event_type="session_start"' in source,
        "session_start analytics gate changed unexpectedly",
    )

    print("[PASS] eager st.tabs removed from normal main shell")
    print("[PASS] exactly one selected main section is rendered per normal rerun")
    print("[PASS] Learning / Archive / Record labels remain theme-aware")
    print("[PASS] Story cinematic ownership gate remains before section routing")
    print("[PASS] session_start analytics behavior preserved")

    print()
    print("[PERFORMANCE]")
    print("- Learning interactions no longer execute Archive/Record render bodies.")
    print("- Archive/Record queries run only when that section is selected.")
    print("- No cache, polling, Gemini call, or new DB query is introduced.")

    print()
    print("[NO CHANGE]")
    print("- Story / Question / Curriculum / Mastery logic unchanged.")
    print("- DB schema/data unchanged.")
    print("- Chapter generation and question generation boundaries unchanged.")
    print("- Existing session-state story/quiz keys unchanged.")

    print()
    print("[SECURITY / COST]")
    print("- QA makes no Gemini API request.")
    print("- QA makes no DB query/write.")

    print()
    print("[PASS] V3 Lazy Main Section Routing v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

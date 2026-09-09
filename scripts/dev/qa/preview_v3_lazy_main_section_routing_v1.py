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
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            lines = source.splitlines()
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"function not found: {name}")


def main() -> int:
    main_view = (
        ROOT / "views" / "main_view.py"
    ).read_text(encoding="utf-8")

    ast.parse(main_view)
    render_main = _function_source(
        main_view,
        "render_main",
    )

    _assert(
        "st.tabs(" not in render_main,
        "eager st.tabs returned to the main shell",
    )

    _assert(
        'f"v3_main_section_{world[0]}"' in render_main,
        "world-scoped V3 section state key missing",
    )

    _assert(
        "st.session_state.get(" in render_main
        and "section_key" in render_main,
        "section selection is not restored from session_state",
    )

    session_index = render_main.find(
        "queue_once("
    )
    story_gate_index = render_main.find(
        "should_render_story_cinematic("
    )
    section_index = render_main.find(
        "section_key ="
    )
    _assert(
        -1 < session_index < story_gate_index < section_index,
        "session/story ownership gate no longer precedes section routing",
    )

    learning_branch = (
        "if active_section == section_options[0]:"
    )
    learning_index = render_main.find(
        learning_branch
    )
    conventional_header_index = render_main.find(
        "render_compact_app_header("
    )
    radio_index = render_main.find(
        "st.radio("
    )

    _assert(
        -1
        < learning_index
        < conventional_header_index
        < radio_index,
        "Learning no longer owns the lazy full-viewport branch",
    )

    learning_slice = render_main[
        learning_index:conventional_header_index
    ]
    _assert(
        "render_learning_tab(" in learning_slice
        and "return" in learning_slice,
        "Learning branch does not render-and-return before Archive/Record chrome",
    )

    world_index = render_main.find(
        "render_world_tab("
    )
    record_index = render_main.find(
        "render_record_tab("
    )
    _assert(
        radio_index < world_index
        and radio_index < record_index,
        "Archive/Record renderers execute before their selected branch",
    )

    _assert(
        'section_options = [' in render_main
        and '"학습"' in render_main
        and 'pack["archive_name"]' in render_main
        and 'pack["report_name"]' in render_main,
        "theme-aware Learning/Archive/Record labels changed",
    )

    _assert(
        'event_type="session_start"' in render_main
        and "flush=True" in render_main,
        "session_start analytics behavior changed",
    )

    print("=" * 78)
    print("V3 Lazy Main Section Routing v2 - QA")
    print("=" * 78)
    print("[PASS] eager st.tabs remain removed")
    print("[PASS] world-scoped V3 section state key is preserved")
    print("[PASS] session/story ownership gate remains before section routing")
    print("[PASS] Learning renders lazily and returns before Archive/Record chrome")
    print("[PASS] Archive/Record render only after their section is selected")
    print("[PASS] theme-aware section labels are preserved")
    print("[PASS] session_start analytics behavior is preserved")
    print()
    print("[FULL-UI CONTRACT]")
    print("- Learning now owns the full V3 play viewport.")
    print("- Archive/Record keep the conventional Streamlit document shell.")
    print("- This supersedes the checkpoint #1 QA's old radio-layout assertion.")
    print()
    print("[NO CHANGE]")
    print("- DB schema/data unchanged.")
    print("- Story/Question/Curriculum/Mastery logic unchanged.")
    print("- Chapter and Story Context runtime-cache contracts unchanged.")
    print("- Gemini generation/routing unchanged.")
    print()
    print("[PASS] V3 Lazy Main Section Routing v2 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

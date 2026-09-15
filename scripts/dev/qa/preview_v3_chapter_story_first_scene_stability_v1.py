from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "components" / "dialogue_story_experience.py"


def main() -> int:
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    render = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "render_dialogue_story_experience"
    )
    render_source = ast.get_source_segment(source, render) or ""

    assert 'st.toggle(\n            "자동 진행",' in render_source
    assert "value=False" in render_source
    assert "_render_auto_advance_tick(" in render_source
    assert "mark_dialogue_story_seen(chapter_id)" in render_source
    assert "else (chapter_id, index_key, current_index + 1)" in render_source
    assert any(
        isinstance(decorator, ast.Attribute)
        and decorator.attr == "fragment"
        for decorator in render.decorator_list
    )

    move = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_move_story_scene"
    )
    move_source = ast.get_source_segment(source, move) or ""
    assert "st.session_state[index_key]" in move_source

    tick = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_auto_advance_tick_body"
    )
    tick_source = ast.get_source_segment(source, tick) or ""
    assert "if not auto_enabled:" in tick_source
    assert "time.monotonic()" in tick_source

    print("[PASS] Chapter Story starts in deterministic manual mode")
    print("[PASS] autoplay remains available as an explicit opt-in")
    print("[PASS] manual navigation and Story completion contracts remain")
    print("[PASS] manual scene changes use a fragment-scoped rerun")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

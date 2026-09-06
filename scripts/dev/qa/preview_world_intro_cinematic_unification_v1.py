from __future__ import annotations

import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.dialogue_asset_service import resolve_portrait
from services.story_background_service import (
    resolve_story_background,
    select_story_background_key,
)


COMPONENT_PATH = PROJECT_ROOT / "components" / "world_intro_cinematic.py"
THEMES = ("동화", "판타지", "SF", "무협", "미스터리")


def _load_tree() -> tuple[str, ast.Module]:
    source = COMPONENT_PATH.read_text(encoding="utf-8")
    return source, ast.parse(source)


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function: {name}")


def _theme_script(tree: ast.Module) -> dict:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_THEME_SCRIPT":
                return ast.literal_eval(node.value)
    raise AssertionError("missing _THEME_SCRIPT")


def _exec_pure_function(node: ast.FunctionDef):
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, object] = {}
    exec(compile(module, "<qa-pure-function>", "exec"), namespace)
    return namespace[node.name]


def _call_names(node: ast.AST) -> list[str]:
    names: list[str] = []
    for item in ast.walk(node):
        if not isinstance(item, ast.Call):
            continue
        if isinstance(item.func, ast.Name):
            names.append(item.func.id)
        elif isinstance(item.func, ast.Attribute):
            names.append(item.func.attr)
    return names


def _assert_imports(tree: ast.Module) -> None:
    imported: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            imported.update(alias.name for alias in node.names)
    required = {
        "render_dialogue_scene",
        "resolve_portrait",
        "resolve_story_background",
    }
    missing = required - imported
    assert not missing, f"missing reuse imports: {sorted(missing)}"


def _assert_render_scene_contract(tree: ast.Module) -> None:
    fn = _function(tree, "_render_scene")
    calls = _call_names(fn)
    for required in (
        "resolve_portrait",
        "resolve_story_background",
        "render_dialogue_scene",
    ):
        assert required in calls, f"_render_scene missing call: {required}"


def _assert_naming_save_contract(tree: ast.Module) -> None:
    fn = _function(tree, "render_world_intro_naming")
    calls = [node for node in ast.walk(fn) if isinstance(node, ast.Call)]
    matches = [
        node
        for node in calls
        if isinstance(node.func, ast.Name)
        and node.func.id == "update_guide_name_for_world_intro"
    ]
    assert len(matches) == 1, "naming repository call count changed"
    keywords = {keyword.arg for keyword in matches[0].keywords}
    assert keywords == {"world_id", "user_id", "guide_name"}, (
        f"naming repository contract changed: {sorted(keywords)}"
    )


def _assert_naming_auto_stops(tree: ast.Module) -> None:
    fn = _function(tree, "render_world_intro_naming")
    auto_refs = [
        node
        for node in ast.walk(fn)
        if isinstance(node, ast.Name) and node.id == "_AUTO_PRE"
    ]
    assert len(auto_refs) == 2, (
        "_AUTO_PRE reference shape changed; expected condition + call only"
    )
    calls = _call_names(fn)
    assert "text_input" in calls, "naming input missing"


def _assert_state_flow(source: str) -> None:
    required = (
        '_key(world_id, "name_ready")',
        '_key(world_id, "saved_name")',
        '_key(world_id, "post_pending")',
        '_key(world_id, "post_started")',
        '_key(world_id, "post_ready")',
        '_key(world_id, "complete")',
        "_fragment_factory(run_every=0.25)",
    )
    for token in required:
        assert token in source, f"missing state/runtime anchor: {token}"


def _assert_no_generation_or_db_write_in_qa(source: str) -> None:
    lowered = source.lower()
    assert "gemini" not in lowered
    assert "generate_json" not in lowered

    qa_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for node in ast.walk(qa_tree):
        if isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            assert not module.startswith("repositories"), (
                f"QA must not import repository modules: {module}"
            )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("repositories"), (
                    f"QA must not import repository modules: {alias.name}"
                )


def main() -> int:
    source, tree = _load_tree()
    script = _theme_script(tree)

    assert set(THEMES) == set(script), "theme set changed"
    for theme in THEMES:
        assert len(script[theme]["encounter"]) == 3, f"{theme}: encounter != 3"
        assert len(script[theme]["reaction"]) == 3, f"{theme}: reaction != 3"
        assert len(script[theme]["ready"]) == 2, f"{theme}: ready shape changed"

    role_fn = _exec_pure_function(_function(tree, "_intro_speaker_role"))
    for theme in THEMES:
        frames = (
            list(script[theme]["encounter"])
            + list(script[theme]["reaction"])
            + [script[theme]["ready"]]
        )
        for speaker, _ in frames:
            expected = "companion" if speaker == "🐈" else "narrator"
            assert role_fn(speaker) == expected, (
                f"{theme}: role mapping failed for {speaker!r}"
            )

    for theme in THEMES:
        assert resolve_portrait(theme, "narrator") is None, (
            f"{theme}: narrator portrait must be None"
        )
        companion = resolve_portrait(
            theme,
            "companion",
            character_id="default",
        )
        assert companion is not None and companion.is_file(), (
            f"{theme}: default companion portrait not resolved"
        )

    wuxia_frames = [text for _, text in script["무협"]["encounter"]]
    world_id = 41
    first_key = select_story_background_key(
        theme="무협",
        beat_texts=wuxia_frames,
        current_index=0,
        chapter_id=world_id,
    )
    next_key = select_story_background_key(
        theme="무협",
        beat_texts=wuxia_frames,
        current_index=1,
        chapter_id=world_id,
    )
    assert first_key in {"inn_night", "inn_riverside", "inn_day"}, (
        f"wuxia inn resolution failed: {first_key}"
    )
    assert next_key == first_key, (
        f"wuxia lookback failed: first={first_key}, next={next_key}"
    )
    background = resolve_story_background(
        theme="무협",
        beat_texts=wuxia_frames,
        current_index=1,
        chapter_id=world_id,
    )
    assert background is not None and background.is_file(), (
        "wuxia inn background path not resolved"
    )

    _assert_imports(tree)
    _assert_render_scene_contract(tree)
    _assert_naming_save_contract(tree)
    _assert_naming_auto_stops(tree)
    _assert_state_flow(source)
    _assert_no_generation_or_db_write_in_qa(source)

    print("[PASS] World Intro Cinematic Unification v1 deterministic QA")
    print("[PASS] 5 themes: speaker role mapping")
    print("[PASS] narrator portrait=None / companion default portrait resolved")
    print(f"[PASS] wuxia inn background + lookback: {first_key}")
    print("[PASS] encounter=3 / reaction=3 / ready preserved")
    print("[PASS] naming save contract + session_state flow preserved")
    print("[PASS] st.fragment(run_every=0.25) preserved")
    print("[PASS] render_dialogue_scene + shared asset/background services reused")
    print("[PASS] no Gemini / no repository import or DB write in QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ai_client import is_provider_unavailable_error
from services.question_service import QuestionGenerationError
import ui_tabs.learning_tab as learning_tab


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"function not found: {name}")


def main() -> int:
    original_st = learning_tab.st
    try:
        learning_tab.st = SimpleNamespace(session_state={})
        learning_tab._start_question_generation_cooldown(
            world_id=27,
            chapter_id=59,
            now=1_000.0,
        )
        _assert(
            learning_tab._question_generation_retry_remaining(
                world_id=27,
                chapter_id=59,
                now=1_001.0,
            ) == 119,
            "503 cooldown must last 120 seconds",
        )
        _assert(
            learning_tab._question_generation_retry_remaining(
                world_id=27,
                chapter_id=60,
                now=1_001.0,
            ) == 0,
            "cooldown must not block another Chapter",
        )
        _assert(
            learning_tab._question_generation_retry_remaining(
                world_id=27,
                chapter_id=59,
                now=1_120.0,
            ) == 0,
            "expired cooldown must reactivate generation",
        )
    finally:
        learning_tab.st = original_st

    overload = RuntimeError("provider failed")
    overload.status_code = 503
    _assert(
        is_provider_unavailable_error(overload),
        "typed provider helper must recognize HTTP 503",
    )
    _assert(
        not is_provider_unavailable_error(RuntimeError("schema failure")),
        "non-503 failure must not be provider unavailable",
    )
    _assert(
        QuestionGenerationError(
            "safe message",
            category="provider_unavailable",
        ).provider_unavailable,
        "503 category must reach the UI",
    )
    _assert(
        not QuestionGenerationError("generic").provider_unavailable,
        "generic errors must preserve the existing path",
    )

    ui_source = (ROOT / "ui_tabs" / "learning_tab.py").read_text(encoding="utf-8")
    render_source = _function_source(ui_source, "_render_post_story_mode_body")
    cooldown_source = _function_source(
        ui_source,
        "_render_question_generation_cooldown",
    )
    _assert("disabled=True" in cooldown_source, "cooldown must disable generation")
    _assert(
        '"다시 시도할 수 있는지 확인"' in cooldown_source,
        "cooldown must expose a non-generating status refresh",
    )
    _assert(
        "_start_question_generation_cooldown(" in render_source
        and "exc.provider_unavailable" in render_source,
        "only categorized provider failures may start cooldown",
    )
    _assert(
        render_source.count("generate_chapter_questions(") == 1,
        "recovery UX must not add an automatic generation call",
    )
    _assert(
        render_source.index("generate_chapter_questions(")
        < render_source.index("update_chapter_questions("),
        "persistence must remain success-only",
    )

    print("[PASS] 503 category is preserved without raw provider text")
    print("[PASS] cooldown is 120 seconds and scoped by World/Chapter")
    print("[PASS] active cooldown blocks generation without automatic retry")
    print("[PASS] expired cooldown restores manual generation")
    print("[PASS] non-503 errors preserve the generic contract")
    print("[PASS] Question persistence remains success-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

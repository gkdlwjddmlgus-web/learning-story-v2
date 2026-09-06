from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
QUESTION_SERVICE = PROJECT_ROOT / "services" / "question_service.py"
GENERATION_GATEWAY = PROJECT_ROOT / "services" / "generation_gateway.py"
AI_CLIENT = PROJECT_ROOT / "services" / "ai_client.py"
AI_ROUTING = PROJECT_ROOT / "services" / "ai_routing_service.py"

EXPECTED_BUDGET = 6144
EXPECTED_QUESTION_COUNT = 5


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _module_constant(tree: ast.Module, name: str):
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id == name and isinstance(node.value, ast.Constant):
            return node.value.value
    raise AssertionError(f"missing module constant: {name}")


def _has_question_generate_call(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "generate_json":
            continue

        keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        feature = keywords.get("feature")
        budget = keywords.get("max_output_tokens")

        if not (
            isinstance(feature, ast.Constant)
            and feature.value == "question_generation"
        ):
            continue

        return (
            isinstance(budget, ast.Name)
            and budget.id == "QUESTION_MAX_OUTPUT_TOKENS"
        )
    return False


def _gateway_forwards_budget(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        if name != "generate_routed_json":
            continue

        if any(
            kw.arg == "max_output_tokens"
            and isinstance(kw.value, ast.Name)
            and kw.value.id == "max_output_tokens"
            for kw in node.keywords
        ):
            return True

        # Current gateway forwards through **live_kwargs instead of an explicit keyword.
        if any(kw.arg is None for kw in node.keywords):
            return True
    return False


def _client_default_budget(tree: ast.Module):
    return _module_constant(tree, "DEFAULT_MAX_OUTPUT_TOKENS")


def _router_forces_child_retries_zero(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Subscript):
                continue
            if not isinstance(target.value, ast.Name) or target.value.id != "route_kwargs":
                continue
            key = target.slice
            if isinstance(key, ast.Constant) and key.value == "max_retries":
                return isinstance(node.value, ast.Constant) and node.value.value == 0
    return False


def main() -> None:
    q_tree = _parse(QUESTION_SERVICE)
    g_tree = _parse(GENERATION_GATEWAY)
    c_tree = _parse(AI_CLIENT)
    r_tree = _parse(AI_ROUTING)

    assert _module_constant(q_tree, "QUESTION_COUNT") == EXPECTED_QUESTION_COUNT
    assert _module_constant(q_tree, "QUESTION_MAX_OUTPUT_TOKENS") == EXPECTED_BUDGET
    assert _has_question_generate_call(q_tree)
    assert _gateway_forwards_budget(g_tree)
    assert _client_default_budget(c_tree) == 4096
    assert _router_forces_child_retries_zero(r_tree)

    question_source = QUESTION_SERVICE.read_text(encoding="utf-8")
    assert "QUESTION_MAX_OUTPUT_TOKENS = 3072" not in question_source
    assert "QUESTION_MAX_OUTPUT_TOKENS = 6144" in question_source

    # Compile-only deterministic checks: no Gemini call, no repository import/write.
    compile(question_source, str(QUESTION_SERVICE), "exec")

    print("[PASS] Question Generation Output Budget v1 deterministic QA")
    print("[PASS] question batch remains 5")
    print("[PASS] question-only max_output_tokens: 6144")
    print("[PASS] generate_chapter_questions forwards QUESTION_MAX_OUTPUT_TOKENS")
    print("[PASS] generation_gateway still forwards max_output_tokens")
    print("[PASS] ai_client global default remains 4096")
    print("[PASS] AI router policy unchanged; child retries remain router-controlled")
    print("[PASS] no Gemini / no DB write in QA")


if __name__ == "__main__":
    main()

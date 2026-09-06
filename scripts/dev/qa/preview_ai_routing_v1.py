from __future__ import annotations

import sys
from pathlib import Path


# AI_ROUTING_V1_QA_IMPORT_HOTFIX_20260904
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from services.ai_routing_service import (
    GeminiKeySlot,
    build_route_plan,
    clear_route_state,
    global_attempt_budget,
    mark_route_exhausted,
    route_retry_cap,
    route_status_snapshot,
)


def _labels(routes):
    return [f"{route.key_slot}:{route.model}" for route in routes]


def main() -> int:
    clear_route_state()

    keys = [
        GeminiKeySlot("a", "TEST_KEY_A"),
        GeminiKeySlot("b", "TEST_KEY_B"),
        GeminiKeySlot("c", "TEST_KEY_C"),
    ]
    models = ["model-a", "model-b"]

    routes = build_route_plan(
        feature="question_generation",
        requested_model="model-a",
        key_slots=keys,
        models=models,
        model_mode="priority",
    )

    expected = [
        "a:model-a",
        "b:model-a",
        "c:model-a",
        "a:model-b",
        "b:model-b",
        "c:model-b",
    ]
    labels = _labels(routes)

    if labels != expected:
        raise AssertionError(f"route order mismatch: {labels}")

    mark_route_exhausted("a", "model-a", reason="qa")

    filtered = build_route_plan(
        feature="question_generation",
        requested_model="model-a",
        key_slots=keys,
        models=models,
        model_mode="priority",
    )

    if "a:model-a" in _labels(filtered):
        raise AssertionError("exhausted route was not skipped")

    story_routes = build_route_plan(
        feature="story_chapter",
        requested_model="model-a",
        key_slots=keys,
        models=["model-a", "model-b"],
        model_mode="round_robin",
        include_disabled=True,
    )

    if story_routes[0].model != "model-a":
        raise AssertionError(
            "story_chapter must keep requested model first"
        )

    print("=" * 72)
    print("AI Routing v1 foundation QA")
    print("=" * 72)
    print("[PASS] model-first / key-failover route order")
    print("[PASS] exhausted (key, model) route skip")
    print("[PASS] story_chapter requested-model stickiness")
    print("[INFO] global attempt budget:", global_attempt_budget())
    print("[INFO] route retry cap:", route_retry_cap())
    print("[INFO] state:", route_status_snapshot())
    print()
    print("No Gemini API request was made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

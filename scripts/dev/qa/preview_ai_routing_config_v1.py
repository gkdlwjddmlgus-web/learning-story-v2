from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from services.ai_client import DEFAULT_MODEL
from services.ai_routing_service import (
    build_route_plan,
    configured_key_slots,
    configured_models,
    global_attempt_budget,
    is_ai_routing_enabled,
    model_routing_mode,
    route_retry_cap,
)


FEATURES = (
    "story_block_outline",
    "story_chapter",
    "question_generation",
)


def _safe_route_label(route) -> str:
    return (
        f"{route.provider} / "
        f"{route.key_slot} / "
        f"{route.model}"
    )


def main() -> int:
    print("=" * 78)
    print("AI Routing v1 - Config-only QA")
    print("=" * 78)

    enabled = is_ai_routing_enabled()
    keys = configured_key_slots()
    models = configured_models(DEFAULT_MODEL)
    mode = model_routing_mode()
    budget = global_attempt_budget()
    retry_cap = route_retry_cap()

    print(f"[CONFIG] AI_ROUTING_V1 = {enabled}")
    print(f"[CONFIG] model mode = {mode}")
    print(f"[CONFIG] global attempt budget = {budget}")
    print(f"[CONFIG] route retry cap = {retry_cap}")
    print(f"[CONFIG] key slots = {len(keys)}")
    print(f"[CONFIG] models = {len(models)}")
    print()

    print("[KEY SLOTS]")
    for key in keys:
        # 실제 key 값은 절대 출력하지 않는다.
        secret_ref = (
            key.secret_name
            if key.secret_index is None
            else f"{key.secret_name}[{key.secret_index}]"
        )
        print(
            f"- slot={key.slot} "
            f"secret_ref={secret_ref}"
        )

    print()
    print("[MODELS]")
    for index, model in enumerate(models, start=1):
        print(f"- {index}. {model}")

    print()
    print("[ROUTE PLAN]")
    for feature in FEATURES:
        routes = build_route_plan(
            feature=feature,
            requested_model=DEFAULT_MODEL,
            include_disabled=True,
        )

        print(f"- feature={feature}")
        for index, route in enumerate(routes, start=1):
            print(
                f"  {index}. "
                + _safe_route_label(route)
            )

    print()
    print("[SAFETY CHECKS]")

    if budget < 1:
        raise AssertionError(
            "global attempt budget must be >= 1"
        )
    print("[PASS] global attempt budget is valid")

    if retry_cap < 0:
        raise AssertionError(
            "route retry cap must be >= 0"
        )
    print("[PASS] route retry cap is valid")

    if not keys:
        raise AssertionError(
            "no Gemini key slot detected"
        )
    print("[PASS] at least one Gemini key slot detected")

    if not models:
        raise AssertionError(
            "no model detected"
        )
    print("[PASS] at least one model detected")

    for feature in FEATURES:
        routes = build_route_plan(
            feature=feature,
            requested_model=DEFAULT_MODEL,
            include_disabled=True,
        )
        if not routes:
            raise AssertionError(
                f"empty route plan: {feature}"
            )

    print("[PASS] all feature route plans are non-empty")

    print()
    print("[SECURITY]")
    print("- API key values were not printed.")
    print("- Gemini API was not called.")
    print("- No quota was consumed.")
    print("- No runtime state was modified.")
    print()
    print("Config-only QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# AI_ROUTING_V1_LIST_KEYS_MODELS_20260904

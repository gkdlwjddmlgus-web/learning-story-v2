from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import services.ai_routing_service as router


class FakeHTTPError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self._ls_attempt_count = 1
        self._ls_retry_count = 0
        self._ls_retry_reasons = []


KEYS = [
    router.GeminiKeySlot(
        slot="key_1",
        secret_name="GEMINI_API_KEYS",
        secret_index=0,
    ),
    router.GeminiKeySlot(
        slot="key_2",
        secret_name="GEMINI_API_KEYS",
        secret_index=1,
    ),
    router.GeminiKeySlot(
        slot="key_3",
        secret_name="GEMINI_API_KEYS",
        secret_index=2,
    ),
]

MODELS = [
    "model-a",
    "model-b",
    "model-c",
]


def success_meta(kwargs):
    return {
        "attempt_count": 1,
        "retry_count": 0,
        "retry_reasons": [],
        "model": kwargs["model"],
        "key_slot": kwargs["key_slot"],
        "latency_ms": 1,
    }


def run_scenario(name, fake_call, expected_history):
    router.clear_route_state()

    original = {
        "generate_live_json": router.generate_live_json,
        "configured_key_slots": router.configured_key_slots,
        "configured_models": router.configured_models,
        "is_ai_routing_enabled": router.is_ai_routing_enabled,
        "global_attempt_budget": router.global_attempt_budget,
        "failover_route_budget": router.failover_route_budget,
        "transient_retry_budget": router.transient_retry_budget,
        "route_retry_cap": router.route_retry_cap,
        "model_routing_mode": router.model_routing_mode,
    }

    try:
        router.generate_live_json = fake_call
        router.configured_key_slots = lambda: list(KEYS)
        router.configured_models = lambda requested_model=router.DEFAULT_MODEL: list(MODELS)
        router.is_ai_routing_enabled = lambda: True
        router.global_attempt_budget = lambda: 10
        router.failover_route_budget = lambda: 9
        router.transient_retry_budget = lambda: 1
        router.route_retry_cap = lambda: 1
        router.model_routing_mode = lambda: "priority"

        result, meta = router.generate_routed_json(
            feature="qa",
            prompt="qa",
            schema={"type": "object"},
            model="model-a",
            max_retries=1,
            timeout_ms=1_000,
            retry_on_timeout=True,
        )

        history = meta.get("route_history", [])
        if history != expected_history:
            raise AssertionError(
                f"{name}: history mismatch\n"
                f"expected={expected_history}\n"
                f"actual={history}"
            )

        if result.get("ok") is not True:
            raise AssertionError(
                f"{name}: unexpected result={result!r}"
            )

        print(f"[PASS] {name}")
        return meta

    finally:
        for key, value in original.items():
            setattr(router, key, value)
        router.clear_route_state()


def main() -> int:
    print("=" * 78)
    print("AI Routing v1.1 - Error-aware Failover QA")
    print("=" * 78)

    calls = []

    def hard_quota_then_key2(**kwargs):
        calls.append(
            (kwargs["key_slot"], kwargs["model"])
        )
        if kwargs["key_slot"] == "key_1":
            exc = router.AIQuotaExhausted(
                "daily quota exhausted"
            )
            exc._ls_attempt_count = 1
            exc._ls_retry_count = 0
            exc._ls_retry_reasons = []
            raise exc
        return {"ok": True}, success_meta(kwargs)

    run_scenario(
        "hard quota -> same model next key",
        hard_quota_then_key2,
        [
            "gemini:key_1:model-a:hard_quota",
            "gemini:key_2:model-a:success",
        ],
    )

    def overload_then_model_b(**kwargs):
        if kwargs["model"] == "model-a":
            raise FakeHTTPError(
                503,
                "This model is currently experiencing high demand.",
            )
        return {"ok": True}, success_meta(kwargs)

    run_scenario(
        "503 high demand -> same key next model",
        overload_then_model_b,
        [
            "gemini:key_1:model-a:model_overload",
            "gemini:key_1:model-b:success",
        ],
    )

    def rate_limit_then_key2(**kwargs):
        if kwargs["key_slot"] == "key_1":
            raise FakeHTTPError(
                429,
                "Too many requests / rate limit",
            )
        return {"ok": True}, success_meta(kwargs)

    run_scenario(
        "soft 429 -> same model next key",
        rate_limit_then_key2,
        [
            "gemini:key_1:model-a:rate_limit",
            "gemini:key_2:model-a:success",
        ],
    )

    def auth_then_key2(**kwargs):
        if kwargs["key_slot"] == "key_1":
            raise FakeHTTPError(
                401,
                "invalid API key",
            )
        return {"ok": True}, success_meta(kwargs)

    run_scenario(
        "auth -> disable key and use next key",
        auth_then_key2,
        [
            "gemini:key_1:model-a:auth",
            "gemini:key_2:model-a:success",
        ],
    )

    timeout_calls = {}

    def timeout_once_then_success(**kwargs):
        pair = (
            kwargs["key_slot"],
            kwargs["model"],
        )
        timeout_calls[pair] = (
            timeout_calls.get(pair, 0) + 1
        )
        if timeout_calls[pair] == 1:
            exc = TimeoutError("timed out")
            exc._ls_attempt_count = 1
            exc._ls_retry_count = 0
            exc._ls_retry_reasons = []
            raise exc
        return {"ok": True}, success_meta(kwargs)

    meta = run_scenario(
        "timeout -> one bounded same-route retry",
        timeout_once_then_success,
        [
            "gemini:key_1:model-a:timeout",
            "gemini:key_1:model-a:success",
        ],
    )
    if meta.get("router_retries") != 1:
        raise AssertionError(
            "timeout scenario: router_retries != 1"
        )

    router.clear_route_state()
    original = {
        "generate_live_json": router.generate_live_json,
        "configured_key_slots": router.configured_key_slots,
        "configured_models": router.configured_models,
        "is_ai_routing_enabled": router.is_ai_routing_enabled,
        "global_attempt_budget": router.global_attempt_budget,
        "failover_route_budget": router.failover_route_budget,
        "transient_retry_budget": router.transient_retry_budget,
        "route_retry_cap": router.route_retry_cap,
        "model_routing_mode": router.model_routing_mode,
    }

    schema_calls = []
    try:
        def schema_error(**kwargs):
            schema_calls.append(
                (kwargs["key_slot"], kwargs["model"])
            )
            exc = ValueError(
                "schema validation failed"
            )
            exc._ls_attempt_count = 1
            exc._ls_retry_count = 0
            exc._ls_retry_reasons = []
            raise exc

        router.generate_live_json = schema_error
        router.configured_key_slots = lambda: list(KEYS)
        router.configured_models = lambda requested_model=router.DEFAULT_MODEL: list(MODELS)
        router.is_ai_routing_enabled = lambda: True
        router.global_attempt_budget = lambda: 10
        router.failover_route_budget = lambda: 9
        router.transient_retry_budget = lambda: 1
        router.route_retry_cap = lambda: 1
        router.model_routing_mode = lambda: "priority"

        try:
            router.generate_routed_json(
                feature="qa",
                prompt="qa",
                schema={"type": "object"},
                model="model-a",
                max_retries=1,
            )
            raise AssertionError(
                "schema/content scenario unexpectedly succeeded"
            )
        except ValueError as exc:
            history = getattr(
                exc,
                "_ls_route_history",
                [],
            )
            if history != [
                "gemini:key_1:model-a:other"
            ]:
                raise AssertionError(
                    "schema/content route churn detected: "
                    + repr(history)
                )

        if len(schema_calls) != 1:
            raise AssertionError(
                "schema/content consumed more than one route"
            )
        print(
            "[PASS] schema/content error -> no key/model churn"
        )

    finally:
        for key, value in original.items():
            setattr(router, key, value)
        router.clear_route_state()

    hard_calls = []

    def three_hard_quotas_then_model_b(**kwargs):
        hard_calls.append(
            (kwargs["key_slot"], kwargs["model"])
        )
        if kwargs["model"] == "model-a":
            exc = router.AIQuotaExhausted(
                "daily quota exhausted"
            )
            exc._ls_attempt_count = 1
            exc._ls_retry_count = 0
            exc._ls_retry_reasons = []
            raise exc
        return {"ok": True}, success_meta(kwargs)

    meta = run_scenario(
        "all 3 keys exhausted on model-a -> model-b",
        three_hard_quotas_then_model_b,
        [
            "gemini:key_1:model-a:hard_quota",
            "gemini:key_2:model-a:hard_quota",
            "gemini:key_3:model-a:hard_quota",
            "gemini:key_1:model-b:success",
        ],
    )
    if meta.get("attempt_count") != 4:
        raise AssertionError(
            "three-key hard quota failover should use 4 attempts"
        )

    overload_calls = []

    router.clear_route_state()
    original = {
        "generate_live_json": router.generate_live_json,
        "configured_key_slots": router.configured_key_slots,
        "configured_models": router.configured_models,
        "is_ai_routing_enabled": router.is_ai_routing_enabled,
        "global_attempt_budget": router.global_attempt_budget,
        "failover_route_budget": router.failover_route_budget,
        "transient_retry_budget": router.transient_retry_budget,
        "route_retry_cap": router.route_retry_cap,
        "model_routing_mode": router.model_routing_mode,
    }

    try:
        def all_models_overloaded(**kwargs):
            overload_calls.append(
                (kwargs["key_slot"], kwargs["model"])
            )
            raise FakeHTTPError(
                503,
                "model currently experiencing high demand",
            )

        router.generate_live_json = all_models_overloaded
        router.configured_key_slots = lambda: list(KEYS)
        router.configured_models = lambda requested_model=router.DEFAULT_MODEL: list(MODELS)
        router.is_ai_routing_enabled = lambda: True
        router.global_attempt_budget = lambda: 10
        router.failover_route_budget = lambda: 9
        router.transient_retry_budget = lambda: 1
        router.route_retry_cap = lambda: 1
        router.model_routing_mode = lambda: "priority"

        try:
            router.generate_routed_json(
                feature="qa",
                prompt="qa",
                schema={"type": "object"},
                model="model-a",
                max_retries=1,
            )
            raise AssertionError(
                "all-overload scenario unexpectedly succeeded"
            )
        except FakeHTTPError as exc:
            history = getattr(
                exc,
                "_ls_route_history",
                [],
            )
            expected = [
                "gemini:key_1:model-a:model_overload",
                "gemini:key_1:model-b:model_overload",
                "gemini:key_1:model-c:model_overload",
            ]
            if history != expected:
                raise AssertionError(
                    "model overload should not burn other project keys\n"
                    f"expected={expected}\nactual={history}"
                )

        if overload_calls != [
            ("key_1", "model-a"),
            ("key_1", "model-b"),
            ("key_1", "model-c"),
        ]:
            raise AssertionError(
                "503 overload burned extra project keys: "
                + repr(overload_calls)
            )

        print(
            "[PASS] all models overloaded -> no pointless key churn"
        )

    finally:
        for key, value in original.items():
            setattr(router, key, value)
        router.clear_route_state()

    print()
    print("[POLICY]")
    print("- hard quota: same model -> next key")
    print("- soft 429: same model -> next key")
    print("- 503/high demand: same key -> next model")
    print("- timeout: max 1 bounded same-route retry")
    print("- auth: disable key -> next key")
    print("- schema/content/unknown: no route churn")
    print("- default unique failover routes: 9")
    print("- default global physical attempts: 10")
    print()
    print("[SECURITY / COST]")
    print("- No Gemini API request was made.")
    print("- Fake generate_live_json was used for every scenario.")
    print("- No DB query/write was made.")
    print()
    print("AI Routing v1.1 Error-aware Failover QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 이 QA 프로세스 안에서만 Router를 켠다.
# 앱의 기본 설정이나 secrets.toml은 변경하지 않는다.
os.environ["AI_ROUTING_V1"] = "true"
os.environ["AI_ROUTING_GLOBAL_ATTEMPTS"] = "4"
os.environ["AI_ROUTING_ROUTE_RETRIES"] = "0"

from services.ai_client import DEFAULT_MODEL
from services.ai_routing_service import generate_routed_json


SMOKE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["ok"],
    "properties": {
        "ok": {
            "type": "boolean",
        },
    },
}


def main() -> int:
    print("=" * 78)
    print("AI Routing v1 - Live Smoke QA")
    print("=" * 78)
    print("[MODE] Router enabled only for this QA process")
    print("[BUDGET] max 4 Gemini attempts")
    print("[ROUTE RETRIES] 0")
    print("[PROMPT] minimal structured JSON")
    print()

    result, meta = generate_routed_json(
        feature="ai_routing_live_smoke",
        prompt=(
            'Return JSON with exactly one field: '
            '{"ok": true}. Do not add any other field.'
        ),
        schema=SMOKE_SCHEMA,
        model=DEFAULT_MODEL,
        max_retries=0,
        timeout_ms=30_000,
        thinking_level="low",
        max_output_tokens=64,
        retry_on_timeout=False,
    )

    if not isinstance(result, dict):
        raise AssertionError(
            f"unexpected result type: {type(result).__name__}"
        )

    if result.get("ok") is not True:
        raise AssertionError(
            f"unexpected result payload: {result!r}"
        )

    print("[PASS] structured JSON response")
    print(
        "[PASS] selected model:",
        meta.get("model"),
    )
    print(
        "[PASS] selected key slot:",
        meta.get("key_slot"),
    )
    print(
        "[INFO] attempt_count:",
        meta.get("attempt_count"),
    )
    print(
        "[INFO] retry_count:",
        meta.get("retry_count"),
    )
    print(
        "[INFO] route_history:",
        meta.get("route_history"),
    )
    print(
        "[INFO] latency_ms:",
        meta.get("latency_ms"),
    )
    print()
    print("[SECURITY]")
    print("- API key value was not printed.")
    print("- Only logical key slot alias was printed.")
    print()
    print("Live Smoke QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

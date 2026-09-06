from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st

from services.ai_client import (
    AIQuotaExhausted,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MODEL,
    generate_live_json,
)


# AI_ROUTING_V1_FOUNDATION_20260904

MAX_KEY_SLOTS = 8
DEFAULT_GLOBAL_ATTEMPT_BUDGET = 10
DEFAULT_ROUTE_RETRY_CAP = 1
DEFAULT_FAILOVER_ROUTE_BUDGET = 9
DEFAULT_TRANSIENT_RETRY_BUDGET = 1
DEFAULT_MODEL_COOLDOWN_SECONDS = 30
DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS = 60
DEFAULT_AUTH_DISABLE_SECONDS = 86_400

DEFAULT_ROUTING_MODELS = (
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
)

_ROUTE_LOCK = threading.Lock()
_ROUTE_STATE: dict[tuple[str, str], dict[str, Any]] = {}
_MODEL_RR_COUNTER: dict[str, int] = {}


@dataclass(frozen=True)
class GeminiKeySlot:
    slot: str
    secret_name: str
    secret_index: int | None = None



@dataclass(frozen=True)
class AIRoute:
    provider: str
    model: str
    key_slot: str
    secret_name: str
    secret_index: int | None = None



def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {
        "1", "true", "yes", "y", "on",
    }


def _secret(name: str, default: Any = None) -> Any:
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _config_value(name: str, default: Any = None) -> Any:
    env = os.getenv(name)
    if env is not None:
        return env
    return _secret(name, default)


def _bounded_int(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def is_ai_routing_enabled() -> bool:
    """
    AI Routing v1 기본 활성화.

    명시적 override:
    - AI_ROUTING_V1=false  -> OFF
    - AI_ROUTING_V1=true   -> ON

    설정이 없으면 Router를 기본 사용한다.
    """
    return _to_bool(
        _config_value(
            "AI_ROUTING_V1",
            True,
        )
    )


def global_attempt_budget() -> int:
    """
    한 logical generation에서 허용할 전체 physical Gemini call의 최종 hard ceiling.

    v1.1에서는 failover route budget과 transient retry budget을 분리하되,
    어떤 경우에도 이 ceiling을 넘지 않는다.
    """
    return _bounded_int(
        _config_value(
            "AI_ROUTING_GLOBAL_ATTEMPTS",
            DEFAULT_GLOBAL_ATTEMPT_BUDGET,
        ),
        default=DEFAULT_GLOBAL_ATTEMPT_BUDGET,
        minimum=1,
        maximum=16,
    )



def route_retry_cap() -> int:
    return _bounded_int(
        _config_value(
            "AI_ROUTING_ROUTE_RETRIES",
            DEFAULT_ROUTE_RETRY_CAP,
        ),
        default=DEFAULT_ROUTE_RETRY_CAP,
        minimum=0,
        maximum=2,
    )


def failover_route_budget() -> int:
    """
    서로 다른 (key, model) route를 탐색할 수 있는 최대 개수.

    3 keys x 3 models 기본 구성은 최대 9개의 unique route를 가진다.
    """
    return _bounded_int(
        _config_value(
            "AI_ROUTING_FAILOVER_ROUTES",
            DEFAULT_FAILOVER_ROUTE_BUDGET,
        ),
        default=DEFAULT_FAILOVER_ROUTE_BUDGET,
        minimum=1,
        maximum=16,
    )


def transient_retry_budget() -> int:
    """
    timeout/network 계열에서 같은 route를 다시 시도할 수 있는
    logical generation 전체 retry 예산.
    """
    return _bounded_int(
        _config_value(
            "AI_ROUTING_TRANSIENT_RETRIES",
            DEFAULT_TRANSIENT_RETRY_BUDGET,
        ),
        default=DEFAULT_TRANSIENT_RETRY_BUDGET,
        minimum=0,
        maximum=3,
    )


def _cooldown_seconds(
    name: str,
    *,
    default: int,
    maximum: int,
) -> int:
    return _bounded_int(
        _config_value(name, default),
        default=default,
        minimum=1,
        maximum=maximum,
    )

def model_routing_mode() -> str:
    raw = str(
        _config_value("AI_ROUTING_MODEL_MODE", "priority")
        or "priority"
    ).strip().lower()
    return raw if raw in {"priority", "round_robin"} else "priority"


def _normalize_model_list(value: Any) -> list[str]:
    if value is None:
        return []

    values = list(value) if isinstance(value, (list, tuple)) else str(value).split(",")

    result: list[str] = []
    for item in values:
        model = str(item or "").strip()
        if model and model not in result:
            result.append(model)
    return result


def configured_models(
    requested_model: str = DEFAULT_MODEL,
) -> list[str]:
    """기본 stable 모델 풀. 명시적 AI_ROUTING_MODELS 설정이 있으면 override."""
    requested = str(requested_model or DEFAULT_MODEL).strip()
    configured = _normalize_model_list(
        _config_value("AI_ROUTING_MODELS", None)
    )
    preferred = configured if configured else list(DEFAULT_ROUTING_MODELS)

    result: list[str] = []
    for model in [*preferred, requested]:
        model = str(model or "").strip()
        if model and model not in result:
            result.append(model)
    return result



def configured_key_slots() -> list[GeminiKeySlot]:
    """
    권장 형식:
        GEMINI_API_KEYS = ["...", "...", "..."]

    실제 key 값은 Router 객체에 넣지 않고 secret container 이름 + index만 전달한다.
    기존 GEMINI_API_KEY / GEMINI_API_KEY_2 형식도 fallback 호환한다.
    """
    slots: list[GeminiKeySlot] = []

    raw_pool = _secret("GEMINI_API_KEYS", None)
    if isinstance(raw_pool, (list, tuple)):
        for index, value in enumerate(raw_pool):
            if not str(value or "").strip():
                continue
            slots.append(
                GeminiKeySlot(
                    slot=f"key_{index + 1}",
                    secret_name="GEMINI_API_KEYS",
                    secret_index=index,
                )
            )

    if slots:
        return slots

    if _secret("GEMINI_API_KEY", None):
        slots.append(
            GeminiKeySlot(
                slot="primary",
                secret_name="GEMINI_API_KEY",
                secret_index=None,
            )
        )

    for index in range(2, MAX_KEY_SLOTS + 1):
        secret_name = f"GEMINI_API_KEY_{index}"
        if _secret(secret_name, None):
            slots.append(
                GeminiKeySlot(
                    slot=f"key_{index}",
                    secret_name=secret_name,
                    secret_index=None,
                )
            )

    if not slots:
        slots.append(
            GeminiKeySlot(
                slot="primary",
                secret_name="GEMINI_API_KEY",
                secret_index=None,
            )
        )

    return slots



def _next_pacific_midnight_epoch() -> float:
    pacific = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific)
    tomorrow = now.date() + timedelta(days=1)
    reset = datetime.combine(
        tomorrow,
        dt_time.min,
        tzinfo=pacific,
    )
    return reset.timestamp()


def clear_expired_route_state() -> None:
    now = time.time()
    with _ROUTE_LOCK:
        expired = [
            key
            for key, state in _ROUTE_STATE.items()
            if float(state.get("disabled_until") or 0) <= now
        ]
        for key in expired:
            _ROUTE_STATE.pop(key, None)


def clear_route_state() -> None:
    with _ROUTE_LOCK:
        _ROUTE_STATE.clear()
        _MODEL_RR_COUNTER.clear()


def mark_route_exhausted(
    key_slot: str,
    model: str,
    *,
    reason: str = "hard_quota",
) -> None:
    with _ROUTE_LOCK:
        _ROUTE_STATE[(str(key_slot), str(model))] = {
            "status": "daily_exhausted",
            "reason": str(reason),
            "disabled_until": _next_pacific_midnight_epoch(),
        }


def _mark_route_state(
    *,
    key_slot: str,
    model: str,
    status: str,
    reason: str,
    disabled_until: float,
) -> None:
    with _ROUTE_LOCK:
        _ROUTE_STATE[(str(key_slot), str(model))] = {
            "status": str(status),
            "reason": str(reason),
            "disabled_until": float(disabled_until),
        }


def mark_route_cooldown(
    key_slot: str,
    model: str,
    *,
    reason: str,
    seconds: int,
) -> None:
    _mark_route_state(
        key_slot=key_slot,
        model=model,
        status="cooldown",
        reason=reason,
        disabled_until=time.time() + max(1, int(seconds)),
    )


def mark_model_cooldown(
    model: str,
    *,
    reason: str = "model_overload",
    seconds: int | None = None,
) -> None:
    duration = (
        _cooldown_seconds(
            "AI_ROUTING_MODEL_COOLDOWN_SECONDS",
            default=DEFAULT_MODEL_COOLDOWN_SECONDS,
            maximum=300,
        )
        if seconds is None
        else max(1, int(seconds))
    )
    _mark_route_state(
        key_slot="*",
        model=model,
        status="model_cooldown",
        reason=reason,
        disabled_until=time.time() + duration,
    )


def mark_key_auth_failed(
    key_slot: str,
    *,
    reason: str = "auth",
    seconds: int | None = None,
) -> None:
    duration = (
        _cooldown_seconds(
            "AI_ROUTING_AUTH_DISABLE_SECONDS",
            default=DEFAULT_AUTH_DISABLE_SECONDS,
            maximum=604_800,
        )
        if seconds is None
        else max(1, int(seconds))
    )
    _mark_route_state(
        key_slot=key_slot,
        model="*",
        status="auth_failed",
        reason=reason,
        disabled_until=time.time() + duration,
    )

def route_status_snapshot() -> list[dict[str, Any]]:
    clear_expired_route_state()
    now = time.time()

    with _ROUTE_LOCK:
        rows = []
        for (key_slot, model), state in sorted(_ROUTE_STATE.items()):
            rows.append(
                {
                    "key_slot": key_slot,
                    "model": model,
                    "status": state.get("status"),
                    "reason": state.get("reason"),
                    "disabled_seconds": max(
                        0,
                        int(float(state.get("disabled_until") or 0) - now),
                    ),
                }
            )
        return rows


def _route_available(key_slot: str, model: str) -> bool:
    """
    exact route, key-wide state, model-wide state를 모두 확인한다.

    exact:      (key_1, gemini-3.8-flash)
    key-wide:   (key_1, *)
    model-wide: (*, gemini-3.8-flash)
    """
    clear_expired_route_state()
    now = time.time()

    with _ROUTE_LOCK:
        states = (
            _ROUTE_STATE.get((str(key_slot), str(model))),
            _ROUTE_STATE.get((str(key_slot), "*")),
            _ROUTE_STATE.get(("*", str(model))),
        )

    for state in states:
        if not state:
            continue
        if float(state.get("disabled_until") or 0) > now:
            return False

    return True



def _ordered_models(
    feature: str,
    requested_model: str,
    *,
    models: list[str] | None = None,
    mode: str | None = None,
) -> list[str]:
    values = list(
        models if models is not None else configured_models(requested_model)
    )
    if not values:
        values = [requested_model or DEFAULT_MODEL]

    selected_mode = str(mode or model_routing_mode()).strip().lower()

    # Story 본문과 Story repair는 같은 requested model을 우선한다.
    if feature == "story_chapter":
        selected_mode = "priority"

    if selected_mode != "round_robin" or len(values) <= 1:
        return values

    with _ROUTE_LOCK:
        start = _MODEL_RR_COUNTER.get(feature, 0) % len(values)
        _MODEL_RR_COUNTER[feature] = start + 1

    return values[start:] + values[:start]


def build_route_plan(
    *,
    feature: str,
    requested_model: str = DEFAULT_MODEL,
    key_slots: list[GeminiKeySlot] | None = None,
    models: list[str] | None = None,
    model_mode: str | None = None,
    include_disabled: bool = False,
) -> list[AIRoute]:
    keys = list(
        key_slots if key_slots is not None else configured_key_slots()
    )
    ordered_models = _ordered_models(
        feature,
        requested_model,
        models=models,
        mode=model_mode,
    )

    routes: list[AIRoute] = []

    # 같은 모델의 key failover를 먼저 모두 사용한 뒤 다음 모델로 넘어간다.
    for model in ordered_models:
        for key in keys:
            if (
                not include_disabled
                and not _route_available(key.slot, model)
            ):
                continue
            routes.append(
                AIRoute(
                    provider="gemini",
                    model=model,
                    key_slot=key.slot,
                    secret_name=key.secret_name,
                    secret_index=key.secret_index,
                )
            )

    return routes


def _status_code(exc: Exception) -> int | None:
    for name in ("status_code", "code"):
        value = getattr(exc, name, None)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass

    message = str(exc)
    for code in (400, 401, 403, 408, 429, 500, 502, 503, 504):
        if str(code) in message:
            return code
    return None


def _error_kind(exc: Exception) -> str:
    """
    Router policy용 오류 분류.

    hard_quota
        daily/project hard quota. 같은 model의 다음 key가 우선.

    rate_limit
        RPM/TPM/soft 429. 현재 (key, model)을 잠깐 식히고 같은 model의
        다음 key가 우선.

    model_overload
        503/high demand/unavailable. key를 바꾸기보다 같은 key의
        다음 model이 우선.

    timeout
        같은 route의 제한된 retry 후 다음 model.

    transient
        500/502/504 등. 같은 key의 다음 model이 우선.

    auth
        해당 key 전체를 비활성화하고 다음 key.

    other
        schema/JSON/content/400/unknown. 독립 key/model을 소모하지 않고 즉시 반환.
    """
    if isinstance(exc, AIQuotaExhausted):
        return "hard_quota"

    code = _status_code(exc)
    message = str(exc).lower()
    name = type(exc).__name__.lower()

    if code in (401, 403):
        return "auth"

    if (
        "timeout" in name
        or "timed out" in message
        or "deadline exceeded" in message
        or code == 408
    ):
        return "timeout"

    if (
        code == 503
        or "high demand" in message
        or "model is currently experiencing high demand" in message
        or "temporarily overloaded" in message
        or "service unavailable" in message
        or "model unavailable" in message
    ):
        return "model_overload"

    if (
        code == 429
        or "rate limit" in message
        or "too many requests" in message
    ):
        return "rate_limit"

    if (
        code in (500, 502, 504)
        or "bad gateway" in message
        or "gateway timeout" in message
        or "temporarily unavailable" in message
    ):
        return "transient"

    return "other"



def _attach_router_meta(
    exc: Exception,
    *,
    model: str,
    key_slot: str,
    attempt_count: int,
    retry_count: int,
    retry_reasons: list[str],
    latency_ms: int,
    route_history: list[str],
) -> None:
    values = {
        "_ls_model": model,
        "_ls_key_slot": key_slot,
        "_ls_attempt_count": attempt_count,
        "_ls_retry_count": retry_count,
        "_ls_retry_reasons": list(retry_reasons),
        "_ls_latency_ms": latency_ms,
        "_ls_route_history": list(route_history),
    }
    for key, value in values.items():
        try:
            setattr(exc, key, value)
        except Exception:
            pass


def _route_key(route: AIRoute) -> tuple[str, str]:
    return str(route.key_slot), str(route.model)


def _first_available_unattempted(
    routes: list[AIRoute],
    attempted_unique: set[tuple[str, str]],
) -> AIRoute | None:
    for candidate in routes:
        pair = _route_key(candidate)
        if pair in attempted_unique:
            continue
        if not _route_available(
            candidate.key_slot,
            candidate.model,
        ):
            continue
        return candidate
    return None


def _same_model_next_key(
    current: AIRoute,
    routes: list[AIRoute],
    attempted_unique: set[tuple[str, str]],
) -> AIRoute | None:
    """
    hard quota / rate-limit / auth:
    같은 model을 유지한 채 다음 key를 먼저 사용한다.
    """
    found_current = False

    for candidate in routes:
        if candidate.model != current.model:
            continue

        if _route_key(candidate) == _route_key(current):
            found_current = True
            continue

        if not found_current:
            continue

        pair = _route_key(candidate)
        if pair in attempted_unique:
            continue

        if _route_available(
            candidate.key_slot,
            candidate.model,
        ):
            return candidate

    return _first_available_unattempted(
        routes,
        attempted_unique,
    )


def _same_key_next_model(
    current: AIRoute,
    routes: list[AIRoute],
    attempted_unique: set[tuple[str, str]],
) -> AIRoute | None:
    """
    503/model overload / provider transient:
    key를 바꾸기 전에 같은 key의 다음 model을 우선한다.
    """
    current_seen = False

    # build_route_plan은 model-first 순서이므로
    # 같은 key의 model 순서는 routes에서 다시 추출한다.
    same_key = [
        candidate
        for candidate in routes
        if candidate.key_slot == current.key_slot
    ]

    for candidate in same_key:
        if _route_key(candidate) == _route_key(current):
            current_seen = True
            continue

        if not current_seen:
            continue

        pair = _route_key(candidate)
        if pair in attempted_unique:
            continue

        if _route_available(
            candidate.key_slot,
            candidate.model,
        ):
            return candidate

    return _first_available_unattempted(
        routes,
        attempted_unique,
    )


def _exception_attempt_meta(
    exc: Exception,
) -> tuple[int, int, list[str]]:
    attempts = max(
        1,
        int(getattr(exc, "_ls_attempt_count", 1)),
    )
    retries = int(
        getattr(
            exc,
            "_ls_retry_count",
            max(0, attempts - 1),
        )
    )
    reasons = [
        str(reason)
        for reason in getattr(
            exc,
            "_ls_retry_reasons",
            [],
        )
    ]
    return attempts, retries, reasons

def generate_routed_json(
    *,
    feature: str,
    prompt: str,
    schema: dict[str, Any],
    model: str = DEFAULT_MODEL,
    max_retries: int | None = None,
    base_delay: float | None = None,
    timeout_ms: int | None = None,
    thinking_level: str | None = None,
    max_output_tokens: int | None = None,
    retry_on_timeout: bool = True,
) -> tuple[Any, dict[str, Any]]:
    """
    Gemini error-aware multi-key + multi-model router v1.1.

    핵심:
    - hard quota / soft 429 -> same model, next key
    - 503/high demand      -> same key, next model
    - timeout              -> bounded same-route retry, then next model
    - auth                 -> disable key, next key
    - schema/content/other -> no key/model churn
    - generate_live_json 내부 retry는 0으로 고정하고 Router가 retry/failover를 제어
    """

    direct_kwargs: dict[str, Any] = {
        "prompt": prompt,
        "schema": schema,
        "model": model,
        "retry_on_timeout": retry_on_timeout,
    }

    if base_delay is not None:
        direct_kwargs["base_delay"] = base_delay
    if timeout_ms is not None:
        direct_kwargs["timeout_ms"] = timeout_ms
    if thinking_level is not None:
        direct_kwargs["thinking_level"] = thinking_level
    if max_output_tokens is not None:
        direct_kwargs["max_output_tokens"] = max_output_tokens

    if not is_ai_routing_enabled():
        legacy_kwargs = dict(direct_kwargs)
        if max_retries is not None:
            legacy_kwargs["max_retries"] = max_retries

        result, meta = generate_live_json(
            **legacy_kwargs
        )
        meta = dict(meta)
        meta.setdefault("model", model)
        meta.setdefault("key_slot", "primary")
        meta["routing_enabled"] = False
        meta["route_history"] = [
            f"gemini:{meta['key_slot']}:{meta['model']}:success"
        ]
        return result, meta

    routes = build_route_plan(
        feature=feature,
        requested_model=model,
    )

    if not routes:
        exhausted = AIQuotaExhausted(
            "사용 가능한 Gemini model/key route가 없습니다."
        )
        _attach_router_meta(
            exhausted,
            model=model,
            key_slot="none",
            attempt_count=0,
            retry_count=0,
            retry_reasons=["router:no_available_route"],
            latency_ms=0,
            route_history=[],
        )
        raise exhausted

    total_cap = global_attempt_budget()
    unique_cap = min(
        failover_route_budget(),
        len(routes),
    )
    retry_total_cap = transient_retry_budget()
    retry_per_route_cap = route_retry_cap()

    requested_retry_cap = (
        DEFAULT_MAX_RETRIES
        if max_retries is None
        else max(0, int(max_retries))
    )
    retry_per_route_cap = min(
        retry_per_route_cap,
        requested_retry_cap,
    )

    physical_attempts = 0
    router_retries = 0
    aggregate_retries = 0
    aggregate_reasons: list[str] = []
    route_history: list[str] = []
    attempted_unique: set[tuple[str, str]] = set()
    retry_count_by_route: dict[tuple[str, str], int] = {}

    started = time.perf_counter()
    last_error: Exception | None = None
    last_route: AIRoute | None = None
    failure_kinds: list[str] = []

    current = _first_available_unattempted(
        routes,
        attempted_unique,
    )

    while current is not None:
        if physical_attempts >= total_cap:
            break

        pair = _route_key(current)
        is_unique = pair not in attempted_unique

        if is_unique:
            if len(attempted_unique) >= unique_cap:
                break
            attempted_unique.add(pair)

        route_kwargs = dict(direct_kwargs)
        route_kwargs["model"] = current.model

        # 중요: 내부 exponential retry가 503 한 route에 예산을 소비하지 않게 한다.
        route_kwargs["max_retries"] = 0
        route_kwargs["api_key_secret_name"] = current.secret_name
        route_kwargs["api_key_secret_index"] = current.secret_index
        route_kwargs["key_slot"] = current.key_slot

        route_label = (
            f"{current.provider}:{current.key_slot}:{current.model}"
        )

        physical_attempts += 1
        last_route = current

        try:
            result, meta = generate_live_json(
                **route_kwargs
            )

            call_attempts = max(
                1,
                int(meta.get("attempt_count", 1)),
            )
            aggregate_retries += int(
                meta.get("retry_count", 0)
            )
            aggregate_reasons.extend(
                str(reason)
                for reason in meta.get(
                    "retry_reasons",
                    [],
                )
            )
            route_history.append(
                route_label + ":success"
            )

            final_meta = dict(meta)
            final_meta.update(
                {
                    "model": current.model,
                    "key_slot": current.key_slot,
                    "routing_enabled": True,
                    "attempt_count": physical_attempts,
                    "retry_count": (
                        aggregate_retries
                        + router_retries
                    ),
                    "retry_reasons": aggregate_reasons,
                    "route_history": route_history,
                    "latency_ms": int(
                        (
                            time.perf_counter()
                            - started
                        )
                        * 1000
                    ),
                    "router_unique_routes": len(
                        attempted_unique
                    ),
                    "router_retries": router_retries,
                }
            )

            # ai_client가 max_retries=0인데도 메타가 >1이면 보수적으로 기록만 반영한다.
            if call_attempts > 1:
                final_meta["attempt_count"] += (
                    call_attempts - 1
                )

            return result, final_meta

        except Exception as exc:
            last_error = exc
            kind = _error_kind(exc)
            failure_kinds.append(kind)

            _, child_retries, child_reasons = (
                _exception_attempt_meta(exc)
            )
            aggregate_retries += child_retries
            aggregate_reasons.extend(
                child_reasons
            )
            aggregate_reasons.append(
                f"route:{current.key_slot}:{current.model}:{kind}"
            )
            route_history.append(
                route_label + ":" + kind
            )

            if kind == "hard_quota":
                mark_route_exhausted(
                    current.key_slot,
                    current.model,
                    reason=kind,
                )
                current = _same_model_next_key(
                    current,
                    routes,
                    attempted_unique,
                )
                continue

            if kind == "rate_limit":
                mark_route_cooldown(
                    current.key_slot,
                    current.model,
                    reason=kind,
                    seconds=_cooldown_seconds(
                        "AI_ROUTING_RATE_LIMIT_COOLDOWN_SECONDS",
                        default=DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS,
                        maximum=300,
                    ),
                )
                current = _same_model_next_key(
                    current,
                    routes,
                    attempted_unique,
                )
                continue

            if kind == "auth":
                mark_key_auth_failed(
                    current.key_slot,
                    reason=kind,
                )
                current = _same_model_next_key(
                    current,
                    routes,
                    attempted_unique,
                )
                continue

            if kind == "model_overload":
                # 같은 model의 다른 project key를 태우지 않는다.
                mark_model_cooldown(
                    current.model,
                    reason=kind,
                )
                current = _same_key_next_model(
                    current,
                    routes,
                    attempted_unique,
                )
                continue

            if kind == "timeout":
                retries_here = retry_count_by_route.get(
                    pair,
                    0,
                )
                can_retry_same_route = (
                    retry_on_timeout
                    and router_retries < retry_total_cap
                    and retries_here < retry_per_route_cap
                    and physical_attempts < total_cap
                )

                if can_retry_same_route:
                    retry_count_by_route[pair] = (
                        retries_here + 1
                    )
                    router_retries += 1
                    aggregate_reasons.append(
                        f"router_retry:{current.key_slot}:{current.model}:timeout"
                    )
                    # attempted_unique에는 이미 있으므로 같은 route physical retry.
                    continue

                current = _same_key_next_model(
                    current,
                    routes,
                    attempted_unique,
                )
                continue

            if kind == "transient":
                # 500/502/504는 같은 key의 다음 model로 빠르게 전환.
                current = _same_key_next_model(
                    current,
                    routes,
                    attempted_unique,
                )
                continue

            # schema / JSON / content / 400 / unknown:
            # 독립 project key나 다른 model을 소모하지 않는다.
            latency_ms = int(
                (
                    time.perf_counter()
                    - started
                )
                * 1000
            )
            _attach_router_meta(
                exc,
                model=current.model,
                key_slot=current.key_slot,
                attempt_count=physical_attempts,
                retry_count=(
                    aggregate_retries
                    + router_retries
                ),
                retry_reasons=aggregate_reasons,
                latency_ms=latency_ms,
                route_history=route_history,
            )
            raise

    latency_ms = int(
        (
            time.perf_counter()
            - started
        )
        * 1000
    )

    if last_error is None:
        last_error = RuntimeError(
            "AI Router가 결과를 생성하지 못했습니다."
        )

    # 실제 시도한 모든 route가 hard quota였을 때만 최종 hard-quota로 정규화한다.
    if (
        failure_kinds
        and all(
            kind == "hard_quota"
            for kind in failure_kinds
        )
    ):
        final_error: Exception = AIQuotaExhausted(
            "현재 시도 가능한 Gemini route의 일일/하드 할당량이 소진되었습니다."
        )
    else:
        final_error = last_error

    _attach_router_meta(
        final_error,
        model=(
            last_route.model
            if last_route
            else model
        ),
        key_slot=(
            last_route.key_slot
            if last_route
            else "none"
        ),
        attempt_count=physical_attempts,
        retry_count=(
            aggregate_retries
            + router_retries
        ),
        retry_reasons=aggregate_reasons,
        latency_ms=latency_ms,
        route_history=route_history,
    )
    raise final_error


# AI_ROUTING_V1_LIST_KEYS_MODELS_20260904

# AI_ROUTING_V1_DEFAULT_ON_20260904

# AI_ROUTING_V1_1_ERROR_AWARE_FAILOVER_20260904

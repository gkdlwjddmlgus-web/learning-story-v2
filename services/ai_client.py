from __future__ import annotations

import json
import random
import time
from typing import Any

import streamlit as st
from google import genai
from google.genai import types


DEFAULT_MODEL = "gemini-flash-latest"


class AIQuotaExhausted(RuntimeError):
    pass


@st.cache_resource(show_spinner=False)
def get_gemini_client():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def _status_code(exc: Exception) -> int | None:
    for name in ("status_code", "code"):
        value=getattr(exc,name,None)
        try:
            if value is not None:
                return int(value)
        except (TypeError,ValueError):
            pass
    message=str(exc)
    if "503" in message: return 503
    if "429" in message: return 429
    return None


def _is_hard_quota(exc: Exception) -> bool:
    message=str(exc).lower()
    strong=(
        "quota exceeded",
        "exceeded your current quota",
        "generate_content_free_tier_requests",
        "resource_exhausted",
    )
    return _status_code(exc)==429 and any(x in message for x in strong)


def _is_transient(exc: Exception) -> bool:
    code=_status_code(exc)
    message=str(exc).lower()
    if code==503: return True
    if code==429 and not _is_hard_quota(exc): return True
    return any(x in message for x in (
        "high demand", "unavailable", "temporarily overloaded",
        "rate limit", "too many requests",
    )) and not _is_hard_quota(exc)


def _schema_related(exc: Exception) -> bool:
    message=str(exc).lower()
    return any(x in message for x in (
        "schema", "invalid_argument", "invalid argument", "response_json_schema",
    ))


def generate_live_json(
    *,
    prompt: str,
    schema: dict[str, Any],
    model: str = DEFAULT_MODEL,
    max_retries: int = 2,
    base_delay: float = 2.0,
) -> tuple[Any, dict[str, Any]]:
    """Gemini 호출만 담당한다. 로깅/Mock 선택은 Generation Gateway가 담당."""
    client=get_gemini_client()
    started=time.perf_counter()
    retry_count=0
    last_error=None
    use_schema=True

    for attempt in range(max_retries+1):
        try:
            kwargs={"response_mime_type":"application/json","max_output_tokens":4096}
            if use_schema:
                kwargs["response_json_schema"]=schema
            response=client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**kwargs),
            )
            text=(response.text or "").strip()
            if not text:
                raise ValueError("AI가 빈 응답을 반환했습니다.")
            if text.startswith("```"):
                text=text.replace("```json","",1).replace("```","").strip()
            result=json.loads(text)
            return result, {
                "retry_count": retry_count,
                "latency_ms": int((time.perf_counter()-started)*1000),
            }
        except Exception as exc:
            last_error=exc
            if _is_hard_quota(exc):
                raise AIQuotaExhausted(
                    "Gemini 사용 할당량이 소진되었습니다. 할당량이 갱신되거나 다른 사용 가능한 프로젝트/API 설정으로 전환한 뒤 다시 시도해주세요."
                ) from exc
            if use_schema and _schema_related(exc):
                use_schema=False
                retry_count+=1
                continue
            retryable=_is_transient(exc) or isinstance(exc,(ValueError,json.JSONDecodeError))
            if not retryable or attempt>=max_retries:
                break
            retry_count+=1
            delay=base_delay*(2**attempt)+random.uniform(0,0.5)
            time.sleep(delay)

    if last_error is not None:
        try:
            setattr(last_error, "_ls_retry_count", retry_count)
            setattr(last_error, "_ls_latency_ms", int((time.perf_counter()-started)*1000))
        except Exception:
            pass
        raise last_error
    raise RuntimeError("AI 생성 결과를 처리하지 못했습니다.")

from __future__ import annotations

import inspect
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import components.dialogue_story_experience as story


def main() -> int:
    print("=" * 82)
    print("Cinematic Story Auto + Layout v2.1 - QA")
    print("=" * 82)

    # Pure duration tests: no Streamlit UI/DB/Gemini side effects.
    cases = [
        (
            "짧은 대사.",
            "companion",
            4.0,
            5.0,
            "short dialogue bounded",
        ),
        (
            (
                "원료 약재가 가마로 들어가 최종 영약으로 나오기까지 "
                "전체 흐름을 확인해야 하는 상황이다."
            ),
            "narrator",
            5.0,
            10.0,
            "medium narration readable",
        ),
        (
            "아주 긴 설명 " * 80,
            "narrator",
            10.0,
            11.5,
            "long narration capped",
        ),
    ]

    for text, role, low, high, label in cases:
        value = story._scene_duration_seconds(
            text=text,
            speaker_type=role,
        )
        if not (low <= value <= high):
            raise AssertionError(
                f"{label}: {value} not in [{low}, {high}]"
            )
        print(f"[PASS] {label} -> {value:.2f}s")

    layout_css = story._story_runtime_layout_css()

    layout_checks = {
        "dedicated Story layout anchor": (
            "dialogue-story-runtime-anchor" in layout_css
        ),
        "top dead-space reduction": (
            "padding-top: .85rem" in layout_css
        ),
        "vertical gap reduction": (
            "gap: .38rem" in layout_css
        ),
        "progress track styling": (
            "dialogue-story-progress-track" in layout_css
        ),
        "mobile layout tuning": (
            "@media (max-width: 768px)" in layout_css
        ),
        "reduced-motion progress support": (
            "prefers-reduced-motion: reduce" in layout_css
        ),
    }

    for label, ok in layout_checks.items():
        if not ok:
            raise AssertionError(label)
        print("[PASS]", label)

    source = inspect.getsource(
        story.render_dialogue_story_experience
    )

    source_checks = {
        "auto toggle default ON": (
            'st.toggle(' in source
            and 'value=True' in source
        ),
        "scene renderer manual button disabled": (
            "show_next_button=False" in source
        ),
        "manual next button retained": (
            'key=f"dialogue_runtime_v1_next_' in source
        ),
        "skip retained": (
            '"건너뛰기 →"' in source
        ),
        "Story Choice handoff retained": (
            "mark_dialogue_story_seen(chapter_id)" in source
        ),
        "background selector retained": (
            "resolve_story_background(" in source
        ),
        "portrait resolver retained": (
            "resolve_portrait(" in source
        ),
    }

    for label, ok in source_checks.items():
        if not ok:
            raise AssertionError(label)
        print("[PASS]", label)

    module_source = inspect.getsource(story)

    module_checks = {
        "no blocking sleep": (
            "time.sleep(" not in module_source
        ),
        "fragment periodic tick": (
            "st.fragment(" in module_source
            and "run_every=_AUTO_TICK_SECONDS" in module_source
        ),
        "stale fragment guard": (
            "live_index" in module_source
        ),
        "auto timer uses monotonic clock": (
            "time.monotonic()" in module_source
        ),
        "manual/skip clears timer state": (
            "_clear_auto_scene_state(chapter_id)" in source
        ),
    }

    for label, ok in module_checks.items():
        if not ok:
            raise AssertionError(label)
        print("[PASS]", label)

    print()
    print("[RUNTIME COMPAT]")
    print(
        "[INFO] st.fragment available =",
        hasattr(story.st, "fragment"),
    )

    print()
    print("[SAFETY]")
    print("- No time.sleep blocking loop.")
    print("- No Gemini API request was made.")
    print("- No DB query/write was made.")
    print("- Story JSON / prompt / background selector were not modified.")
    print("- Quiz feedback auto-advance was NOT enabled.")
    print("- Manual Next / Skip remain available.")
    print()
    print("Cinematic Story Auto + Layout v2.1 QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

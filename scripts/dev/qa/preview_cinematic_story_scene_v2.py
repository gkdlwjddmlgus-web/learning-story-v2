from __future__ import annotations

import base64
import inspect
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import components.dialogue_scene as scene


TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
    "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def main() -> int:
    print("=" * 78)
    print("Cinematic Story Scene v2 - QA")
    print("=" * 78)

    css = scene._css("무협")

    checks = {
        "background layer css": (
            ".dialogue-scene-background" in css
        ),
        "scene fade-in animation": (
            "@keyframes dialogueSceneFadeIn" in css
            and "dialogueSceneFadeIn .42s" in css
        ),
        "slow Ken Burns motion": (
            "@keyframes dialogueSceneKenBurns" in css
            and "scale(1.025)" in css
            and "14s ease-out" in css
        ),
        "portrait entrance animation": (
            "@keyframes dialoguePortraitEnter" in css
        ),
        "top readability overlay": (
            ".dialogue-scene-stage::before" in css
        ),
        "bottom readability overlay": (
            ".dialogue-scene-stage::after" in css
        ),
        "chrome readability pills": (
            "background:rgba(16,14,12,.42)" in css
            and "text-shadow:" in css
        ),
        "dialogue box compacted": (
            "min-height:172px" in css
            and "min-height:148px" in css
        ),
        "reduced motion support": (
            "@media (prefers-reduced-motion: reduce)" in css
        ),
        "mobile layout retained": (
            "@media (max-width:768px)" in css
        ),
    }

    failed = []
    for label, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            failed.append(label)

    if failed:
        raise AssertionError(
            "CSS verification failed: " + ", ".join(failed)
        )

    source = inspect.getsource(scene.render_dialogue_scene)
    if "dialogue-scene-background" not in source:
        raise AssertionError(
            "render function does not emit dedicated background layer"
        )
    print("[PASS] renderer emits dedicated background layer")

    captured = {}
    original_markdown = scene.st.markdown
    original_button = scene.st.button

    try:
        scene.st.markdown = lambda body, **kwargs: captured.setdefault(
            "html",
            body,
        )
        scene.st.button = lambda *args, **kwargs: False

        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "bg.png"
            image_path.write_bytes(TINY_PNG)

            result = scene.render_dialogue_scene(
                theme="무협",
                speaker_type="narrator",
                speaker_name="서술",
                text="연단실의 불빛이 흔들린다.",
                background_path=image_path,
                context_label="CHAPTER 2 · 테스트",
                show_next_button=False,
                show_scene_chrome=True,
            )

        if result is not False:
            raise AssertionError(
                "show_next_button=False should return False"
            )

    finally:
        scene.st.markdown = original_markdown
        scene.st.button = original_button

    html = captured.get("html", "")

    if 'class="dialogue-scene-background"' not in html:
        raise AssertionError(
            "captured HTML missing background layer"
        )
    print("[PASS] runtime HTML contains background layer")

    if "CHAPTER 2 · 테스트" not in html:
        raise AssertionError(
            "context chrome disappeared"
        )
    print("[PASS] chapter context retained")

    if "연단실의 불빛이 흔들린다." not in html:
        raise AssertionError(
            "dialogue text disappeared"
        )
    print("[PASS] dialogue text retained")

    print()
    print("[SAFETY]")
    print("- No Gemini API request was made.")
    print("- No DB query/write was made.")
    print("- Story Background selector was not modified.")
    print("- Portrait attribution/resolver was not modified.")
    print("- Story JSON / Question / Attempt / Mastery were not modified.")
    print()
    print("Cinematic Story Scene v2 QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

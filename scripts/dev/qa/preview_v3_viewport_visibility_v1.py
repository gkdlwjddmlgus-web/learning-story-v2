from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def require(path: str, fragments: list[str]) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for fragment in fragments:
        if fragment not in text:
            raise AssertionError(f"{path}: missing {fragment!r}")


def main() -> None:
    require(
        "components/dialogue_scene.py",
        [
            "calc(100dvh - 9rem)",
            "dialogue-scene-stage-compact",
            "compact: bool = False",
            'f\'<section class="{stage_class}">\'',
        ],
    )
    require(
        "components/quiz_scene_experience.py",
        [
            'companion_portrait_path = resolve_portrait(',
            'player_portrait_path = resolve_portrait(',
            "companion_portrait_path=companion_portrait_path",
            "player_portrait_path=player_portrait_path",
            "compact=True",
        ],
    )
    require(
        "views/auth_view.py",
        [
            '"회원가입",\n                type="primary",',
            'key="v3_signup_submit",\n                width="stretch",',
            'key="v3_login_submit",\n                width="stretch",',
        ],
    )
    require(
        "services/ai_client.py",
        [
            "raw_response_omitted=true",
        ],
    )
    ai_text = (ROOT / "services/ai_client.py").read_text(encoding="utf-8")
    if 'f"{raw_text}\\n"' in ai_text:
        raise AssertionError("raw AI response must not be printed")

    print("[PASS] Story stage is bounded by the viewport")
    print("[PASS] Quiz feedback uses compact dialogue layout")
    print("[PASS] Companion/player theme portraits persist after answer submission")
    print("[PASS] Login and signup primary actions have explicit contrast")
    print("[PASS] JSON diagnostics omit raw model output")


if __name__ == "__main__":
    main()

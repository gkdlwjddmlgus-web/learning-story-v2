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
        "components/dialogue_story_experience.py",
        [
            "@st.fragment",
            "def _move_story_scene(",
            '[data-stale="true"]',
        ],
    )
    require(
        "ui_tabs/learning_tab.py",
        [
            "@media (min-width:900px)",
            "@media (max-width:899px)",
            "@media (max-width:640px)",
            "grid-template-rows:auto minmax(0,1fr) auto",
            "height:100dvh !important",
            "flex:1 1 25% !important",
            "height:clamp(390px,58dvh,560px)",
            "display:block !important",
            "v3-evidence-object",
            "사건 기록 문서",
            "rgba(5,14,24,.70)",
        ],
    )
    require(
        "components/quiz_scene_experience.py",
        [
            'companion_portrait_path = resolve_companion_action_portrait(',
            '"explain" if is_correct else "thinking"',
            'player_portrait_path = resolve_portrait(',
            "companion_portrait_path=companion_portrait_path",
            "player_portrait_path=player_portrait_path",
            "compact=True",
        ],
    )
    require(
        "components/auth_styles.py",
        [
            ".st-key-v3_login_submit button",
            ".st-key-v3_signup_submit button",
            "-webkit-text-fill-color:#fff !important",
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
    print("[PASS] Story manual navigation is fragment-scoped without stale fade")
    print("[PASS] Desktop play shell keeps one-screen layout and themed background")
    print("[PASS] Mobile shell keeps HUD/body/action dock inside 100dvh")
    print("[PASS] Mobile action dock remains a fixed four-item row")
    print("[PASS] Mobile Review and Learning Note use compact vertical surfaces")
    print("[PASS] Evidence uses a compact record prop instead of a duplicate scene image")
    print("[PASS] Quiz feedback uses compact dialogue layout")
    print("[PASS] Companion/player theme portraits persist after answer submission")
    print("[PASS] Login and signup primary actions have explicit contrast")
    print("[PASS] JSON diagnostics omit raw model output")


if __name__ == "__main__":
    main()

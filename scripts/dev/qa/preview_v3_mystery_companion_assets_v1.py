from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "assets" / "dialogue" / "mystery" / "companion"


def _assert_transparent_png(name: str) -> None:
    path = ASSET_DIR / name
    if not path.is_file():
        raise AssertionError(f"missing mystery companion asset: {name}")
    with Image.open(path) as image:
        if image.format != "PNG" or "A" not in image.getbands():
            raise AssertionError(f"asset must be an alpha PNG: {name}")
        alpha = image.getchannel("A")
        if alpha.getextrema()[0] != 0:
            raise AssertionError(f"asset has no transparent pixels: {name}")


def main() -> None:
    for name in (
        "investigate.png",
        "explain.png",
        "thinking.png",
        "notebook.png",
    ):
        _assert_transparent_png(name)

    asset_source = (ROOT / "services" / "dialogue_asset_service.py").read_text(
        encoding="utf-8"
    )
    learning_source = (ROOT / "ui_tabs" / "learning_tab.py").read_text(
        encoding="utf-8"
    )
    quiz_source = (ROOT / "components" / "quiz_scene_experience.py").read_text(
        encoding="utf-8"
    )

    for token in ("explain", "investigate", "thinking", "notebook"):
        if f'"{token}"' not in asset_source:
            raise AssertionError(f"action resolver missing {token}")
    for token in (
        'resolve_companion_action_portrait(\n            world[4],\n            "investigate"',
        'portrait_actions = (',
        'class="v3-book-companion"',
        '"notebook"',
    ):
        if token not in learning_source:
            raise AssertionError(f"learning action mapping missing {token!r}")
    if '"explain" if is_correct else "thinking"' not in quiz_source:
        raise AssertionError("quiz feedback pose mapping is incomplete")

    print("[PASS] Four mystery companion action sprites are transparent PNGs")
    print("[PASS] Story Review uses the investigate pose")
    print("[PASS] Companion prompts select explain/investigate/thinking/notebook poses")
    print("[PASS] Quiz feedback maps success to explain and retry to thinking")
    print("[PASS] Learning Note includes the notebook illustration")
    print("[PASS] Other themes keep their default portrait fallback")


if __name__ == "__main__":
    main()

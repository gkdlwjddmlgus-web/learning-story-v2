from __future__ import annotations

import re
from pathlib import Path


# DAY6_DIALOGUE_ASSET_SYSTEM_V1

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSET_ROOT = PROJECT_ROOT / "assets" / "dialogue"

SUPPORTED_EXTENSIONS = (
    ".png",
    ".webp",
    ".jpg",
    ".jpeg",
)

_THEME_ALIASES = {
    "동화": "fairy",
    "fairy": "fairy",
    "fairytale": "fairy",
    "미스터리": "mystery",
    "미스테리": "mystery",
    "mystery": "mystery",
    "무협": "martial",
    "martial": "martial",
    "wuxia": "martial",
    "sf": "sf",
    "sci-fi": "sf",
    "science fiction": "sf",
    "판타지": "fantasy",
    "fantasy": "fantasy",
}

_ROLE_ALIASES = {
    "companion": "companion",
    "cat": "companion",
    "고양이": "companion",
    "npc": "npc",
    "player": "player",
    "user": "player",
    "사용자": "player",
    "narrator": "narrator",
    "내레이션": "narrator",
}

_SAFE_KEY = re.compile(r"[^0-9A-Za-z가-힣_-]+")


def normalize_theme(theme: str) -> str:
    raw = str(theme or "").strip()
    if not raw:
        return "fairy"

    lowered = raw.lower()
    return _THEME_ALIASES.get(
        raw,
        _THEME_ALIASES.get(lowered, lowered),
    )


def normalize_role(role: str) -> str:
    raw = str(role or "").strip()
    lowered = raw.lower()

    normalized = _ROLE_ALIASES.get(
        raw,
        _ROLE_ALIASES.get(lowered, lowered),
    )

    if normalized not in {
        "companion",
        "npc",
        "player",
        "narrator",
    }:
        return "npc"

    return normalized


def normalize_asset_key(value: str | None, *, fallback: str) -> str:
    raw = str(value or "").strip()

    if not raw:
        raw = fallback

    safe = _SAFE_KEY.sub("_", raw).strip("_")
    return safe or fallback


def _first_existing(directory: Path, stems: list[str]) -> Path | None:
    for stem in stems:
        for extension in SUPPORTED_EXTENSIONS:
            candidate = directory / f"{stem}{extension}"
            if candidate.is_file():
                return candidate
    return None


def portrait_directory(
    theme: str,
    role: str,
    *,
    asset_root: str | Path | None = None,
) -> Path | None:
    root = Path(asset_root) if asset_root else DEFAULT_ASSET_ROOT
    normalized_role = normalize_role(role)

    if normalized_role == "narrator":
        return None

    if normalized_role == "player":
        return root / "common" / "player"

    return root / normalize_theme(theme) / normalized_role


def resolve_portrait(
    theme: str,
    role: str,
    *,
    character_id: str | None = None,
    asset_root: str | Path | None = None,
) -> Path | None:
    """
    Search order:
    1. <character_id>.<ext>
    2. default.<ext>

    Narrator always resolves to None.
    """
    directory = portrait_directory(
        theme,
        role,
        asset_root=asset_root,
    )

    if directory is None:
        return None

    key = normalize_asset_key(
        character_id,
        fallback="default",
    )

    stems = [key]
    if key != "default":
        stems.append("default")

    return _first_existing(directory, stems)


def background_directory(
    theme: str,
    *,
    asset_root: str | Path | None = None,
) -> Path:
    root = Path(asset_root) if asset_root else DEFAULT_ASSET_ROOT
    return root / "backgrounds" / normalize_theme(theme)


def resolve_background(
    theme: str,
    *,
    scene_id: str | None = None,
    asset_root: str | Path | None = None,
) -> Path | None:
    """
    Search order:
    1. <scene_id>.<ext>
    2. default.<ext>
    """
    directory = background_directory(
        theme,
        asset_root=asset_root,
    )

    key = normalize_asset_key(
        scene_id,
        fallback="default",
    )

    stems = [key]
    if key != "default":
        stems.append("default")

    return _first_existing(directory, stems)


def describe_resolution(
    theme: str,
    role: str,
    *,
    character_id: str | None = None,
    scene_id: str | None = None,
    asset_root: str | Path | None = None,
) -> dict[str, str | None]:
    portrait = resolve_portrait(
        theme,
        role,
        character_id=character_id,
        asset_root=asset_root,
    )

    background = resolve_background(
        theme,
        scene_id=scene_id,
        asset_root=asset_root,
    )

    portrait_dir = portrait_directory(
        theme,
        role,
        asset_root=asset_root,
    )

    background_dir = background_directory(
        theme,
        asset_root=asset_root,
    )

    return {
        "theme": normalize_theme(theme),
        "role": normalize_role(role),
        "character_id": normalize_asset_key(
            character_id,
            fallback="default",
        ),
        "scene_id": normalize_asset_key(
            scene_id,
            fallback="default",
        ),
        "portrait_directory": (
            str(portrait_dir)
            if portrait_dir is not None
            else None
        ),
        "portrait_path": (
            str(portrait)
            if portrait is not None
            else None
        ),
        "background_directory": str(background_dir),
        "background_path": (
            str(background)
            if background is not None
            else None
        ),
    }

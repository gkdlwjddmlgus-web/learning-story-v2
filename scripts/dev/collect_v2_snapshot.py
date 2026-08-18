from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path.cwd()
OUTPUT_ZIP = ROOT / "learning_story_v2_snapshot.zip"
TREE_TXT = ROOT / "learning_story_v2_tree.txt"

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "backups", "node_modules",
}

EXCLUDED_FILES = {
    ".streamlit/secrets.toml",
    ".env",
}

ALLOWED_SUFFIXES = {
    ".py", ".txt", ".toml", ".md", ".json", ".sql", ".yaml", ".yml",
}

SPECIAL_FILES = {
    ".gitignore",
    "requirements.txt",
}


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    relative_posix = relative.as_posix()

    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False

    if relative_posix in EXCLUDED_FILES:
        return False

    if path.name in SPECIAL_FILES:
        return True

    return path.suffix.lower() in ALLOWED_SUFFIXES


def collect_files() -> list[Path]:
    files = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if path in {OUTPUT_ZIP, TREE_TXT}:
            continue

        if should_include(path):
            files.append(path)

    return sorted(
        files,
        key=lambda p: p.relative_to(ROOT).as_posix(),
    )


def write_tree(files: list[Path]) -> None:
    lines = [
        "Learning Story V2 project snapshot",
        f"Root: {ROOT}",
        "",
        "[Included files]",
    ]

    for path in files:
        lines.append(path.relative_to(ROOT).as_posix())

    TREE_TXT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def make_zip(files: list[Path]) -> None:
    with zipfile.ZipFile(
        OUTPUT_ZIP,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zf:
        for path in files:
            zf.write(
                path,
                arcname=path.relative_to(ROOT).as_posix(),
            )

        zf.write(
            TREE_TXT,
            arcname=TREE_TXT.name,
        )


def main() -> None:
    files = collect_files()

    if not files:
        raise SystemExit(
            "수집할 프로젝트 파일을 찾지 못했습니다. "
            "Learning Story V2 프로젝트 루트에서 실행해주세요."
        )

    write_tree(files)
    make_zip(files)

    print("=" * 72)
    print("Learning Story V2 - Phase 1 Snapshot")
    print("=" * 72)
    print()
    print(f"포함 파일 수: {len(files)}")
    print(f"프로젝트 트리: {TREE_TXT}")
    print(f"업로드용 ZIP: {OUTPUT_ZIP}")
    print()
    print("[자동 제외]")
    print("- .git / .venv / venv / __pycache__ / backups")
    print("- .streamlit/secrets.toml")
    print("- .env")
    print()
    print("생성된 learning_story_v2_snapshot.zip만 ChatGPT에 업로드하면 됩니다.")


if __name__ == "__main__":
    main()

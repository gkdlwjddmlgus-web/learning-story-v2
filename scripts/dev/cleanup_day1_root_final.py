from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd()

# 루트에 남겨야 하는 실행/설정 파일
KEEP_FILES = {
    ".gitignore",
    "app.py",
    "auth.py",
    "db.py",
    "requirements.txt",
}

KEEP_DIRS = {
    ".git",
    ".streamlit",
    "backups",
    "components",
    "docs",
    "repositories",
    "scripts",
    "services",
    "sql",
    "ui_tabs",
    "views",
}

# 오늘 임시 패치/설치 파일 패턴
MOVE_TO_MIGRATIONS = (
    "install_day1_*.py",
    "migrate_day1_*.py",
    "cleanup_v2_project.py",
)

MOVE_TO_DOCS = (
    "README_DAY1*.md",
    "README_DAY1*.txt",
    "README_DAY*.md",
)

MOVE_TO_PAYLOADS = (
    "_patch_payload",
)

# 혹시 이전 작업에서 루트에 남은 일반 README 패치 문서
OPTIONAL_DOC_PATTERNS = (
    "README_*UPDATE*.md",
    "README_*FIX*.md",
)


def unique_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if destination.is_dir() or not destination.suffix:
        return destination.with_name(
            f"{destination.name}_{stamp}"
        )

    return destination.with_name(
        f"{destination.stem}_{stamp}{destination.suffix}"
    )


def move_item(source: Path, destination: Path, moved: list[dict]) -> None:
    if not source.exists():
        return

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = unique_destination(
        destination
    )

    shutil.move(
        str(source),
        str(destination),
    )

    moved.append(
        {
            "from": str(source.relative_to(ROOT)),
            "to": str(destination.relative_to(ROOT)),
        }
    )


def collect(patterns: tuple[str, ...]) -> list[Path]:
    found: list[Path] = []

    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if path not in found:
                found.append(path)

    return sorted(
        found,
        key=lambda p: p.name.lower(),
    )


def main() -> None:
    print("=" * 76)
    print("Learning Story V2 - Day 1 Root Final Cleanup")
    print("=" * 76)

    required = [
        ROOT / "app.py",
        ROOT / "db.py",
        ROOT / "services",
        ROOT / "repositories",
        ROOT / "ui_tabs",
    ]

    missing = [
        path for path in required
        if not path.exists()
    ]

    if missing:
        print()
        print("[중단] 프로젝트 루트에서 실행해주세요.")
        for path in missing:
            print(f"- 없음: {path}")
        raise SystemExit(1)

    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    migration_dir = (
        ROOT
        / "scripts"
        / "migrations"
        / "archive"
        / "day1_20260818"
    )
    docs_dir = (
        ROOT
        / "docs"
        / "archive"
        / "day1_20260818"
    )
    payload_dir = (
        ROOT
        / "scripts"
        / "archive"
        / "payloads"
        / "day1_20260818"
    )
    manifest_dir = (
        ROOT
        / "docs"
        / "cleanup"
    )

    for directory in (
        migration_dir,
        docs_dir,
        payload_dir,
        manifest_dir,
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    moved: list[dict] = []

    for source in collect(MOVE_TO_MIGRATIONS):
        move_item(
            source,
            migration_dir / source.name,
            moved,
        )

    for source in collect(
        MOVE_TO_DOCS + OPTIONAL_DOC_PATTERNS
    ):
        move_item(
            source,
            docs_dir / source.name,
            moved,
        )

    for name in MOVE_TO_PAYLOADS:
        source = ROOT / name
        if source.exists():
            move_item(
                source,
                payload_dir / source.name,
                moved,
            )

    # 루트 상태 기록
    root_items = sorted(
        [
            p.name
            for p in ROOT.iterdir()
            if p.name != ".git"
        ],
        key=str.lower,
    )

    unexpected_root_files = [
        name
        for name in root_items
        if (
            (ROOT / name).is_file()
            and name not in KEEP_FILES
        )
    ]

    unexpected_root_dirs = [
        name
        for name in root_items
        if (
            (ROOT / name).is_dir()
            and name not in KEEP_DIRS
        )
    ]

    manifest = {
        "created_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "moved_count": len(moved),
        "moved": moved,
        "root_items_after_cleanup": root_items,
        "unexpected_root_files": unexpected_root_files,
        "unexpected_root_dirs": unexpected_root_dirs,
        "note": (
            "삭제 작업은 수행하지 않았습니다. "
            "실행 코드와 설정 파일은 그대로 유지했습니다."
        ),
    }

    manifest_path = (
        manifest_dir
        / f"day1_final_cleanup_{stamp}.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"[완료] 이동 항목: {len(moved)}")
    print()
    print("[루트에 유지]")
    for name in sorted(KEEP_FILES):
        if (ROOT / name).exists():
            print(f"- {name}")

    print()
    print("[정리 폴더]")
    print(f"- {migration_dir.relative_to(ROOT)}")
    print(f"- {docs_dir.relative_to(ROOT)}")
    print(f"- {payload_dir.relative_to(ROOT)}")

    print()
    print("[삭제]")
    print("- 없음")

    if unexpected_root_files or unexpected_root_dirs:
        print()
        print("[추가 확인 필요]")
        for name in unexpected_root_files:
            print(f"- 파일: {name}")
        for name in unexpected_root_dirs:
            print(f"- 폴더: {name}")
    else:
        print()
        print("[루트 상태]")
        print("- 예상한 실행/설정 파일과 프로젝트 폴더만 남았습니다.")

    print()
    print("[기록]")
    print(manifest_path)

    print()
    print("[Git 다음 단계]")
    print("git status --short")
    print("git add -A")
    print('git commit -m "Day 1: cleanup and mock E2E flow verified"')
    print("git push origin main")


if __name__ == "__main__":
    main()

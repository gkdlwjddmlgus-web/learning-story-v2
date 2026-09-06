from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ARCHIVE_TAG = "20260906"

# Root-level development artifacts only.
# Source code, assets, QA, backups, DB files, and tracked application files are untouched.
MIGRATION_GLOBS = (
    "migrate_*.py",
)

TOOL_GLOBS = (
    "prepare_*_audit*.py",
    "inspect_*.py",
    "repair_*.py",
)

AUDIT_ZIP_GLOBS = (
    "*_audit_*.zip",
    "question_pipeline_audit_*.zip",
)

TEMP_DIR_NAMES = (
    "_background_preview_tmp",
)


def find_project_root() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (
            (candidate / "services").is_dir()
            and (candidate / "ui_tabs").is_dir()
            and (candidate / "components").is_dir()
        ):
            return candidate

    raise SystemExit(
        "[ERROR] project root not found.\n"
        "Run from C:/코딩/심화_프로젝트/학습게임_V2"
    )


def unique_root_matches(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    found: dict[str, Path] = {}
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.parent != root:
                continue
            found[path.name] = path
    return sorted(found.values(), key=lambda p: p.name.casefold())


def build_plan(root: Path) -> list[tuple[Path, Path]]:
    plan: list[tuple[Path, Path]] = []

    migration_dir = (
        root / "scripts" / "dev" / "migrations" / f"archive_{ARCHIVE_TAG}"
    )
    tools_dir = (
        root / "scripts" / "dev" / "tools" / f"archive_{ARCHIVE_TAG}"
    )
    audits_dir = (
        root / "artifacts" / "audits" / ARCHIVE_TAG
    )
    temp_dir = (
        root / "artifacts" / "tmp" / ARCHIVE_TAG
    )

    for src in unique_root_matches(root, MIGRATION_GLOBS):
        plan.append((src, migration_dir / src.name))

    for src in unique_root_matches(root, TOOL_GLOBS):
        plan.append((src, tools_dir / src.name))

    for src in unique_root_matches(root, AUDIT_ZIP_GLOBS):
        plan.append((src, audits_dir / src.name))

    for name in TEMP_DIR_NAMES:
        src = root / name
        if src.exists():
            plan.append((src, temp_dir / src.name))

    return plan


def validate_plan(root: Path, plan: list[tuple[Path, Path]]) -> None:
    errors: list[str] = []

    seen_destinations: set[Path] = set()

    for src, dst in plan:
        if not src.exists():
            errors.append(f"source missing: {src.relative_to(root)}")
            continue

        if dst in seen_destinations:
            errors.append(f"duplicate destination: {dst.relative_to(root)}")
        seen_destinations.add(dst)

        if dst.exists():
            errors.append(
                f"destination already exists: {dst.relative_to(root)}"
            )

        # Safety boundary: only root-level sources may be moved.
        if src.parent != root:
            errors.append(
                f"refusing non-root source: {src.relative_to(root)}"
            )

    if errors:
        raise SystemExit(
            "[PLAN ERROR]\n- "
            + "\n- ".join(errors)
            + "\nNo files changed."
        )


def print_plan(root: Path, plan: list[tuple[Path, Path]]) -> None:
    if not plan:
        print("[INFO] nothing to organize")
        return

    print(f"[PLAN] {len(plan)} root-level artifact(s) will be moved")
    for src, dst in plan:
        kind = "DIR " if src.is_dir() else "FILE"
        print(
            f"[MOVE] {kind} "
            f"{src.relative_to(root)}"
            f" -> "
            f"{dst.relative_to(root)}"
        )


def apply_plan(root: Path, plan: list[tuple[Path, Path]]) -> None:
    created_dirs: set[Path] = set()

    for src, dst in plan:
        if dst.parent not in created_dirs:
            dst.parent.mkdir(parents=True, exist_ok=True)
            created_dirs.add(dst.parent)

        shutil.move(str(src), str(dst))
        print(
            f"[OK] {src.relative_to(root)}"
            f" -> "
            f"{dst.relative_to(root)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Safely organize root-level migration/audit/temp artifacts "
            "without deleting them."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = find_project_root()
    print(f"[cleanup_project_workspace_v1] project_root={root}")

    plan = build_plan(root)
    validate_plan(root, plan)
    print_plan(root, plan)

    print()
    print("[KEEP] application source files")
    print("[KEEP] services/ components/ ui_tabs/")
    print("[KEEP] assets/backgrounds/")
    print("[KEEP] scripts/dev/qa/")
    print("[KEEP] scripts/dev/backups/")
    print("[KEEP] DB / existing project data")
    print("[NO DELETE] every cleanup action is a move")

    if args.dry_run:
        print("[DRY-RUN] no files changed")
        return 0

    apply_plan(root, plan)
    print()
    print("[DONE] workspace artifacts organized")
    print("[NEXT] git status --short")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

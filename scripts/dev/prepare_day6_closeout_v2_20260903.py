from __future__ import annotations

import argparse
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


TOOL_ID = "prepare_day6_closeout_v2_20260903"

# 프로젝트 루트에 쌓인 Day 작업용 스크립트만 정리한다.
# app.py / db.py / auth.py 같은 런타임 코드는 절대 대상이 아니다.
ROOT_WORK_SCRIPT_PATTERNS = (
    "migrate_*.py",
    "cleanup_day*.py",
    "verify_day*.py",
    "prepare_day*.py",
)

# 최신 코드 스냅샷에 포함할 주요 실행/설계 영역.
INCLUDE_DIRS = (
    "components",
    "repositories",
    "services",
    "views",
    "ui_tabs",
    "sql",
    "docs",
    "assets",
    "tests",
    "scripts/dev",
)

ROOT_INCLUDE_NAMES = {
    "app.py",
    "auth.py",
    "db.py",
    "requirements.txt",
    "pyproject.toml",
    "uv.lock",
    ".gitignore",
    "README.md",
}

ROOT_ALLOWED_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
}

# ZIP/문법검사 대상에서 제외할 디렉터리.
EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "backups",
    ".migration_backups",
    "_migration_backups",
    "audit_exports",
    "node_modules",
}

# 비밀정보/로컬 데이터는 절대 Audit ZIP에 넣지 않는다.
EXCLUDED_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "secrets.toml",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".zip",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".log",
}

REQUIRED_PROJECT_ITEMS = (
    "app.py",
    "components",
    "repositories",
    "services",
    "views",
    "ui_tabs",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Learning Story V2 DAY 6 마감 정리 v2: "
            "루트 작업용 Migration/검증 스크립트 archive 이동 + "
            "현재 런타임 기준 Closeout Audit ZIP 생성"
        )
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="파일을 변경하지 않고 정리 계획/문법 검사만 수행",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="작업용 스크립트를 archive로 옮기고 Closeout ZIP 생성",
    )

    parser.add_argument(
        "--keep-tool-in-root",
        action="store_true",
        help="적용 후 이 정리 도구 자체를 scripts/dev로 이동하지 않고 루트에 유지",
    )

    return parser.parse_args()


def project_root() -> Path:
    return Path.cwd().resolve()


def normalized_path(path: Path) -> str:
    return path.as_posix()


def validate_root(root: Path) -> None:
    missing = [
        item
        for item in REQUIRED_PROJECT_ITEMS
        if not (root / item).exists()
    ]

    if missing:
        print("[ERROR] Learning Story V2 프로젝트 루트로 보이지 않습니다.")
        print("[ERROR] missing:", ", ".join(missing))
        print("[HINT] app.py가 있는 프로젝트 최상위에서 실행하세요.")
        raise SystemExit(1)


def is_secret_or_local_file(path: Path) -> bool:
    name = path.name
    lower_name = name.lower()

    if name in EXCLUDED_FILE_NAMES:
        return True

    if lower_name.startswith(".env"):
        return True

    if lower_name == "secrets.toml":
        return True

    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True

    return False


def is_excluded_by_parent(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True

    return any(
        part in EXCLUDED_DIR_NAMES
        for part in rel.parts[:-1]
    )


def git_output(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return ""

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


def git_tracked(root: Path, path: Path) -> bool:
    rel = normalized_path(path.relative_to(root))

    try:
        result = subprocess.run(
            [
                "git",
                "ls-files",
                "--error-unmatch",
                "--",
                rel,
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return False

    return result.returncode == 0


def work_script_candidates(
    root: Path,
    self_path: Path,
) -> list[Path]:
    found: dict[str, Path] = {}

    for pattern in ROOT_WORK_SCRIPT_PATTERNS:
        for path in root.glob(pattern):
            if not path.is_file():
                continue

            if path.resolve() == self_path:
                continue

            # 별도 상시 export 도구가 있다면 루트에 유지.
            if path.name == "export_audit_bundle.py":
                continue

            found[path.name] = path

    return [
        found[name]
        for name in sorted(found)
    ]


def iter_selected_files(
    root: Path,
    self_path: Path,
    *,
    exclude_root_work_scripts: bool = True,
) -> list[Path]:
    selected: dict[str, Path] = {}

    for name in ROOT_INCLUDE_NAMES:
        path = root / name

        if (
            path.is_file()
            and not is_secret_or_local_file(path)
        ):
            selected[
                normalized_path(
                    path.relative_to(root)
                )
            ] = path

    # 루트의 기타 가벼운 코드/설정 파일.
    for path in root.iterdir():
        if not path.is_file():
            continue

        if path.resolve() == self_path:
            continue

        if is_secret_or_local_file(path):
            continue

        if (
            path.suffix.lower()
            not in ROOT_ALLOWED_SUFFIXES
        ):
            continue

        if (
            exclude_root_work_scripts
            and any(
                path.match(pattern)
                for pattern
                in ROOT_WORK_SCRIPT_PATTERNS
            )
        ):
            continue

        selected[
            normalized_path(
                path.relative_to(root)
            )
        ] = path

    for dirname in INCLUDE_DIRS:
        base = root / dirname

        if (
            not base.exists()
            or not base.is_dir()
        ):
            continue

        for path in base.rglob("*"):
            if not path.is_file():
                continue

            if is_excluded_by_parent(
                path,
                root,
            ):
                continue

            if is_secret_or_local_file(path):
                continue

            if (
                path.suffix.lower()
                in EXCLUDED_SUFFIXES
            ):
                continue

            selected[
                normalized_path(
                    path.relative_to(root)
                )
            ] = path

    return [
        selected[key]
        for key in sorted(selected)
    ]


def syntax_check(
    files: list[Path],
) -> list[tuple[Path, str]]:
    failures: list[
        tuple[Path, str]
    ] = []

    for path in files:
        if path.suffix.lower() != ".py":
            continue

        try:
            source = path.read_text(
                encoding="utf-8"
            )
            compile(
                source,
                str(path),
                "exec",
            )
        except Exception as exc:
            failures.append(
                (
                    path,
                    f"{type(exc).__name__}: {exc}",
                )
            )

    return failures


def print_candidate_plan(
    root: Path,
    candidates: list[Path],
    archive_dir: Path,
) -> None:
    print()
    print("[ROOT WORK SCRIPT CLEANUP]")

    if not candidates:
        print(
            "- 이동할 루트 Day 작업용 스크립트가 없습니다."
        )
        return

    print(
        f"- 대상 {len(candidates)}개"
    )

    for path in candidates:
        tracked = (
            "tracked"
            if git_tracked(
                root,
                path,
            )
            else "untracked"
        )

        destination = (
            archive_dir.relative_to(root)
            / path.name
        )

        print(
            "  · "
            f"{path.name} -> "
            f"{normalized_path(destination)} "
            f"[{tracked}]"
        )


def make_manifest(
    *,
    root: Path,
    created_at: str,
    moved_names: list[str],
    selected_files: list[Path],
    syntax_failures: list[
        tuple[Path, str]
    ],
) -> str:
    branch = (
        git_output(
            root,
            "branch",
            "--show-current",
        )
        or "(unknown)"
    )

    head = (
        git_output(
            root,
            "rev-parse",
            "HEAD",
        )
        or "(unknown)"
    )

    status = (
        git_output(
            root,
            "status",
            "--short",
        )
        or "(clean or unavailable)"
    )

    python_count = sum(
        1
        for path in selected_files
        if path.suffix.lower() == ".py"
    )

    lines = [
        "Learning Story V2 - DAY 6 Closeout Audit Bundle",
        "=" * 68,
        f"created_at: {created_at}",
        f"project_root: {root}",
        f"git_branch: {branch}",
        f"git_head: {head}",
        "",
        "[PURPOSE]",
        "- Archive root-level Day work/migration scripts",
        "- Snapshot current runtime/source state near DAY 6 closeout",
        "- Preserve a compact audit artifact before DAY 7 work",
        "",
        "[IMPORTANT QA NOTE]",
        "- This ZIP is a code/runtime snapshot, not an automatic declaration that every DAY 6 QA item passed.",
        "- Quota-dependent AI generation QA may still remain pending outside this script.",
        "",
        "[MOVED ROOT WORK SCRIPTS]",
    ]

    if moved_names:
        lines.extend(
            f"- {name}"
            for name in moved_names
        )
    else:
        lines.append("- none")

    lines += [
        "",
        "[SYNTAX CHECK]",
        f"- python_files_checked: {python_count}",
        f"- failures: {len(syntax_failures)}",
    ]

    for path, message in syntax_failures:
        lines.append(
            "  FAIL "
            f"{normalized_path(path.relative_to(root))}: "
            f"{message}"
        )

    lines += [
        "",
        "[INCLUDED FILES]",
        f"- count: {len(selected_files)}",
    ]

    lines.extend(
        "- "
        + normalized_path(
            path.relative_to(root)
        )
        for path in selected_files
    )

    lines += [
        "",
        "[GIT STATUS AT EXPORT]",
        status,
        "",
    ]

    return "\n".join(lines)


def make_tree(
    root: Path,
    selected_files: list[Path],
) -> str:
    rels = [
        normalized_path(
            path.relative_to(root)
        )
        for path in selected_files
    ]

    return "\n".join(rels) + "\n"


def create_zip(
    *,
    root: Path,
    output_path: Path,
    selected_files: list[Path],
    manifest: str,
    tree: str,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = (
        output_path.with_suffix(
            ".zip.part"
        )
    )

    if temp_path.exists():
        temp_path.unlink()

    try:
        with zipfile.ZipFile(
            temp_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as zf:
            for path in selected_files:
                arcname = normalized_path(
                    path.relative_to(root)
                )
                zf.write(
                    path,
                    arcname,
                )

            zf.writestr(
                "DAY6_CLOSEOUT_MANIFEST.txt",
                manifest,
            )
            zf.writestr(
                "PROJECT_TREE.txt",
                tree,
            )

        # 실제 ZIP CRC 검증.
        with zipfile.ZipFile(
            temp_path,
            "r",
        ) as zf:
            bad_member = zf.testzip()

            if bad_member is not None:
                raise RuntimeError(
                    "ZIP CRC verification failed: "
                    f"{bad_member}"
                )

        if output_path.exists():
            output_path.unlink()

        temp_path.replace(
            output_path
        )

    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def move_root_work_scripts(
    candidates: list[Path],
    archive_dir: Path,
) -> list[
    tuple[Path, Path]
]:
    moved: list[
        tuple[Path, Path]
    ] = []

    if not candidates:
        return moved

    archive_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    try:
        for source in candidates:
            destination = (
                archive_dir
                / source.name
            )

            if destination.exists():
                raise RuntimeError(
                    "archive destination already exists: "
                    f"{destination}"
                )

            shutil.move(
                str(source),
                str(destination),
            )

            moved.append(
                (
                    source,
                    destination,
                )
            )

    except Exception:
        for source, destination in reversed(
            moved
        ):
            if (
                destination.exists()
                and not source.exists()
            ):
                shutil.move(
                    str(destination),
                    str(source),
                )

        try:
            archive_dir.rmdir()
        except OSError:
            pass

        raise

    return moved


def rollback_moves(
    moved: list[
        tuple[Path, Path]
    ],
    archive_dir: Path,
) -> None:
    for source, destination in reversed(
        moved
    ):
        if (
            destination.exists()
            and not source.exists()
        ):
            shutil.move(
                str(destination),
                str(source),
            )

    try:
        archive_dir.rmdir()
    except OSError:
        pass


def archive_this_tool(
    root: Path,
    self_path: Path,
) -> None:
    # 루트에 내려받아 실행한 경우에만 scripts/dev로 이동.
    if self_path.parent != root:
        return

    target_dir = (
        root
        / "scripts"
        / "dev"
    )

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = (
        target_dir
        / self_path.name
    )

    if target.exists():
        try:
            if (
                target.read_bytes()
                == self_path.read_bytes()
            ):
                self_path.unlink()

                print(
                    "[TOOL] root copy removed; "
                    f"existing: {target.relative_to(root)}"
                )
                return

        except Exception:
            pass

        target = (
            target_dir
            / (
                f"{self_path.stem}_"
                f"{datetime.now().strftime('%H%M%S')}"
                f"{self_path.suffix}"
            )
        )

    try:
        shutil.move(
            str(self_path),
            str(target),
        )

        print(
            "[TOOL] archived to "
            f"{target.relative_to(root)}"
        )

    except Exception as exc:
        print(
            "[WARN] 이 도구 자체는 자동 이동하지 못했습니다: "
            f"{type(exc).__name__}: {exc}"
        )
        print(
            "[WARN] 수동으로 "
            f"{self_path.name} -> scripts/dev/ "
            "로 옮기면 됩니다."
        )


def main() -> int:
    args = parse_args()

    root = project_root()
    validate_root(root)

    self_path = (
        Path(__file__).resolve()
    )

    now = datetime.now()
    stamp = now.strftime(
        "%Y%m%d_%H%M%S"
    )

    archive_dir = (
        root
        / "scripts"
        / "migrations"
        / "archive"
        / f"day6_root_cleanup_{stamp}"
    )

    output_path = (
        root
        / "audit_exports"
        / (
            "learning_story_v2_"
            f"day6_closeout_{stamp}.zip"
        )
    )

    candidates = (
        work_script_candidates(
            root,
            self_path,
        )
    )

    # 정리 전에 현재 런타임 코드 기준 문법 검사.
    current_selected = (
        iter_selected_files(
            root,
            self_path,
            exclude_root_work_scripts=True,
        )
    )

    failures = syntax_check(
        current_selected
    )

    print("=" * 76)
    print(
        "Learning Story V2 - DAY 6 Closeout Preparation v2"
    )
    print("=" * 76)
    print(
        f"[TOOL] {TOOL_ID}"
    )
    print(
        f"[ROOT] {root}"
    )
    print(
        "[MODE] "
        + (
            "DRY-RUN"
            if args.dry_run
            else "APPLY"
        )
    )
    print(
        "[ARCHIVE] "
        f"{archive_dir.relative_to(root)}"
    )
    print(
        "[ZIP] "
        f"{output_path.relative_to(root)}"
    )

    print_candidate_plan(
        root,
        candidates,
        archive_dir,
    )

    print()
    print(
        "[LATEST RUNTIME CODE SELECTION]"
    )
    print(
        "- 선택 파일: "
        f"{len(current_selected)}개"
    )
    print(
        "- Python 문법 검사 대상: "
        f"{sum(1 for p in current_selected if p.suffix.lower() == '.py')}개"
    )

    if failures:
        print(
            "[VERIFY][FAIL] "
            f"Python syntax error {len(failures)}개"
        )

        for path, message in failures:
            print(
                "  · "
                f"{path.relative_to(root)} "
                f"-> {message}"
            )

        print(
            "[STOP] 실행 코드 문법 오류가 있어 "
            "정리/ZIP 생성을 중단합니다."
        )
        return 1

    print(
        "[VERIFY][PASS] latest runtime Python syntax"
    )

    branch = git_output(
        root,
        "branch",
        "--show-current",
    )
    head = git_output(
        root,
        "rev-parse",
        "--short",
        "HEAD",
    )

    if branch or head:
        print(
            "[GIT] "
            f"branch={branch or '?'} "
            f"head={head or '?'}"
        )

    if args.dry_run:
        print()
        print(
            "[DRY-RUN RESULT]"
        )
        print(
            "- 파일 이동 없음"
        )
        print(
            "- ZIP 생성 없음"
        )
        print(
            "- DB 변경 없음"
        )
        print(
            "- 실행 코드 변경 없음"
        )
        print(
            "- 기존 Story / Question 변경 없음"
        )
        print()
        print(
            "[NEXT]"
        )
        print(
            f"python {self_path.name} --apply"
        )
        return 0

    moved: list[
        tuple[Path, Path]
    ] = []

    try:
        if candidates:
            moved = (
                move_root_work_scripts(
                    candidates,
                    archive_dir,
                )
            )

            print()
            print(
                "[MOVE][PASS] "
                f"root work script {len(moved)}개 archive 이동"
            )

        else:
            print()
            print(
                "[MOVE][SKIP] "
                "이동할 root work script 없음"
            )

        # 이동 후 최신 파일 집합을 다시 계산.
        selected = (
            iter_selected_files(
                root,
                self_path,
                exclude_root_work_scripts=True,
            )
        )

        post_failures = syntax_check(
            selected
        )

        if post_failures:
            raise RuntimeError(
                "post-cleanup syntax verification failed: "
                + "; ".join(
                    f"{path.relative_to(root)}: {message}"
                    for path, message
                    in post_failures
                )
            )

        moved_names = [
            source.name
            for source, _destination
            in moved
        ]

        manifest = make_manifest(
            root=root,
            created_at=now.isoformat(
                timespec="seconds"
            ),
            moved_names=moved_names,
            selected_files=selected,
            syntax_failures=post_failures,
        )

        tree = make_tree(
            root,
            selected,
        )

        create_zip(
            root=root,
            output_path=output_path,
            selected_files=selected,
            manifest=manifest,
            tree=tree,
        )

        print(
            "[ZIP][PASS] "
            f"{output_path.relative_to(root)}"
        )
        print(
            "[ZIP][SIZE] "
            f"{output_path.stat().st_size / (1024 * 1024):.2f} MB"
        )
        print(
            "[VERIFY][PASS] ZIP CRC"
        )
        print(
            "[VERIFY][PASS] "
            "secrets / DB / venv / backups / historical archives 제외"
        )
        print(
            "[DB] 변경 없음"
        )
        print(
            "[RUNTIME] 실행 코드 변경 없음"
        )

    except Exception as exc:
        print(
            f"[ERROR] "
            f"{type(exc).__name__}: {exc}"
        )

        if output_path.exists():
            try:
                output_path.unlink()
            except OSError:
                pass

        if moved:
            rollback_moves(
                moved,
                archive_dir,
            )
            print(
                "[ROLLBACK] root work scripts restored"
            )

        return 1

    print()
    print(
        "[DONE]"
    )
    print(
        "- 프로젝트 루트의 Day 작업용 Migration/검증 파일을 archive로 정리했습니다."
    )
    print(
        "- DAY 6 마감 시점의 최신 코드 Closeout Audit ZIP을 생성했습니다."
    )
    print(
        "- 기존 Story / Question / DB / Event 데이터는 수정하지 않았습니다."
    )
    print(
        "- 이 작업은 QA 완료 선언이 아니라 코드 스냅샷/정리 작업입니다."
    )

    if not args.keep_tool_in_root:
        archive_this_tool(
            root,
            self_path,
        )
    else:
        print(
            "[TOOL] --keep-tool-in-root 옵션으로 "
            "현재 파일을 루트에 유지합니다."
        )

    print()
    print(
        "[ARCHIVE DIR]"
    )
    print(
        archive_dir
    )
    print(
        "[AUDIT ZIP]"
    )
    print(
        output_path
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

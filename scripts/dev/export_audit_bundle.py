#!/usr/bin/env python3
"""
Learning Story V2 - 코드 감사용 ZIP 생성기

사용:
    python export_audit_bundle.py

또는 scripts/dev/에 저장했다면:
    python scripts/dev/export_audit_bundle.py

결과:
    audit_exports/learning_story_v2_audit_YYYYMMDD_HHMMSS.zip
"""

from __future__ import annotations

import sys
import zipfile
from datetime import datetime
from pathlib import Path


ROOT_FILES = {
    "app.py",
    "auth.py",
    "db.py",
    "requirements.txt",
    "pyproject.toml",
    "uv.lock",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    ".gitignore",
    "README.md",
    "README.txt",
}

INCLUDE_DIRS = {
    "components",
    "repositories",
    "services",
    "views",
    "ui_tabs",
    "sql",
    "docs",
    "scripts/dev",
    "scripts/migrations",
    ".streamlit",
}

ALLOWED_SUFFIXES = {
    ".py", ".sql", ".toml", ".txt", ".md", ".json",
    ".yaml", ".yml", ".ini", ".cfg",
}

ALLOWED_NAMES_WITHOUT_SUFFIX = {
    "Dockerfile",
    "Procfile",
}

EXCLUDED_DIR_NAMES = {
    ".git", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".idea", ".vscode", "node_modules",
    "backups", "archive", "archives", "audit_exports",
}

EXCLUDED_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "secrets.toml",
    "credentials.json",
    "service_account.json",
}

SENSITIVE_NAME_PARTS = {
    "secret",
    "credential",
    "api_key",
    "apikey",
    "private_key",
}

EXCLUDED_SUFFIXES = {
    ".zip", ".7z", ".rar", ".tar", ".gz",
    ".db", ".sqlite", ".sqlite3",
    ".csv", ".parquet", ".feather",
    ".pkl", ".pickle", ".joblib",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".mp4", ".mov", ".pdf",
    ".pyc", ".pyo",
}

MAX_FILE_SIZE_MB = 5


def find_project_root(start: Path) -> Path:
    candidates = [start.resolve(), Path(__file__).resolve().parent]
    checked = set()

    for base in candidates:
        for path in [base, *base.parents]:
            if path in checked:
                continue
            checked.add(path)

            if (path / "app.py").is_file() and (path / "services").is_dir():
                return path

    raise FileNotFoundError(
        "프로젝트 루트를 찾지 못했습니다. "
        "app.py와 services/가 있는 Learning Story V2 프로젝트 안에서 실행해주세요."
    )


def is_sensitive(path: Path) -> bool:
    name_lower = path.name.lower()

    if path.name in EXCLUDED_FILE_NAMES:
        return True

    if any(part in name_lower for part in SENSITIVE_NAME_PARTS):
        return True

    return False


def should_include_file(path: Path, project_root: Path) -> bool:
    if not path.is_file():
        return False

    try:
        rel = path.relative_to(project_root)
    except ValueError:
        return False

    if any(part in EXCLUDED_DIR_NAMES for part in rel.parts[:-1]):
        return False

    if is_sensitive(path):
        return False

    suffix = path.suffix.lower()

    if suffix in EXCLUDED_SUFFIXES:
        return False

    if path.name not in ALLOWED_NAMES_WITHOUT_SUFFIX and suffix not in ALLOWED_SUFFIXES:
        return False

    try:
        size_mb = path.stat().st_size / (1024 * 1024)
    except OSError:
        return False

    return size_mb <= MAX_FILE_SIZE_MB


def collect_files(project_root: Path) -> list[Path]:
    files = set()

    for filename in ROOT_FILES:
        path = project_root / filename
        if should_include_file(path, project_root):
            files.add(path)

    for dirname in INCLUDE_DIRS:
        base = project_root / dirname
        if not base.exists():
            continue

        for path in base.rglob("*"):
            if should_include_file(path, project_root):
                files.add(path)

    return sorted(files, key=lambda p: str(p.relative_to(project_root)).lower())


def build_manifest(project_root: Path, files: list[Path]) -> str:
    lines = [
        "Learning Story V2 - Audit Bundle Manifest",
        f"Created: {datetime.now().isoformat(timespec='seconds')}",
        f"Project root: {project_root}",
        "",
        "Included files:",
    ]

    for path in files:
        rel = path.relative_to(project_root).as_posix()
        size_kb = path.stat().st_size / 1024
        lines.append(f"- {rel} ({size_kb:.1f} KB)")

    lines += [
        "",
        "Excluded by design:",
        "- .env / secrets.toml / credentials / API keys",
        "- .git / .venv / cache directories",
        "- backups / archive directories",
        "- DB / CSV / parquet / images / videos / existing ZIP files",
        "- files larger than 5 MB",
        "",
    ]

    return "\n".join(lines)


def create_zip(project_root: Path, files: list[Path]) -> Path:
    output_dir = project_root / "audit_exports"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"learning_story_v2_audit_{timestamp}.zip"

    with zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as zf:
        for path in files:
            arcname = path.relative_to(project_root).as_posix()
            zf.write(path, arcname=arcname)

        zf.writestr("MANIFEST.txt", build_manifest(project_root, files))

    return output_path


def main() -> int:
    try:
        project_root = find_project_root(Path.cwd())
        files = collect_files(project_root)

        if not files:
            print("[ERROR] ZIP에 포함할 파일을 찾지 못했습니다.")
            return 1

        output_path = create_zip(project_root, files)
        total_size_mb = sum(p.stat().st_size for p in files) / (1024 * 1024)

        print("=" * 68)
        print("Learning Story V2 - 코드 감사용 ZIP 생성 완료")
        print("=" * 68)
        print(f"프로젝트 루트 : {project_root}")
        print(f"포함 파일 수   : {len(files)}")
        print(f"원본 총 크기   : {total_size_mb:.2f} MB")
        print(f"생성 파일      : {output_path}")
        print("")
        print("보안 파일(.env, secrets.toml, credentials 등)은 제외했습니다.")
        print("ZIP 내부 MANIFEST.txt에서 포함 파일 목록을 확인할 수 있습니다.")
        print("=" * 68)
        return 0

    except Exception as exc:
        print(f"[ERROR] ZIP 생성 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

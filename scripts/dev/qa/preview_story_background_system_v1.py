from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.story_background_service import (
    background_specs,
    resolve_story_background,
    select_story_background_key,
)


EXPECTED_COUNTS = {
    "동화": 8,
    "판타지": 8,
    "SF": 8,
    "무협": 8,
    "미스터리": 8,
}


def _check_key(
    *,
    theme: str,
    text: str,
    allowed: set[str],
    label: str,
    chapter_id: int = 40,
) -> None:
    key = select_story_background_key(
        theme=theme,
        beat_texts=[text],
        current_index=0,
        chapter_id=chapter_id,
    )
    if key not in allowed:
        raise AssertionError(
            f"{label}: key={key!r}, allowed={sorted(allowed)!r}"
        )
    print("[PASS]", label, "->", key)


def main() -> int:
    print("=" * 78)
    print("Story Background System v1 - QA")
    print("=" * 78)

    total = 0

    for theme, expected in EXPECTED_COUNTS.items():
        specs = background_specs(theme)
        if len(specs) != expected:
            raise AssertionError(
                f"{theme}: registry={len(specs)}, expected={expected}"
            )

        missing = []
        for spec in specs:
            slug = {
                "동화": "fairy",
                "판타지": "fantasy",
                "SF": "sf",
                "무협": "wuxia",
                "미스터리": "mystery",
            }[theme]
            path = (
                PROJECT_ROOT
                / "assets"
                / "backgrounds"
                / slug
                / spec.filename
            )
            if not path.is_file():
                missing.append(str(path.relative_to(PROJECT_ROOT)))

        if missing:
            raise AssertionError(
                f"{theme}: missing assets: {missing}"
            )

        total += len(specs)
        print(
            f"[PASS] {theme} registry/assets -> {len(specs)}"
        )

    if total != 40:
        raise AssertionError(
            f"total registry assets={total}, expected=40"
        )
    print("[PASS] total registered background assets -> 40")

    _check_key(
        theme="동화",
        text="구름 위 마을의 다리 끝에 작은 집들이 떠 있었다.",
        allowed={"cloud_village"},
        label="fairy cloud village",
    )
    _check_key(
        theme="판타지",
        text="일행은 지하 던전의 봉인실 앞에서 멈췄다.",
        allowed={"underground_dungeon"},
        label="fantasy dungeon",
    )
    _check_key(
        theme="SF",
        text="연구소 분석실에서 샘플 데이터를 다시 확인했다.",
        allowed={"research_lab"},
        label="sf research lab",
    )
    _check_key(
        theme="무협",
        text="객잔 안에 술 냄새와 등불의 열기가 가득했다.",
        allowed={"inn_night", "inn_riverside", "inn_day"},
        label="wuxia inn variants",
    )
    _check_key(
        theme="무협",
        text=(
            "연단실 안에서 약재를 연단로에 넣고 "
            "영약의 회수량을 장부와 대조했다."
        ),
        allowed={"alchemy_room"},
        label="wuxia alchemy room",
    )
    _check_key(
        theme="미스터리",
        text="비가 내린 골목 사건 현장에는 출입선이 둘러져 있었다.",
        allowed={"crime_alley"},
        label="mystery crime alley",
    )

    beats = [
        "문파의 연무장에는 새벽 안개가 내려앉아 있었다.",
        "무공이 낮게 중얼거렸다.",
        "멀리서 종소리가 한 번 울렸다.",
    ]
    first = select_story_background_key(
        theme="무협",
        beat_texts=beats,
        current_index=0,
        chapter_id=17,
    )
    carried = select_story_background_key(
        theme="무협",
        beat_texts=beats,
        current_index=2,
        chapter_id=17,
    )

    if first != "sect_courtyard" or carried != first:
        raise AssertionError(
            f"lookback persistence failed: first={first}, carried={carried}"
        )
    print("[PASS] nearest prior location persists across dialogue beats")

    shifted_beats = [
        *beats,
        "일행은 문파를 떠나 죽림의 산길로 접어들었다.",
        "바람에 대나무 잎이 부딪쳤다.",
    ]
    shifted = select_story_background_key(
        theme="무협",
        beat_texts=shifted_beats,
        current_index=4,
        chapter_id=17,
    )

    if shifted != "bamboo_mountain_path":
        raise AssertionError(
            f"location shift failed: {shifted}"
        )
    print("[PASS] newer location cue changes background")

    fallback_a = select_story_background_key(
        theme="SF",
        beat_texts=["아무 장소 단서가 없는 짧은 대화다."],
        current_index=0,
        chapter_id=22,
    )
    fallback_b = select_story_background_key(
        theme="SF",
        beat_texts=["전혀 다른 장소 단서 없는 문장이다."],
        current_index=0,
        chapter_id=22,
    )

    if fallback_a != fallback_b:
        raise AssertionError(
            f"chapter fallback unstable: {fallback_a} != {fallback_b}"
        )
    print("[PASS] chapter fallback is deterministic")

    resolved = resolve_story_background(
        theme="무협",
        beat_texts=["객잔 문이 열리며 등불이 흔들렸다."],
        current_index=0,
        chapter_id=40,
    )
    if resolved is None or not resolved.is_file():
        raise AssertionError(
            f"runtime path resolution failed: {resolved}"
        )
    print(
        "[PASS] runtime path resolution ->",
        resolved.relative_to(PROJECT_ROOT),
    )

    print()
    print("[SAFETY]")
    print("- No Gemini API request was made.")
    print("- No DB query/write was made.")
    print("- Existing Story JSON/schema was not modified.")
    print("- Existing portrait resolver was not modified.")
    print()
    print("Story Background System v1 QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

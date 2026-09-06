from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


# STORY_BACKGROUND_SYSTEM_V1_20260906

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKGROUND_ROOT = PROJECT_ROOT / "assets" / "backgrounds"


@dataclass(frozen=True)
class BackgroundSpec:
    key: str
    filename: str
    keywords: tuple[str, ...]


_THEME_ALIASES = {
    "동화": "fairy",
    "fairy": "fairy",
    "fairytale": "fairy",
    "판타지": "fantasy",
    "fantasy": "fantasy",
    "sf": "sf",
    "sci-fi": "sf",
    "science fiction": "sf",
    "무협": "wuxia",
    "wuxia": "wuxia",
    "martial": "wuxia",
    "미스터리": "mystery",
    "미스테리": "mystery",
    "mystery": "mystery",
}


_BACKGROUND_REGISTRY: dict[str, tuple[BackgroundSpec, ...]] = {
    "fairy": (
        BackgroundSpec(
            "forest_village_path",
            "map1.png",
            ("숲길", "숲속 마을", "오솔길", "산책로", "길 안내"),
        ),
        BackgroundSpec(
            "cottage_village",
            "map2.png",
            ("마을", "오두막", "집", "골목", "작은 다리", "주택"),
        ),
        BackgroundSpec(
            "moonlit_meadow",
            "map3.png",
            ("달빛", "풍차", "개울", "초원", "밤하늘", "별이 뜬"),
        ),
        BackgroundSpec(
            "forest_festival",
            "map4.png",
            ("축제", "행사", "천막", "노점", "잔치", "장터"),
        ),
        BackgroundSpec(
            "cloud_village",
            "map5.png",
            (
                "구름 위 마을",
                "구름 마을",
                "하늘 위 마을",
                "하늘 마을",
                "구름",
                "천공",
                "공중",
                "떠 있는",
                "떠있는",
            ),
        ),
        BackgroundSpec(
            "giant_tree_interior",
            "map6.png",
            ("거대한 나무", "나무 안", "나무속", "나무집", "고목", "수목"),
        ),
        BackgroundSpec(
            "starlight_lake",
            "map7.png",
            ("호수", "별빛", "연못", "물가", "정자", "수면"),
        ),
        BackgroundSpec(
            "green_valley",
            "map8.jpg",
            ("계곡", "들판", "산맥", "평원", "초원", "산골"),
        ),
    ),
    "fantasy": (
        BackgroundSpec(
            "castle_city",
            "map1.png",
            ("성곽", "성문", "왕도", "도시", "성채 도시"),
        ),
        BackgroundSpec(
            "crystal_ruins",
            "map2.png",
            ("수정 유적", "고대 유적", "유적", "폐허", "제단"),
        ),
        BackgroundSpec(
            "arcane_archive",
            "map3.png",
            ("대마법 도서관", "마법 도서관", "비전 서고", "아카이브", "서고"),
        ),
        BackgroundSpec(
            "citadel_market",
            "map4.png",
            ("성채 광장", "시장", "장터", "상점", "광장"),
        ),
        BackgroundSpec(
            "underground_dungeon",
            "map5.png",
            ("던전", "지하 신전", "지하", "동굴", "봉인실"),
        ),
        BackgroundSpec(
            "magic_academy",
            "map6.png",
            ("마법학교", "마법 학교", "아카데미", "교실", "수업", "학원"),
        ),
        BackgroundSpec(
            "dragon_valley",
            "map7.png",
            ("드래곤", "용의 계곡", "용", "화산", "용암", "협곡"),
        ),
        BackgroundSpec(
            "royal_palace",
            "map8.png",
            ("왕궁", "궁전", "왕좌", "알현", "대전", "왕실"),
        ),
    ),
    "sf": (
        BackgroundSpec(
            "orbital_observation_deck",
            "map1.png",
            ("전망대", "관측", "함교", "궤도", "우주정거장", "창밖"),
        ),
        BackgroundSpec(
            "planet_landing_base",
            "map2.png",
            ("착륙", "행성 기지", "전초기지", "격납고", "착륙장"),
        ),
        BackgroundSpec(
            "neon_future_city",
            "map3.png",
            ("네온", "미래 도시", "메가시티", "도심", "고층"),
        ),
        BackgroundSpec(
            "asteroid_mining_base",
            "map4.png",
            ("소행성", "광산", "채굴", "광물", "암석 기지"),
        ),
        BackgroundSpec(
            "spaceship_engine_room",
            "map5.png",
            ("엔진", "기관실", "동력", "반응로", "에너지 코어", "코어실"),
        ),
        BackgroundSpec(
            "alien_forest",
            "map6.png",
            ("외계 숲", "외계 정글", "정글", "외계 식물", "균류", "생태"),
        ),
        BackgroundSpec(
            "ruined_planet_city",
            "map7.png",
            ("폐허 도시", "버려진 도시", "멸망", "도시 폐허", "잔해"),
        ),
        BackgroundSpec(
            "research_lab",
            "map8.png",
            ("연구소", "실험실", "분석실", "바이오", "샘플", "연구실"),
        ),
    ),
    "wuxia": (
        BackgroundSpec(
            "bamboo_mountain_path",
            "map1.png",
            ("죽림", "대나무", "산길", "산문", "숲길"),
        ),
        BackgroundSpec(
            "sect_courtyard",
            "map2.png",
            ("문파", "문중", "연무장", "수련장", "사문", "도장"),
        ),
        BackgroundSpec(
            "riverside_town",
            "map3.png",
            ("강변", "마을", "다리", "시장", "거리", "강호 마을"),
        ),
        BackgroundSpec(
            "snowy_tournament_ground",
            "map4.png",
            ("비무", "비무대", "대회", "결투", "연무대", "설산"),
        ),
        BackgroundSpec(
            "inn_night",
            "map5.png",
            ("객잔", "주점", "술집", "여관", "주루"),
        ),
        BackgroundSpec(
            "inn_riverside",
            "map6.png",
            ("객잔", "주루", "강변 객잔", "술자리", "주막"),
        ),
        BackgroundSpec(
            "inn_day",
            "map7.png",
            ("객잔", "주막", "식사", "아침", "점심", "여관"),
        ),
        BackgroundSpec(
            "alchemy_room",
            "map8.png",
            (
                "연단실",
                "연단로",
                "연단",
                "약재",
                "약방",
                "영약",
                "단약",
                "가마",
                "약장",
                "약초",
            ),
        ),
    ),
    "mystery": (
        BackgroundSpec(
            "detective_study",
            "map1.png",
            ("탐정 사무실", "탐정실", "서재", "사무실", "벽난로"),
        ),
        BackgroundSpec(
            "foggy_train_station",
            "map2.png",
            ("기차역", "역", "플랫폼", "열차", "기차"),
        ),
        BackgroundSpec(
            "gothic_mansion_hall",
            "map3.png",
            ("저택", "대저택", "홀", "응접실", "계단"),
        ),
        BackgroundSpec(
            "old_library",
            "map4.png",
            ("오래된 도서관", "도서관", "서고", "책장", "문헌"),
        ),
        BackgroundSpec(
            "crime_alley",
            "map5.png",
            ("골목", "사건 현장", "범죄 현장", "뒷골목", "현장"),
        ),
        BackgroundSpec(
            "hotel_lobby",
            "map6.png",
            ("호텔", "로비", "프런트", "프론트", "숙박"),
        ),
        BackgroundSpec(
            "underground_archive",
            "map7.png",
            ("지하 기록", "기록 보관", "기록실", "보관실", "문서고"),
        ),
        BackgroundSpec(
            "abandoned_theater",
            "map8.png",
            ("폐극장", "극장", "무대", "객석", "공연장"),
        ),
    ),
}


def normalize_background_theme(theme: str) -> str:
    raw = str(theme or "").strip()
    if not raw:
        return "fairy"

    lowered = raw.lower()
    normalized = _THEME_ALIASES.get(
        raw,
        _THEME_ALIASES.get(lowered, lowered),
    )

    return (
        normalized
        if normalized in _BACKGROUND_REGISTRY
        else "fairy"
    )


def background_specs(
    theme: str,
) -> tuple[BackgroundSpec, ...]:
    return _BACKGROUND_REGISTRY[
        normalize_background_theme(theme)
    ]


def _clean(value: str | None) -> str:
    return " ".join(
        str(value or "").strip().lower().split()
    )


def _matching_specs(
    theme: str,
    text: str | None,
) -> list[BackgroundSpec]:
    clean = _clean(text)
    if not clean:
        return []

    scored: list[tuple[int, BackgroundSpec]] = []

    for spec in background_specs(theme):
        score = sum(
            max(1, len(keyword))
            for keyword in spec.keywords
            if _clean(keyword) in clean
        )
        if score > 0:
            scored.append((score, spec))

    if not scored:
        return []

    best_score = max(score for score, _ in scored)

    return [
        spec
        for score, spec in scored
        if score == best_score
    ]


def _stable_pick(
    specs: Sequence[BackgroundSpec],
    *,
    chapter_id: int | None,
) -> BackgroundSpec:
    if not specs:
        raise ValueError("specs must not be empty")

    seed = int(chapter_id or 0)
    return specs[seed % len(specs)]


def select_story_background_key(
    *,
    theme: str,
    beat_texts: Sequence[str],
    current_index: int,
    chapter_id: int | None = None,
    chapter_title: str | None = None,
    lookback: int = 6,
) -> str:
    """
    현재 beat에서 장소 단서를 우선 찾고,
    없다면 직전 beat들을 역순으로 훑어 가장 최근 장소를 유지한다.

    장면 텍스트에 장소 단서가 전혀 없으면 chapter_id 기반의
    deterministic fallback을 사용해 같은 Chapter 안에서 배경이
    이유 없이 계속 바뀌지 않게 한다.
    """
    specs = background_specs(theme)
    if not specs:
        raise RuntimeError("background registry is empty")

    if beat_texts:
        safe_index = max(
            0,
            min(int(current_index), len(beat_texts) - 1),
        )

        start = safe_index
        stop = max(-1, safe_index - max(1, int(lookback)))

        for index in range(start, stop, -1):
            matches = _matching_specs(
                theme,
                beat_texts[index],
            )
            if matches:
                return _stable_pick(
                    matches,
                    chapter_id=chapter_id,
                ).key

    title_matches = _matching_specs(
        theme,
        chapter_title,
    )
    if title_matches:
        return _stable_pick(
            title_matches,
            chapter_id=chapter_id,
        ).key

    return _stable_pick(
        specs,
        chapter_id=chapter_id,
    ).key


def background_spec_by_key(
    theme: str,
    key: str,
) -> BackgroundSpec | None:
    wanted = str(key or "").strip()

    for spec in background_specs(theme):
        if spec.key == wanted:
            return spec

    return None


def resolve_story_background(
    *,
    theme: str,
    beat_texts: Sequence[str],
    current_index: int,
    chapter_id: int | None = None,
    chapter_title: str | None = None,
    background_root: str | Path | None = None,
) -> Path | None:
    root = (
        Path(background_root)
        if background_root is not None
        else DEFAULT_BACKGROUND_ROOT
    )

    normalized_theme = normalize_background_theme(theme)

    key = select_story_background_key(
        theme=theme,
        beat_texts=beat_texts,
        current_index=current_index,
        chapter_id=chapter_id,
        chapter_title=chapter_title,
    )

    spec = background_spec_by_key(
        theme,
        key,
    )
    if spec is None:
        return None

    candidate = (
        root
        / normalized_theme
        / spec.filename
    )

    if candidate.is_file():
        return candidate

    # Registry의 특정 파일이 빠진 경우에도 같은 테마의 첫 실제 asset을
    # deterministic fallback으로 사용한다.
    existing = [
        root / normalized_theme / item.filename
        for item in background_specs(theme)
        if (root / normalized_theme / item.filename).is_file()
    ]

    if not existing:
        return None

    return existing[
        int(chapter_id or 0) % len(existing)
    ]

# STORY_BACKGROUND_SYSTEM_V1_0_1_CLOUD_VILLAGE_HOTFIX_20260906

# STORY_BACKGROUND_SYSTEM_V1_1_WUXIA_ALCHEMY_20260906

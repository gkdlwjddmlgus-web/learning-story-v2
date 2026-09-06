from __future__ import annotations

from typing import Any


# THEME_NARRATIVE_ARCHITECTURE_V1_20260904

_THEME_ALIASES = {
    "fairytale": "동화",
    "동화": "동화",
    "fantasy": "판타지",
    "판타지": "판타지",
    "sf": "SF",
    "sci-fi": "SF",
    "sci_fi": "SF",
    "SF": "SF",
    "무협": "무협",
    "martial": "무협",
    "wuxia": "무협",
    "mystery": "미스터리",
    "미스터리": "미스터리",
}


THEME_NARRATIVE_PROFILES: dict[str, dict[str, Any]] = {
    "동화": {
        "core_experience": "만남 · 우정 · 감정 · 경이 · 여정 · 성장",
        "narrative_archetypes": (
            "journey",
            "new_friend",
            "helping_hand",
            "magical_discovery",
            "festival",
            "rescue",
            "reunion",
            "misunderstanding",
            "gift_or_trade",
        ),
        "event_examples": (
            "낯선 숲/마을/길에서 새로운 인물과 만난다",
            "도움을 주거나 받아 친구 관계가 생긴다",
            "기묘한 장소나 물건을 발견한다",
            "축제·놀이·약속·작은 갈등이 발생한다",
            "동료나 NPC가 위험에 빠져 구하거나 함께 빠져나온다",
            "이전에 만난 인물이 다시 등장해 관계가 변화한다",
        ),
        "relationship_roles": (
            "new_friend",
            "recurring_friend",
            "gentle_rival",
            "helper",
            "trickster",
            "villager",
        ),
        "avoid_default": (
            "모든 Chapter를 이상 현상 조사로 시작하지 않는다",
            "모든 진행을 단서/로그/원인 규명으로 환원하지 않는다",
        ),
    },
    "판타지": {
        "core_experience": "모험 · 성장 · 위험 · 세력 · 동료 · 선택",
        "narrative_archetypes": (
            "quest",
            "dungeon",
            "relic_discovery",
            "new_companion",
            "rival_encounter",
            "monster_attack",
            "faction_conflict",
            "escort_or_rescue",
            "trial",
            "temporary_alliance",
        ),
        "event_examples": (
            "길드/마을/왕국에서 새로운 의뢰나 부탁을 받는다",
            "던전·유적·봉인된 장소를 탐험한다",
            "유물이나 고대 흔적을 발견한다",
            "새 동료·라이벌·적대 세력을 만난다",
            "몬스터 습격이나 위험으로 즉시 행동해야 한다",
            "적이었던 인물과 공통의 위협 때문에 일시 협력한다",
        ),
        "relationship_roles": (
            "adventurer",
            "mentor",
            "rival",
            "guild_member",
            "faction_leader",
            "temporary_ally",
        ),
        "avoid_default": (
            "판타지를 탐정극의 배경 교체판으로 만들지 않는다",
            "던전/모험을 매번 기록 분석과 원인 추적으로 끝내지 않는다",
        ),
    },
    "SF": {
        "core_experience": "탐사 · 미지 · 기술 · 생존 · 우주적 규모 · 조우",
        "narrative_archetypes": (
            "planet_exploration",
            "asteroid_crisis",
            "alien_first_contact",
            "distress_signal",
            "system_failure",
            "derelict_station",
            "ai_anomaly",
            "environmental_shift",
            "new_crew_encounter",
            "evacuation",
        ),
        "event_examples": (
            "새 행성/위성/우주 구조물에 도착한다",
            "소행성·궤도·환경 변화 같은 갑작스러운 위기를 맞는다",
            "외계 생명체/문명과 처음 조우한다",
            "구조 신호를 받아 접근 여부를 결정한다",
            "우주선 시스템 고장으로 제한된 자원 안에서 판단한다",
            "버려진 정거장이나 미지의 구조물을 탐사한다",
        ),
        "relationship_roles": (
            "crew_member",
            "scientist",
            "pilot",
            "alien",
            "android_or_ai",
            "rival_explorer",
        ),
        "avoid_default": (
            "모든 SF Chapter를 기계 이상 원인 조사로 만들지 않는다",
            "위기·탐사·첫 조우를 단순 로그 판독 미스터리로 축소하지 않는다",
        ),
    },
    "무협": {
        "core_experience": "성장 · 명예 · 인연 · 강호 · 경쟁 · 기연",
        "narrative_archetypes": (
            "secret_manual",
            "hidden_realm",
            "tournament",
            "sect_trial",
            "master_encounter",
            "rival_duel",
            "escort_mission",
            "faction_conflict",
            "old_debt",
            "fortuitous_encounter",
        ),
        "event_examples": (
            "비급 또는 오래된 무공 기록을 발견한다",
            "비경·금지된 계곡·숨은 수련지를 찾는다",
            "무림대회/비무/문파 시험에 참가한다",
            "사부·고수·라이벌과 조우한다",
            "표국 호위나 인물 보호 임무에 휘말린다",
            "과거의 은원이나 도움 때문에 인물이 다시 찾아온다",
        ),
        "relationship_roles": (
            "master",
            "senior_or_junior",
            "rival",
            "sect_member",
            "wanderer",
            "faction_leader",
        ),
        "avoid_default": (
            "무협을 사건 현장 조사 중심의 탐정극으로 만들지 않는다",
            "비급/비경/대회를 단서 수집의 외형만 바꾼 형태로 축소하지 않는다",
        ),
    },
    "미스터리": {
        "core_experience": "추론 · 정보 · 의심 · 모순 · 진실 · 반전",
        "narrative_archetypes": (
            "missing_person",
            "theft",
            "locked_room",
            "cipher",
            "false_testimony",
            "pursuit",
            "infiltration",
            "red_herring",
            "contradiction",
            "scene_reconstruction",
        ),
        "event_examples": (
            "실종/절도/밀실 사건이 발생한다",
            "증언과 기록 사이 모순을 찾는다",
            "암호·가짜 단서·거짓 증언을 구별한다",
            "추적이나 잠입으로 새로운 정보를 얻는다",
            "여러 사실을 종합해 사건의 일부 진상을 좁힌다",
        ),
        "relationship_roles": (
            "witness",
            "suspect",
            "investigator",
            "informant",
            "rival_detective",
            "recurring_contact",
        ),
        "avoid_default": (
            "용의자 4명 중 범인 찾기 한 형식만 반복하지 않는다",
            "같은 단서 수집 순서를 매 Chapter 복제하지 않는다",
        ),
    },
}


def normalize_theme(theme: str | None) -> str:
    raw = str(theme or "").strip()
    if raw in THEME_NARRATIVE_PROFILES:
        return raw
    lowered = raw.lower()
    return _THEME_ALIASES.get(lowered, _THEME_ALIASES.get(raw, "동화"))


def get_theme_narrative_profile(theme: str | None) -> dict[str, Any]:
    normalized = normalize_theme(theme)
    profile = THEME_NARRATIVE_PROFILES[normalized]
    return {
        key: tuple(value) if isinstance(value, tuple) else value
        for key, value in profile.items()
    }


def _bullets(values) -> str:
    return "\n".join(f"- {value}" for value in values or ())


def build_theme_narrative_planner_rules(
    *,
    theme: str | None,
    recent_interaction_modes: list[str] | None = None,
) -> str:
    normalized = normalize_theme(theme)
    profile = get_theme_narrative_profile(normalized)
    archetypes = ", ".join(profile["narrative_archetypes"])
    roles = ", ".join(profile["relationship_roles"])
    recent = ", ".join(
        str(value).strip()
        for value in (recent_interaction_modes or [])
        if str(value).strip()
    ) or "없음"

    non_mystery = normalized != "미스터리"
    default_rule = (
        "- 이 Theme에서 investigation/anomaly/clue는 여러 선택지 중 하나일 뿐 기본 Story 골격이 아니다.\n"
        "- Block의 3개 Chapter가 모두 '이상 발견 → 조사 → 원인 규명' 구조가 되면 실패다."
        if non_mystery
        else
        "- 미스터리에서도 사건 종류·정보 획득 방식·추론 단계는 변주한다.\n"
        "- 같은 용의자/단서 수집 템플릿을 Block마다 복제하지 않는다."
    )

    return f"""
[Theme Narrative Director · Block Planner]
Theme: {normalized}
핵심 경험: {profile['core_experience']}
사용 가능한 거시 Narrative Archetype:
- {archetypes}

가능한 사건/장면 예시:
{_bullets(profile['event_examples'])}

관계/NPC 역할 후보:
- {roles}

피해야 할 기본값:
{_bullets(profile['avoid_default'])}

{default_rule}

설계 규칙:
- narrative_archetype은 거시적인 Story 경험이고 interaction_mode는 학습 문제의 미시 행동이다. 둘을 같은 것으로 취급하지 않는다.
- 현재 OUTLINE_SCHEMA에 별도 narrative_archetype 필드가 없으므로, 선택한 archetype의 성격을 title_seed/narrative_goal/ending_hook에 자연스럽게 반영한다.
- 같은 Block 안의 Chapter들은 가능한 한 서로 다른 거시 사건/관계 beat를 사용한다.
- 최소 한 Chapter에서는 새 인물, 기존 인물 재등장, 관계 변화, 경쟁/협력 중 하나를 자연스럽게 고려한다. Story 맥락상 부자연스러우면 억지로 넣지 않는다.
- 학습 Concept는 사건을 푸는 '단서'에만 쓰지 않는다. 이동, 선택, 생존, 수련, 협상, 탐사, 비교, 제작, 위험 판단, 관계 변화 등 Theme 경험을 가능하게 하는 지식으로도 사용할 수 있다.
- Chapter 끝은 반드시 '조사 필요'일 필요가 없다. 다음 목적지, 약속, 위험, 만남, 대결, 발견, 기회, 관계 변화, 열린 질문 중 Theme에 맞는 동력을 남긴다.
- 최근 interaction_mode: {recent}
- 최근 interaction_mode가 무엇이든 거시 Story를 다시 investigation으로 수렴시키지 않는다.
""".strip()


def build_theme_narrative_writer_rules(
    *,
    theme: str | None,
    chapter_outline: dict[str, Any] | None = None,
    opening_choice: dict[str, Any] | None = None,
) -> str:
    normalized = normalize_theme(theme)
    profile = get_theme_narrative_profile(normalized)
    archetypes = ", ".join(profile["narrative_archetypes"])
    outline = chapter_outline or {}
    interaction_mode = str(outline.get("interaction_mode") or "미지정").strip()
    choice = str((opening_choice or {}).get("choice_text") or "").strip() or "없음"

    non_mystery_rule = (
        "- 비미스터리 Theme에서는 '이상 징후 → 로그 확인 → 불일치 발견 → 원인 조사'를 자동 기본 구조로 사용하지 않는다.\n"
        "- 관찰/자료가 필요해도 그것은 장면의 일부일 뿐, 전체 Chapter의 장르를 미스터리로 바꾸지 않는다."
        if normalized != "미스터리"
        else
        "- 미스터리의 추론성은 유지하되 사건/추적/잠입/암호/증언/재구성 등 장면 행동을 변주한다."
    )

    return f"""
[Theme Narrative Director · Chapter Writer]
Theme: {normalized}
핵심 경험: {profile['core_experience']}
Narrative 후보: {archetypes}
현재 미시 interaction_mode: {interaction_mode}
직전 사용자가 실제로 고른 Story Choice: {choice}

{non_mystery_rule}

Writer 규칙:
- reasoning-safe adapter가 학습 결론을 숨긴다고 해서 Story 전체를 '조사'로 바꾸지 않는다.
- chapter outline의 title_seed/narrative_goal/ending_hook가 가진 Theme 사건 방향을 최대한 보존한다.
- NPC를 단서 제공 장치로만 쓰지 않는다. 친구, 동료, 라이벌, 사부, 승무원, 외계인, 목격자 등 Theme 역할에 맞게 욕구와 반응을 가진 인물로 다룬다.
- character_updates가 필요한 실제 만남/관계 변화가 발생했다면 그 변화를 Story와 state update에 일치시킨다.
- Concept는 현실 용어를 유지하되, 사용자가 세계 안에서 무언가를 판단/선택/수행하는 이유로 연결한다.
- Chapter 마지막은 다음 행동·선택·만남·위험·발견·경쟁·관계 변화·추론 중 Theme에 맞는 동력으로 이어질 수 있다.
- 직접 원인/정답/가설 결론을 Question 전에 선공개하지 않는 기존 Reasoning Boundary는 그대로 지킨다.
""".strip()

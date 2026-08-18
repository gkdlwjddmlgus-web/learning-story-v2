from __future__ import annotations

import html

import streamlit as st


THEME_ORDER = [
    "동화",
    "판타지",
    "SF",
    "무협",
    "미스터리",
]

# 과거 테스트 월드 호환. 신규 생성 화면에는 노출하지 않는다.
THEME_ALIASES = {
    "현대": "미스터리",
    "모험": "판타지",
}

THEME_PACKS = {
    "동화": {
        "key": "fairytale",
        "identity": "고양이와 한 권의 이야기를 완성한다.",
        "preview": (
            "종이와 파스텔빛 여백을 중심으로 한 감성적인 동화책 분위기입니다. "
            "같은 고양이와 페이지를 넘기듯 이야기를 완성합니다."
        ),
        "story_label": "✦ STORY",
        "quest_label": "PAGE QUESTION",
        "quest_title": "다음 페이지를 열기 위해 생각해볼까요?",
        "archive_name": "나의 이야기 서재",
        "report_name": "학습 기록",
        "block_complete": "한 장의 이야기가 끝났습니다.",
        "ending_label": "THE END",
        "learning_note": "다시 읽어볼 학습 노트",
        "phase_labels": {
            "setup": "이야기의 시작",
            "development": "깊어지는 이야기",
            "turn": "달라진 의미",
            "resolution": "마지막 페이지",
        },
        "cat_role": "함께 페이지를 넘기는 동료 고양이",
        "question_prefix": "페이지의 질문",
    },
    "판타지": {
        "key": "fantasy",
        "identity": "고양이와 하나의 낯선 세계를 여행한다.",
        "preview": (
            "고대 기록과 룬, 석재와 금속의 질감을 사용합니다. "
            "게임 HUD가 아니라 판타지 소설과 세계 기록을 읽는 느낌을 지향합니다."
        ),
        "story_label": "✦ CHRONICLE",
        "quest_label": "WORLD RECORD",
        "quest_title": "이 세계의 기록을 직접 확인해볼까요?",
        "archive_name": "세계 기록",
        "report_name": "학습 기록",
        "block_complete": "여정의 한 구간을 지나왔습니다.",
        "ending_label": "JOURNEY COMPLETE",
        "learning_note": "탐험 기록 · 학습 노트",
        "phase_labels": {
            "setup": "세계에 발을 들이다",
            "development": "넓어지는 세계",
            "turn": "뒤집힌 진실",
            "resolution": "여정의 끝",
        },
        "cat_role": "낯선 세계를 함께 걷는 동료 고양이",
        "question_prefix": "기록의 질문",
    },
    "SF": {
        "key": "sf",
        "identity": "고양이와 미지의 시스템과 사건을 해독한다.",
        "preview": (
            "미래 연구시설과 우주 미스터리를 바탕으로 반투명 패널, "
            "신호와 좌표, 시스템 로그의 시각 언어를 사용합니다."
        ),
        "story_label": "SYSTEM LOG",
        "quest_label": "DATA CHECK",
        "quest_title": "현재 기록을 분석해 시스템을 복구해볼까요?",
        "archive_name": "ARCHIVE",
        "report_name": "LEARNING REPORT",
        "block_complete": "MISSION LOG가 갱신되었습니다.",
        "ending_label": "MISSION COMPLETE",
        "learning_note": "ANALYSIS NOTE",
        "phase_labels": {
            "setup": "INITIAL SIGNAL",
            "development": "SYSTEM EXPANSION",
            "turn": "SIGNAL REVERSAL",
            "resolution": "FINAL PROTOCOL",
        },
        "cat_role": "차가운 기술 세계에서 함께 반응하는 동료 고양이",
        "question_prefix": "DATA CHECK",
    },
    "무협": {
        "key": "wuxia",
        "identity": "고양이와 강호의 인연과 은원을 지나간다.",
        "preview": (
            "한지와 먹, 붉은 낙관, 여백을 활용한 담백한 강호록 분위기입니다. "
            "과도한 게임식 무협 HUD 대신 인물과 관계의 이야기를 강조합니다."
        ),
        "story_label": "江湖記 · 강호록",
        "quest_label": "문답",
        "quest_title": "기록을 살펴보고 스스로 답을 찾아보자.",
        "archive_name": "강호록",
        "report_name": "수련 기록",
        "block_complete": "강호록의 한 장이 마무리되었습니다.",
        "ending_label": "完 · 인연의 끝",
        "learning_note": "서찰에 남긴 학습 기록",
        "phase_labels": {
            "setup": "강호에 들다",
            "development": "얽히는 인연",
            "turn": "드러난 은원",
            "resolution": "인연을 매듭짓다",
        },
        "cat_role": "강호를 함께 떠도는 평범한 동료 고양이",
        "question_prefix": "문답",
    },
    "미스터리": {
        "key": "mystery",
        "identity": "고양이와 흩어진 단서를 연결해 진실에 도달한다.",
        "preview": (
            "현대 미스터리 소설과 사건 파일을 결합합니다. "
            "기록, 시간, 장소와 메모를 차분히 정리해 하나의 진실에 접근합니다."
        ),
        "story_label": "CASE FILE",
        "quest_label": "EVIDENCE CHECK",
        "quest_title": "기록과 단서를 대조해볼까요?",
        "archive_name": "사건 기록",
        "report_name": "분석 기록",
        "block_complete": "사건 기록의 한 구간이 정리되었습니다.",
        "ending_label": "CASE CLOSED",
        "learning_note": "검토 메모 · 학습 노트",
        "phase_labels": {
            "setup": "사건 발생",
            "development": "쌓이는 단서",
            "turn": "단서의 재해석",
            "resolution": "진실에 도달하다",
        },
        "cat_role": "작은 단서와 미묘한 변화를 발견하는 동료 고양이",
        "question_prefix": "증거 검토",
    },
}

PORTAL_PACK = {
    "key": "portal",
    "identity": "학습 세계의 분위기를 선택하세요.",
    "preview": (
        "아직 테마가 정해지지 않았습니다. "
        "테마를 선택하면 배경, 카드, 버튼과 이야기 프레임이 즉시 바뀝니다."
    ),
    "story_label": "STORY",
    "quest_label": "LEARNING",
    "quest_title": "학습을 시작해볼까요?",
    "archive_name": "세계",
    "report_name": "기록",
    "block_complete": "한 구간이 끝났습니다.",
    "ending_label": "COMPLETE",
    "learning_note": "학습 노트",
    "phase_labels": {
        "setup": "기",
        "development": "승",
        "turn": "전",
        "resolution": "결",
    },
    "cat_role": "함께 여행하는 동료 고양이",
    "question_prefix": "질문",
}


def canonical_theme(theme: str | None) -> str | None:
    if theme is None:
        return None

    return THEME_ALIASES.get(
        theme,
        theme,
    )


def get_theme_pack(
    theme: str | None,
) -> dict:
    canonical = canonical_theme(
        theme
    )

    return THEME_PACKS.get(
        canonical,
        PORTAL_PACK,
    )


def get_theme_prompt_rules(
    theme: str | None,
) -> str:
    canonical = canonical_theme(
        theme
    )

    rules = {
        "동화": """
Theme = 동화.
- 한 권의 살아있는 이야기책 같은 감각을 유지한다.
- 감성적이고 부드럽지만 유아용 문체로 과도하게 단순화하지 않는다.
- 별/달/잎/종이 같은 이미지는 분위기 장치일 뿐 학습 개념을 마법 용어로 바꾸지 않는다.
- 동료 고양이는 함께 페이지를 넘기는 존재이며 전문 교사가 아니다.
""",
        "판타지": """
Theme = 판타지.
- 판타지 게임 HUD가 아니라 판타지 소설과 세계 기록의 감각을 유지한다.
- 장소, 문화, 인물, 고대 기록을 통해 세계를 경험하게 한다.
- HP/MP/인벤토리/몬스터 사냥 중심 구조를 만들지 않는다.
- 실제 학습 용어를 주문이나 마법 명칭으로 치환하지 않는다.
- 동료 고양이는 마법 생물로 강제 변환하지 않는다.
""",
        "SF": """
Theme = SF.
- 미래 연구시설 + 우주 미스터리를 기본 시각/서사 언어로 사용한다.
- 신호, 시스템 로그, 기록, 좌표와 같은 정보 구조는 Story 장치다.
- ENERGY/WEAPON/AMMO 같은 자원관리 HUD를 만들지 않는다.
- 실제 학습 개념은 정확한 현실 용어로 유지한다.
- 고양이는 로봇으로 변하지 않으며 차가운 기술 세계의 감정적 온도를 담당한다.
""",
        "무협": """
Theme = 무협.
- 인물 관계, 인연, 은원과 선택을 중심에 둔다.
- 모든 사건을 전투나 비급 획득으로 해결하지 않는다.
- 문파는 게임 진영이 아니라 Story 장치다.
- 경지/검술 수치를 반복 노출하지 않는다.
- 한지, 서찰, 장부, 기록 대조 같은 장치를 자연스럽게 활용한다.
- 고양이는 영물/신수로 강제 설정하지 않는다.
""",
        "미스터리": """
Theme = 미스터리.
- 사건, 단서, 증언, 모순, 재해석, 진실의 구조를 유지한다.
- 사건의 핵심 진실은 Blueprint에 고정된 내용을 따른다.
- 반전은 기존 정보의 재해석이어야 한다.
- 갑작스러운 새 범인/쌍둥이/마지막 순간의 새 핵심 설정을 금지한다.
- 동료 고양이는 작은 물건, 냄새, 행동을 발견할 수 있지만 범인을 먼저 맞히지 않는다.
""",
    }

    return rules.get(
        canonical,
        """
Theme 고유 규칙을 존중하되 Story가 학습 용어의 억지스러운 세계관 치환이 되지 않게 한다.
동료 고양이는 학습 분야의 전문가가 아니라 사용자와 함께 사건을 경험하는 동료다.
""",
    )


def _css_for_theme(
    theme: str | None,
) -> str:
    canonical = canonical_theme(
        theme
    )

    # 초기 World 생성 화면 / 로그인과 연결되는 Portal 스타일.
    if canonical not in THEME_PACKS:
        return """
        <style>
        html, body { color-scheme: dark !important; }
        .stApp {
            background:
                radial-gradient(circle at 12% 13%, rgba(46,111,168,.18), transparent 30%),
                radial-gradient(circle at 88% 86%, rgba(61,191,194,.10), transparent 32%),
                linear-gradient(145deg,#07111f 0%,#0c1c2d 50%,#10283b 100%) !important;
            color:#edf7ff !important;
        }
        [data-testid="stHeader"] { background:rgba(5,13,24,.94) !important; }
        .main .block-container { max-width:1180px; padding-top:2.6rem; padding-bottom:4rem; }
        h1,h2,h3,h4,[data-testid="stMarkdownContainer"] { color:#edf7ff; }
        [data-testid="stCaptionContainer"],.stCaption { color:#9bb5c9 !important; }
        .theme-panel,.world-create-preview,.story-card,.theme-intro-card {
            background:rgba(8,24,40,.62) !important;
            border:1px solid rgba(92,220,248,.20) !important;
            box-shadow:0 18px 42px rgba(0,0,0,.15);
            border-radius:22px;
        }
        .theme-kicker,.story-label,.chapter-kicker { color:#67e5ff !important; }
        .stTextInput input,.stTextArea textarea,[data-baseweb="select"] > div {
            color-scheme:dark !important;
            background:rgba(15,38,57,.90) !important;
            color:#f4fbff !important;
            border:1px solid rgba(113,199,224,.28) !important;
            border-radius:14px !important;
        }
        .stButton > button {
            border-radius:14px !important;
            min-height:3rem;
            font-weight:800 !important;
        }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background:linear-gradient(135deg,#20a9d1,#4bd6df) !important;
            color:#041018 !important;
            border:none !important;
        }
        </style>
        """

    if canonical == "동화":
        return """
        <style>
        html,body { color-scheme:light !important; }
        .stApp {
            background:
                radial-gradient(circle at 8% 8%,rgba(255,218,230,.76),transparent 29%),
                radial-gradient(circle at 92% 15%,rgba(205,242,226,.83),transparent 31%),
                radial-gradient(circle at 78% 88%,rgba(222,214,255,.65),transparent 33%),
                linear-gradient(160deg,#fff9ee 0%,#fff7f5 47%,#f4fff8 100%) !important;
            color:#4d4038 !important;
        }
        [data-testid="stHeader"] { background:rgba(255,249,242,.93) !important; }
        .theme-kicker,.story-label,.chapter-kicker { color:#bd7386 !important; }
        .chapter-title,h1,h2,h3,h4 { color:#493a34 !important; }
        .chapter-meta,.theme-muted { color:#987e73 !important; }
        .story-card,.theme-panel,.world-create-preview,.theme-intro-card {
            background:linear-gradient(180deg,rgba(255,255,255,.94),rgba(255,252,247,.91)) !important;
            border:1px solid rgba(211,179,166,.50) !important;
            box-shadow:0 18px 44px rgba(113,86,72,.09);
            border-radius:28px;
        }
        .story-card { position:relative; }
        .story-card::after {
            content:"✦";
            position:absolute; right:1.25rem; top:1rem;
            color:rgba(218,139,159,.40);
        }
        .story-paragraph { color:#53443d !important; }
        .stTextInput input,.stTextArea textarea,[data-baseweb="select"] > div {
            color-scheme:light !important;
            background:rgba(255,255,255,.91) !important;
            color:#4d4038 !important;
            border:1px solid rgba(214,181,170,.60) !important;
            border-radius:16px !important;
        }
        .stButton > button {
            border-radius:999px !important;
            border:1px solid rgba(205,143,157,.48) !important;
            background:rgba(255,255,255,.74) !important;
            color:#795865 !important;
        }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background:linear-gradient(135deg,#f29ab0,#f6ad99) !important;
            color:white !important; border:none !important;
        }
        .learning-note { background:#eef5ff; border-color:#d7e5f5; color:#4e6889; }
        </style>
        """

    if canonical == "판타지":
        return """
        <style>
        html,body { color-scheme:dark !important; }
        .stApp {
            background:
                radial-gradient(circle at 13% 10%,rgba(116,86,36,.24),transparent 27%),
                radial-gradient(circle at 88% 25%,rgba(69,57,110,.26),transparent 31%),
                linear-gradient(150deg,#111410 0%,#1c1a17 48%,#171522 100%) !important;
            color:#eee7d5 !important;
        }
        [data-testid="stHeader"] { background:rgba(16,17,14,.94) !important; }
        .theme-kicker,.story-label,.chapter-kicker { color:#d6ad62 !important; }
        .chapter-title,h1,h2,h3,h4 { color:#f3e6c5 !important; font-family:Georgia,"Times New Roman",serif; }
        .chapter-meta,.theme-muted { color:#a99b7d !important; }
        .story-card,.theme-panel,.world-create-preview,.theme-intro-card {
            background:
                linear-gradient(145deg,rgba(38,35,29,.94),rgba(28,26,31,.92)) !important;
            border:1px solid rgba(202,165,93,.34) !important;
            box-shadow:0 20px 50px rgba(0,0,0,.28);
            border-radius:8px;
        }
        .story-card {
            border-left:4px solid rgba(202,165,93,.72) !important;
        }
        .story-paragraph { color:#e2dac7 !important; font-family:Georgia,"Times New Roman",serif; }
        .stTextInput input,.stTextArea textarea,[data-baseweb="select"] > div {
            color-scheme:dark !important;
            background:rgba(31,30,28,.95) !important;
            color:#efe6d2 !important;
            border:1px solid rgba(202,165,93,.32) !important;
            border-radius:7px !important;
        }
        .stButton > button {
            border-radius:6px !important;
            border:1px solid rgba(202,165,93,.42) !important;
            background:rgba(45,39,31,.84) !important;
            color:#ead9b3 !important;
        }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background:linear-gradient(135deg,#7b5c28,#b28a45) !important;
            color:#fff3d4 !important; border:none !important;
        }
        .learning-note { background:rgba(58,50,37,.82); border-color:rgba(202,165,93,.30); color:#e6d8b7; }
        </style>
        """

    if canonical == "SF":
        return """
        <style>
        html,body { color-scheme:dark !important; }
        .stApp {
            background-color:#06111d !important;
            background-image:
                linear-gradient(rgba(63,202,239,.045) 1px,transparent 1px),
                linear-gradient(90deg,rgba(63,202,239,.045) 1px,transparent 1px),
                radial-gradient(circle at 82% 14%,rgba(0,214,255,.15),transparent 25%),
                radial-gradient(circle at 12% 78%,rgba(85,73,255,.13),transparent 29%) !important;
            background-size:38px 38px,38px 38px,auto,auto !important;
            color:#dceff7 !important;
        }
        [data-testid="stHeader"] { background:rgba(4,12,21,.91) !important; }
        .theme-kicker,.story-label,.chapter-kicker { color:#4ee4ff !important; letter-spacing:.17em !important; }
        .chapter-title,h1,h2,h3,h4 { color:#e7f8ff !important; font-family:Inter,Arial,sans-serif; }
        .chapter-meta,.theme-muted { color:#79aab9 !important; }
        .story-card,.theme-panel,.world-create-preview,.theme-intro-card {
            background:linear-gradient(145deg,rgba(8,29,44,.86),rgba(8,20,37,.78)) !important;
            border:1px solid rgba(62,214,244,.27) !important;
            box-shadow:0 0 0 1px rgba(84,147,255,.05),0 22px 55px rgba(0,0,0,.25);
            border-radius:3px;
            backdrop-filter:blur(12px);
        }
        .story-card { border-top:2px solid rgba(78,228,255,.52) !important; }
        .story-paragraph { color:#cfe4ec !important; }
        .stTextInput input,.stTextArea textarea,[data-baseweb="select"] > div {
            color-scheme:dark !important;
            background:rgba(6,26,41,.92) !important;
            color:#dff8ff !important;
            border:1px solid rgba(62,214,244,.31) !important;
            border-radius:2px !important;
        }
        .stButton > button {
            border-radius:2px !important;
            border:1px solid rgba(62,214,244,.38) !important;
            background:rgba(9,35,51,.86) !important;
            color:#8ceeff !important;
            text-transform:uppercase;
            letter-spacing:.04em;
        }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background:linear-gradient(135deg,#0d6f8a,#13b5c8) !important;
            color:#eaffff !important; border:none !important;
        }
        .learning-note { background:rgba(7,35,58,.92); border-color:rgba(73,184,255,.30); color:#a9ddff; }
        </style>
        """

    if canonical == "무협":
        return """
        <style>
        html,body { color-scheme:light !important; }
        .stApp {
            background:
                radial-gradient(circle at 13% 20%,rgba(36,31,27,.06),transparent 24%),
                radial-gradient(circle at 86% 76%,rgba(139,35,29,.07),transparent 27%),
                linear-gradient(135deg,#eee6d4 0%,#f7f0df 52%,#ebe0c8 100%) !important;
            color:#342f29 !important;
        }
        [data-testid="stHeader"] { background:rgba(238,230,212,.94) !important; }
        .theme-kicker,.story-label,.chapter-kicker { color:#9a3028 !important; }
        .chapter-title,h1,h2,h3,h4 { color:#28231f !important; font-family:"Nanum Myeongjo","Noto Serif KR",Georgia,serif; }
        .chapter-meta,.theme-muted { color:#7a6c5c !important; }
        .story-card,.theme-panel,.world-create-preview,.theme-intro-card {
            background:rgba(250,245,232,.87) !important;
            border:1px solid rgba(80,68,54,.20) !important;
            box-shadow:0 16px 38px rgba(68,55,41,.10);
            border-radius:2px;
        }
        .story-card { border-right:5px solid rgba(154,48,40,.55) !important; }
        .story-paragraph { color:#3f3830 !important; font-family:"Nanum Myeongjo","Noto Serif KR",Georgia,serif; }
        .stTextInput input,.stTextArea textarea,[data-baseweb="select"] > div {
            color-scheme:light !important;
            background:rgba(252,248,237,.93) !important;
            color:#342f29 !important;
            border:1px solid rgba(72,63,53,.28) !important;
            border-radius:2px !important;
        }
        .stButton > button {
            border-radius:2px !important;
            border:1px solid rgba(70,59,48,.28) !important;
            background:rgba(245,238,221,.92) !important;
            color:#45382d !important;
        }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background:linear-gradient(135deg,#7e2923,#a83d31) !important;
            color:#fff5df !important; border:none !important;
        }
        .learning-note { background:#f0e8d7; border-color:#c5b69b; color:#52483c; }
        </style>
        """

    # Mystery
    return """
    <style>
    html,body { color-scheme:light !important; }
    .stApp {
        background:
            linear-gradient(rgba(36,36,34,.022) 1px,transparent 1px),
            linear-gradient(90deg,rgba(36,36,34,.018) 1px,transparent 1px),
            radial-gradient(circle at 92% 12%,rgba(130,25,31,.08),transparent 28%),
            linear-gradient(145deg,#ece9e1 0%,#f7f5ef 48%,#e9e7e0 100%) !important;
        background-size:27px 27px,27px 27px,auto,auto !important;
        color:#292a29 !important;
    }
    [data-testid="stHeader"] { background:rgba(242,240,234,.94) !important; }
    .theme-kicker,.story-label,.chapter-kicker { color:#8a2730 !important; }
    .chapter-title,h1,h2,h3,h4 { color:#222523 !important; }
    .chapter-meta,.theme-muted { color:#696c67 !important; }
    .story-card,.theme-panel,.world-create-preview,.theme-intro-card {
        background:rgba(250,249,245,.91) !important;
        border:1px solid rgba(44,48,46,.18) !important;
        box-shadow:0 14px 35px rgba(31,33,32,.09);
        border-radius:6px;
    }
    .story-card { border-top:4px solid rgba(138,39,48,.62) !important; }
    .story-paragraph { color:#323532 !important; }
    .stTextInput input,.stTextArea textarea,[data-baseweb="select"] > div {
        color-scheme:light !important;
        background:rgba(251,250,247,.95) !important;
        color:#292a29 !important;
        border:1px solid rgba(44,48,46,.25) !important;
        border-radius:5px !important;
    }
    .stButton > button {
        border-radius:5px !important;
        border:1px solid rgba(44,48,46,.25) !important;
        background:rgba(247,245,239,.94) !important;
        color:#303331 !important;
    }
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background:linear-gradient(135deg,#68232a,#96333b) !important;
        color:#fff7f1 !important; border:none !important;
    }
    .learning-note { background:#f0eee8; border-color:#cfcbc1; color:#464946; }
    </style>
    """


COMMON_CSS = """
<style>
.main .block-container {
    max-width:1180px;
    padding-top:2.2rem;
    padding-bottom:4rem;
}

[data-testid="stCaptionContainer"],.stCaption {
    opacity:.82;
}

button[data-baseweb="tab"] {
    font-weight:760 !important;
}

[data-testid="stExpander"] {
    border-radius:12px !important;
    overflow:hidden;
}

[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius:14px;
}

.world-create-preview,
.theme-panel,
.theme-intro-card {
    padding:1.2rem 1.35rem;
    margin:.55rem 0 1.45rem;
}

.theme-kicker {
    font-size:.76rem;
    font-weight:900;
    letter-spacing:.14em;
    margin-bottom:.45rem;
}

.theme-preview-title {
    font-size:1.18rem;
    font-weight:850;
    margin-bottom:.35rem;
}

.theme-preview-copy {
    line-height:1.65;
    opacity:.88;
}

.chapter-heading {
    max-width:900px;
    margin:2.4rem auto 1.2rem;
    text-align:center;
}

.chapter-kicker {
    font-size:.77rem;
    font-weight:900;
    letter-spacing:.15em;
    margin-bottom:.5rem;
}

.chapter-title {
    font-size:clamp(1.85rem,3vw,2.65rem);
    font-weight:900;
    line-height:1.23;
    word-break:keep-all;
}

.chapter-meta {
    margin-top:.65rem;
    font-size:.91rem;
    opacity:.78;
}

.story-progress-shell {
    max-width:900px;
    margin:.4rem auto 1.2rem;
}

.story-card {
    max-width:900px;
    margin:0 auto 1.55rem;
    padding:2.25rem 2.6rem 2.55rem;
}

.story-label {
    display:block;
    font-size:.76rem;
    font-weight:900;
    letter-spacing:.13em;
    margin-bottom:1.45rem;
}

.story-paragraph {
    max-width:760px;
    margin:0 auto 1.35rem;
    font-size:1.07rem;
    line-height:1.92;
    letter-spacing:-.01em;
    word-break:keep-all;
    overflow-wrap:break-word;
}

.story-paragraph:last-child {
    margin-bottom:0;
}

.story-separator {
    max-width:900px;
    margin:1.5rem auto 1.05rem;
    text-align:center;
    opacity:.5;
    letter-spacing:.42rem;
}

.quest-section-heading {
    max-width:900px;
    margin:0 auto 1rem;
    text-align:center;
}

.quest-section-heading .quest-kicker {
    font-size:.74rem;
    font-weight:900;
    letter-spacing:.13em;
    opacity:.74;
}

.quest-section-heading .quest-title {
    font-size:1.28rem;
    font-weight:850;
    margin-top:.25rem;
}

.dialogue-row {
    display:flex;
    width:100%;
    margin:14px 0;
}
.dialogue-row.user { justify-content:flex-end; }
.dialogue-row.npc { justify-content:flex-start; }

.dialogue-bubble {
    position:relative;
    max-width:78%;
    padding:14px 17px;
    border-radius:16px;
    line-height:1.65;
    border:1px solid rgba(120,130,150,.18);
    box-shadow:0 4px 14px rgba(0,0,0,.06);
    word-break:keep-all;
}
.dialogue-bubble .speaker {
    display:block;
    font-weight:850;
    margin-bottom:5px;
    font-size:.92rem;
}
.dialogue-bubble.user {
    background:rgba(238,242,247,.92);
    color:#24303d;
}
.dialogue-bubble.npc-correct {
    background:#eaf8ef;
    color:#126b38;
}
.dialogue-bubble.npc-wrong {
    background:#fff0f0;
    color:#a42d25;
}

.learning-note {
    margin:1rem 0;
    padding:1rem 1.15rem;
    border:1px solid;
    border-radius:12px;
    line-height:1.72;
}
.learning-note .note-label {
    display:block;
    font-size:.76rem;
    font-weight:900;
    letter-spacing:.08em;
    margin-bottom:.35rem;
}

.block-complete-panel,
.story-ending-panel {
    max-width:900px;
    margin:1.35rem auto;
    padding:1.35rem 1.5rem;
    border:1px solid rgba(128,128,128,.20);
    border-radius:14px;
    background:rgba(127,127,127,.07);
    text-align:center;
}

.choice-card {
    padding:.8rem 0 .3rem;
}

.archive-chapter-card {
    line-height:1.78;
}

.mastery-row {
    display:grid;
    grid-template-columns:minmax(170px,1fr) 2fr 80px;
    gap:.8rem;
    align-items:center;
    margin:.55rem 0;
}

@media (max-width:768px) {
    .story-card {
        padding:1.55rem 1.3rem 1.75rem;
    }
    .story-paragraph {
        font-size:1rem;
        line-height:1.82;
    }
    .dialogue-bubble {
        max-width:91%;
    }
    .mastery-row {
        grid-template-columns:1fr;
    }
}
</style>
"""


def _theme_enhancement_css(
    theme: str | None,
) -> str:
    """
    Streamlit의 전역 Light/Dark 설정과 무관하게 Theme Pack 자체의
    대비와 배경 표현을 보정한다.

    특히 판타지/SF는 OS·브라우저·Streamlit이 Light mode여도
    widget label, placeholder, select text가 충분한 대비를 갖도록
    명시적으로 색을 지정한다.
    """
    canonical = canonical_theme(theme)

    if canonical == "판타지":
        return """
        <style>
        .stApp {
            background-image:
                radial-gradient(circle at 14% 12%, rgba(216,173,92,.18), transparent 28%),
                radial-gradient(circle at 82% 18%, rgba(121,94,186,.24), transparent 30%),
                radial-gradient(circle at 68% 82%, rgba(47,86,70,.17), transparent 34%),
                radial-gradient(circle, rgba(240,211,145,.20) 0 1px, transparent 1.4px),
                linear-gradient(145deg,#10130f 0%,#1c1818 46%,#171422 100%) !important;
            background-size:auto,auto,auto,88px 88px,auto !important;
        }

        .stApp::before {
            content:"";
            position:fixed;
            inset:0;
            pointer-events:none;
            background:
                radial-gradient(circle at 12% 30%,rgba(255,224,154,.68) 0 1px,transparent 1.8px),
                radial-gradient(circle at 27% 74%,rgba(255,224,154,.40) 0 1px,transparent 1.8px),
                radial-gradient(circle at 63% 24%,rgba(193,170,255,.52) 0 1px,transparent 1.8px),
                radial-gradient(circle at 88% 67%,rgba(255,224,154,.48) 0 1px,transparent 1.8px);
            opacity:.52;
            z-index:0;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {
            position:relative;
            z-index:1;
        }

        .stApp [data-testid="stWidgetLabel"],
        .stApp [data-testid="stWidgetLabel"] p,
        .stApp label,
        .stApp [data-testid="stCaptionContainer"],
        .stApp .stCaption {
            color:#d8ccb1 !important;
        }

        .stApp .stTextInput input,
        .stApp .stTextArea textarea,
        .stApp div[data-baseweb="select"] > div {
            background:#24211e !important;
            color:#f4ead5 !important;
            -webkit-text-fill-color:#f4ead5 !important;
        }

        .stApp .stTextInput input::placeholder,
        .stApp .stTextArea textarea::placeholder {
            color:#a99c83 !important;
            -webkit-text-fill-color:#a99c83 !important;
            opacity:1 !important;
        }

        .stApp div[data-baseweb="select"] span,
        .stApp div[data-baseweb="select"] svg {
            color:#f4ead5 !important;
            fill:#f4ead5 !important;
        }

        div[data-baseweb="popover"] ul[role="listbox"] {
            background:#24211e !important;
            color:#f4ead5 !important;
        }

        div[data-baseweb="popover"] li[role="option"] {
            color:#f4ead5 !important;
        }
        </style>
        """

    if canonical == "SF":
        return """
        <style>
        @keyframes ls-sf-twinkle {
            0%,100% { opacity:.28; transform:translateY(0); }
            50% { opacity:.72; transform:translateY(-1px); }
        }

        .stApp {
            background-image:
                linear-gradient(rgba(73,209,240,.045) 1px,transparent 1px),
                linear-gradient(90deg,rgba(73,209,240,.045) 1px,transparent 1px),
                radial-gradient(circle at 84% 14%,rgba(0,224,255,.19),transparent 28%),
                radial-gradient(circle at 12% 80%,rgba(80,79,255,.19),transparent 31%),
                radial-gradient(circle at 52% 42%,rgba(19,92,140,.12),transparent 38%),
                linear-gradient(150deg,#04101c 0%,#071726 50%,#041521 100%) !important;
            background-size:40px 40px,40px 40px,auto,auto,auto,auto !important;
        }

        .stApp::before {
            content:"";
            position:fixed;
            inset:0;
            pointer-events:none;
            z-index:0;
            background:
                radial-gradient(circle at 6% 17%,#b7f7ff 0 1px,transparent 1.7px),
                radial-gradient(circle at 16% 63%,#7de9ff 0 1px,transparent 1.8px),
                radial-gradient(circle at 31% 28%,#d3fbff 0 1px,transparent 1.7px),
                radial-gradient(circle at 44% 82%,#8aa6ff 0 1px,transparent 1.8px),
                radial-gradient(circle at 57% 15%,#b7f7ff 0 1px,transparent 1.7px),
                radial-gradient(circle at 71% 69%,#72ddff 0 1px,transparent 1.8px),
                radial-gradient(circle at 87% 35%,#d3fbff 0 1px,transparent 1.7px),
                radial-gradient(circle at 94% 82%,#8198ff 0 1px,transparent 1.8px);
            animation:ls-sf-twinkle 5.2s ease-in-out infinite;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {
            position:relative;
            z-index:1;
        }

        .stApp [data-testid="stWidgetLabel"],
        .stApp [data-testid="stWidgetLabel"] p,
        .stApp label,
        .stApp [data-testid="stCaptionContainer"],
        .stApp .stCaption {
            color:#b9d7e3 !important;
        }

        .stApp .stTextInput input,
        .stApp .stTextArea textarea,
        .stApp div[data-baseweb="select"] > div {
            background:#0b2435 !important;
            color:#e9faff !important;
            -webkit-text-fill-color:#e9faff !important;
        }

        .stApp .stTextInput input::placeholder,
        .stApp .stTextArea textarea::placeholder {
            color:#6e9daf !important;
            -webkit-text-fill-color:#6e9daf !important;
            opacity:1 !important;
        }

        .stApp div[data-baseweb="select"] span,
        .stApp div[data-baseweb="select"] svg {
            color:#e9faff !important;
            fill:#e9faff !important;
        }

        div[data-baseweb="popover"] ul[role="listbox"] {
            background:#0b2435 !important;
            color:#e9faff !important;
        }

        div[data-baseweb="popover"] li[role="option"] {
            color:#e9faff !important;
        }
        </style>
        """

    if canonical == "무협":
        return """
        <style>
        .stApp {
            background-image:
                repeating-linear-gradient(0deg,rgba(82,63,40,.025) 0 1px,transparent 1px 7px),
                radial-gradient(ellipse at 9% 18%,rgba(45,38,31,.10),transparent 26%),
                radial-gradient(ellipse at 91% 76%,rgba(151,48,39,.10),transparent 29%),
                radial-gradient(ellipse at 64% 24%,rgba(125,101,65,.08),transparent 31%),
                linear-gradient(140deg,#eee3ca 0%,#faf3e2 46%,#e8dac0 100%) !important;
        }

        .world-create-preview,
        .theme-panel,
        .theme-intro-card,
        .story-card {
            box-shadow:
                0 18px 45px rgba(76,59,40,.10),
                inset 0 0 45px rgba(122,95,60,.035) !important;
        }
        </style>
        """

    if canonical == "미스터리":
        return """
        <style>
        .stApp {
            background-image:
                linear-gradient(rgba(43,47,45,.025) 1px,transparent 1px),
                linear-gradient(90deg,rgba(43,47,45,.020) 1px,transparent 1px),
                radial-gradient(circle at 87% 14%,rgba(137,37,46,.11),transparent 29%),
                radial-gradient(circle at 13% 78%,rgba(47,67,77,.08),transparent 31%),
                radial-gradient(circle at 55% 40%,rgba(255,255,255,.58),transparent 36%),
                linear-gradient(145deg,#e8e5dd 0%,#f8f6f0 50%,#e5e6e2 100%) !important;
            background-size:28px 28px,28px 28px,auto,auto,auto,auto !important;
        }

        .world-create-preview,
        .theme-panel,
        .theme-intro-card,
        .story-card {
            background:
                linear-gradient(160deg,rgba(255,255,252,.94),rgba(246,244,238,.91)) !important;
        }
        </style>
        """

    return ""


def apply_theme_styles(
    theme: str | None,
) -> None:
    st.markdown(
        COMMON_CSS,
        unsafe_allow_html=True,
    )
    st.markdown(
        _css_for_theme(theme),
        unsafe_allow_html=True,
    )
    st.markdown(
        _theme_enhancement_css(theme),
        unsafe_allow_html=True,
    )


def render_theme_preview(
    theme: str | None,
) -> None:
    pack = get_theme_pack(
        theme
    )

    title = (
        canonical_theme(theme)
        or "THEME SELECT"
    )

    st.markdown(
        f"""
        <div class="world-create-preview">
            <div class="theme-kicker">THEME PREVIEW</div>
            <div class="theme-preview-title">{html.escape(title)}</div>
            <div class="theme-preview-copy">
                {html.escape(pack["preview"])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_phase_label(
    theme: str | None,
    phase: str | None,
) -> str:
    pack = get_theme_pack(
        theme
    )

    return pack["phase_labels"].get(
        phase or "",
        phase or "-",
    )

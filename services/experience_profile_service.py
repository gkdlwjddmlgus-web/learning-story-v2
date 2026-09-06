from __future__ import annotations

# QUESTION_DIFFICULTY_COMPANION_VOICE_QUALITY_GATE_V1_20260906

from typing import Any


LEARNER_LEVEL_PROFILES: dict[str, dict[str, str]] = {
    "입문": {
        "display_name": "입문 · 선행지식 0",
        "audience": "해당 분야를 처음 접하는 사람. 문장 자체는 초등 고학년~중학생도 이해할 수 있는 일상어를 우선한다.",
        "prior_knowledge": "전문용어와 기본 구조를 모른다고 가정한다.",
        "story_rule": (
            "Story에서 새 전문용어를 한꺼번에 쏟아내지 않는다. "
            "한 장면에서 핵심 새 용어는 1~2개만 소개하고 처음 등장할 때 쉬운 뜻을 짧게 붙인다."
        ),
        "brief_rule": (
            "문제를 내기 전에 concept_brief에서 필요한 지식을 1~2문장으로 먼저 가르친다. "
            "일상 비유 또는 쉬운 설명 → 실제 용어 순서로 쓴다."
        ),
        "source_rule": (
            "원본 로그/코드/전문 문서를 바로 던지지 않는다. evidence_summary를 쉬운 한국어로 먼저 제공하고, "
            "원본은 evidence_context에 짧게 분리한다. 생소한 용어는 evidence_help에서 즉시 뜻을 설명한다."
        ),
        "question_rule": (
            "방금 배운 한 가지 개념을 한 단계 적용하면 풀 수 있게 한다. "
            "선행지식을 숨은 전제로 요구하지 않는다. 보기 문장도 쉬운 표현을 우선한다."
        ),
        "ui_mode": "guided",
    },
    "초급": {
        "display_name": "초급 · 쉬운 기초 적용",
        "audience": "핵심 용어를 조금 접했지만 아직 스스로 기술 문서를 읽기 어려운 사람.",
        "prior_knowledge": "가장 기초적인 용어만 조금 안다고 가정한다.",
        "story_rule": (
            "전문용어는 사용하되 한 장면에 너무 많이 넣지 않는다. "
            "중요한 새 용어는 문맥 안에서 짧게 뜻을 짚어준다."
        ),
        "brief_rule": (
            "concept_brief에서 핵심 개념과 문제에 필요한 관점을 짧게 알려준 뒤 적용하게 한다."
        ),
        "source_rule": (
            "evidence_summary를 쉬운 요약으로 제공하고 evidence_context에는 짧은 실제형 자료를 둔다. "
            "생소한 약어/용어는 evidence_help로 보조한다."
        ),
        "question_rule": (
            "개념 비교와 간단한 상황 적용을 중심으로 한다. "
            "한 문제에서 동시에 요구하는 새 개념은 최대 2개로 제한한다."
        ),
        "ui_mode": "supported",
    },
    "중급": {
        "display_name": "중급 · 기본지식 활용",
        "audience": "기본 개념을 알고 실제 사례에 적용하려는 학습자.",
        "prior_knowledge": "핵심 용어와 기본 흐름을 알고 있다고 가정한다.",
        "story_rule": (
            "실제 용어를 자연스럽게 사용하고 Story 설명보다 사건/상황을 우선한다."
        ),
        "brief_rule": (
            "concept_brief는 정답을 알려주지 않는 짧은 관점 힌트만 제공한다."
        ),
        "source_rule": (
            "실제에 가까운 로그·설정·기록을 사용할 수 있다. "
            "evidence_summary는 핵심 상황만 짚고 상세 자료 판독을 요구한다."
        ),
        "question_rule": (
            "비교·진단·원인 추론·적절한 조치를 묻는다. 단순 정의 문제를 최소화한다. "
            "한눈에 보이는 단일 단서만 찾게 하지 말고, 가능하면 서로 다른 근거/조건 2개 이상을 연결해 판단하게 한다. "
            "오답도 실제로 선택할 법한 방법으로 구성해 입문/초급과 사고 깊이를 분명히 구분한다."
        ),
        "ui_mode": "direct",
    },
    "고급": {
        "display_name": "고급 · 전공/실무 판단",
        "audience": "전공 기초 또는 실무형 판단 연습이 가능한 학습자.",
        "prior_knowledge": "핵심 용어, 기본 구조, 대표적인 운영 개념을 이미 안다고 가정한다.",
        "story_rule": (
            "전문용어를 과도하게 풀어쓰지 않고 실제 상황의 압축된 정보를 사용한다."
        ),
        "brief_rule": (
            "concept_brief는 필요 시 확인할 수 있는 최소 관점만 제공하고 문제 해결에 정답을 노출하지 않는다."
        ),
        "source_rule": (
            "원본에 가까운 로그·설정·메트릭·문서를 직접 제시한다. 불필요한 쉬운 요약은 줄인다."
        ),
        "question_rule": (
            "아키텍처, failure mode, trade-off, 운영 리스크와 최적 조치를 판단하게 한다."
        ),
        "ui_mode": "raw",
    },
}


REASONING_PROFILES: dict[str, dict[str, str]] = {
    "intro": {
        "label": "이해",
        "rule": "방금 배운 핵심 역할·흐름을 한 단계 적용하면 풀 수 있게 한다.",
    },
    "basic": {
        "label": "기초 적용",
        "rule": "두 개념을 비교하거나 간단한 상황에 적용해 판단하게 한다.",
    },
    "intermediate": {
        "label": "분석",
        "rule": (
            "원인·조치·흐름·관측 결과를 연결해 분석하게 한다. "
            "가능하면 독립된 근거 2개 이상을 결합하고, 그럴듯한 대안 사이의 trade-off를 비교하게 한다."
        ),
    },
    "advanced": {
        "label": "전공/실무 판단",
        "rule": "여러 조건의 trade-off, failure mode, 아키텍처 선택을 종합 판단하게 한다.",
    },
}


TASK_PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    "observe": [
        ("observe_anchor", "핵심 상황 보기", "주어진 자료에서 이번 판단의 기준이 되는 핵심 사실을 찾는다."),
        ("spot_difference", "차이 찾기", "두 상태/기록의 중요한 차이를 비교한다."),
        ("interpret", "의미 해석", "차이가 학습 Concept에서 무엇을 뜻하는지 판단한다."),
        ("apply_rule", "규칙 적용", "배운 원리로 가능한 설명을 좁힌다."),
        ("observe_conclusion", "발견 정리", "앞의 판단과 새 자료를 합쳐 이번 Chapter의 진행 결과를 정리한다."),
    ],
    "compare": [
        ("read_candidates", "후보 확인", "비교할 여러 주장/기록/선택의 핵심을 확인한다."),
        ("compare_basis", "기준 세우기", "학습 Concept에서 무엇을 기준으로 비교해야 하는지 적용한다."),
        ("cross_compare", "서로 대조하기", "후보들의 차이를 같은 기준으로 비교한다."),
        ("eliminate", "맞지 않는 후보 줄이기", "기술적으로 성립하지 않거나 덜 적절한 후보를 좁힌다."),
        ("compare_conclusion", "비교 결론", "앞 판단과 새 자료를 종합해 다음 진행에 필요한 결론을 얻는다."),
    ],
    "trace": [
        ("entry", "시작점 찾기", "흐름이 시작되는 지점 또는 첫 상태를 확인한다."),
        ("next_hop", "다음 단계 잇기", "어떤 단계로 이어지는지 학습 Concept로 판단한다."),
        ("bypass", "빠진 단계 찾기", "정상 흐름과 비교해 누락·우회·변경된 지점을 찾는다."),
        ("propagation", "영향 따라가기", "변화가 다음 단계에 어떤 영향을 주는지 추적한다."),
        ("trace_conclusion", "경로 정리", "앞의 추적과 새 자료를 합쳐 실제 경로 또는 다음 추적 지점을 정리한다."),
    ],
    "diagnose": [
        ("symptom", "증상 확인", "관측된 현상에서 가장 중요한 신호를 찾는다."),
        ("cause_candidates", "원인 후보 비교", "가능한 원인들을 같은 기술 기준으로 비교한다."),
        ("test_result", "검사 결과 읽기", "추가 자료가 어떤 원인을 지지하는지 판단한다."),
        ("cause_narrow", "원인 좁히기", "맞지 않는 설명을 제거해 원인을 좁힌다."),
        ("diagnose_conclusion", "진단 결론", "앞의 신호와 새 자료를 종합해 현재 단계의 진단을 정리한다."),
    ],
    "verify": [
        ("claim", "주장 확인", "검증할 주장이나 가설의 핵심 조건을 확인한다."),
        ("rule_check", "원리 대조", "배운 Concept와 주장이 맞는지 비교한다."),
        ("evidence_match", "자료 대조", "실제 자료가 주장을 지지하거나 반박하는지 판단한다."),
        ("edge_check", "예외 확인", "비슷하지만 다른 경우와 구분한다."),
        ("verify_conclusion", "검증 결론", "앞 결과와 새 자료를 종합해 믿을 수 있는 결론을 정리한다."),
    ],
    "sequence": [
        ("steps", "단계 확인", "주어진 처리/행동의 단계들을 구분한다."),
        ("order", "순서 맞추기", "학습 Concept에 맞는 정상 순서를 판단한다."),
        ("changed_step", "바뀐 단계 찾기", "정상 흐름과 달라진 순서나 위치를 확인한다."),
        ("effect", "변화 영향 보기", "순서 변화가 결과에 어떤 영향을 주는지 판단한다."),
        ("sequence_conclusion", "흐름 정리", "앞 판단과 새 자료로 실제 처리 흐름을 정리한다."),
    ],
    "design": [
        ("goal", "목표 정하기", "해결/복구/검증에서 가장 중요한 목표를 확인한다."),
        ("option_compare", "방법 비교", "가능한 방법들의 장단점을 학습 Concept로 비교한다."),
        ("risk_check", "위험 확인", "각 선택이 만들 수 있는 문제를 판단한다."),
        ("plan_select", "계획 선택", "현재 조건에 가장 적절한 방법을 고른다."),
        ("design_conclusion", "계획 확정", "앞 판단과 새 조건을 합쳐 다음 행동 계획을 정리한다."),
    ],
    "decode": [
        ("symbol", "표시 읽기", "기록/규칙/기호에서 핵심 의미를 확인한다."),
        ("rule", "규칙 연결", "배운 Concept와 표시의 관계를 찾는다."),
        ("compare", "해석 비교", "가능한 해석들을 같은 기준으로 비교한다."),
        ("apply", "해석 적용", "현재 상황에 맞는 해석을 적용한다."),
        ("decode_conclusion", "해독 결과", "앞의 해석과 새 자료를 합쳐 다음 진행에 필요한 뜻을 정리한다."),
    ],
    "strategy": [
        ("situation", "상황 읽기", "현재 조건과 제한을 파악한다."),
        ("options", "선택지 비교", "가능한 전략을 학습 Concept로 비교한다."),
        ("counter", "반대 상황 생각하기", "각 전략이 실패할 수 있는 조건을 판단한다."),
        ("best_fit", "맞는 전략 고르기", "현재 조건에 가장 맞는 전략을 선택한다."),
        ("strategy_conclusion", "전략 정리", "앞 판단과 새 상황을 종합해 다음 행동을 정한다."),
    ],
    "synthesize": [
        ("facts", "핵심 사실 모으기", "누적된 정보 중 결론에 필요한 사실을 골라낸다."),
        ("connect", "사실 연결하기", "각 사실이 어떤 원리로 이어지는지 판단한다."),
        ("alternative", "다른 설명 비교", "비슷한 설명 중 맞지 않는 것을 제거한다."),
        ("weight", "근거 강도 보기", "가장 설득력 있는 근거 조합을 판단한다."),
        ("synthesis_conclusion", "최종 정리", "앞의 누적 결과와 새 자료를 합쳐 현재 단계의 결론을 정리한다."),
    ],
}


THEME_EXPERIENCE_PROFILES: dict[str, dict[str, Any]] = {
    "미스터리": {
        "source_label": "증거 자료",
        "summary_label": "증거 요약",
        "help_label": "용어 도움",
        "step_noun": "조사",
        "interaction_noun": "조사 방식",
        "progress_label": "단서 확보",
        "review_progress_label": "검토 후 확보한 단서",
        "conclusion_label": "조사 결론",
        "review_conclusion_label": "검토 후 조사 결론",
        "next_label": "다음 조사",
        "prepare_label": "조사 단계 {count}개 준비",
        "spinner_label": "Story의 사건과 Curriculum을 연결해 조사 단계 {count}개를 만들고 있습니다...",
        "arc_guidance": "사건 파악 → 진술/기록 검증 → 경로/가설 추적 → 반전/검증 → 사건 종합의 흐름을 변주한다.",
        "writer_rules": (
            "사용자는 탐정처럼 증거를 읽고 모순을 찾고 가설을 좁힌다. "
            "매 Chapter를 범인 지목으로 만들지 말고 조사 방식 자체를 바꾼다. "
            "고양이는 증거를 발견하거나 반응하지만 전문 해설자가 아니다."
        ),
        "modes": {
            "scene_reconstruction": ("현장 재구성", "흩어진 기록을 이용해 사건 직전 흐름을 복원한다.", "sequence"),
            "witness_verification": ("진술 검증", "등장인물의 기술적 진술을 비교해 사실과 모순을 가린다.", "verify"),
            "log_forensics": ("로그 포렌식", "로그와 운영 기록에서 이상 시작 지점을 좁힌다.", "diagnose"),
            "alibi_check": ("알리바이 검증", "작업 주장이 실제 시스템 구조상 가능한지 확인한다.", "verify"),
            "evidence_comparison": ("증거 대조", "서로 다른 기록과 설정을 비교해 가설을 지지/반박한다.", "compare"),
            "route_trace": ("경로 추적", "데이터나 요청이 이동한 경로에서 우회·누락 지점을 찾는다.", "trace"),
            "hypothesis_test": ("가설 검증", "현재 가설을 확인하거나 반박할 적절한 검증을 선택한다.", "verify"),
            "contradiction_hunt": ("모순 추적", "확정된 사실 사이의 기술적 모순을 찾는다.", "compare"),
            "trap_design": ("검증 장치 설계", "의심되는 행동을 드러낼 안전한 검증 조건을 설계한다.", "design"),
            "case_synthesis": ("사건 종합", "누적 증거를 종합해 원인·수법·다음 추적 방향을 정리한다.", "synthesize"),
        },
        "phase_pool": {
            "setup": ("scene_reconstruction", "witness_verification", "evidence_comparison"),
            "development": ("log_forensics", "alibi_check", "route_trace", "hypothesis_test"),
            "turn": ("contradiction_hunt", "hypothesis_test", "trap_design", "route_trace"),
            "resolution": ("evidence_comparison", "contradiction_hunt", "case_synthesis"),
        },
        "final_mode": "case_synthesis",
    },
    "SF": {
        "source_label": "시스템 자료",
        "summary_label": "상태 브리핑",
        "help_label": "시스템 용어",
        "step_noun": "작업",
        "interaction_noun": "임무 방식",
        "progress_label": "진단 결과",
        "review_progress_label": "검토 후 확인한 결과",
        "conclusion_label": "복구 결론",
        "review_conclusion_label": "검토 후 복구 결론",
        "next_label": "다음 작업",
        "prepare_label": "시스템 작업 {count}개 준비",
        "spinner_label": "Story의 시스템 상황과 Curriculum을 연결해 작업 {count}개를 만들고 있습니다...",
        "arc_guidance": "이상 신호 발견 → 시스템 진단/격리 → 신호·모듈 추적 → 예기치 않은 반응 → 복구/재동기화 → 임무 해결로 전개한다.",
        "writer_rules": (
            "사용자는 우주선·도시·연구기지 등의 시스템을 진단하고 복구하는 임무를 수행한다. "
            "모든 Chapter를 로그 조사로 만들지 말고 센서 해석, 모듈 격리, 시뮬레이션, 복구 경로 선택을 변주한다. "
            "고양이는 센서나 이상 신호를 먼저 발견하는 동료이지 시스템 교관이 아니다."
        ),
        "modes": {
            "anomaly_scan": ("이상 신호 스캔", "정상 상태와 다른 신호를 찾아 이상 범위를 좁힌다.", "observe"),
            "system_diagnostics": ("시스템 진단", "관측된 증상에서 고장 원인을 단계적으로 좁힌다.", "diagnose"),
            "signal_trace": ("신호 추적", "센서·네트워크·데이터 신호가 이동한 경로를 따라간다.", "trace"),
            "module_isolation": ("모듈 격리", "문제를 일으키는 모듈을 안전하게 분리할 방법을 판단한다.", "design"),
            "simulation_test": ("시뮬레이션 검증", "가설을 안전한 가상 조건에서 검증한다.", "verify"),
            "ai_verification": ("AI 판단 검증", "AI 또는 자동 시스템의 판단이 기술적으로 타당한지 확인한다.", "verify"),
            "recovery_route": ("복구 경로 설계", "제약조건을 고려해 가장 안전한 복구 순서를 고른다.", "design"),
            "cascade_analysis": ("연쇄 이상 분석", "하나의 이상이 다른 시스템으로 퍼지는 과정을 분석한다.", "trace"),
            "resynchronization": ("재동기화", "엇갈린 시스템 상태를 정상 순서로 다시 맞춘다.", "sequence"),
            "mission_resolution": ("임무 해결", "누적된 진단 결과를 종합해 시스템을 안정화한다.", "synthesize"),
        },
        "phase_pool": {
            "setup": ("anomaly_scan", "system_diagnostics", "signal_trace"),
            "development": ("module_isolation", "simulation_test", "ai_verification", "cascade_analysis"),
            "turn": ("cascade_analysis", "recovery_route", "ai_verification", "signal_trace"),
            "resolution": ("resynchronization", "recovery_route", "mission_resolution"),
        },
        "final_mode": "mission_resolution",
    },
    "판타지": {
        "source_label": "기록·룬 자료",
        "summary_label": "해독 브리핑",
        "help_label": "용어 풀이",
        "step_noun": "해독",
        "interaction_noun": "탐구 방식",
        "progress_label": "해독 결과",
        "review_progress_label": "검토 후 얻은 해독 결과",
        "conclusion_label": "의식/탐구 결론",
        "review_conclusion_label": "검토 후 탐구 결론",
        "next_label": "다음 탐구",
        "prepare_label": "탐구 단계 {count}개 준비",
        "spinner_label": "Story의 기록과 Curriculum을 연결해 탐구 단계 {count}개를 만들고 있습니다...",
        "arc_guidance": "이상 현상 발견 → 고대 기록/규칙 해독 → 유물·봉인 구조 파악 → 숨은 규칙/반전 → 복원 계획 → 최종 의식 또는 해결로 전개한다.",
        "writer_rules": (
            "사용자는 세계의 규칙을 해독하고 유물·기록·봉인의 원리를 이해해 문제를 해결한다. "
            "현실 학습 Concept를 마법 이름으로 바꾸지 말고, Story 장치가 Concept를 이해해야 작동하도록 구성한다. "
            "고양이는 기록이나 작은 변화를 발견하는 동료다."
        ),
        "modes": {
            "ancient_record_decode": ("고대 기록 해독", "기록 속 규칙과 실제 학습 Concept의 의미를 해석한다.", "decode"),
            "rune_rule_check": ("룬 규칙 확인", "여러 규칙/표식 중 현재 조건에 맞는 원리를 판별한다.", "verify"),
            "artifact_analysis": ("유물 구조 분석", "유물의 구조와 작동 흐름을 Concept로 분석한다.", "observe"),
            "seal_structure": ("봉인 구조 파악", "여러 단계의 연결 관계와 제약을 추적한다.", "trace"),
            "spell_comparison": ("주문/기록 비교", "비슷한 설명과 구조의 차이를 학습 Concept로 비교한다.", "compare"),
            "ritual_sequence": ("의식 순서 복원", "정상 처리 순서와 바뀐 단계를 찾아 올바른 흐름을 복원한다.", "sequence"),
            "hidden_rule": ("숨은 규칙 발견", "겉으로 드러나지 않은 제약이나 패턴을 찾아낸다.", "diagnose"),
            "corruption_trace": ("변질 흔적 추적", "정상 상태가 어디서 달라졌는지 경로를 따라간다.", "trace"),
            "restoration_plan": ("복원 계획", "안전하게 구조를 되돌리기 위한 방법을 설계한다.", "design"),
            "final_ritual": ("최종 의식", "누적된 해독과 규칙을 종합해 마지막 해결을 완성한다.", "synthesize"),
        },
        "phase_pool": {
            "setup": ("ancient_record_decode", "rune_rule_check", "artifact_analysis"),
            "development": ("seal_structure", "spell_comparison", "ritual_sequence", "hidden_rule"),
            "turn": ("hidden_rule", "corruption_trace", "restoration_plan", "spell_comparison"),
            "resolution": ("ritual_sequence", "restoration_plan", "final_ritual"),
        },
        "final_mode": "final_ritual",
    },
    "무협": {
        "source_label": "강호 기록",
        "summary_label": "상황 요약",
        "help_label": "용어 풀이",
        "step_noun": "판단",
        "interaction_noun": "행동 방식",
        "progress_label": "간파한 사실",
        "review_progress_label": "검토 후 간파한 사실",
        "conclusion_label": "판단 결론",
        "review_conclusion_label": "검토 후 판단 결론",
        "next_label": "다음 행동",
        "prepare_label": "판단 단계 {count}개 준비",
        "spinner_label": "Story의 강호 상황과 Curriculum을 연결해 판단 단계 {count}개를 만들고 있습니다...",
        "arc_guidance": "의뢰/이상 징후 → 흔적 추적·비급 해석 → 수법/전략 비교 → 세력 변화/함정 → 결전 준비 → 최종 판단으로 전개한다.",
        "writer_rules": (
            "사용자는 흔적을 읽고 비급·수법·전략을 비교하며 강호의 사건을 해결한다. "
            "학습 Concept를 무공 이름으로 바꾸지 말고 현실 용어는 기록·전략 설명 안에 그대로 유지한다. "
            "고양이는 흔적을 발견하거나 긴장에 반응하는 동료다."
        ),
        "modes": {
            "trace_reading": ("흔적 추적", "남은 기록과 이동 흐름을 따라 사건의 방향을 좁힌다.", "trace"),
            "testimony_check": ("진술 대조", "여러 인물의 주장을 같은 기술 기준으로 검증한다.", "verify"),
            "manual_decode": ("비급 해석", "기록된 규칙과 구조를 실제 Concept로 해석한다.", "decode"),
            "technique_compare": ("수법 비교", "여러 방식의 특징과 조건을 비교한다.", "compare"),
            "flow_analysis": ("흐름 분석", "단계와 연결 관계를 따라 이상 지점을 파악한다.", "sequence"),
            "opponent_method": ("상대 수법 검증", "상대의 주장/행동이 실제 조건에서 가능한지 확인한다.", "verify"),
            "strategy_choice": ("전략 판단", "조건에 맞는 가장 적절한 대응 전략을 고른다.", "strategy"),
            "trap_reading": ("함정 간파", "겉으로 맞아 보이는 선택에서 숨은 제약과 위험을 찾는다.", "diagnose"),
            "duel_preparation": ("결전 준비", "제약과 위험을 고려해 실행 계획을 세운다.", "design"),
            "martial_resolution": ("진상 정리", "누적된 사실과 판단을 종합해 사건의 결론을 정리한다.", "synthesize"),
        },
        "phase_pool": {
            "setup": ("trace_reading", "testimony_check", "manual_decode"),
            "development": ("technique_compare", "flow_analysis", "opponent_method", "strategy_choice"),
            "turn": ("trap_reading", "strategy_choice", "opponent_method", "trace_reading"),
            "resolution": ("duel_preparation", "strategy_choice", "martial_resolution"),
        },
        "final_mode": "martial_resolution",
    },
    "동화": {
        "source_label": "이야기 자료",
        "summary_label": "쉬운 힌트",
        "help_label": "말뜻 도움",
        "step_noun": "발견",
        "interaction_noun": "모험 방식",
        "progress_label": "발견한 사실",
        "review_progress_label": "함께 다시 보고 발견한 사실",
        "conclusion_label": "해결 결과",
        "review_conclusion_label": "함께 다시 보고 얻은 해결 결과",
        "next_label": "다음 모험",
        "prepare_label": "모험 단계 {count}개 준비",
        "spinner_label": "Story와 Curriculum을 연결해 모험 단계 {count}개를 만들고 있습니다...",
        "arc_guidance": "작은 문제 발견 → 길/규칙 찾기 → 친구들의 문제 돕기 → 예상 밖의 변화 → 해결책 모으기 → 세계의 변화와 마무리로 전개한다.",
        "writer_rules": (
            "사용자는 친근한 세계에서 규칙을 발견하고 친구들의 문제를 해결하며 배운 개념을 사용한다. "
            "불필요하게 위협적이거나 시험 같은 분위기를 만들지 않는다. "
            "고양이는 길을 안내하고 작은 변화를 발견하는 동료이며 억지 냥체를 반복하지 않는다."
        ),
        "modes": {
            "gentle_observation": ("작은 변화 발견", "장면의 변화를 관찰해 배울 규칙의 실마리를 찾는다.", "observe"),
            "route_choice": ("길 찾기", "여러 경로의 조건을 비교해 알맞은 길을 고른다.", "strategy"),
            "friend_story": ("친구 이야기 듣기", "여러 설명을 비교해 어떤 도움이 필요한지 판단한다.", "verify"),
            "rule_discovery": ("규칙 발견", "반복되는 패턴에서 핵심 원리를 찾아낸다.", "decode"),
            "sorting_puzzle": ("분류와 정리", "특징에 따라 대상을 비교하고 알맞게 나눈다.", "compare"),
            "cause_effect": ("원인과 결과 잇기", "한 변화가 다음 결과로 이어지는 흐름을 이해한다.", "sequence"),
            "repair_plan": ("고치기 계획", "작은 문제를 안전하게 해결할 방법을 고른다.", "design"),
            "cooperation_choice": ("도움 모으기", "여러 도움/도구 중 상황에 맞는 선택을 한다.", "strategy"),
            "solution_build": ("해결책 완성", "앞에서 배운 규칙과 단서를 모아 해결책을 만든다.", "synthesize"),
            "celebration_resolution": ("세계의 변화", "해결 결과를 정리하고 배운 것이 세계에 만든 변화를 확인한다.", "synthesize"),
        },
        "phase_pool": {
            "setup": ("gentle_observation", "route_choice", "friend_story"),
            "development": ("rule_discovery", "sorting_puzzle", "cause_effect", "repair_plan"),
            "turn": ("cause_effect", "cooperation_choice", "repair_plan", "rule_discovery"),
            "resolution": ("solution_build", "cooperation_choice", "celebration_resolution"),
        },
        "final_mode": "celebration_resolution",
    },
}


def get_learner_level_profile(learner_level: str | None) -> dict[str, str]:
    return LEARNER_LEVEL_PROFILES.get(
        str(learner_level or "초급"),
        LEARNER_LEVEL_PROFILES["초급"],
    )


def get_reasoning_profile(requested_difficulty: str | None) -> dict[str, str]:
    return REASONING_PROFILES.get(
        str(requested_difficulty or "basic"),
        REASONING_PROFILES["basic"],
    )


def get_theme_experience_profile(theme: str | None) -> dict[str, Any]:
    return THEME_EXPERIENCE_PROFILES.get(
        str(theme or "동화"),
        THEME_EXPERIENCE_PROFILES["동화"],
    )


def get_interaction_info(theme: str, mode: str | None) -> dict[str, str]:
    profile = get_theme_experience_profile(theme)
    modes = profile["modes"]
    requested = str(mode or "").strip()

    if requested not in modes:
        requested = next(iter(modes))

    label, goal, pattern = modes[requested]
    return {
        "mode": requested,
        "label": label,
        "goal": goal,
        "pattern": pattern,
        "question_style": (
            f"{label} 행동 안에서 실제 Story 자료를 읽고 학습 Concept를 적용한다."
        ),
    }


def get_story_phase(*, chapter_number: int, target_chapter_count: int) -> str:
    if target_chapter_count <= 1:
        return "resolution"

    progress = chapter_number / target_chapter_count
    if progress <= 0.22:
        return "setup"
    if progress <= 0.52:
        return "development"
    if progress <= 0.80:
        return "turn"
    return "resolution"


def pick_interaction_mode(
    *,
    theme: str,
    chapter_number: int,
    target_chapter_count: int,
    phase: str | None = None,
    avoid: set[str] | None = None,
) -> str:
    profile = get_theme_experience_profile(theme)
    phase = phase or get_story_phase(
        chapter_number=chapter_number,
        target_chapter_count=target_chapter_count,
    )
    avoid = avoid or set()

    final_mode = profile["final_mode"]
    if chapter_number >= target_chapter_count:
        return final_mode

    pool = list(profile["phase_pool"].get(
        phase,
        profile["phase_pool"]["development"],
    ))
    pool = [mode for mode in pool if mode != final_mode] or pool

    start_index = (chapter_number - 1) % len(pool)
    ordered = pool[start_index:] + pool[:start_index]

    for mode in ordered:
        if mode not in avoid:
            return mode
    return ordered[0]


def enrich_interaction_outline(
    chapter_outline: dict[str, Any] | None,
    *,
    theme: str,
    chapter_number: int,
    target_chapter_count: int,
    recent_modes: list[str] | None = None,
) -> dict[str, Any]:
    item = dict(chapter_outline or {})
    phase = str(
        item.get("phase")
        or get_story_phase(
            chapter_number=chapter_number,
            target_chapter_count=target_chapter_count,
        )
    )

    profile = get_theme_experience_profile(theme)
    requested = str(item.get("interaction_mode") or "").strip()
    valid = requested in profile["modes"]
    avoid = {mode for mode in (recent_modes or []) if mode}

    mode = (
        requested
        if valid and requested not in avoid
        else pick_interaction_mode(
            theme=theme,
            chapter_number=chapter_number,
            target_chapter_count=target_chapter_count,
            phase=phase,
            avoid=avoid,
        )
    )

    info = get_interaction_info(theme, mode)
    item["interaction_mode"] = info["mode"]
    item["interaction_label"] = info["label"]
    item["interaction_goal"] = str(
        item.get("interaction_goal") or info["goal"]
    ).strip()
    item["interaction_question_style"] = info["question_style"]
    return item


def get_action_plan(
    *,
    theme: str,
    interaction_mode: str | None,
) -> list[tuple[str, str, str]]:
    info = get_interaction_info(theme, interaction_mode)
    return list(TASK_PATTERNS.get(
        info["pattern"],
        TASK_PATTERNS["observe"],
    ))


def build_theme_planner_rules(
    *,
    theme: str,
    recent_modes: list[str] | None = None,
) -> str:
    profile = get_theme_experience_profile(theme)
    catalog = "\n".join(
        f"- {mode}: {label} · {goal}"
        for mode, (label, goal, _pattern) in profile["modes"].items()
    )
    return f"""
[{theme} Theme Chapter 행동 설계]
각 Chapter에는 interaction_mode와 interaction_goal을 반드시 지정한다.

허용 행동 방식:
{catalog}

Theme 전체 흐름:
{profile['arc_guidance']}

최근 사용 방식:
{recent_modes or []}

규칙:
- 같은 Block 안에서는 가능한 한 서로 다른 interaction_mode를 사용한다.
- 직전 Chapter와 같은 방식을 기계적으로 반복하지 않는다.
- Theme의 표현만 바꾸고 실제 행동은 매번 같은 '로그 조사/증거 찾기'가 되지 않게 한다.
- interaction_goal에는 이번 Chapter에서 사용자가 실제로 무엇을 해내는지 쓴다.
- 전체 마지막 Chapter 전에는 final_mode={profile['final_mode']}를 남발하지 않는다.
"""


def build_theme_writer_rules(theme: str) -> str:
    profile = get_theme_experience_profile(theme)
    return f"""
[{theme} Theme Writer 규칙]
{profile['writer_rules']}
- 이번 interaction_mode가 Story 장면에서 실제 행동으로 드러나야 한다.
- 학습 문제에서 판단해야 할 기술적 정답을 Story 본문에서 미리 확정하지 않는다.
- 현실 학습 Concept의 이름은 그대로 유지하되 Theme 세계의 행동/자료와 자연스럽게 연결한다.
"""


def build_story_pedagogy_rules(learner_level: str) -> str:
    profile = get_learner_level_profile(learner_level)
    return f"""
[학습자 친화 Story 규칙]
선택 수준: {learner_level}
대상: {profile['audience']}
선행지식 가정: {profile['prior_knowledge']}
Story 작성: {profile['story_rule']}
- Story가 학습 전에 전문용어 시험지가 되지 않게 한다.
- 어려운 용어가 필요하면 장면 안에서 짧고 자연스럽게 의미를 알려준다.
"""


def build_question_pedagogy_rules(
    *,
    learner_level: str,
    requested_difficulty: str,
) -> str:
    support = get_learner_level_profile(learner_level)
    reasoning = get_reasoning_profile(requested_difficulty)
    return f"""
[Pedagogy Profile]
사용자가 선택한 현재 수준: {learner_level}
학습 지원 프로필: {support['display_name']}
대상 독자: {support['audience']}
선행지식 가정: {support['prior_knowledge']}

가르치기 규칙:
- {support['brief_rule']}
- {support['source_rule']}
- {support['question_rule']}

현재 적응형 사고 난이도: {requested_difficulty} · {reasoning['label']}
사고 난이도 규칙: {reasoning['rule']}

매우 중요:
- learner_level은 '얼마나 많이 가르쳐주고 설명할지'를 결정한다.
- requested_difficulty는 '방금 배운 내용을 얼마나 깊게 생각하게 할지'를 결정한다.
- 적응형 난이도가 올라가도 입문 사용자의 선행지식을 갑자기 중급자로 가정하지 않는다.
- 입문/초급에서는 먼저 짧게 가르친 뒤 문제를 낸다. 배우기 전에 시험부터 보게 하지 않는다.
"""



def build_curriculum_pedagogy_rules(learner_level: str) -> str:
    profile = get_learner_level_profile(learner_level)

    level_specific = {
        "입문": (
            "Concept sequence의 초반 35~45%는 용어·역할·전체 흐름처럼 선행지식 0에서 시작하는 내용으로 둔다. "
            "첫 몇 Chapter에서 실무 약어, 복잡한 아키텍처, 운영 장애를 핵심 Concept로 한꺼번에 넣지 않는다. "
            "각 Concept는 바로 앞 Concept를 이해하면 다음으로 갈 수 있게 작은 계단으로 설계한다."
        ),
        "초급": (
            "핵심 용어와 기본 흐름을 먼저 정리한 뒤 간단한 적용과 비교로 넘어간다. "
            "복잡한 운영/아키텍처 판단은 후반부로 미룬다."
        ),
        "중급": (
            "기본 개념 복습은 짧게 두고 실제 적용, 진단, 연결 관계를 중심으로 구성한다."
        ),
        "고급": (
            "기본 개념을 빠르게 통과하고 아키텍처, 운영, failure mode, trade-off까지 다룬다."
        ),
    }

    return f"""
[Curriculum 난이도 설계]
선택 수준: {learner_level}
대상: {profile['audience']}
선행지식 가정: {profile['prior_knowledge']}
- {level_specific.get(learner_level, level_specific['초급'])}
- '현재 수준'은 문제 난이도만이 아니라 Concept 순서와 설명 출발점을 결정한다.
- 입문/초급 Curriculum은 이미 알고 있는 지식을 확인하는 복습 코스가 아니라 처음 배우는 사람이 따라갈 수 있는 학습 경로여야 한다.
"""

def get_ui_support_mode(learner_level: str) -> str:
    return get_learner_level_profile(learner_level)["ui_mode"]

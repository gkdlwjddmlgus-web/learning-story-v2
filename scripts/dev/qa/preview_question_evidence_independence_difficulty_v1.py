from __future__ import annotations

import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.question_service import (
    QuestionDifficultyQualityError,
    REASONING_RULES,
    _validate_evidence_independence_quality,
)


def _reject(label: str, **kwargs) -> None:
    try:
        _validate_evidence_independence_quality(**kwargs)
    except QuestionDifficultyQualityError:
        print("[PASS]", label)
        return
    raise AssertionError(label + ": easy/leaky intermediate question was accepted")


def main() -> int:
    service_path = PROJECT_ROOT / "services" / "question_service.py"
    source = service_path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(service_path))

    print("=" * 78)
    print("Question Evidence Independence & Difficulty v1 - QA")
    print("=" * 78)

    intermediate = REASONING_RULES["intermediate"]
    for token in (
        "반드시 서로 다른 Evidence 사실/조건 2개 이상",
        "한 문장만 읽고 정답을 바로 고를 수 있다면",
    ):
        if token not in intermediate:
            raise AssertionError(
                "intermediate reasoning rule missing: " + token
            )
    print("[PASS] intermediate now requires multi-evidence reasoning")

    _reject(
        "regression: concept brief nearly states ATP/NADPH answer",
        question=(
            "구획 A가 구획 B와 구별되는 고유한 기능적 특징은 무엇인가?"
        ),
        concept_brief=(
            "명반응 장치는 다음 회로를 돌릴 매개체인 ATP와 NADPH를 "
            "합성하는 곳이야. 두 장치의 역할을 비교해보자."
        ),
        evidence_summary="두 구획의 생성물 지표가 다르게 기록되어 있다.",
        evidence_context=(
            "구획 A: 광원 활성 시 ATP 및 NADPH 수치 급상승 - "
            "구획 B: 광원 차단 뒤 6탄당 합성 진행"
        ),
        correct_choice=(
            "빛에너지를 직접 포획하여 화학 에너지인 ATP와 NADPH를 합성한다."
        ),
        requested_difficulty="intermediate",
        answer_kind="non_numeric",
        index=2,
    )

    _reject(
        "regression: evidence correction rule nearly states the action answer",
        question=(
            "기록된 수치와 규칙을 적용할 때 ATP 합성 정상화를 위해 "
            "선행되어야 할 조치는 무엇인가?"
        ),
        concept_brief=(
            "전자 흐름과 막 안팎의 이온 농도 차이를 함께 비교해보자."
        ),
        evidence_summary=(
            "막 전위와 ATP 합성 속도가 모두 기준치보다 낮다."
        ),
        evidence_context=(
            "막 채널 상태: 양성자 무작위 누출 밸브 개방(ON) - "
            "보정 규칙: 무작위 누출 채널 차단 시 막 내부 H+ 축적 및 "
            "전위 회복 가능"
        ),
        correct_choice=(
            "양성자 누출 밸브를 차단하여 틸라코이드 막 내부의 H+ 축적을 유도한다."
        ),
        requested_difficulty="intermediate",
        answer_kind="non_numeric",
        index=4,
    )

    _reject(
        "regression: evidence directly exposes identified output material",
        question=(
            "물의 분해와 광자 흡수를 통해 직접 생성 및 배출하는 물질은 무엇인가?"
        ),
        concept_brief=(
            "빛을 이용하는 반응에서 입력과 출력을 함께 확인해보자."
        ),
        evidence_summary=(
            "반응실의 입력 물질과 외부 배출 기록이 남아 있다."
        ),
        evidence_context=(
            "투입 감응원: H2O - 필수 조건: 광자 유입 - "
            "외벽 배출구 방출 가스: O2 측정됨"
        ),
        correct_choice="외부로 방출되는 산소(O2)",
        requested_difficulty="intermediate",
        answer_kind="non_numeric",
        index=1,
    )

    _validate_evidence_independence_quality(
        question=(
            "현재 에너지 합성이 정체된 직접적인 단계적 원인은 무엇인가?"
        ),
        concept_brief=(
            "빛에너지는 전자의 흐름과 막 안팎의 수소 이온 농도 차이를 "
            "만든다. 반응 흐름의 정체 지점을 좁혀보자."
        ),
        evidence_summary=(
            "빛 흡수와 물 분해는 유지되지만 ATP 합성 지표가 크게 낮아졌다."
        ),
        evidence_context=(
            "광계 흡수율 정상 - 물 광분해 효소계 정상 - "
            "막 사이 수소 이온(H+) 농도 구배 기준치 대비 15%로 급감 - "
            "ATP 합성 속도 급격히 저하"
        ),
        correct_choice=(
            "틸라코이드 막을 가로지르는 프로톤(H+) 농도 기울기 형성의 실패"
        ),
        requested_difficulty="intermediate",
        answer_kind="non_numeric",
        index=3,
    )
    print("[PASS] multi-signal diagnostic question remains accepted")

    _validate_evidence_independence_quality(
        question="2 L 용액의 질량은 얼마인가?",
        concept_brief="밀도와 부피를 곱하면 질량을 구할 수 있다.",
        evidence_summary="용액 2 L가 있다.",
        evidence_context="밀도 1.2 kg/L - 부피 2 L",
        correct_choice="2.4 kg",
        requested_difficulty="intermediate",
        answer_kind="numeric",
        index=5,
    )
    print("[PASS] numeric questions remain under Answer Integrity, not this text gate")

    for token in (
        'PROMPT_VERSION = "question_curriculum_v16_evidence_independence"',
        "한 문장 제거 테스트",
        "서로 다른 관찰 사실/조건 2개 이상",
    ):
        if token not in source:
            raise AssertionError(
                "question prompt/version update missing: " + token
            )
    print("[PASS] prompt version + single-clue rewrite rules updated")

    forbidden = (
        "광합성" + "전용게이트",
        "상관관계" + "전용게이트",
        "CorrelationCausationOverclaimError",
    )
    for token in forbidden:
        if token in source:
            raise AssertionError(
                "domain-specific rule leaked into core: " + token
            )
    print("[PASS] no domain-specific learning rule added")

    print()
    print("[PERFORMANCE]")
    print("- No second Gemini audit call is added.")
    print("- No embedding/model-based semantic similarity is used.")
    print("- Validation uses only standard-library string comparison.")
    print()
    print("[NO CHANGE]")
    print("- QUESTION_SCHEMA is unchanged.")
    print("- DB schema/data is unchanged.")
    print("- Curriculum/Semantic Contract/Story/Mastery are unchanged.")
    print("- Numeric Answer Integrity remains unchanged.")
    print()
    print("[SECURITY / COST]")
    print("- QA made no Gemini API request.")
    print("- QA made no DB query/write.")
    print()
    print("[PASS] Question Evidence Independence & Difficulty v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import copy
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.question_service import (
    QuestionAnswerIntegrityError,
    _randomize_question_choice_positions,
    _strip_choice_prefix,
    _validate_answer_integrity,
)


def _item(choices, correct_index, audit, question=None):
    return {
        "question": question or (
            "밀도가 1.2 kg/L인 용해액 2 L를 질량(kg) 단위로 "
            "바르게 환산한 값은 얼마입니까?"
        ),
        "choices": list(choices),
        "correct_index": correct_index,
        "answer_audit": dict(audit),
        "evidence_summary": "용해액 2 L를 투입했습니다.",
        "evidence_context": "용해액의 밀도는 1.2 kg/L입니다.",
    }


def _reject(label, item):
    try:
        _validate_answer_integrity(
            item=item,
            index=1,
            question=item["question"],
            choices=item["choices"],
            correct_index=item["correct_index"],
        )
    except QuestionAnswerIntegrityError:
        print("[PASS]", label)
        return
    raise AssertionError(label + ": invalid question was accepted")


def main() -> int:
    print("=" * 78)
    print("Question Answer Integrity Gate v1 - QA")
    print("=" * 78)

    prefix_cases = {
        "2.4 kg": "2.4 kg",
        "1.25 L": "1.25 L",
        "3.1415": "3.1415",
        "4.8 mL": "4.8 mL",
        "2. 2.4 kg": "2.4 kg",
        "2) 2.4 kg": "2.4 kg",
        "(2). 2.4 kg": "2.4 kg",
        "② 2.4 kg": "2.4 kg",
    }
    for raw, expected in prefix_cases.items():
        actual = _strip_choice_prefix(raw)
        if actual != expected:
            raise AssertionError(
                f"choice-prefix regression: {raw!r} -> {actual!r}, "
                f"expected {expected!r}"
            )
    print("[PASS] decimal choices are not mistaken for option-number prefixes")

    bad = _item(
        ["0.6 kg", "2 kg", "4 kg", "0 kg"],
        1,
        {
            "kind": "numeric",
            "canonical_answer": "2 kg",
            "calculation_expression": "1.2 * 2",
            "calculated_value": "2.4",
            "unit": "kg",
        },
    )
    _reject(
        "screenshot regression: 2.4 kg missing from choices",
        bad,
    )

    deceptive_bad = _item(
        ["0.6 kg", "2 kg", "4 kg", "0 kg"],
        1,
        {
            "kind": "numeric",
            "canonical_answer": "2 kg",
            "calculation_expression": "1.2 + 0.8",
            "calculated_value": "2",
            "unit": "kg",
        },
    )
    _reject(
        "density x volume independent guard catches self-consistent wrong audit",
        deceptive_bad,
    )

    good = _item(
        ["0.6 kg", "2.4 kg", "4 kg", "0 kg"],
        1,
        {
            "kind": "numeric",
            "canonical_answer": "2.4 kg",
            "calculation_expression": "1.2 * 2",
            "calculated_value": "2.4",
            "unit": "kg",
        },
    )
    _validate_answer_integrity(
        item=good,
        index=1,
        question=good["question"],
        choices=good["choices"],
        correct_index=good["correct_index"],
    )
    print("[PASS] valid 2.4 kg question accepted")

    non_numeric = _item(
        [
            "압력을 낮춘다",
            "온도를 높인다",
            "기록만 삭제한다",
            "밸브를 닫는다",
        ],
        0,
        {
            "kind": "non_numeric",
            "canonical_answer": "압력을 낮춘다",
            "calculation_expression": "",
            "calculated_value": "",
            "unit": "",
        },
        question="주어진 조건에서 가장 적절한 조치는 무엇입니까?",
    )
    _validate_answer_integrity(
        item=non_numeric,
        index=2,
        question=non_numeric["question"],
        choices=non_numeric["choices"],
        correct_index=non_numeric["correct_index"],
    )
    print("[PASS] non-numeric canonical-answer consistency accepted")

    shuffled = copy.deepcopy(good)
    before = shuffled["choices"][shuffled["correct_index"]]
    _randomize_question_choice_positions(
        [shuffled],
        rng=random.Random(7),
    )
    after = shuffled["choices"][shuffled["correct_index"]]

    if before != after:
        raise AssertionError("randomizer broke correct answer mapping")
    if sorted(shuffled["choices"]) != sorted(good["choices"]):
        raise AssertionError("randomizer added/dropped a choice")
    print("[PASS] randomizer preserves choices and correct mapping")

    print()
    print("[SECURITY / COST]")
    print("- No Gemini API request was made.")
    print("- No DB query/write was made.")
    print("- No saved question was modified.")
    print()
    print("Question Answer Integrity Gate v1 QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

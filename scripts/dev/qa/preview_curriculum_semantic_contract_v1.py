from __future__ import annotations

import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.curriculum_service import get_concept_contracts
from services.mock_generation import mock_curriculum


def main() -> int:
    paths = {
        "foundation": PROJECT_ROOT / "services" / "foundation_service.py",
        "curriculum": PROJECT_ROOT / "services" / "curriculum_service.py",
        "question": PROJECT_ROOT / "services" / "question_service.py",
        "mock": PROJECT_ROOT / "services" / "mock_generation.py",
        "learning": PROJECT_ROOT / "ui_tabs" / "learning_tab.py",
    }

    sources = {}
    for name, path in paths.items():
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        sources[name] = source

    print("=" * 78)
    print("Curriculum Semantic Contract v1 - QA")
    print("=" * 78)

    foundation = sources["foundation"]
    for token in (
        '"semantic_contract"',
        '"core_rule"',
        '"common_misconception"',
        '"reasoning_boundary"',
        'CURRICULUM_PROMPT_VERSION = "curriculum_v4_semantic_contract"',
        "특정 분야용 고정 템플릿이 아니다",
    ):
        if token not in foundation:
            raise AssertionError("foundation contract schema/prompt missing: " + token)
    print("[PASS] Curriculum schema + generic semantic-contract prompt")

    mock = mock_curriculum(
        {
            "topic": "범용 테스트 주제",
            "learner_level": "중급",
            "theme": "무협",
        }
    )
    sequence = mock.get("concept_sequence") or []
    if not sequence:
        raise AssertionError("mock curriculum has no concept sequence")
    for item in sequence:
        contract = item.get("semantic_contract")
        if not isinstance(contract, dict):
            raise AssertionError("mock concept has no semantic_contract")
        if not all(
            str(contract.get(key) or "").strip()
            for key in (
                "core_rule",
                "common_misconception",
                "reasoning_boundary",
            )
        ):
            raise AssertionError("mock semantic_contract has empty field")
    print("[PASS] mock Curriculum satisfies semantic-contract shape")

    sample_curriculum = {
        "concept_sequence": [
            {
                "name": "개념 A",
                "order": 1,
                "semantic_contract": {
                    "core_rule": "A 핵심 원리",
                    "common_misconception": "A 대표 오개념",
                    "reasoning_boundary": "A 추론 경계",
                },
            },
            {
                "name": "개념 B",
                "order": 2,
                # legacy-style item: no semantic_contract
            },
            {
                "name": "개념 C",
                "order": 3,
                "semantic_contract": {
                    "core_rule": "C 핵심 원리",
                    "common_misconception": "",
                    "reasoning_boundary": "C 추론 경계",
                },
            },
        ]
    }
    resolved = get_concept_contracts(
        curriculum=sample_curriculum,
        target_concepts=["개념 A", "개념 B", "개념 C"],
    )
    if list(resolved) != ["개념 A"]:
        raise AssertionError(f"legacy/partial fallback failed: {resolved}")
    print("[PASS] resolver returns only complete contracts and skips legacy/partial data")

    question = sources["question"]
    for token in (
        'PROMPT_VERSION = "question_curriculum_v16_evidence_independence"',
        "concept_contracts: dict[str, dict[str, str]] | None = None",
        "[Curriculum Semantic Contract]",
        "common_misconception을 정답 논리로 만들지 않는다",
        "reasoning_boundary를 넘어서는",
        "Contract가 없는 기존 Curriculum Concept",
    ):
        if token not in question:
            raise AssertionError("question semantic grounding missing: " + token)
    print("[PASS] Question Generator accepts optional contracts + semantic grounding")

    learning = sources["learning"]
    for token in (
        "get_world_foundation",
        "get_concept_contracts",
        "concept_contracts=(",
    ):
        if token not in learning:
            raise AssertionError("learning-tab contract wiring missing: " + token)
    print("[PASS] learning_tab resolves current target contracts through service layer")

    # Core code must not encode the motivating data-analysis misconception.
    migration_specific_forbidden = (
        "CorrelationCausationOverclaimError",
        "_validate_correlation_causation_integrity",
        "CORRELATION_CAUSATION_OVERCLAIM_INTEGRITY_GATE",
    )
    for token in migration_specific_forbidden:
        if token in question:
            raise AssertionError(
                "domain-specific correlation gate leaked into core question service: "
                + token
            )
    print("[PASS] no correlation-specific deterministic gate added to core")

    print()
    print("[COMPATIBILITY]")
    print("- Existing Curricula without semantic_contract fall back safely.")
    print("- No existing Curriculum/Question/Attempt/Mastery rows are rewritten.")
    print("- No DB schema migration is required; Curriculum remains JSONB.")
    print()
    print("[SECURITY / COST]")
    print("- No Gemini API request was made.")
    print("- No DB query/write was made by this QA.")
    print()
    print("[PASS] Curriculum Semantic Contract v1 deterministic QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

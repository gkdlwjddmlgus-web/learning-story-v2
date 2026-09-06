from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui_tabs.learning_tab import _format_choice_reply


def main() -> int:
    print("=" * 78)
    print("Quiz Answer Reply Decimal Hotfix v1.0.1 - QA")
    print("=" * 78)

    cases = [
        (3, "2.4 kg", "3번 · 2.4 kg", "raw decimal choice preserved"),
        (2, "1.25 L", "2번 · 1.25 L", "another decimal preserved"),
        (3, "3. 2.4 kg", "3번 · 2.4 kg", "dot option prefix removed"),
        (3, "3) 2.4 kg", "3번 · 2.4 kg", "paren option prefix removed"),
        (3, "(3) 2.4 kg", "3번 · 2.4 kg", "parenthesized prefix removed"),
        (3, "(3). 2.4 kg", "3번 · 2.4 kg", "parenthesized dot prefix removed"),
        (3, "③ 2.4 kg", "3번 · 2.4 kg", "circled option prefix removed"),
    ]

    for number, raw, expected, label in cases:
        actual = _format_choice_reply(
            choice_number=number,
            choice_text=raw,
        )
        if actual != expected:
            raise AssertionError(
                f"{label}: {raw!r} -> {actual!r}, expected {expected!r}"
            )
        print("[PASS]", label)

    print()
    print("[UNCHANGED]")
    print("- scoring / correct_index")
    print("- Attempt user_answer")
    print("- Mastery / DB")
    print("- Question generation / AI routing")
    print()
    print("Quiz Answer Reply Decimal Hotfix v1.0.1 QA complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations


# DAY6_GENERATED_TEXT_READABILITY_V1_1
def generated_text_readability_css() -> str:
    """
    AI-generated text 공통 가독성 규칙.

    원칙:
    - Python 문자 수 기준 강제 개행을 하지 않는다.
    - 브라우저가 실제 렌더링 폭을 기준으로 줄바꿈한다.
    - 가능한 한 단어/공백 경계를 유지한다.
    - URL/긴 영문 토큰처럼 컨테이너를 넘는 예외만 안전하게 분리한다.
    - 기존 테마별 글자 크기/색/정렬은 최대한 유지한다.
    """
    return r"""
    <style>
    .quest-question,
    .dialogue-text,
    .story-scene-line,
    .story-paragraph {
        word-break: keep-all !important;
        overflow-wrap: break-word !important;
        line-break: strict !important;
        hyphens: none !important;
    }

    .quest-question,
    .dialogue-text,
    .story-paragraph {
        text-wrap: pretty !important;
    }

    .story-scene-line {
        text-wrap: balance !important;
    }

    .dialogue-text {
        white-space: pre-line !important;
    }

    .story-paragraph {
        max-inline-size: 72ch;
    }

    @media (max-width: 760px) {
        .story-paragraph {
            max-inline-size: 100%;
        }
    }
    </style>
    """

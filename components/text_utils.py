import re


def normalize_ai_text(text: str | None) -> str:
    if not text:
        return ""

    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_sentences(text: str) -> list[str]:
    # 문장부호 뒤 공백을 기준으로 분리한다.
    # lookbehind를 쓰지 않아 Python 버전 차이에도 안전하다.
    parts = re.split(r"([.!?。！？])\s+", text)

    sentences = []
    current = ""

    for part in parts:
        if not part:
            continue

        current += part

        if part in ".!?。！？":
            sentences.append(current.strip())
            current = ""

        elif current and not current.endswith((" ", "\n")):
            current += " "

    if current.strip():
        sentences.append(current.strip())

    return sentences


def format_story_markdown(text: str | None) -> str:
    """
    AI 스토리 표시용.

    1) AI가 이미 빈 줄로 문단을 만들었다면 그대로 유지한다.
    2) 문단 구분 없이 한 덩어리로 온 경우에만
       2문장 정도씩 묶어서 화면용 문단을 만든다.
    """
    text = normalize_ai_text(text)

    if not text:
        return ""

    if "\n\n" in text:
        paragraphs = [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ]
        return "\n\n".join(paragraphs)

    one_line = re.sub(r"\n+", " ", text).strip()
    sentences = _split_sentences(one_line)

    if len(sentences) <= 2:
        return one_line

    paragraphs = []
    for i in range(0, len(sentences), 2):
        paragraphs.append(" ".join(sentences[i:i + 2]))

    return "\n\n".join(paragraphs)


def format_inline_text(text: str | None) -> str:
    """
    문제/보기/설명처럼 한 덩어리로 보여야 하는 텍스트는
    불필요한 줄바꿈만 공백으로 정리한다.
    """
    text = normalize_ai_text(text)
    return re.sub(r"\s*\n+\s*", " ", text).strip()

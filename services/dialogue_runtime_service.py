from __future__ import annotations

import re
from dataclasses import dataclass

import streamlit as st

from components.story_cinematic import get_story_cinematic_seen_key
from services.dev_config import is_dialogue_runtime_enabled


# DAY6_DIALOGUE_RUNTIME_SERVICE_V2
# DIALOGUE_SPEAKER_PORTRAIT_INTEGRITY_V1_20260904\n# DIALOGUE_SAME_PARAGRAPH_COMPANION_ACTION_V1_1_20260906

_QUOTE_PATTERN = re.compile(
    r'([“"][^”"\n]+[”"])'
)

_SPEECH_VERB_PATTERN = re.compile(
    r"(말했|말하|대답|물었|외쳤|중얼|속삭|소리쳤|되물었|"
    r"답했|덧붙였|말했다|물었다|대답했다|외쳤다|"
    r"중얼거렸|속삭였|소리쳤다)"
)

_PLAYER_HINT_PATTERN = re.compile(
    r"(당신|사용자|나는|내가|우리는|우리가|주인공)"
)

_NPC_SPEAKER_PATTERN = re.compile(
    r"([가-힣A-Za-z0-9_· -]{1,20})"
    r"(?:이|가|은|는)\s*"
    r"(?:말했|말하|대답|물었|외쳤|중얼|속삭|소리쳤|"
    r"되물었|답했|덧붙였)"
)

_SENTENCE_SPLIT_PATTERN = re.compile(
    r"(?<=[.!?。！？])\s+"
)

MAX_SCENE_CHARS = 170
MAX_SCENE_SENTENCES = 2
_CONTEXT_CHARS = 140


@dataclass(frozen=True)
class DialogueBeat:
    speaker_type: str
    speaker_name: str
    text: str


def _clean_text(value: str | None) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip(),
    ).strip()


def _split_paragraphs(story_text: str) -> list[str]:
    text = str(story_text or "").strip()
    if not text:
        return []

    paragraphs = [
        item.strip()
        for item in re.split(
            r"\n\s*\n+",
            text,
        )
        if item.strip()
    ]

    return paragraphs or [text]


def _strip_quote(value: str) -> str:
    text = str(value or "").strip()
    if (
        len(text) >= 2
        and text[0] in {'"', '“'}
        and text[-1] in {'"', '”'}
    ):
        return text[1:-1].strip()
    return text


def _split_sentences(text: str) -> list[str]:
    clean = _clean_text(text)
    if not clean:
        return []

    sentences = [
        item.strip()
        for item in _SENTENCE_SPLIT_PATTERN.split(clean)
        if item.strip()
    ]

    return sentences or [clean]


def _sentence_count(text: str) -> int:
    return max(
        1,
        len(_split_sentences(text)),
    )


def _split_single_long_sentence(
    text: str,
    *,
    max_chars: int,
) -> list[str]:
    """
    한 문장 자체가 Scene 한도를 넘으면 공백 경계에서만 우선 분절한다.
    공백이 전혀 없는 비정상적으로 긴 토큰만 마지막 수단으로 hard split한다.
    """
    clean = _clean_text(text)
    if len(clean) <= max_chars:
        return [clean]

    words = clean.split()
    if len(words) <= 1:
        return [
            clean[index:index + max_chars]
            for index in range(
                0,
                len(clean),
                max_chars,
            )
        ]

    chunks: list[str] = []
    current = ""

    for word in words:
        candidate = (
            word
            if not current
            else f"{current} {word}"
        )

        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(word) <= max_chars:
            current = word
            continue

        chunks.extend(
            word[index:index + max_chars]
            for index in range(
                0,
                len(word),
                max_chars,
            )
        )

    if current:
        chunks.append(current)

    return chunks


def _split_for_scene_limit(
    text: str,
    *,
    max_chars: int = MAX_SCENE_CHARS,
    max_sentences: int = MAX_SCENE_SENTENCES,
) -> list[str]:
    """
    1) 문장 경계를 우선한다.
    2) 같은 Scene에 최대 max_sentences 문장까지만 묶는다.
    3) max_chars를 넘기지 않는다.
    4) 한 문장이 max_chars보다 길 때만 공백 경계로 추가 분절한다.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return []

    atomic: list[str] = []

    for sentence in sentences:
        atomic.extend(
            _split_single_long_sentence(
                sentence,
                max_chars=max_chars,
            )
        )

    chunks: list[str] = []
    current_parts: list[str] = []

    for part in atomic:
        candidate_parts = [
            *current_parts,
            part,
        ]
        candidate = " ".join(candidate_parts)

        if (
            current_parts
            and (
                len(candidate) > max_chars
                or len(candidate_parts) > max_sentences
            )
        ):
            chunks.append(
                " ".join(current_parts)
            )
            current_parts = [part]
            continue

        current_parts = candidate_parts

    if current_parts:
        chunks.append(
            " ".join(current_parts)
        )

    return [
        _clean_text(chunk)
        for chunk in chunks
        if _clean_text(chunk)
    ]


def _is_guide_vocative(
    text: str,
    guide_name: str | None,
) -> bool:
    """
    '루루, ...'처럼 고양이 이름을 불러 시작하는 문장은
    고양이가 말하는 것이 아니라 Player가 고양이에게 하는 말로 본다.
    """
    clean = _clean_text(text)
    guide = _clean_text(guide_name)

    if not clean or not guide:
        return False

    return bool(
        re.match(
            rf"^{re.escape(guide)}\s*[,，]\s*\S+",
            clean,
        )
    )


def _is_guide_action_narration(
    text: str,
    guide_name: str | None,
) -> bool:
    """
    '루루가 ~했다', '루루는 ~했다'는 대사가 아니라 Narrator 서술이다.
    """
    clean = _clean_text(text)
    guide = _clean_text(guide_name)

    if not clean or not guide:
        return False

    return bool(
        re.match(
            rf"^{re.escape(guide)}(?:이|가|은|는)\b",
            clean,
        )
    )


def _previous_paragraph_guide_focus(
    text: str,
    guide_name: str | None,
) -> bool:
    """
    바로 앞 문단의 마지막 문장이 Companion을 중심으로 끝났는지 보수적으로 확인한다.

    용도:
    루루가 고개를 갸웃했다.

    “이 흐름이 조금 묘해.”

    처럼 행동 서술과 직접 대사가 문단 경계로 분리된 경우에만
    다음 따옴표 문장을 Companion 대사로 이어준다.
    """
    clean = _clean_text(text)
    guide = _clean_text(guide_name)

    if not clean or not guide:
        return False

    sentences = _split_sentences(clean)
    last = sentences[-1] if sentences else clean

    return bool(
        re.match(
            rf"^(?:(?:그리고|그러자|그때|잠시 후|잠시|곧|이내)\s+)?"
            rf"{re.escape(guide)}(?:이|가|은|는)\s*",
            last,
        )
    )

def _same_paragraph_guide_action_focus(
    text: str,
    guide_name: str | None,
) -> bool:
    """
    같은 문단에서 직접 대사 바로 앞 서술의 마지막 문장이
    Companion을 문법적 주체로 두는 행동 서술인지 보수적으로 확인한다.

    예:
    소리 없이 다가온 무무가 먹물이 번진 난을 꼬리로 가리켰다.
    “서첩과 장부의 기록이 군데군데 맞지 않네.”

    앞 서술은 Narrator beat로 유지하고,
    이어지는 quote만 Companion beat로 분리한다.
    """
    clean = _clean_text(text)
    guide = _clean_text(guide_name)

    if not clean or not guide:
        return False

    sentences = _split_sentences(clean)
    last = sentences[-1] if sentences else clean

    guide_subject = re.search(
        rf"(?<![가-힣A-Za-z0-9_·])"
        rf"{re.escape(guide)}(?:이|가|은|는)\b",
        last,
    )
    if not guide_subject:
        return False

    prefix = last[:guide_subject.start()]
    if re.search(
        r"(?:나는|내가|우리는|우리가|"
        r"당신은|당신이|사용자는|사용자가|"
        r"주인공은|주인공이)",
        prefix,
    ):
        return False

    return True


def _speaker_from_quote_context(
    *,
    quote_text: str,
    previous_text: str,
    next_text: str,
    guide_name: str | None,
    previous_paragraph_text: str = "",
) -> tuple[str, str]:
    """
    따옴표 대사의 화자를 판정한다.

    우선순위:
    1. 같은 문단의 명시적 Player 발화 표지 -> Player
    2. 같은 문단의 이름 + 발화 동사 -> Companion/NPC
    3. 같은 문단에 Companion 이름 + 발화 동사 -> Companion
    4. 문단 시작 따옴표이고 직전 문단 마지막 문장이 Companion 중심 행동이면 -> Companion
    5. 불명확 -> Narrator

    Agency Gate 정합성:
    - 단순히 '루루, ...'라고 시작한다는 이유만으로 Player 대사로 추정하지 않는다.
    - Player는 명시적 발화 attribution이 있을 때만 legacy 호환으로 분류한다.
    """
    previous = _clean_text(previous_text)[-_CONTEXT_CHARS:]
    following = _clean_text(next_text)[:_CONTEXT_CHARS]
    context = _clean_text(
        f"{previous} {following}"
    )
    guide = _clean_text(guide_name)

    if (
        _PLAYER_HINT_PATTERN.search(context)
        and _SPEECH_VERB_PATTERN.search(context)
    ):
        return "player", "나"

    match = _NPC_SPEAKER_PATTERN.search(
        context
    )
    if match:
        speaker = _clean_text(
            match.group(1)
        )
        speaker = re.sub(
            r"^(그리고|그러자|그때|잠시|곧|이내)\s+",
            "",
            speaker,
        ).strip()

        if speaker:
            if (
                guide
                and (
                    speaker == guide
                    or speaker.endswith(" " + guide)
                )
            ):
                return "companion", guide
            return "npc", speaker

    if _same_paragraph_guide_action_focus(
        previous_text,
        guide,
    ):
        return "companion", guide

    if (
        guide
        and guide in context
        and _SPEECH_VERB_PATTERN.search(context)
    ):
        return "companion", guide

    if _previous_paragraph_guide_focus(
        previous_paragraph_text,
        guide,
    ):
        return "companion", guide

    return "narrator", "NARRATOR"



def _classify_plain_sentence(
    *,
    sentence: str,
    guide_name: str | None,
) -> tuple[str, str]:
    """
    따옴표 밖의 일반 Story 문장은 Narrator로 유지한다.

    Agency Gate 정합성:
    - '루루, ...' 같은 호격만 보고 Player 발화로 추정하지 않는다.
    - '루루가/루루는 ~했다'는 Companion 행동을 서술하는 Narrator 문장이다.
    - 명시적 직접 대사는 _speaker_from_quote_context에서만 화자를 판정한다.
    """
    clean = _clean_text(sentence)

    if not clean:
        return "narrator", "NARRATOR"

    if _is_guide_action_narration(
        clean,
        guide_name,
    ):
        return "narrator", "NARRATOR"

    return "narrator", "NARRATOR"



def _append_beat(
    beats: list[DialogueBeat],
    *,
    speaker_type: str,
    speaker_name: str,
    text: str,
) -> None:
    """
    Scene 길이 제한을 지키면서 같은 화자의 인접 Beat는 가능한 범위에서만 병합한다.
    """
    for chunk in _split_for_scene_limit(
        text
    ):
        if (
            beats
            and beats[-1].speaker_type == speaker_type
            and beats[-1].speaker_name == speaker_name
        ):
            previous = beats[-1]
            candidate = _clean_text(
                f"{previous.text} {chunk}"
            )

            if (
                len(candidate) <= MAX_SCENE_CHARS
                and _sentence_count(candidate)
                <= MAX_SCENE_SENTENCES
            ):
                beats[-1] = DialogueBeat(
                    speaker_type=previous.speaker_type,
                    speaker_name=previous.speaker_name,
                    text=candidate,
                )
                continue

        beats.append(
            DialogueBeat(
                speaker_type=speaker_type,
                speaker_name=speaker_name,
                text=chunk,
            )
        )


def _append_plain_text_beats(
    beats: list[DialogueBeat],
    *,
    text: str,
    guide_name: str | None,
) -> None:
    for sentence in _split_sentences(
        text
    ):
        speaker_type, speaker_name = (
            _classify_plain_sentence(
                sentence=sentence,
                guide_name=guide_name,
            )
        )

        _append_beat(
            beats,
            speaker_type=speaker_type,
            speaker_name=speaker_name,
            text=sentence,
        )


def build_dialogue_beats(
    *,
    story_text: str,
    guide_name: str | None,
) -> list[DialogueBeat]:
    """
    Existing plain-text Story를 Dialogue Beat로 변환한다.

    Speaker / Portrait Integrity v1:
    1. 같은 문단의 명시적 attribution을 최우선한다.
    2. 문단이 직접 대사로 시작하고 바로 앞 문단의 마지막 문장이
       Companion 중심 행동이면 그 대사를 Companion으로 이어준다.
    3. 단순 호격만으로 Player를 추정하지 않는다.
    4. 불명확한 직접 대사는 Narrator로 둔다.
    5. 기존 Scene 길이 제한과 원문 보존 규칙을 유지한다.

    원문/DB/AI Prompt를 수정하거나 재생성하지 않는다.
    """
    beats: list[DialogueBeat] = []
    paragraphs = _split_paragraphs(
        story_text
    )

    for paragraph_index, paragraph in enumerate(
        paragraphs
    ):
        parts = _QUOTE_PATTERN.split(
            paragraph
        )

        for index, part in enumerate(parts):
            if not part or not part.strip():
                continue

            is_quote = (
                part[0] in {'"', '“'}
                and part[-1] in {'"', '”'}
            )

            if not is_quote:
                _append_plain_text_beats(
                    beats,
                    text=part,
                    guide_name=guide_name,
                )
                continue

            previous_text = (
                parts[index - 1]
                if index > 0
                else ""
            )
            next_text = (
                parts[index + 1]
                if index + 1 < len(parts)
                else ""
            )

            # Cross-paragraph attribution은 따옴표가 현재 문단의 첫 실질 내용일 때만 허용한다.
            # 같은 문단 앞쪽에 서술이 있으면 그 local context가 더 강한 근거다.
            previous_paragraph_text = ""
            if (
                paragraph_index > 0
                and not _clean_text(previous_text)
            ):
                previous_paragraph_text = (
                    paragraphs[paragraph_index - 1]
                )

            quote_text = _strip_quote(
                part
            )

            speaker_type, speaker_name = (
                _speaker_from_quote_context(
                    quote_text=quote_text,
                    previous_text=previous_text,
                    next_text=next_text,
                    guide_name=guide_name,
                    previous_paragraph_text=previous_paragraph_text,
                )
            )

            _append_beat(
                beats,
                speaker_type=speaker_type,
                speaker_name=speaker_name,
                text=quote_text,
            )

    if not beats:
        clean_story = _clean_text(
            story_text
        )
        if clean_story:
            _append_beat(
                beats,
                speaker_type="narrator",
                speaker_name="NARRATOR",
                text=clean_story,
            )

    return beats



def dialogue_index_key(chapter_id: int) -> str:
    return f"_dialogue_runtime_v1_index_{int(chapter_id)}"


def should_render_dialogue_story(
    *,
    chapter_id: int,
    story_text: str,
) -> bool:
    if not is_dialogue_runtime_enabled():
        return False

    if not str(story_text or "").strip():
        return False

    seen_key = get_story_cinematic_seen_key(chapter_id)
    return not bool(st.session_state.get(seen_key))


def mark_dialogue_story_seen(chapter_id: int) -> None:
    st.session_state[get_story_cinematic_seen_key(chapter_id)] = True

    index_key = dialogue_index_key(chapter_id)
    if index_key in st.session_state:
        del st.session_state[index_key]

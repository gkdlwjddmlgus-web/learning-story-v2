from __future__ import annotations

import uuid

import streamlit as st

from repositories.event_repository import insert_events


BUFFER_KEY = "_analytics_event_buffer"
SESSION_ID_KEY = "_analytics_session_id"


def get_session_id() -> str:
    if SESSION_ID_KEY not in st.session_state:
        st.session_state[
            SESSION_ID_KEY
        ] = uuid.uuid4().hex

    return st.session_state[
        SESSION_ID_KEY
    ]


def queue_event(
    event_type: str,
    *,
    user_id: int | None = None,
    world_id: int | None = None,
    story_arc_id: int | None = None,
    chapter_id: int | None = None,
    metadata: dict | None = None,
    flush: bool = False,
) -> None:
    """
    Analytics Event는 진행에 필요한 Critical Data가 아니다.
    따라서 저장 실패가 사용자 흐름을 막지 않도록 best-effort로 처리한다.
    """
    buffer = st.session_state.setdefault(
        BUFFER_KEY,
        [],
    )

    buffer.append(
        {
            "user_id": user_id,
            "world_id": world_id,
            "story_arc_id": story_arc_id,
            "chapter_id": chapter_id,
            "session_id": get_session_id(),
            "event_type": event_type,
            "metadata": metadata or {},
        }
    )


    if flush or len(buffer) >= 6:
        flush_events()



def flush_events() -> None:
    buffer = st.session_state.get(
        BUFFER_KEY,
        [],
    )

    if not buffer:
        return

    pending = list(buffer)


    try:
        insert_events(
            pending
        )
    except Exception as exc:
        # Analytics 저장 실패 때문에 Story/학습이 멈추면 안 된다.
        return


    st.session_state[
        BUFFER_KEY
    ] = []



def queue_once(
    key: str,
    event_type: str,
    **kwargs,
) -> None:
    session_key = (
        f"_event_once_{key}"
    )

    if st.session_state.get(
        session_key
    ):
        return

    queue_event(
        event_type,
        **kwargs,
    )

    st.session_state[
        session_key
    ] = True

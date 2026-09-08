from __future__ import annotations

import streamlit as st

from repositories.chapter_repository import (
    get_chapter,
)


_CACHE_PREFIX = "_v3_chapter_runtime"


def _cache_key(
    *,
    world_id: int,
    chapter_number: int,
) -> str:
    return (
        f"{_CACHE_PREFIX}:"
        f"{int(world_id)}:"
        f"{int(chapter_number)}"
    )


def get_runtime_chapter(
    *,
    world_id: int,
    chapter_number: int,
):
    # Session-scoped current Chapter snapshot.
    # Ordinary Streamlit full reruns reuse the same World/Chapter value.
    # Chapter mutation boundaries explicitly invalidate this cache.
    # None is cached too; successful generation clears the World cache.
    key = _cache_key(
        world_id=world_id,
        chapter_number=chapter_number,
    )

    if key not in st.session_state:
        st.session_state[key] = get_chapter(
            world_id=world_id,
            chapter_number=chapter_number,
        )

    return st.session_state[key]


def invalidate_runtime_chapter(
    *,
    world_id: int,
    chapter_number: int,
) -> None:
    key = _cache_key(
        world_id=world_id,
        chapter_number=chapter_number,
    )
    st.session_state.pop(
        key,
        None,
    )


def invalidate_runtime_world(
    world_id: int,
) -> None:
    prefix = (
        f"{_CACHE_PREFIX}:"
        f"{int(world_id)}:"
    )

    for key in list(
        st.session_state.keys()
    ):
        if str(key).startswith(
            prefix
        ):
            del st.session_state[key]

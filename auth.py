from __future__ import annotations

import hashlib
import os

from repositories.user_repository import (
    create_user,
    get_user_by_username,
)


PBKDF2_ITERATIONS = 200_000


def _hash_password(
    password: str,
    salt: bytes,
) -> str:
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )

    return hashed.hex()


def register_user(
    username: str,
    display_name: str,
    password: str,
):
    username = username.strip()
    display_name = display_name.strip()

    if not username:
        return False, "아이디를 입력해주세요."

    if not password:
        return False, "비밀번호를 입력해주세요."

    # 1차 사용자 친화적 사전 확인
    if get_user_by_username(
        username
    ):
        return (
            False,
            "이미 존재하는 아이디입니다.",
        )

    salt = os.urandom(16)

    password_hash = _hash_password(
        password,
        salt,
    )

    # 2차 DB-level 충돌 방어:
    # 조회 직후 다른 요청이 동일 username을 먼저 생성해도
    # raw UniqueViolation 대신 None을 받는다.
    user_id = create_user(
        username=username,
        display_name=(
            display_name
            or username
        ),
        password_hash=password_hash,
        password_salt=salt.hex(),
    )

    if user_id is None:
        return (
            False,
            "이미 존재하는 아이디입니다.",
        )

    return True, user_id


def login_user(
    username: str,
    password: str,
):
    username = username.strip()

    user = get_user_by_username(
        username
    )

    if not user:
        return (
            False,
            "아이디 또는 비밀번호가 올바르지 않습니다.",
        )

    (
        user_id,
        username,
        display_name,
        stored_hash,
        stored_salt,
    ) = user

    salt = bytes.fromhex(
        stored_salt
    )

    input_hash = _hash_password(
        password,
        salt,
    )

    if input_hash != stored_hash:
        return (
            False,
            "아이디 또는 비밀번호가 올바르지 않습니다.",
        )

    return True, {
        "user_id": user_id,
        "username": username,
        "display_name": display_name,
    }

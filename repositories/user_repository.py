from __future__ import annotations

from db import get_pool


def get_user_by_username(
    username: str,
):
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    id,
                    username,
                    display_name,
                    password_hash,
                    password_salt
                from public.v2_app_users
                where username = %s
                """,
                (username,),
            )

            return cur.fetchone()


def create_user(
    username: str,
    display_name: str,
    password_hash: str,
    password_salt: str,
) -> int | None:
    """
    사용자를 생성한다.

    username 중복 시 PostgreSQL 예외를 그대로 노출하지 않고
    None을 반환한다.
    """
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.v2_app_users (
                    username,
                    display_name,
                    password_hash,
                    password_salt
                )
                values (%s, %s, %s, %s)
                on conflict (username)
                do nothing
                returning id
                """,
                (
                    username,
                    display_name,
                    password_hash,
                    password_salt,
                ),
            )

            row = cur.fetchone()

        conn.commit()

    if row is None:
        return None

    return row[0]

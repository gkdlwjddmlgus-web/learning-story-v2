from __future__ import annotations

import streamlit as st
from psycopg_pool import ConnectionPool


@st.cache_resource
def get_pool() -> ConnectionPool:
    database_url = st.secrets["DATABASE_URL"]

    return ConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=4,
        timeout=10,
        max_idle=300,
    )


def test_connection() -> dict:
    pool = get_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    current_database(),
                    current_user,
                    now()
                """
            )
            row = cur.fetchone()

    return {
        "database": row[0],
        "user": row[1],
        "server_time": row[2],
    }
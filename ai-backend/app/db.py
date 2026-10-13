from __future__ import annotations
import os
from contextvars import ContextVar
from typing import Any
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_user_id: ContextVar[str|None] = ContextVar("plc_user_id", default=None)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://plc:plc@localhost:5432/plc")
pool = ConnectionPool(
    DATABASE_URL,
    kwargs={"row_factory": dict_row},
    open=True,
)

def open_pool():
    pass

def set_user(user_id: str):
    if not user_id:
        raise ValueError("Authenticated user id is required")
    return _user_id.set(str(user_id))

def user_id() -> str:
    value = _user_id.get()
    if not value:
        raise RuntimeError("No authenticated user context")
    return value

def reset(token): _user_id.reset(token)


def execute(sql: str, params=()):
    open_pool()
    with pool.connection() as conn:
        with conn.transaction():
            conn.execute(
                "SELECT set_config('app.user_id', %s, true)",
                (user_id(),),
            )
            with conn.cursor() as cur:
                cur.execute(sql, params)


def fetchone(sql: str, params=()):
    open_pool()
    with pool.connection() as conn:
        with conn.transaction():
            conn.execute(
                "SELECT set_config('app.user_id', %s, true)",
                (user_id(),),
            )
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()


def fetchall(sql: str, params=()):
    open_pool()
    with pool.connection() as conn:
        with conn.transaction():
            conn.execute(
                "SELECT set_config('app.user_id', %s, true)",
                (user_id(),),
            )
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

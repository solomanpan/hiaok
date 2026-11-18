"""Alembic (async). Config lives in pyproject.toml [tool.alembic]; the URL comes from DB_MASTER_URL.

uv run alembic upgrade head
uv run alembic revision --autogenerate -m "add xxx"
"""

import asyncio
import logging

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

import src.infrastructure.do  # noqa: F401  (registers every table)
from src.application.config import DatabaseConfig
from src.infrastructure.database import Base

logging.basicConfig(level=logging.INFO, format="%(levelname)-5.5s [%(name)s] %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

target_metadata = Base.metadata
# migrations always hit master; override with: alembic -x url=postgresql+asyncpg://... upgrade head
URL = context.get_x_argument(as_dictionary=True).get("url") or DatabaseConfig().master_url


def run_migrations_offline() -> None:
    """``alembic upgrade head --sql`` -> print DDL instead of executing it."""
    context.configure(url=URL, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(URL, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())

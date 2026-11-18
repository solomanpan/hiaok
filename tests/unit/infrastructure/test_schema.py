"""Schema guards that need no database (PostgreSQL dialect compilation + Alembic offline mode)."""

import subprocess
import sys
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.dialects import postgresql

import src.infrastructure.do  # noqa: F401  (registers every table)
from src.infrastructure.database.base import Base

ROOT = Path(__file__).resolve().parents[3]


def test_every_update_sets_update_time_without_trigger():
    """PostgreSQL never refreshes update_time on its own: SQLAlchemy must add it to each UPDATE."""
    for table in Base.metadata.sorted_tables:
        sql = str(update(table).values(state=1).compile(dialect=postgresql.dialect()))
        assert "update_time=now()" in sql, table.name


def test_migration_creates_no_trigger():
    sql = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "CREATE TABLE" in sql
    assert "TRIGGER" not in sql.upper()


def test_db_properties_doc_is_up_to_date():
    import importlib.util

    spec = importlib.util.spec_from_file_location("gen_db_doc", ROOT / "scripts" / "gen_db_doc.py")
    assert spec and spec.loader
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)

    actual = (ROOT / "db.properties.md").read_text(encoding="utf-8")
    assert actual == gen.render(), "db.properties.md is stale: run `uv run python scripts/gen_db_doc.py`"

"""Regenerate ``db.properties.md`` (full PostgreSQL DDL) from the Alembic migrations.

    uv run python scripts/gen_db_doc.py

Uses Alembic offline mode (``alembic upgrade head --sql``): no database connection is needed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "db.properties.md"

HEADER = """# 数据库结构（PostgreSQL DDL）

> 本文件由 `scripts/gen_db_doc.py` 根据 Alembic 迁移自动生成（`alembic upgrade head --sql`），
> 修改表结构后请重新执行 `uv run python scripts/gen_db_doc.py`，**不要手改**。
> 迁移版本：`{revision}`

## 约定

- 每张表都有公共列：`id`（自增主键）、`org_uuid`、`create_time`、`update_time`、`description`、
  `state`（0 有效 / 1 无效）、`remark`、`opr`（操作人）、`delete_flag`（0 未删除 / 1 已删除，软删除）。
- 唯一约束均为**部分唯一索引** `WHERE delete_flag = 0`：软删除后编码可以再次使用。
- **不使用 trigger。** `create_time` / `update_time` 在 INSERT 时由 `DEFAULT now()` 填充；
  PostgreSQL 没有 MySQL 的 `ON UPDATE CURRENT_TIMESTAMP`，UPDATE 时不会自动刷新 `update_time`，
  因此由应用层负责：SQLAlchemy 的 `onupdate=func.now()` 会在每条 UPDATE 中写入 `update_time = now()`。
  **绕过 SQLAlchemy 直接执行的 UPDATE 语句需要自己写 `update_time = now()`。**

## 一次性执行

下面各表的 SQL 按依赖顺序排列，可以直接整体执行（建议包在一个事务里）。

"""


def offline_sql() -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def table_of(stmt: str) -> str | None:
    patterns = (
        r"^CREATE TABLE \"?(\w+)\"?",
        r"^CREATE (?:UNIQUE )?INDEX \w+ ON \"?(\w+)\"?",
        r"^COMMENT ON TABLE \"?(\w+)\"?",
        r"^COMMENT ON COLUMN \"?(\w+)\"?\.",
    )
    for p in patterns:
        if m := re.match(p, stmt):
            return m.group(1)
    return None


def render() -> str:
    sql = offline_sql()
    revision = re.search(r"VALUES \('(\w+)'\)", sql)
    statements = [s.strip() for s in sql.split(";\n") if s.strip()]

    order: list[str] = []
    by_table: dict[str, list[str]] = defaultdict(list)
    comments: dict[str, str] = {}
    for stmt in statements:
        stmt = "\n".join(line.rstrip() for line in stmt.splitlines() if not line.startswith("-- Running"))
        stmt = stmt.strip()
        table = table_of(stmt)
        if table is None or table == "alembic_version":
            continue  # BEGIN / COMMIT / alembic bookkeeping
        if table not in by_table:
            order.append(table)
        by_table[table].append(stmt + ";")
        if m := re.match(r"^COMMENT ON TABLE \"?\w+\"? IS '(.*)'", stmt):
            comments[table] = m.group(1)

    parts = [HEADER.format(revision=revision.group(1) if revision else "?")]
    parts.append("| 表 | 说明 |\n|---|---|\n")
    parts.extend(f"| [`{t}`](#{t}) | {comments.get(t, '')} |\n" for t in order)
    for t in order:
        parts.append(f"\n## {t}\n\n{comments.get(t, '')}\n\n```sql\n")
        parts.append("\n\n".join(by_table[t]))
        parts.append("\n```\n")
    return "".join(parts)


def main() -> None:
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

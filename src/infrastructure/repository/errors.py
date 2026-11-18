"""IntegrityError -> DomainError, using the constraint name to say *which* value collided."""

from __future__ import annotations

from functools import cache

from hiaok_core.exception import DomainError
from hiaok_core.factory import ErrorCatalog, ErrorSpec
from sqlalchemy.exc import IntegrityError

from ..database import Base

_UNIQUE_VIOLATION = "23505"


class RepositoryErrors(ErrorCatalog):
    duplicate = ErrorSpec.conflict("duplicate_{columns}", "{what} already exists ({constraint})")


@cache
def _unique_columns() -> dict[str, tuple[str, ...]]:
    out: dict[str, tuple[str, ...]] = {}
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            if index.unique and index.name:
                out[str(index.name)] = tuple(c.name for c in index.columns if c.name != "org_uuid")
    return out


def integrity_to_domain(exc: IntegrityError) -> DomainError | None:
    cause = getattr(exc.orig, "__cause__", None) or exc.orig
    if getattr(cause, "sqlstate", None) != _UNIQUE_VIOLATION:
        return None
    name = str(getattr(cause, "constraint_name", "") or "")
    columns = _unique_columns().get(name, ())
    what = ", ".join(columns) or "value"
    return RepositoryErrors.duplicate(columns="_".join(columns) or "value", what=what, constraint=name)

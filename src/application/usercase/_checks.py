"""Cross-aggregate existence checks shared by usercases."""

from __future__ import annotations

from collections.abc import Iterable

from expression import Error, Ok, Result
from hiaok_core.exception import DomainError, not_found

from ...domain.entity import AggregateRoot
from ..service.base import CrudService


async def ensure_all_exist[A: AggregateRoot](
    service: CrudService[A], org_uuid: str, uuids: Iterable[str]
) -> Result[list[A], DomainError]:
    wanted = set(uuids)
    if not wanted:
        return Ok([])
    found = await service.list_by_uuids(org_uuid, wanted)
    missing = wanted - {a.uuid for a in found}
    if missing:
        return Error(not_found(service.entity, ", ".join(sorted(missing))))
    return Ok(found)


async def ensure_exists[A: AggregateRoot](
    service: CrudService[A], org_uuid: str, uuid: str | None
) -> Result[A | None, DomainError]:
    if uuid is None:
        return Ok(None)
    return (await service.get(org_uuid, uuid)).map(lambda a: a)

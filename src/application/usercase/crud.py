"""Generic CRUD usercases: curried (service, to_model) first, request data last.

usercase = crud_usercases(tenant_service, TenantModel.from_domain)   # partial application
await usercase.create(CreateTenant(...))                            # -> Result[TenantModel, DomainError]
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from expression import Result
from hiaok_core.exception import DomainError
from hiaok_core.fp import AsyncResult, curry

from ...domain.entity import AggregateRoot
from ...domain.repository import Page, PageQuery
from ..model.base import CreateCommand, UpdateCommand
from ..service.base import CrudService


@curry
def create_entity(service: CrudService[Any], to_model: Callable[[Any], Any], cmd: CreateCommand[Any]):
    return AsyncResult.of(service.create(cmd)).map(to_model)


@curry
def get_entity(service: CrudService[Any], to_model: Callable[[Any], Any], org_uuid: str, uuid: str):
    return AsyncResult.of(service.get(org_uuid, uuid)).map(to_model)


@curry
async def list_entities(
    service: CrudService[Any], to_model: Callable[[Any], Any], org_uuid: str | None, page: PageQuery
):
    return (await service.list(org_uuid, page)).map(to_model)


@curry
def update_entity(
    service: CrudService[Any], to_model: Callable[[Any], Any], org_uuid: str, uuid: str, cmd: UpdateCommand[Any]
):
    return AsyncResult.of(service.update(org_uuid, uuid, cmd)).map(to_model)


@curry
def delete_entity(service: CrudService[Any], org_uuid: str, uuid: str):
    return service.delete(org_uuid, uuid)


@dataclass(frozen=True)
class CrudUserCases[M, C, U]:
    create: Callable[[C], Awaitable[Result[M, DomainError]]]
    get: Callable[[str, str], Awaitable[Result[M, DomainError]]]
    list: Callable[[str | None, PageQuery], Awaitable[Page[M]]]
    update: Callable[[str, str, U], Awaitable[Result[M, DomainError]]]
    delete: Callable[[str, str], Awaitable[Result[None, DomainError]]]


def crud_usercases[A: AggregateRoot, M](
    service: CrudService[A], to_model: Callable[[A], M]
) -> CrudUserCases[M, CreateCommand[A], UpdateCommand[A]]:
    return CrudUserCases(
        create=create_entity(service, to_model),
        get=get_entity(service, to_model),
        list=list_entities(service, to_model),
        update=update_entity(service, to_model),
        delete=delete_entity(service),
    )

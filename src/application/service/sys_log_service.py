from __future__ import annotations

from hiaok_core.facade import TransactionManager

from ...domain.entity import SysLog
from ...domain.repository import Page, PageQuery, SysLogRepository
from .datasource import master, slave


class SysLogService:
    def __init__(self, tx: TransactionManager, repository: SysLogRepository) -> None:
        self._tx = tx
        self._repo = repository

    @property
    def tx(self) -> TransactionManager:
        return self._tx

    @master
    async def append(self, log: SysLog) -> None:
        await self._repo.append(log)

    @slave
    async def list(self, org_uuid: str, page: PageQuery, event_type: str | None = None) -> Page[SysLog]:
        return await self._repo.list(org_uuid, page, event_type)

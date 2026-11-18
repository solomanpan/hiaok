from __future__ import annotations

from expression import Ok, Result
from hiaok_core.exception import DomainError, not_found
from hiaok_core.facade import Cache, EventPublisher, IdGenerator, TransactionManager

from ...domain.entity import SysConfig
from ...domain.repository import SysConfigRepository
from ..model import SysConfigModel
from .base import CrudService
from .datasource import slave
from .ids import next_id


def config_cache_key(org_uuid: str, config_key: str) -> str:
    return f"sys_config:{org_uuid}:{config_key}"


class SysConfigService(CrudService[SysConfig]):
    """Read-through cache on ``get_by_key``; the cache entry is evicted after every committed write."""

    entity = "SysConfig"

    def __init__(
        self,
        tx: TransactionManager,
        repository: SysConfigRepository,
        publisher: EventPublisher,
        cache: Cache,
        ttl_seconds: int = 300,
        new_id: IdGenerator = next_id,
    ) -> None:
        super().__init__(tx, repository, publisher, new_id)
        self._configs = repository
        self._cache = cache
        self._ttl = ttl_seconds

    async def get_by_key(self, org_uuid: str, config_key: str) -> Result[SysConfig, DomainError]:
        cached = await self._cache.get(config_cache_key(org_uuid, config_key))
        if cached.is_some():
            return Ok(SysConfigModel.from_json(cached.value).to_domain())
        loaded = await self._load_by_key(org_uuid, config_key)
        if isinstance(loaded, Ok):
            await self._cache.set(
                config_cache_key(org_uuid, config_key), SysConfigModel.from_domain(loaded.ok).to_json(), self._ttl
            )
        return loaded

    @slave
    async def _load_by_key(self, org_uuid: str, config_key: str) -> Result[SysConfig, DomainError]:
        return (await self._configs.find_by_key(org_uuid, config_key)).to_result(not_found("SysConfig", config_key))

    # writes: evict after commit (other nodes are covered by the SysConfigChanged/Entity* event handlers)
    async def save(self, aggregate: SysConfig) -> Result[SysConfig, DomainError]:
        self._evict_after_commit(aggregate)
        return await super().save(aggregate)

    async def remove(self, aggregate: SysConfig) -> Result[None, DomainError]:
        self._evict_after_commit(aggregate)
        return await super().remove(aggregate)

    def _evict_after_commit(self, aggregate: SysConfig) -> None:
        key = config_cache_key(aggregate.org_uuid, aggregate.config_key.value)

        async def evict() -> None:
            await self._cache.delete(key)

        self.tx.current().map(lambda t: t.after_commit(evict))

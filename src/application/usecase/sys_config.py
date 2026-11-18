from __future__ import annotations

from hiaok_core.fp import AsyncResult, curry

from ...domain.repository import PageQuery
from ..model import SysConfigModel, SysLogModel
from ..service import SysConfigService, SysLogService


@curry
def get_config_by_key(configs: SysConfigService, org_uuid: str, config_key: str):
    """Read-through cache (Redis) -> replica."""
    return AsyncResult.of(configs.get_by_key(org_uuid, config_key)).map(SysConfigModel.from_domain)


@curry
async def list_logs(logs: SysLogService, org_uuid: str, page: PageQuery, event_type: str | None = None):
    return (await logs.list(org_uuid, page, event_type)).map(SysLogModel.from_domain)

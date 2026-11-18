from fastapi import APIRouter, Query

from ..dependency import ListLogsDep, PageDep
from ..schema.common import PageResponse
from ..schema.sys_log import SysLogResponse

router = APIRouter(prefix="/orgs/{org_uuid}/logs", tags=["sys_log"])


@router.get("")
async def list_logs(
    org_uuid: str, page: PageDep, uc: ListLogsDep, event_type: str | None = Query(None)
) -> PageResponse[SysLogResponse]:
    """Audit trail written asynchronously by the event consumer (newest first)."""
    return PageResponse.of(await uc(org_uuid, page, event_type), SysLogResponse.of)

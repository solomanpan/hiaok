from fastapi import APIRouter

from ..dependency import ListLogsDep
from ..schema.common import PageResponse
from ..schema.envelope import ApiRequest, ApiResponse
from ..schema.sys_log import SysLogListRequest, SysLogResponse

router = APIRouter(prefix="/log", tags=["sys_log"])


@router.post("/list")
async def list_logs(
    request: ApiRequest[SysLogListRequest], usercase: ListLogsDep
) -> ApiResponse[PageResponse[SysLogResponse]]:
    """Audit trail written asynchronously by the event consumer (newest first)."""
    info = request.req_info
    return ApiResponse.ok(
        PageResponse.of(await usercase(info.org_uuid, info.query, info.event_type), SysLogResponse.of)
    )

from fastapi import APIRouter

from ..dependency import GetCommandOutcomeDep, ListLogsDep
from ..schema.command import CommandOutcomeRequest, CommandOutcomeResponse
from ..schema.common import PageResponse
from ..schema.envelope import ApiRequest, ApiResponse
from ..schema.sys_log import SysLogListRequest, SysLogResponse

router = APIRouter(prefix="/log", tags=["sys_log"])


@router.post("/list")
async def list_logs(
    request: ApiRequest[SysLogListRequest], usecase: ListLogsDep
) -> ApiResponse[PageResponse[SysLogResponse]]:
    """Audit trail written asynchronously by the event consumer (newest first)."""
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase(info.org_uuid, info.query, info.event_type), SysLogResponse.of))


@router.post("/get-by-request")
async def get_command_outcome(
    request: ApiRequest[CommandOutcomeRequest], usecase: GetCommandOutcomeDep
) -> ApiResponse[CommandOutcomeResponse]:
    """Outcome of an asynchronous write, by the ``requestId`` it was submitted with.

    ``pending`` means nothing is recorded yet: not consumed yet, still being retried, or dead-lettered.
    """
    info = request.req_info
    return ApiResponse.ok(CommandOutcomeResponse.of(await usecase(info.org_uuid, info.target_request_id)))

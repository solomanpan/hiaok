from fastapi import APIRouter

from ...application.model import MovePayload
from ..dependency import GroupTreeDep, UserGroupCrudDep, WriteSubmitterDep
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import Keyed, MoveRequest, OrgPageRequest, OrgScoped, PageResponse, TreeNodeResponse
from ..schema.envelope import ApiRequest, ApiResponse, reply
from ..schema.user_group import UserGroupCreateRequest, UserGroupResponse, UserGroupUpdateRequest

router = APIRouter(prefix="/group", tags=["user_group"])


@router.post("/tree")
async def group_tree(
    request: ApiRequest[OrgScoped], usecase: GroupTreeDep
) -> ApiResponse[list[TreeNodeResponse[UserGroupResponse]]]:
    nodes = await usecase(request.req_info.org_uuid)
    return ApiResponse.ok([TreeNodeResponse[UserGroupResponse].of(node, UserGroupResponse.of) for node in nodes])


@router.post("/add")
async def create_user_group(
    request: ApiRequest[UserGroupCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("UserGroup", request.request_id, info.org_uuid, info.to_command()))


@router.post("/list")
async def list_user_groups(
    request: ApiRequest[OrgPageRequest], usecase: UserGroupCrudDep
) -> ApiResponse[PageResponse[UserGroupResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), UserGroupResponse.of))


@router.post("/get")
async def get_user_group(request: ApiRequest[Keyed], usecase: UserGroupCrudDep) -> ApiResponse[UserGroupResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), UserGroupResponse.of)


@router.post("/update")
async def update_user_group(
    request: ApiRequest[UserGroupUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(
        await submitter.update("UserGroup", request.request_id, info.org_uuid, info.uuid, info.to_command())
    )


@router.post("/delete")
async def delete_user_group(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("UserGroup", request.request_id, info.org_uuid, info.uuid))


@router.post("/move")
async def move_group(request: ApiRequest[MoveRequest], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    """Cycle-safe: moving a node under its own subtree fails with ``tree_cycle``."""
    info = request.req_info
    return accepted(
        await submitter.act(
            "UserGroup", "move", request.request_id, info.org_uuid, info.uuid, MovePayload(info.parent_uuid)
        )
    )

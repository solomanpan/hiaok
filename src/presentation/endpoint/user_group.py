from fastapi import APIRouter

from ..dependency import GroupTreeDep, MoveGroupDep, UserGroupCrudDep
from ..schema.common import Keyed, MoveRequest, OrgPageRequest, OrgScoped, PageResponse, TreeNodeResponse
from ..schema.envelope import ApiRequest, ApiResponse, done, reply
from ..schema.user_group import UserGroupCreateRequest, UserGroupResponse, UserGroupUpdateRequest

router = APIRouter(prefix="/group", tags=["user_group"])


@router.post("/tree")
async def group_tree(
    request: ApiRequest[OrgScoped], usercase: GroupTreeDep
) -> ApiResponse[list[TreeNodeResponse[UserGroupResponse]]]:
    nodes = await usercase(request.req_info.org_uuid)
    return ApiResponse.ok([TreeNodeResponse[UserGroupResponse].of(node, UserGroupResponse.of) for node in nodes])


@router.post("/add")
async def create_user_group(
    request: ApiRequest[UserGroupCreateRequest], usercase: UserGroupCrudDep
) -> ApiResponse[UserGroupResponse]:
    return reply(await usercase.create(request.req_info.to_command()), UserGroupResponse.of)


@router.post("/list")
async def list_user_groups(
    request: ApiRequest[OrgPageRequest], usercase: UserGroupCrudDep
) -> ApiResponse[PageResponse[UserGroupResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usercase.list(info.org_uuid, info.query), UserGroupResponse.of))


@router.post("/get")
async def get_user_group(request: ApiRequest[Keyed], usercase: UserGroupCrudDep) -> ApiResponse[UserGroupResponse]:
    info = request.req_info
    return reply(await usercase.get(info.org_uuid, info.uuid), UserGroupResponse.of)


@router.post("/update")
async def update_user_group(
    request: ApiRequest[UserGroupUpdateRequest], usercase: UserGroupCrudDep
) -> ApiResponse[UserGroupResponse]:
    info = request.req_info
    return reply(await usercase.update(info.org_uuid, info.uuid, info.to_command()), UserGroupResponse.of)


@router.post("/delete")
async def delete_user_group(request: ApiRequest[Keyed], usercase: UserGroupCrudDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usercase.delete(info.org_uuid, info.uuid))


@router.post("/move")
async def move_group(request: ApiRequest[MoveRequest], usercase: MoveGroupDep) -> ApiResponse[UserGroupResponse]:
    """Cycle-safe: moving a node under its own subtree is rejected (``tree_cycle``)."""
    info = request.req_info
    return reply(await usercase(info.org_uuid, info.uuid, info.parent_uuid), UserGroupResponse.of)

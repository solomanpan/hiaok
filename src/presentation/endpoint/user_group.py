from fastapi import APIRouter, status

from ..dependency import GroupTreeDep, MoveGroupDep, PageDep, UserGroupCrudDep
from ..exception import unwrap
from ..schema.common import MoveRequest, PageResponse, TreeNodeResponse
from ..schema.user_group import UserGroupCreateRequest, UserGroupResponse, UserGroupUpdateRequest

router = APIRouter(prefix="/orgs/{org_uuid}/groups", tags=["user_group"])


@router.get("/tree", name="group_tree")
async def group_tree(org_uuid: str, uc: GroupTreeDep) -> list[TreeNodeResponse[UserGroupResponse]]:
    return [TreeNodeResponse[UserGroupResponse].of(node, UserGroupResponse.of) for node in await uc(org_uuid)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user_group(org_uuid: str, body: UserGroupCreateRequest, uc: UserGroupCrudDep) -> UserGroupResponse:
    return unwrap(await uc.create(body.to_command(org_uuid)), UserGroupResponse.of)


@router.get("")
async def list_groups(org_uuid: str, page: PageDep, uc: UserGroupCrudDep) -> PageResponse[UserGroupResponse]:
    return PageResponse.of(await uc.list(org_uuid, page), UserGroupResponse.of)


@router.get("/{group_uuid}")
async def get_user_group(org_uuid: str, group_uuid: str, uc: UserGroupCrudDep) -> UserGroupResponse:
    return unwrap(await uc.get(org_uuid, group_uuid), UserGroupResponse.of)


@router.patch("/{group_uuid}")
async def update_user_group(
    org_uuid: str, group_uuid: str, body: UserGroupUpdateRequest, uc: UserGroupCrudDep
) -> UserGroupResponse:
    return unwrap(await uc.update(org_uuid, group_uuid, body.to_command()), UserGroupResponse.of)


@router.delete("/{group_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_group(org_uuid: str, group_uuid: str, uc: UserGroupCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, group_uuid), lambda _: None)


@router.put("/{group_uuid}/parent")
async def move_group(org_uuid: str, group_uuid: str, body: MoveRequest, uc: MoveGroupDep) -> UserGroupResponse:
    """Cycle-safe: moving a node under its own subtree is rejected (422 tree_cycle)."""
    return unwrap(await uc(org_uuid, group_uuid, body.parent_uuid), UserGroupResponse.of)

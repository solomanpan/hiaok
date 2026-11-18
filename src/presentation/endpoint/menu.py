from fastapi import APIRouter

from ...application.model import MovePayload
from ..dependency import MenuCrudDep, MenuTreeDep, WriteSubmitterDep, has_permission
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import Keyed, MoveRequest, OrgPageRequest, OrgScoped, PageResponse, TreeNodeResponse
from ..schema.envelope import ApiRequest, ApiResponse, reply
from ..schema.menu import MenuCreateRequest, MenuResponse, MenuUpdateRequest

router = APIRouter(prefix="/menu", tags=["menu"])


@router.post("/tree", dependencies=[has_permission("menu:tree")])
async def menu_tree(
    request: ApiRequest[OrgScoped], usecase: MenuTreeDep
) -> ApiResponse[list[TreeNodeResponse[MenuResponse]]]:
    nodes = await usecase(request.req_info.org_uuid)
    return ApiResponse.ok([TreeNodeResponse[MenuResponse].of(node, MenuResponse.of) for node in nodes])


@router.post("/add", dependencies=[has_permission("menu:add")])
async def create_menu(
    request: ApiRequest[MenuCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("Menu", request.request_id, info.org_uuid, info.to_command()))


@router.post("/list", dependencies=[has_permission("menu:list")])
async def list_menus(
    request: ApiRequest[OrgPageRequest], usecase: MenuCrudDep
) -> ApiResponse[PageResponse[MenuResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), MenuResponse.of))


@router.post("/get", dependencies=[has_permission("menu:get")])
async def get_menu(request: ApiRequest[Keyed], usecase: MenuCrudDep) -> ApiResponse[MenuResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), MenuResponse.of)


@router.post("/update", dependencies=[has_permission("menu:update")])
async def update_menu(
    request: ApiRequest[MenuUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.update("Menu", request.request_id, info.org_uuid, info.uuid, info.to_command()))


@router.post("/delete", dependencies=[has_permission("menu:delete")])
async def delete_menu(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("Menu", request.request_id, info.org_uuid, info.uuid))


@router.post("/move", dependencies=[has_permission("menu:move")])
async def move_menu(request: ApiRequest[MoveRequest], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    """Cycle-safe: moving a node under its own subtree fails with ``tree_cycle``."""
    info = request.req_info
    return accepted(
        await submitter.act("Menu", "move", request.request_id, info.org_uuid, info.uuid, MovePayload(info.parent_uuid))
    )

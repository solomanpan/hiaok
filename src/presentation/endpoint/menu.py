from fastapi import APIRouter

from ..dependency import MenuCrudDep, MenuTreeDep, MoveMenuDep
from ..schema.common import Keyed, MoveRequest, OrgPageRequest, OrgScoped, PageResponse, TreeNodeResponse
from ..schema.envelope import ApiRequest, ApiResponse, done, reply
from ..schema.menu import MenuCreateRequest, MenuResponse, MenuUpdateRequest

router = APIRouter(prefix="/menu", tags=["menu"])


@router.post("/tree")
async def menu_tree(
    request: ApiRequest[OrgScoped], usercase: MenuTreeDep
) -> ApiResponse[list[TreeNodeResponse[MenuResponse]]]:
    nodes = await usercase(request.req_info.org_uuid)
    return ApiResponse.ok([TreeNodeResponse[MenuResponse].of(node, MenuResponse.of) for node in nodes])


@router.post("/add")
async def create_menu(request: ApiRequest[MenuCreateRequest], usercase: MenuCrudDep) -> ApiResponse[MenuResponse]:
    return reply(await usercase.create(request.req_info.to_command()), MenuResponse.of)


@router.post("/list")
async def list_menus(
    request: ApiRequest[OrgPageRequest], usercase: MenuCrudDep
) -> ApiResponse[PageResponse[MenuResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usercase.list(info.org_uuid, info.query), MenuResponse.of))


@router.post("/get")
async def get_menu(request: ApiRequest[Keyed], usercase: MenuCrudDep) -> ApiResponse[MenuResponse]:
    info = request.req_info
    return reply(await usercase.get(info.org_uuid, info.uuid), MenuResponse.of)


@router.post("/update")
async def update_menu(request: ApiRequest[MenuUpdateRequest], usercase: MenuCrudDep) -> ApiResponse[MenuResponse]:
    info = request.req_info
    return reply(await usercase.update(info.org_uuid, info.uuid, info.to_command()), MenuResponse.of)


@router.post("/delete")
async def delete_menu(request: ApiRequest[Keyed], usercase: MenuCrudDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usercase.delete(info.org_uuid, info.uuid))


@router.post("/move")
async def move_menu(request: ApiRequest[MoveRequest], usercase: MoveMenuDep) -> ApiResponse[MenuResponse]:
    """Cycle-safe: moving a node under its own subtree is rejected (``tree_cycle``)."""
    info = request.req_info
    return reply(await usercase(info.org_uuid, info.uuid, info.parent_uuid), MenuResponse.of)

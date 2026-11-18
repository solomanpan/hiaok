from fastapi import APIRouter, status

from ..dependency import MenuCrudDep, MenuTreeDep, MoveMenuDep, PageDep
from ..exception import unwrap
from ..schema.common import MoveRequest, PageResponse, TreeNodeResponse
from ..schema.menu import MenuCreateRequest, MenuResponse, MenuUpdateRequest

router = APIRouter(prefix="/orgs/{org_uuid}/menus", tags=["menu"])


@router.get("/tree", name="menu_tree")
async def menu_tree(org_uuid: str, uc: MenuTreeDep) -> list[TreeNodeResponse[MenuResponse]]:
    return [TreeNodeResponse[MenuResponse].of(node, MenuResponse.of) for node in await uc(org_uuid)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_menu(org_uuid: str, body: MenuCreateRequest, uc: MenuCrudDep) -> MenuResponse:
    return unwrap(await uc.create(body.to_command(org_uuid)), MenuResponse.of)


@router.get("")
async def list_menus(org_uuid: str, page: PageDep, uc: MenuCrudDep) -> PageResponse[MenuResponse]:
    return PageResponse.of(await uc.list(org_uuid, page), MenuResponse.of)


@router.get("/{menu_uuid}")
async def get_menu(org_uuid: str, menu_uuid: str, uc: MenuCrudDep) -> MenuResponse:
    return unwrap(await uc.get(org_uuid, menu_uuid), MenuResponse.of)


@router.patch("/{menu_uuid}")
async def update_menu(org_uuid: str, menu_uuid: str, body: MenuUpdateRequest, uc: MenuCrudDep) -> MenuResponse:
    return unwrap(await uc.update(org_uuid, menu_uuid, body.to_command()), MenuResponse.of)


@router.delete("/{menu_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu(org_uuid: str, menu_uuid: str, uc: MenuCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, menu_uuid), lambda _: None)


@router.put("/{menu_uuid}/parent")
async def move_menu(org_uuid: str, menu_uuid: str, body: MoveRequest, uc: MoveMenuDep) -> MenuResponse:
    """Cycle-safe: moving a node under its own subtree is rejected (422 tree_cycle)."""
    return unwrap(await uc(org_uuid, menu_uuid, body.parent_uuid), MenuResponse.of)

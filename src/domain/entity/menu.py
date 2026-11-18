from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from expression import Error, Ok, Result, effect
from hiaok_core.exception import DomainError, validation

from ..enum import MenuType
from ..vo import Code, non_blank
from .base import AggregateRoot


@dataclass(frozen=True, kw_only=True)
class Menu(AggregateRoot):
    menu_uuid: str
    menu_code: Code
    menu_name: str
    menu_type: MenuType = MenuType.MENU
    parent_uuid: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    sort_order: int = 0
    visible: bool = True

    @property
    def uuid(self) -> str:
        return self.menu_uuid

    @staticmethod
    def create(
        org_uuid: str,
        menu_uuid: str,
        menu_code: str,
        menu_name: str,
        *,
        menu_type: MenuType = MenuType.MENU,
        parent_uuid: str | None = None,
        path: str | None = None,
        component: str | None = None,
        icon: str | None = None,
        sort_order: int = 0,
        visible: bool = True,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[Menu, DomainError]:
        @effect.result[Menu, DomainError]()
        def build() -> Generator[Any, Any, Menu]:
            code = yield from Code.create(menu_code, "menu_code")
            name = yield from non_blank(menu_name, "menu_name")
            menu = Menu(
                org_uuid=org_uuid,
                menu_uuid=menu_uuid,
                menu_code=code,
                menu_name=name,
                menu_type=MenuType(menu_type),
                parent_uuid=parent_uuid,
                path=path,
                component=component,
                icon=icon,
                sort_order=sort_order,
                visible=visible,
                description=description,
                remark=remark,
            )
            return menu.created()

        return build()

    def update(
        self,
        *,
        menu_name: str | None = None,
        path: str | None = None,
        component: str | None = None,
        icon: str | None = None,
        sort_order: int | None = None,
        visible: bool | None = None,
    ) -> Result[Menu, DomainError]:
        @effect.result[Menu, DomainError]()
        def build() -> Generator[Any, Any, Menu]:
            name = (yield from non_blank(menu_name, "menu_name")) if menu_name is not None else self.menu_name
            return self.changed(
                menu_name=name,
                path=path if path is not None else self.path,
                component=component if component is not None else self.component,
                icon=icon if icon is not None else self.icon,
                sort_order=self.sort_order if sort_order is None else sort_order,
                visible=self.visible if visible is None else visible,
            )

        return build()

    def move_to(self, parent_uuid: str | None) -> Result[Menu, DomainError]:
        if parent_uuid == self.menu_uuid:
            return Error(validation("invalid_parent", "a menu cannot be its own parent"))
        return Ok(self.changed(parent_uuid=parent_uuid))

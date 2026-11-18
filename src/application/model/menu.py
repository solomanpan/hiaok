from __future__ import annotations

from dataclasses import dataclass

from expression import Result
from hiaok_core.exception import DomainError

from ...domain.entity import Menu
from ...domain.enum import MenuType
from ...domain.vo import Code
from .base import CreateMeta, EntityModel, UpdateMeta, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class MenuModel(EntityModel):
    menu_uuid: str
    menu_code: str
    menu_name: str
    menu_type: int = MenuType.MENU
    parent_uuid: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    sort_order: int = 0
    visible: bool = True

    @classmethod
    def from_domain(cls, m: Menu) -> MenuModel:
        return cls(
            **entity_fields(m),
            menu_uuid=m.menu_uuid,
            menu_code=m.menu_code.value,
            menu_name=m.menu_name,
            menu_type=int(m.menu_type),
            parent_uuid=m.parent_uuid,
            path=m.path,
            component=m.component,
            icon=m.icon,
            sort_order=m.sort_order,
            visible=m.visible,
        )

    def to_domain(self) -> Menu:
        return Menu(
            **entity_kwargs(self),
            menu_uuid=self.menu_uuid,
            menu_code=Code(self.menu_code),
            menu_name=self.menu_name,
            menu_type=MenuType(self.menu_type),
            parent_uuid=self.parent_uuid,
            path=self.path,
            component=self.component,
            icon=self.icon,
            sort_order=self.sort_order,
            visible=self.visible,
        )


@dataclass(frozen=True, kw_only=True)
class CreateMenu(CreateMeta):
    org_uuid: str
    menu_code: str
    menu_name: str
    menu_type: int = MenuType.MENU
    parent_uuid: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    sort_order: int = 0
    visible: bool = True

    def to_domain(self, uuid: str) -> Result[Menu, DomainError]:
        return Menu.create(
            self.org_uuid,
            uuid,
            self.menu_code,
            self.menu_name,
            menu_type=MenuType(self.menu_type),
            parent_uuid=self.parent_uuid,
            path=self.path,
            component=self.component,
            icon=self.icon,
            sort_order=self.sort_order,
            visible=self.visible,
            description=self.description,
            remark=self.remark,
        )


@dataclass(frozen=True, kw_only=True)
class UpdateMenu(UpdateMeta):
    menu_name: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    sort_order: int | None = None
    visible: bool | None = None

    def apply_to(self, m: Menu) -> Result[Menu, DomainError]:
        return m.update(
            menu_name=self.menu_name,
            path=self.path,
            component=self.component,
            icon=self.icon,
            sort_order=self.sort_order,
            visible=self.visible,
        ).map(self.apply_meta)

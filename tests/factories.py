"""Test-data factories (polyfactory). Unspecified fields get sensible defaults / unique sequences.

    RoleFactory.build()                                   # a valid, event-free Role
    RoleFactory.build(permission_uuids=frozenset({"p1"}))  # override any field
    PermissionFactory.batch(3)

Factories construct entities directly (trusted, like loading from the database): use the aggregate's
``create`` / ``register`` when the test is *about* validation or recorded events.
"""

from __future__ import annotations

from itertools import count

from polyfactory.factories import DataclassFactory
from polyfactory.fields import Use

from src.domain.entity import Menu, Permission, Role
from src.domain.vo import Code

ORG = "org-1"
TENANT = "tenant-1"
_seq = count(1)


def _n() -> int:
    return next(_seq)


class _EntityFactory[T](DataclassFactory[T]):
    __is_base_factory__ = True
    __use_defaults__ = True  # keep the dataclass defaults: state=ENABLED, events=(), audit=Audit() ...
    __check_model__ = False

    org_uuid = ORG


class RoleFactory(_EntityFactory[Role]):
    role_uuid = Use(lambda: f"role-{_n()}")
    tenant_uuid = TENANT
    role_code = Use(lambda: Code(f"role_{_n()}"))
    role_name = Use(lambda: f"Role {_n()}")


class PermissionFactory(_EntityFactory[Permission]):
    permission_uuid = Use(lambda: f"perm-{_n()}")
    perm_code = Use(lambda: Code(f"resource{_n()}:read"))
    perm_name = Use(lambda: f"Permission {_n()}")


class MenuFactory(_EntityFactory[Menu]):
    menu_uuid = Use(lambda: f"menu-{_n()}")
    menu_code = Use(lambda: Code(f"menu_{_n()}"))
    menu_name = Use(lambda: f"Menu {_n()}")

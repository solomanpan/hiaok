"""Aggregates that only need the standard lifecycle."""

from ...domain.entity import Permission, Project, Tenant
from .base import CrudService


class TenantService(CrudService[Tenant]):
    entity = "Tenant"


class ProjectService(CrudService[Project]):
    entity = "Project"


class PermissionService(CrudService[Permission]):
    entity = "Permission"

from fastapi import APIRouter, status

from ..dependency import PageDep, TenantCrudDep
from ..exception import unwrap
from ..schema.common import PageResponse
from ..schema.tenant import TenantCreateRequest, TenantResponse, TenantUpdateRequest

router = APIRouter(prefix="/orgs/{org_uuid}/tenants", tags=["tenant"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tenant(org_uuid: str, body: TenantCreateRequest, uc: TenantCrudDep) -> TenantResponse:
    return unwrap(await uc.create(body.to_command(org_uuid)), TenantResponse.of)


@router.get("")
async def list_tenants(org_uuid: str, page: PageDep, uc: TenantCrudDep) -> PageResponse[TenantResponse]:
    return PageResponse.of(await uc.list(org_uuid, page), TenantResponse.of)


@router.get("/{tenant_uuid}")
async def get_tenant(org_uuid: str, tenant_uuid: str, uc: TenantCrudDep) -> TenantResponse:
    return unwrap(await uc.get(org_uuid, tenant_uuid), TenantResponse.of)


@router.patch("/{tenant_uuid}")
async def update_tenant(
    org_uuid: str, tenant_uuid: str, body: TenantUpdateRequest, uc: TenantCrudDep
) -> TenantResponse:
    return unwrap(await uc.update(org_uuid, tenant_uuid, body.to_command()), TenantResponse.of)


@router.delete("/{tenant_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(org_uuid: str, tenant_uuid: str, uc: TenantCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, tenant_uuid), lambda _: None)

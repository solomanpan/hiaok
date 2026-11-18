from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from ...application.model import CreateOrganization, OrganizationModel, OrgDetailModel, UpdateOrganization
from .common import EntityResponse, MetaRequest, MetaUpdateRequest


class OrgDetailDTO(BaseModel):
    """Used both as request and response body."""

    legal_name: str | None = Field(default=None, max_length=255)
    registration_no: str | None = Field(default=None, max_length=64)
    address: str | None = Field(default=None, max_length=512)
    postal_code: str | None = Field(default=None, max_length=16)
    contact_name: str | None = Field(default=None, max_length=128)
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=255)

    model_config = {"from_attributes": True}

    def to_model(self) -> OrgDetailModel:
        return OrgDetailModel(**self.model_dump())


class OrganizationCreateRequest(MetaRequest):
    org_code: str = Field(..., examples=["ACME"])
    org_name: str = Field(..., examples=["Acme Inc."])
    detail: OrgDetailDTO = Field(default_factory=lambda: OrgDetailDTO())

    def to_command(self) -> CreateOrganization:
        return CreateOrganization(
            org_code=self.org_code,
            org_name=self.org_name,
            detail=self.detail.to_model(),
            description=self.description,
            remark=self.remark,
        )


class OrganizationUpdateRequest(MetaUpdateRequest):
    org_name: str | None = None

    def to_command(self) -> UpdateOrganization:
        return UpdateOrganization(**self.model_dump())


class OrganizationResponse(EntityResponse):
    org_code: str
    org_name: str
    detail: OrgDetailDTO

    @classmethod
    def of(cls, m: OrganizationModel) -> OrganizationResponse:
        return cls.model_validate(m)

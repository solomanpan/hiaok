"""Authentication / authorization models: the login token's session and the resolved principal."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from ...domain.service import authority


@dataclass(frozen=True)
class LoginCommand:
    org_uuid: str
    tenant_uuid: str
    username: str
    password: str

    def __repr__(self) -> str:
        return f"LoginCommand(org_uuid={self.org_uuid!r}, tenant_uuid={self.tenant_uuid!r}, username={self.username!r})"


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    expires_in: int
    user_uuid: str


@dataclass(frozen=True)
class Session:
    """What a login token stands for."""

    user_uuid: str
    org_uuid: str
    tenant_uuid: str

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> Session:
        return cls(**json.loads(raw))


@dataclass(frozen=True)
class GrantedAuthorities:
    """The cacheable part of a user's authorities (menus are not needed to authorize a call)."""

    role_codes: tuple[str, ...]
    permission_codes: tuple[str, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> GrantedAuthorities:
        data = json.loads(raw)
        return cls(tuple(data["role_codes"]), tuple(data["permission_codes"]))


@dataclass(frozen=True)
class Principal:
    """The authenticated caller. ``*`` among the permission codes grants everything (incl. every role check)."""

    user_uuid: str
    org_uuid: str
    tenant_uuid: str
    role_codes: frozenset[str]
    permission_codes: frozenset[str]

    @classmethod
    def of(cls, session: Session, granted: GrantedAuthorities) -> Principal:
        return cls(
            session.user_uuid,
            session.org_uuid,
            session.tenant_uuid,
            frozenset(granted.role_codes),
            frozenset(granted.permission_codes),
        )

    @property
    def is_superuser(self) -> bool:
        return "*" in self.permission_codes

    def has_permission(self, *required: str) -> bool:
        """Any of ``required`` (``role:*`` covers ``role:add``)."""
        return any(authority.is_granted(self.permission_codes, code) for code in required)

    def has_role(self, *required: str) -> bool:
        """Any of ``required`` role codes."""
        return self.is_superuser or any(code in self.role_codes for code in required)

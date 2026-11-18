"""Login sessions and the cached authorities, both kept in the shared cache.

* ``session:<sha256(token)>``            -> Session            (TTL = session lifetime; delete = log out)
* ``authz:<org>:<version>:<user>``       -> GrantedAuthorities (TTL = authority lifetime)
* ``authz_ver:<org>``                    -> version            (changing it evicts every cached user of the org)
"""

from __future__ import annotations

import hashlib
import secrets
import uuid

from expression import Option, Some, option
from hiaok_core.facade import Cache

from ..model import GrantedAuthorities, Session

_VERSION_TTL = 86_400  # outlives any authority TTL (config caps it at one day)


def _session_key(token: str) -> str:
    return f"session:{hashlib.sha256(token.encode()).hexdigest()}"


def _version_key(org_uuid: str) -> str:
    return f"authz_ver:{org_uuid}"


class AuthService:
    def __init__(self, cache: Cache, session_ttl: int = 7200, authority_ttl: int = 60) -> None:
        self._cache = cache
        self.session_ttl = session_ttl
        self._authority_ttl = authority_ttl

    # ---- sessions ----
    async def issue(self, session: Session) -> str:
        token = secrets.token_urlsafe(32)
        await self._cache.set(_session_key(token), session.to_json(), self.session_ttl)
        return token

    async def resolve(self, token: str) -> Option[Session]:
        raw = await self._cache.get(_session_key(token))
        return Some(Session.from_json(raw.value)) if raw.is_some() else option.NOTHING

    async def revoke(self, token: str) -> None:
        await self._cache.delete(_session_key(token))

    # ---- authorities ----
    async def _authority_key(self, org_uuid: str, user_uuid: str) -> str:
        version = await self._cache.get(_version_key(org_uuid))
        return f"authz:{org_uuid}:{version.value if version.is_some() else '0'}:{user_uuid}"

    async def cached_authorities(self, org_uuid: str, user_uuid: str) -> Option[GrantedAuthorities]:
        raw = await self._cache.get(await self._authority_key(org_uuid, user_uuid))
        return Some(GrantedAuthorities.from_json(raw.value)) if raw.is_some() else option.NOTHING

    async def cache_authorities(self, org_uuid: str, user_uuid: str, granted: GrantedAuthorities) -> None:
        await self._cache.set(await self._authority_key(org_uuid, user_uuid), granted.to_json(), self._authority_ttl)

    async def invalidate_authorities(self, org_uuid: str) -> None:
        await self._cache.set(_version_key(org_uuid), uuid.uuid4().hex, _VERSION_TTL)

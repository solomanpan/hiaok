"""One-time captcha challenges. The answer lives in the cache under a random id and is consumed by the first check."""

from __future__ import annotations

import hmac
import secrets
import uuid

from hiaok_core.facade import Cache

# no 0/O/1/I/L: easy to confuse in a distorted image
ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LENGTH = 4


def _key(captcha_id: str) -> str:
    return f"captcha:{captcha_id}"


class CaptchaService:
    def __init__(self, cache: Cache, ttl_seconds: int = 120) -> None:
        self._cache = cache
        self.ttl_seconds = ttl_seconds

    async def issue(self) -> tuple[str, str]:
        """-> (captcha_id, code). The code is only shown to the client as an image."""
        captcha_id = uuid.uuid4().hex
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        await self._cache.set(_key(captcha_id), code, self.ttl_seconds)
        return captcha_id, code

    async def verify(self, captcha_id: str | None, answer: str | None) -> bool:
        """Consumes the challenge: a second attempt with the same id fails even when the answer was right."""
        if not captcha_id or not answer:
            return False
        stored = await self._cache.get(_key(captcha_id))
        await self._cache.delete(_key(captcha_id))
        if stored.is_none():
            return False
        return hmac.compare_digest(stored.value.upper().encode(), answer.strip().upper().encode())

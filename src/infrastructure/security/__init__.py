"""PasswordHasher adapter: scrypt from the standard library (no extra dependency)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os


class ScryptPasswordHasher:
    def __init__(self, n: int = 2**14, r: int = 8, p: int = 1) -> None:
        self._n, self._r, self._p = n, r, p

    def hash(self, raw: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.scrypt(raw.encode(), salt=salt, n=self._n, r=self._r, p=self._p, dklen=32)
        b64 = base64.b64encode
        return f"scrypt${self._n}${self._r}${self._p}${b64(salt).decode()}${b64(digest).decode()}"

    def verify(self, raw: str, hashed: str) -> bool:
        try:
            _, n, r, p, salt, digest = hashed.split("$")
            expected = base64.b64decode(digest)
            actual = hashlib.scrypt(
                raw.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected)
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(actual, expected)

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class PageQuery:
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True)
class Page[T]:
    items: tuple[T, ...]
    total: int
    offset: int
    limit: int

    def map[U](self, f: Callable[[T], U]) -> Page[U]:
        return Page(tuple(f(i) for i in self.items), self.total, self.offset, self.limit)

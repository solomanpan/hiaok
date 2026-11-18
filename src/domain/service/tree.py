"""Pure tree helpers for self-referencing aggregates (menu / department / user_group)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from expression import Ok, Result
from hiaok_core.exception import DomainError
from hiaok_core.factory import ErrorCatalog, ErrorSpec
from toolz import groupby


class TreeErrors(ErrorCatalog):
    parent_not_found = ErrorSpec.validation("parent_not_found", "parent '{parent}' not found")
    cycle = ErrorSpec.validation("tree_cycle", "the new parent is inside the node's own subtree")


@dataclass(frozen=True)
class TreeNode[T]:
    item: T
    children: tuple[TreeNode[T], ...] = field(default=())


def build_tree[T](
    items: Iterable[T],
    key: Callable[[T], str],
    parent: Callable[[T], str | None],
    sort_key: Callable[[T], int | str] = lambda _: 0,
) -> list[TreeNode[T]]:
    """Orphans (parent not in ``items``) become roots, so filtered subsets still render."""
    nodes = list(items)
    present = {key(n) for n in nodes}
    by_parent = groupby(lambda n: parent(n) if parent(n) in present else None, nodes)

    def grow(parent_key: str | None) -> tuple[TreeNode[T], ...]:
        children = sorted(by_parent.get(parent_key, []), key=sort_key)
        return tuple(TreeNode(c, grow(key(c))) for c in children)

    return list(grow(None))


def ensure_no_cycle[T](
    items: Iterable[T],
    key: Callable[[T], str],
    parent: Callable[[T], str | None],
    node_key: str,
    new_parent_key: str | None,
) -> Result[None, DomainError]:
    """Moving ``node_key`` under ``new_parent_key`` must not put it below its own subtree."""
    parents = {key(i): parent(i) for i in items}
    if new_parent_key is not None and new_parent_key not in parents:
        return TreeErrors.parent_not_found.err(parent=new_parent_key)
    current = new_parent_key
    seen: set[str] = set()
    while current is not None and current not in seen:
        if current == node_key:
            return TreeErrors.cycle.err()
        seen.add(current)
        current = parents.get(current)
    return Ok(None)

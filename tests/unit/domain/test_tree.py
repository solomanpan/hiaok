from dataclasses import dataclass

from support import err

from src.domain.service.tree import build_tree, ensure_no_cycle


@dataclass(frozen=True)
class N:
    id: str
    parent: str | None
    order: int = 0


def _key(n):
    return n.id


def _parent(n):
    return n.parent


#   a ── b ── c
#   └─── d
NODES = [N("a", None), N("b", "a", 2), N("c", "b"), N("d", "a", 1)]


def test_build_tree_sorts_children():
    [root] = build_tree(NODES, _key, _parent, lambda n: n.order)
    assert root.item.id == "a"
    assert [c.item.id for c in root.children] == ["d", "b"]
    assert root.children[1].children[0].item.id == "c"


def test_orphans_become_roots():
    roots = build_tree([N("c", "b"), N("x", None)], _key, _parent)
    assert {r.item.id for r in roots} == {"c", "x"}


def test_cycle_detection():
    assert err(ensure_no_cycle(NODES, _key, _parent, "a", "c")).code == "tree_cycle"
    assert err(ensure_no_cycle(NODES, _key, _parent, "b", "b")).code == "tree_cycle"
    assert ensure_no_cycle(NODES, _key, _parent, "c", "d").is_ok()
    assert ensure_no_cycle(NODES, _key, _parent, "c", None).is_ok()
    assert err(ensure_no_cycle(NODES, _key, _parent, "c", "zz")).code == "parent_not_found"

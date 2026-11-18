"""Layering rules of the project, enforced on every test run.

presentation -> application -> domain <- infrastructure        (everything may use hiaok_core, an external package)
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def _imports(path: Path) -> set[str]:
    """Absolute module names imported by ``path``; relative imports are resolved against its package."""
    package = list(path.relative_to(ROOT).with_suffix("").parts[:-1])
    tree = ast.parse(path.read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                found.add(node.module or "")
            else:
                base = package[: len(package) - (node.level - 1)]
                found.add(".".join([*base, *([node.module] if node.module else [])]))
    return found


def _violations(package: Path, forbidden: tuple[str, ...]) -> list[str]:
    bad = []
    for path in package.rglob("*.py"):
        for module in _imports(path):
            if module.startswith(forbidden):
                bad.append(f"{path.relative_to(ROOT)} imports {module}")
    return bad


@pytest.mark.parametrize(
    ("layer", "forbidden"),
    [
        ("domain", ("src.application", "src.infrastructure", "src.presentation", "fastapi", "sqlalchemy")),
        ("application", ("src.infrastructure", "src.presentation", "fastapi", "sqlalchemy")),
        ("infrastructure", ("src.presentation", "fastapi")),
    ],
)
def test_layer_dependencies(layer, forbidden):
    assert _violations(SRC / layer, forbidden) == []


@pytest.mark.parametrize(
    ("layer", "allowed"),
    [
        ("domain", {"entity", "vo", "enum", "service", "repository"}),
        ("application", {"service", "usecase", "config", "model"}),
        ("presentation", {"endpoint", "schema", "dependency"}),
    ],
)
def test_layer_packages(layer, allowed):
    packages = {p.name for p in (SRC / layer).iterdir() if p.is_dir() and p.name != "__pycache__"}
    assert packages == allowed


def test_no_port_po_or_mapper_naming():
    names = {p.name for p in SRC.rglob("*") if p.name != "__pycache__"}
    assert not names & {"port", "ports", "po", "mapper", "shared"}


def test_src_is_the_package():
    """``src/`` itself is the package (no nested ``src/hiaok/``)."""
    assert (SRC / "__init__.py").exists() and not (SRC / "hiaok").exists()


def test_package_internal_imports_are_relative():
    """Inside ``src`` imports are relative (``from ..domain import ...``); only alembic's env.py is absolute."""
    offenders = []
    for path in SRC.rglob("*.py"):
        if path.name == "env.py" and "migrations" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom) and node.level == 0
                else []
            )
            offenders += [f"{path.relative_to(ROOT)}: {n}" for n in names if n == "src" or n.startswith("src.")]
    assert offenders == []


def test_data_objects_are_named_do():
    from src.infrastructure import do

    assert do.__all__ and all(name.endswith("DO") for name in do.__all__)


def test_every_entity_dao_converts_both_ways():
    from src.infrastructure import dao
    from src.infrastructure.dao import EntityDao, LinkDao

    for name in dao.__all__:
        cls = getattr(dao, name)
        if cls in (dao.BaseDao, EntityDao, LinkDao) or issubclass(cls, LinkDao):
            continue
        assert issubclass(cls, EntityDao), f"{name} must extend EntityDao (to_entity / to_do)"

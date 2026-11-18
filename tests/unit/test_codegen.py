"""scripts/codegen.py: name helpers, spec context, rendering, overwrite protection."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("codegen", ROOT / "scripts" / "codegen.py")
assert _spec and _spec.loader
codegen = importlib.util.module_from_spec(_spec)
sys.modules["codegen"] = codegen  # dataclasses look their module up in sys.modules
_spec.loader.exec_module(codegen)


@pytest.mark.parametrize(
    ("raw", "snake", "pascal", "camel", "kebab"),
    [
        ("UserGroup", "user_group", "UserGroup", "userGroup", "user-group"),
        ("user_group", "user_group", "UserGroup", "userGroup", "user-group"),
        ("user-group", "user_group", "UserGroup", "userGroup", "user-group"),
        ("menu", "menu", "Menu", "menu", "menu"),
    ],
)
def test_name_helpers(raw, snake, pascal, camel, kebab):
    assert (codegen.snake(raw), codegen.pascal(raw), codegen.camel(raw), codegen.kebab(raw)) == (
        snake,
        pascal,
        camel,
        kebab,
    )


@pytest.mark.parametrize(("raw", "plural"), [("menu", "menus"), ("category", "categories"), ("box", "boxes")])
def test_plural(raw, plural):
    assert codegen.plural(raw) == plural


def test_context_derives_names_and_keeps_the_module_table():
    ctx = codegen.load_context(ROOT / "codegen" / "specs" / "example.toml")
    assert (ctx["class_name"], ctx["snake_name"], ctx["plural_name"]) == ("SampleItem", "sample_item", "sample_items")
    assert ctx["module"]["table"] == "sample_item" and len(ctx["fields"]) == 3


def test_example_set_renders_valid_python():
    ctx = codegen.load_context(ROOT / "codegen" / "specs" / "example.toml")
    [out] = codegen.render_set(ROOT / "codegen" / "templates" / "example", ctx)
    assert out.target == ROOT / "src" / "domain" / "entity" / "sample_item.py"
    assert not out.target.exists()  # the example must never collide with a real module
    ast.parse(out.content)
    assert "class SampleItem(AggregateRoot):" in out.content
    assert "owner_user_uuid: str | None = None" in out.content
    assert "sample_item_uuid: str" in out.content
    assert "from ..vo import Code" in out.content


def test_undefined_variables_fail_loudly(tmp_path):
    (tmp_path / "x.txt.j2").write_text("{{ no_such_var }}")
    with pytest.raises(Exception, match="no_such_var"):
        codegen.render_set(tmp_path, {})


def test_never_overwrites_without_force(tmp_path, monkeypatch):
    monkeypatch.setattr(codegen, "ROOT", tmp_path)
    target = tmp_path / "a.txt"
    target.write_text("keep me")
    files = [codegen.Rendered(target, "new")]
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        codegen.write(files, force=False)
    assert target.read_text() == "keep me"
    codegen.write(files, force=True)
    assert target.read_text() == "new"

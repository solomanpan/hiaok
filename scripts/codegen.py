"""Render a template set (jinja2) from a module spec (TOML) into the project.

    uv run python scripts/codegen.py codegen/specs/project.toml                 # template set from the spec
    uv run python scripts/codegen.py codegen/specs/project.toml --set aggregate # explicit template set
    uv run python scripts/codegen.py codegen/specs/project.toml --dry-run       # list what would be written
    uv run python scripts/codegen.py codegen/specs/project.toml --force         # overwrite existing files

Template sets live in ``codegen/templates/<set>/``. Their directory tree mirrors the project; file *and* directory
names are templates too, and the ``.j2`` suffix is dropped: ``src/domain/entity/{{ snake_name }}.py.j2`` ->
``src/domain/entity/project.py``. See ``codegen/README.md`` for the context available to templates.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "codegen" / "templates"


# ---------------------------------------------------------------- name helpers (also jinja filters)
def snake(name: str) -> str:
    """``UserGroup`` / ``userGroup`` / ``user-group`` -> ``user_group``"""
    name = re.sub(r"[-\s]+", "_", name)
    name = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    return name.lower()


def pascal(name: str) -> str:
    """``user_group`` -> ``UserGroup``"""
    return "".join(part[:1].upper() + part[1:] for part in snake(name).split("_"))


def camel(name: str) -> str:
    """``user_group`` -> ``userGroup``"""
    p = pascal(name)
    return p[:1].lower() + p[1:]


def kebab(name: str) -> str:
    """``user_group`` -> ``user-group``"""
    return snake(name).replace("_", "-")


def plural(name: str) -> str:
    """Naive English plural for route names: ``menu`` -> ``menus``, ``category`` -> ``categories``."""
    if name.endswith("y") and name[-2:-1] not in "aeiou":
        return name[:-1] + "ies"
    if name.endswith(("s", "x", "ch", "sh")):
        return name + "es"
    return name + "s"


FILTERS = {"snake": snake, "pascal": pascal, "camel": camel, "kebab": kebab, "plural": plural}


# ---------------------------------------------------------------- spec -> context
def load_context(spec_path: Path) -> dict[str, Any]:
    """The whole TOML document is the context, plus derived names when ``[module] name`` is given."""
    spec = tomllib.loads(spec_path.read_text(encoding="utf-8"))
    module = spec.get("module", {})
    if "name" in module:
        name = module["name"]
        derived = {
            "class_name": pascal(name),
            "snake_name": snake(name),
            "kebab_name": kebab(name),
            "plural_name": plural(snake(name)),
        }
        spec = {**derived, **spec}  # explicit values in the spec win over derived ones
    spec.setdefault("fields", [])
    return spec


def make_env(template_set: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(template_set),
        undefined=StrictUndefined,  # a typo in a template fails loudly instead of rendering ""
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(FILTERS)
    return env


# ---------------------------------------------------------------- render
@dataclass(frozen=True)
class Rendered:
    target: Path
    content: str


def render_set(template_set: Path, context: dict[str, Any]) -> list[Rendered]:
    env = make_env(template_set)
    out: list[Rendered] = []
    for source in sorted(template_set.rglob("*.j2")):
        relative = source.relative_to(template_set).as_posix()
        target = env.from_string(relative[: -len(".j2")]).render(context)
        content = env.get_template(relative).render(context)
        out.append(Rendered(ROOT / target, content))
    return out


def write(files: list[Rendered], *, force: bool) -> list[Path]:
    existing = [f.target for f in files if f.target.exists()]
    if existing and not force:
        listing = "\n  ".join(str(p.relative_to(ROOT)) for p in existing)
        raise SystemExit(f"refusing to overwrite (use --force):\n  {listing}")
    for f in files:
        f.target.parent.mkdir(parents=True, exist_ok=True)
        f.target.write_text(f.content, encoding="utf-8")
    return [f.target for f in files]


def format_python(paths: list[Path]) -> None:
    py = [str(p) for p in paths if p.suffix == ".py"]
    if not py:
        return
    for cmd in (["ruff", "check", "--fix", "-q", *py], ["ruff", "format", "-q", *py]):
        try:
            subprocess.run([sys.executable, "-m", *cmd], cwd=ROOT, check=False)
        except FileNotFoundError:  # pragma: no cover - ruff missing: leave the files unformatted
            return


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", type=Path, help="module spec (TOML)")
    parser.add_argument(
        "--set", dest="template_set", help="template set under codegen/templates (default: spec's `template`)"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the files that would be written")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    args = parser.parse_args(argv)

    context = load_context(args.spec)
    name = args.template_set or context.get("template")
    if not name:
        raise SystemExit('no template set: pass --set or put `template = "..."` at the top of the spec')
    template_set = TEMPLATES / name
    if not template_set.is_dir():
        raise SystemExit(f"template set not found: {template_set.relative_to(ROOT)}")

    files = render_set(template_set, context)
    if args.dry_run:
        for f in files:
            mark = "overwrite" if f.target.exists() else "create"
            print(f"{mark:9} {f.target.relative_to(ROOT)}")
        return
    written = write(files, force=args.force)
    format_python(written)
    for path in written:
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
